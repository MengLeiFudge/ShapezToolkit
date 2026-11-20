"""自动循环调用一份拆层测高通路，输出保留原层号的层流。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Gate, Literal, Ref, constant
from .scan_circuit import scan_step
from .sequential_circuit import clock, latch, select, timing_contract


def build_scanner(channel_base: int = 1_014_000) -> tuple[Circuit, dict]:
    """主副寄存器分阶段写入；原目标仅在复位期间装载。"""
    if not 1 <= channel_base < (1 << 24) - 1024:
        raise ValueError("频道基址需要为实例保留后续1024个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    timing = clock(circuit, enable, phase_steps=8)
    reset = circuit.add("LogicGateNot", enable)
    master_load = circuit.add("LogicGateOr", timing.phases[0], reset)
    slave_load = circuit.add("LogicGateOr", timing.phases[2], reset)
    master_working = latch(circuit, Literal(None), master_load)
    slave_data = select(circuit, enable, master_working, target)
    working = latch(circuit, slave_data, slave_load)
    always = circuit.add("ConstantSignal", config=constant(1))
    scanned = scan_step(circuit, working, always)
    next_working = select(circuit, enable, scanned.lower, target)
    # 此处闭合真实无线反馈；latch返回的就是写入IF的输出节点。
    pending = circuit.gates[master_working.node]
    circuit.gates[master_working.node] = Gate(pending.kind, (next_working, pending.inputs[1]), pending.config)
    captured = []
    for source, initial in ((scanned.top, None), (scanned.original_layer, None), (scanned.valid, 0)):
        data = select(circuit, enable, source, Literal(initial))
        master = latch(circuit, data, master_load)
        captured.append(latch(circuit, master, slave_load))
    captured_top, captured_layer, captured_valid = captured
    original_split = circuit.add("VirtualUnstacker", target)
    original_exists = circuit.add("LogicGateCompare", Ref(original_split.node, 1), Literal(None), config="Bg==")
    input_valid = circuit.add("LogicGateAnd", original_exists, enable)
    window = circuit.add("LogicGateAnd", timing.phases[3], input_valid)
    sample = circuit.add("LogicGateAnd", window, captured_valid)
    empty = circuit.add("LogicGateCompare", working, Literal(None), config="AQ==")
    done = circuit.add("LogicGateAnd", window, empty)
    top = circuit.add("LogicGateIf", captured_top, sample)
    original_layer = circuit.add("LogicGateIf", captured_layer, sample)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 1023:
        raise ValueError("自动扫描部件超出其保留频道范围")
    return circuit, {
        "component": "iterative_layer_scanner", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": {"sample": channels[sample], "top": channels[top],
                    "original_layer": channels[original_layer], "done": channels[done],
                    "remaining": channels[working]},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 1023],
        "timing": timing_contract(timing),
        "input_protocol": "保持target不变，enable=0完成复位后改为1。读取期间保持target与enable；再次输入须重新复位。",
        "sample_protocol": "每周期阶段3提供一份top及其1～5原层号；sample高电平为有效窗口，只读取一次，不按每个tick重复读取。输出末端在sample上升后再等24信号tick，仍在该窗口内时采样。",
        "done_protocol": "done在最后一份有效层所在阶段3开始为真，此后各阶段3重复为真。先接收本窗口sample对应的层，再处理done；done不是可制作性结论。",
        "termination": "每轮去掉最高非空层，最多五轮；之后sample持续为假。原始空底层和中间空层不会被当作非空原料。",
        "scope": "输入任意非空四象限五层图形，自动拆成至多五份原层位的层流；不判断目标可制作性，不输出完整制造配方。",
        "proof": "4q5l/clocked-control.md、4q5l/iterative-scanner.md",
        "verification": "静态端口、实际占地与几何网络核对；未运行扫描循环、门级模拟或游戏",
    }


def main() -> int:
    """编译自动扫描生产蓝图及频道表，不运行循环。"""
    parser = argparse.ArgumentParser(description="生成自动循环拆层并输出原层号的四象限五层扫描器")
    parser.add_argument("--channel-base", type=int, default=1_014_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_scanner(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"自动层扫描器已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
