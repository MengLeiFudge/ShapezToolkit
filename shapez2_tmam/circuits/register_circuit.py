"""用写入、重叠和保持三个阶段锁存任意信号的原生寄存器。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Literal


def build_register(channel_base: int = 1_012_000) -> tuple[Circuit, dict]:
    """分离上料与保持控制，避免单选锁存在关闭写入时产生循环空洞。"""
    if not 1 <= channel_base < (1 << 24) - 256:
        raise ValueError("频道基址需要为实例保留后续256个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    data = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    load = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    retain = circuit.add("ControlledSignalReceiver", Literal(channel_base + 2))
    incoming = circuit.add("LogicGateIf", data, load)
    stored = circuit.add("LogicGateIf", incoming, retain)
    # 重叠阶段两路都发布同一值；保持阶段只有反馈路，空信号仍可被保存。
    circuit.aliases.append((incoming, stored))
    channels = circuit.channel_map()
    report = {
        "component": "signal_register",
        "inputs": {"data": channel_base, "load": channel_base + 1, "retain": channel_base + 2},
        "outputs": {"value": channels[incoming]},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 255],
        "write_protocol": [
            {"phase": "load", "load": 1, "retain": 0, "hold_signal_ticks": 512},
            {"phase": "overlap", "load": 1, "retain": 1, "hold_signal_ticks": 512},
            {"phase": "retain", "load": 0, "retain": 1, "hold_signal_ticks": 512}],
        "data_hold": "data 在三个写入阶段均保持为同一值；第三阶段结束后才可复用数据总线。",
        "initialization": "首次使用前完整执行一次写入；清零可写整数0，清空可写空信号。",
        "idle": "load=0、retain=1 持续保持；load=0、retain=0 会清空寄存器。",
        "scope": "保存整数、图形、颜色及空信号；不包含地址选择器、时钟或阶段控制器。",
        "proof": "4q5l/register-circuit.md；仅本机Hybrid/AlwaysHighUPS常速连续推进与固定接线；不适用于调试单步、模式切换、强制低UPS或快进。",
        "timing": "反馈网络不调用组合 DAG 保持期；按明确的三阶段写入协议使用，无完成脉冲。",
        "verification": "静态端口、实际占地与几何网络核对；未运行写入循环、门级模拟或游戏",
    }
    return circuit, report


def main() -> int:
    """编译生产寄存器及频道说明，不执行反馈或写入模拟。"""
    parser = argparse.ArgumentParser(description="生成具有三阶段写入协议的任意信号寄存器")
    parser.add_argument("--channel-base", type=int, default=1_012_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_register(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"信号寄存器已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
