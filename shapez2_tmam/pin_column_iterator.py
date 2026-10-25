"""自动遍历顶针单列候选的八个控制位，复用一份结构数据通路。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Gate, Literal
from .half_circuit import _combine
from .pin_column_circuit import column_candidate
from .sequential_circuit import clock, latch, select, timing_contract


def build_pin_iterator(channel_base: int = 1_022_000) -> tuple[Circuit, dict]:
    """主副计数状态生成每轮一个控制字，阶段3只发布通过本地约束的候选。"""
    if not 1 <= channel_base < (1 << 24) - 2048:
        raise ValueError("频道基址需要为实例保留后续2048个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    materials = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 2 * z)) for z in range(5))
    tags = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 2 * z + 1)) for z in range(5))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 10))
    timing = clock(circuit, enable, phase_steps=13)
    reset = circuit.add("LogicGateNot", enable)
    master_load = circuit.add("LogicGateOr", timing.phases[0], reset)
    slave_load = circuit.add("LogicGateOr", timing.phases[2], reset)
    initial_values = (0,) * 8 + (1,)
    masters = []
    state = []
    for initial in initial_values:
        master = latch(circuit, Literal(initial), master_load)
        slave_data = select(circuit, enable, master, Literal(initial))
        masters.append(master)
        state.append(latch(circuit, slave_data, slave_load))
    active = state[-1]
    carry = active
    next_values = []
    for bit in state[:8]:
        next_values.append(circuit.add("LogicGateXOr", bit, carry))
        carry = circuit.add("LogicGateAnd", bit, carry)
    next_values.append(circuit.add("LogicGateAnd", active, circuit.add("LogicGateNot", carry)))
    for master, next_value, initial in zip(masters, next_values, initial_values):
        data = select(circuit, enable, next_value, Literal(initial))
        pending = circuit.gates[master.node]
        circuit.gates[master.node] = Gate(pending.kind, (data, pending.inputs[1]), pending.config)
    candidate = column_candidate(circuit, materials, tags, tuple(state[:8]), enable)
    valid = circuit.add("LogicGateAnd", candidate.valid, active)
    captured = []
    for source in (*candidate.materials, *candidate.tags, valid):
        data = select(circuit, enable, source, Literal(0))
        master = latch(circuit, data, master_load)
        captured.append(latch(circuit, master, slave_load))
    # 阶段2后计数已加一；平衡前缀借位恢复本轮控制字，省掉八对快照寄存器。
    inverted = [circuit.add("LogicGateNot", bit) for bit in state[:8]]
    word = [inverted[0]]
    for index in range(1, 8):
        borrow = _combine(circuit, "LogicGateAnd", inverted[:index])
        word.append(circuit.add("LogicGateXOr", state[index], borrow))
    window = circuit.add("LogicGateAnd", timing.phases[3], enable)
    sample = circuit.add("LogicGateAnd", window, captured[-1])
    exhausted = circuit.add("LogicGateAnd", window, circuit.add("LogicGateNot", active))
    published = [circuit.add("LogicGateIf", value, sample) for value in captured[:8]]
    published_word = [circuit.add("LogicGateIf", value, sample) for value in word]
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 2047:
        raise ValueError("顶针单列迭代器超出其保留频道范围")
    return circuit, {
        "component": "pin_column_iterator", "quadrants": 4, "height": 5,
        "inputs": {"target_bottom_to_top": [{"material": channel_base + 2 * z, "tag": channel_base + 2 * z + 1} for z in range(5)],
                   "enable": channel_base + 10},
        "outputs": {"sample": channels[sample], "exhausted": channels[exhausted],
                    "source_bottom_four": [{"material": channels[kind], "tag": channels[tag]}
                                           for kind, tag in zip(published[:4], published[4:])],
                    "control_word_bits_low_to_high": [channels[bit] for bit in published_word]},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 2047],
        "timing": timing_contract(timing),
        "input_protocol": "五格材料/标签在整个读取期间保持不变；enable=0完成复位后改为1。材料0空/1普通/2针/3晶体，标签合同同pin-column-4q5l。",
        "sample_protocol": "每个阶段3最多一份本地有效候选。输出端sample上升后再等24信号tick，在窗口内只采一次；sample为假继续等后续窗口。",
        "termination": "依次处理控制字0～255，256轮后exhausted在阶段3为真，之后不再发布sample。耗尽不代表完整目标不可制作。",
        "resource_bound": "一份单列数据通路、八个二进制计数位、一个活动位、九项结果的主副锁存；不保存256份候选或完整半形目录。",
        "time_bound": "每轮52模拟秒，256轮约3小时42分；这是当前保守参数的整列遍历界，尚未优化为实用搜索等待时间。",
        "scope": "自动单列结构候选流；不含四列笛卡尔组合、第五层补全、递归回退、制造配方流或完整可制作性判定。",
        "proof": "4q5l/pin-column-circuit.md；四阶段控制使用该文的三阶段传播界。",
        "verification": "静态端口、实际占地与几何网络核对；未运行目标、枚举循环、门级模拟或游戏",
    }


def main() -> int:
    """编译自动单列候选蓝图及频道表，不运行遍历循环。"""
    parser = argparse.ArgumentParser(description="生成自动循环的顶针单列候选迭代器")
    parser.add_argument("--channel-base", type=int, default=1_022_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_pin_iterator(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"顶针单列迭代器已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
