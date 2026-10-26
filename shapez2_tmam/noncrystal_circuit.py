"""生成无晶体目标的完整判定与逐层配方电路；含晶体输入返回 unknown。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Literal, Ref
from .synthesis.physics import Rules


def build_noncrystal(quadrants: int, channel_base: int = 1_002_000) -> tuple[Circuit, dict]:
    """用五次拆层和四次虚拟堆叠重建目标，同时检查全部格位没有晶体。"""
    if quadrants not in (4, 6):
        raise ValueError("原生无晶体电路目前限定四或六象限")
    rules = Rules(quadrants)
    if not 1 <= channel_base < (1 << 24) - 1024:
        raise ValueError("频道基址需要为实例保留后续 1024 个频道，并保持低于 2^24")
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    layers = []
    remaining = target
    for _ in range(5):
        split = circuit.add("VirtualUnstacker", remaining)
        layers.append(Ref(split.node, 1))
        remaining = split
    crystals = []
    crystal = rules.parse("cu" + "--" * (quadrants - 1))
    for layer in layers:
        rotated = layer
        for q in range(quadrants):
            if q:
                rotated = circuit.add("VirtualRotator", rotated)
            analyzed = circuit.add("VirtualAnalyzer", rotated)
            crystals.append(circuit.add("LogicGateCompare", analyzed, Literal(crystal), config="AQ=="))
    while len(crystals) > 1:
        crystals = [circuit.add("LogicGateOr", crystals[i], crystals[i + 1])
                    if i + 1 < len(crystals) else crystals[i]
                    for i in range(0, len(crystals), 2)]
    has_crystal = crystals[0]
    reconstructed = layers[-1]
    for layer in reversed(layers[:-1]):
        lower_empty = circuit.add("LogicGateCompare", reconstructed, Literal(None), config="AQ==")
        upper_empty = circuit.add("LogicGateCompare", layer, Literal(None), config="AQ==")
        stacked = circuit.add("VirtualStacker", reconstructed, layer)
        upper_only = circuit.add("LogicGateIf", layer, lower_empty)
        lower_only = circuit.add("LogicGateIf", reconstructed, upper_empty)
        circuit.aliases.append((stacked, upper_only, lower_only))
        reconstructed = stacked
    valid = circuit.add("LogicGateCompare", layers[0], Literal(None), config="Bg==")
    noncrystal = circuit.add("LogicGateNot", has_crystal)
    accepted = circuit.add("LogicGateAnd", valid, noncrystal)
    accepted = circuit.add("LogicGateAnd", accepted, enable)
    matches = circuit.add("LogicGateCompare", reconstructed, target, config="AQ==")
    solved = circuit.add("LogicGateAnd", accepted, matches)
    differs = circuit.add("LogicGateNot", matches)
    unsolvable = circuit.add("LogicGateAnd", accepted, differs)
    unknown = circuit.add("LogicGateAnd", valid, has_crystal)
    unknown = circuit.add("LogicGateAnd", unknown, enable)
    statuses = (circuit.add("LogicGateIf", Literal(1), solved),
                circuit.add("LogicGateIf", Literal(2), unsolvable),
                circuit.add("LogicGateIf", Literal(3), unknown))
    circuit.aliases.append(statuses)
    published = [circuit.add("LogicGateIf", layer, solved) for layer in layers]
    output = circuit.add("LogicGateIf", reconstructed, solved)
    channels = circuit.channel_map()
    report = {
        "component": "noncrystal_solver", "quadrants": quadrants, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": {"status": channels[statuses[0]], "solvable": channels[solved],
                    "unsolvable": channels[unsolvable], "unknown": channels[unknown],
                    "reconstructed": channels[output],
                    "layers_top_to_bottom": [channels[ref] for ref in published]},
        "statuses": {"1": "solved", "2": "unsolvable", "3": "unknown",
                     "null": "输入不是非空图形，或 enable 为假"},
        "recipe": "非空层输出按逆序取基础单层原料，逐层堆叠；空信号跳过。",
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 1023],
        "scope": "无晶体目标的完整判定与配方；含晶体目标返回 unknown。",
        "verification": "静态端口、实际占地与几何网络核对；未运行门级模拟或游戏",
        "timing": "组合电路，无完成脉冲；整组输入保持不少于 settling.hold_signal_ticks。",
        "settling": circuit.settling_bound(),
    }
    return circuit, report


def main() -> int:
    """编译原生蓝图和频道说明，不执行目标求解或门级模拟。"""
    parser = argparse.ArgumentParser(description="生成四/六象限无晶体求解部件")
    parser.add_argument("--quadrants", type=int, choices=(4, 6), required=True)
    parser.add_argument("--channel-base", type=int, default=1_002_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_noncrystal(args.quadrants, args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"无晶体求解部件已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
