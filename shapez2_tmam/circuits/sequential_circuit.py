"""具有精确无线延迟前提的四阶段时钟与信号锁存器。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref


@dataclass(frozen=True)
class Clock:
    """四个等长阶段；停机时保持阶段3，启动后的第一个完整阶段是0。"""

    phases: tuple[Ref, ...]
    wave: Ref
    phase_ticks: int
    reset_ticks: int


def clock(circuit: Circuit, enable: Ref, phase_steps: int = 48) -> Clock:
    """复制链与一次反相形成延迟环；每个 Ref 边精确延迟12信号tick。"""
    if phase_steps < 2:
        raise ValueError("每阶段至少需要两个无线延迟级")
    start = len(circuit.gates)
    wave = Ref(start + 2 * phase_steps - 1)
    delayed = wave
    tap = wave
    for step in range(2 * phase_steps - 2):
        delayed = circuit.add("LogicGateIf", delayed, Literal(1))
        if step + 1 == phase_steps:
            tap = delayed
    inverted = circuit.add("LogicGateNot", delayed)
    output = circuit.add("LogicGateAnd", enable, inverted)
    if output != wave:
        raise RuntimeError("时钟反馈节点编号与延迟链不一致")
    # 四条预处理路径等深，避免直接信号与反相信号错拍。
    high = circuit.add("LogicGateIf", wave, Literal(1))
    low = circuit.add("LogicGateNot", wave)
    delayed_high = circuit.add("LogicGateIf", tap, Literal(1))
    delayed_low = circuit.add("LogicGateNot", tap)
    phases = tuple(circuit.add("LogicGateAnd", a, b) for a, b in (
        (high, delayed_low), (high, delayed_high),
        (low, delayed_high), (low, delayed_low)))
    ticks = phase_steps * 12
    return Clock(phases, wave, ticks, 4 * ticks + 128)


class SignalControl:
    """同一条件的等深正反控制，可供多份选择器或锁存器共用。"""

    def __init__(self, circuit: Circuit, condition: Ref):
        self.circuit = circuit
        self.enabled = circuit.add("LogicGateIf", condition, Literal(1))
        self.disabled = circuit.add("LogicGateNot", condition)

    def select(self, yes: Ref | Literal, no: Ref | Literal) -> Ref:
        """两支各保留一级控制延迟，输出共用互补驱动频道。"""
        first = self.circuit.add("LogicGateIf", yes, self.enabled)
        second = self.circuit.add("LogicGateIf", no, self.disabled)
        self.circuit.aliases.append((first, second))
        return first

    def latch(self, data: Ref | Literal) -> Ref:
        """条件真时写入，否则由独立的本锁存器反馈保持。"""
        incoming = self.circuit.add("LogicGateIf", data, self.enabled)
        retained = self.circuit.add("LogicGateIf", incoming, self.disabled)
        self.circuit.aliases.append((incoming, retained))
        return incoming


def select(circuit: Circuit, condition: Ref, yes: Ref | Literal, no: Ref | Literal) -> Ref:
    """等深控制的任意信号二选一；稳定运行时每tick恰有一个分支被选中。"""
    return SignalControl(circuit, condition).select(yes, no)


def latch(circuit: Circuit, data: Ref | Literal, load: Ref) -> Ref:
    """透明写入、关闭后保持；load与其反相经过相同级数。"""
    return SignalControl(circuit, load).latch(data)


def timing_contract(timing: Clock) -> dict:
    """声明源码证明依赖的导入、更新和复位边界。"""
    return {
        "phase_signal_ticks": timing.phase_ticks,
        "cycle_signal_ticks": 4 * timing.phase_ticks,
        "reset_hold_signal_ticks": timing.reset_ticks,
        "reference_edge_signal_ticks": 12,
        "conditions": "整份蓝图批量导入或完整重载后固定接线；Hybrid/AlwaysHighUPS常速连续推进，每批最多4信号tick；频道独占。调试单步、模式切换、强制低UPS及快进不适用。",
        "reset": "enable=0持续不少于reset_hold_signal_ticks，再一次改为1并保持。复位时阶段3为真；启动先出现一小段阶段3，随后依次完整循环0、1、2、3。",
        "proof": "4q5l/clocked-control.md；精确延迟与锁存器证明不依赖组合DAG保持期。",
    }


def build_clock(channel_base: int = 1_013_000) -> tuple[Circuit, dict]:
    """生成可供后续状态机复用的固定四阶段时钟。"""
    if not 1 <= channel_base < (1 << 24) - 512:
        raise ValueError("频道基址需要为实例保留后续512个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    timing = clock(circuit, enable)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 511:
        raise ValueError("四阶段时钟超出其保留频道范围")
    return circuit, {
        "component": "four_phase_clock",
        "inputs": {"enable": channel_base},
        "outputs": {"phases": [channels[phase] for phase in timing.phases],
                    "wave": channels[timing.wave]},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 511],
        "timing": timing_contract(timing),
        "scope": "四个互斥等长阶段；不包含完整求解、指令存储或运算完成判定。",
        "verification": "静态端口、实际占地与几何网络核对；未运行反馈、门级模拟或游戏",
    }


def main() -> int:
    """编译生产时钟及频道表，不运行时钟或反馈模拟。"""
    parser = argparse.ArgumentParser(description="生成四阶段时序控制时钟")
    parser.add_argument("--channel-base", type=int, default=1_013_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_clock(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"四阶段时钟已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
