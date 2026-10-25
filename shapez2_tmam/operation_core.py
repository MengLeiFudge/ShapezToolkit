"""生成四/六象限共用的虚拟加工核心；此核心不判定完整目标可制作性。"""

import argparse
import base64
import json
from pathlib import Path

from .circuit import Circuit, Literal, Ref


OPERATIONS = (
    "copy", "rotate_cw", "rotate_ccw", "rotate_half", "cut_front", "cut_back", "pin", "stack",
    "swap_front_a", "swap_front_b", "crystal", "unstack", "analyze", "paint_top",
)


def build_core(quadrants: int, channel_base: int = 1_000_000) -> tuple[Circuit, dict]:
    """构建共用加工单元及其频道表；输入须保持到组合路径传播完成。

    opcode 为 0～13；a、b 为物品信号，color 为颜色信号，enable 为真才发布。
    primary/secondary 是所选虚拟操作的两个结果，recognized 仅表示 opcode
    被识别且 enable 为真，不表示目标可制作或运算输入类型合法。
    """
    if quadrants not in (4, 6):
        raise ValueError("加工核心需要四或六象限配置")
    if not 1 <= channel_base < (1 << 24) - 512:
        raise ValueError("频道基址需要在 1～16776703 内，并为本实例保留后续 512 个频道")
    circuit = Circuit(channel_base + 32)
    inputs = {name: circuit.add("ControlledSignalReceiver", Literal(channel_base + i))
              for i, name in enumerate(("opcode", "a", "b", "color", "enable"))}
    a, b = inputs["a"], inputs["b"]
    clockwise = circuit.add("VirtualRotator", a)
    counterclockwise = circuit.add("VirtualRotatorCCW", a)
    half = a
    for _ in range(quadrants // 2):
        half = circuit.add("VirtualRotator", half)
    front = circuit.add("VirtualHalfCutter", a)
    back = circuit.add("VirtualHalfCutter", half)
    for _ in range(quadrants // 2):
        back = circuit.add("VirtualRotator", back)
    pin = circuit.add("VirtualPinPusher", a)
    stacked = circuit.add("VirtualStacker", a, b)
    swapped = circuit.add("VirtualHalvesSwapper", a, b)
    crystal = circuit.add("VirtualCrystalGenerator", a, inputs["color"])
    unstacked = circuit.add("VirtualUnstacker", a)
    analyzed = circuit.add("VirtualAnalyzer", a)
    painted = circuit.add("VirtualPainter", a, inputs["color"])
    primary = (a, clockwise, counterclockwise, half, front, back, pin, stacked,
               swapped, Ref(swapped.node, 1), crystal, unstacked, analyzed, painted)
    secondary = {11: Ref(unstacked.node, 1), 12: Ref(analyzed.node, 1)}
    selected = []
    published = []
    extra = []
    equal_mode = base64.b64encode(b"\x01").decode("ascii")
    for code, result in enumerate(primary):
        equals = circuit.add("LogicGateCompare", inputs["opcode"], Literal(code), config=equal_mode)
        enabled = circuit.add("LogicGateAnd", equals, inputs["enable"])
        selected.append(enabled)
        published.append(circuit.add("LogicGateIf", result, enabled))
        if code in secondary:
            extra.append(circuit.add("LogicGateIf", secondary[code], enabled))
    circuit.aliases.extend((tuple(published), tuple(extra)))
    while len(selected) > 1:
        selected = [circuit.add("LogicGateOr", selected[i], selected[i + 1])
                    if i + 1 < len(selected) else selected[i]
                    for i in range(0, len(selected), 2)]
    recognized = selected[0]
    channels = circuit.channel_map()
    report = {
        "component": "virtual_operation_core",
        "quadrants": quadrants,
        "height": 5,
        "inputs": {name: channel_base + i for i, name in enumerate(inputs)},
        "outputs": {"primary": channels[published[0]], "secondary": channels[extra[0]],
                    "recognized": channels[recognized]},
        "opcodes": dict(enumerate(OPERATIONS)),
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 511],
        "scope": "虚拟加工核心；不包含可制作性求解、配方存储或时序调度器",
        "verification": "静态端口、实际占地与几何网络核对；未运行门级模拟或游戏",
        "timing": "组合电路，无完成脉冲；整组输入保持不少于 settling.hold_signal_ticks。",
        "settling": circuit.settling_bound(),
    }
    return circuit, report


def main() -> int:
    """编译加工核心蓝图及频道说明，拒绝将部件输出描述为完整 TMAM。"""
    parser = argparse.ArgumentParser(description="生成 TMAM 共用虚拟加工核心及频道表")
    parser.add_argument("--quadrants", type=int, choices=(4, 6), required=True)
    parser.add_argument("--channel-base", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path, required=True, help="蓝图文件路径；同目录另写 .json 频道表")
    args = parser.parse_args()
    circuit, report = build_core(args.quadrants, args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"加工核心已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
