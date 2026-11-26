"""供时序控制器复用的单步拆层及原高度解码电路。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref, encode_document
from .wired_module import wired_module
from .decoder_circuit import height_flags


@dataclass(frozen=True)
class ScannedLayer:
    """本次最高层、原层号和保留原坐标的下半。"""

    top: Ref
    lower: Ref
    original_layer: Ref
    valid: Ref


def scan_step(circuit: Circuit, target: Ref, enable: Ref | Literal) -> ScannedLayer:
    """添加一次拆层测高的数据通路，供组合部件与循环控制器共用。"""
    split = circuit.add("VirtualUnstacker", target)
    upper = Ref(split.node, 1)
    exists = circuit.add("LogicGateCompare", upper, Literal(None), config="Bg==")
    valid = circuit.add("LogicGateAnd", exists, enable)
    flags = height_flags(circuit, target, valid)
    heights = tuple(circuit.add("LogicGateIf", Literal(height), flag) for height, flag in enumerate(flags, 1))
    circuit.aliases.append(heights)
    return ScannedLayer(
        circuit.add("LogicGateIf", upper, valid),
        circuit.add("LogicGateIf", split, valid), heights[0], valid)


def build_scan(channel_base: int = 1_011_000) -> tuple[Circuit, dict]:
    """输出原始顶层、下半和顶层原层号；控制器可将下半写回后再次调用。"""
    if not 1 <= channel_base < (1 << 24) - 256:
        raise ValueError("频道基址需要为实例保留后续256个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    scanned = scan_step(circuit, target, enable)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 255:
        raise ValueError("单步扫描部件超出其保留频道范围")
    report = {
        "component": "top_layer_scan", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": {"has_layer": channels[scanned.valid], "top": channels[scanned.top],
                    "lower": channels[scanned.lower], "original_layer": channels[scanned.original_layer]},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 255],
        "scope": "一次扫描最高非空层，保留原坐标的下半及从1开始的原层号；不判断可制作性。",
        "iteration": "保持当前输入并等待 settling；同时锁存 top、original_layer、lower；将锁存的 lower 写回 target 再调用。最多五次。",
        "termination": "has_layer 为假时无可读取层；有效输入的最后一层扫描后 lower 为空。",
        "controller": "本部件只有共用组合数据通路；时钟、寄存器、写回和配方控制器尚未包含。",
        "verification": "静态端口、实际占地与几何网络核对；未运行门级模拟或游戏",
        "timing": "无完成脉冲；整组输入保持不少于 settling.hold_signal_ticks。",
        "settling": circuit.settling_bound(),
    }
    return circuit, report


def main() -> int:
    """编译生产蓝图及频道表，不执行扫描循环或门级模拟。"""
    parser = argparse.ArgumentParser(description="生成时序复用的四象限五层单步扫描部件")
    parser.add_argument("--channel-base", type=int, default=1_011_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_scan(args.channel_base)
    document = wired_module(circuit, report["outputs"])
    report.update(gate_platforms=1, platform_type="Foundation_3x3", global_receivers=2,
                  global_transmitters=4, internal_wireless_channels=0)
    encoded = encode_document(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"单步扫描部件已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
