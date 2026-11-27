"""保留空底层与空中间层的原生图形解码电路。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref
from ..synthesis.physics import Rules


@dataclass(frozen=True)
class DecodedCell:
    """原层号、原象限的一格；部件去色到 q0，颜色单独保存。"""

    shape: Ref
    color: Ref
    occupied: Ref
    pin: Ref
    crystal: Ref


@dataclass(frozen=True)
class DecodedShape:
    """解码后的五个原层位及逐格信号，valid 只表示有效输入且已启用。"""

    valid: Ref
    rows: tuple[Ref, ...]
    cells: tuple[tuple[DecodedCell, ...], ...]


def height_flags(circuit: Circuit, source: Ref, valid: Ref, maximum: int = 5) -> tuple[Ref, ...]:
    """给当前原始图形生成高度一热标志；空输入的全部标志为假。"""
    if not 1 <= maximum <= 5:
        raise ValueError("高度测量上界需要在1～5之间")
    start = len(circuit.gates)
    filled = circuit.add("VirtualCrystalGenerator", source, Literal("color:r"))
    flags = []
    for _ in range(maximum):
        split = circuit.add("VirtualUnstacker", filled)
        upper_exists = circuit.add("LogicGateCompare", Ref(split.node, 1), Literal(None), config="Bg==")
        lower_empty = circuit.add("LogicGateCompare", split, Literal(None), config="AQ==")
        last = circuit.add("LogicGateAnd", upper_exists, lower_empty)
        flags.append(circuit.add("LogicGateAnd", last, valid))
        filled = split
    if circuit.wire_methods:
        circuit.method_ranges.append((range(start, len(circuit.gates)), tuple(flags)))
    return tuple(flags)


def decode(circuit: Circuit, target: Ref, enable: Ref, rules: Rules) -> DecodedShape:
    """用结晶高度标记重新安放拆出的层；不对原目标执行重力或结晶。"""
    if rules.quadrants not in (4, 6) or rules.height != 5:
        raise ValueError("原生解码电路目前限定四/六象限五层配置")
    remaining = target
    raw_rows = []
    sources = []
    for _ in range(5):
        sources.append(remaining)
        split = circuit.add("VirtualUnstacker", remaining)
        raw_rows.append(Ref(split.node, 1))
        remaining = split
    valid = circuit.add("LogicGateCompare", raw_rows[0], Literal(None), config="Bg==")
    valid = circuit.add("LogicGateAnd", valid, enable)
    choices: list[list[Ref]] = [[] for _ in range(5)]
    for removed, (source, raw) in enumerate(zip(sources, raw_rows)):
        # 每拆出一个非空顶层，剩余高度至少降低一；仅需 5+4+3+2+1 次。
        flags = height_flags(circuit, source, valid, 5 - removed)
        for height, selected in enumerate(flags):
            choices[height].append(circuit.add("LogicGateIf", raw, selected))
    rows = []
    for group in choices:
        # 原始非空层高度严格下降，同一高度只会收到一份非空层。
        circuit.aliases.append(tuple(group))
        rows.append(group[0])
    return DecodedShape(valid, tuple(rows), tuple(decode_row(circuit, row, rules) for row in rows))


def decode_row(circuit: Circuit, row: Ref, rules: Rules) -> tuple[DecodedCell, ...]:
    """为每个象限保留原颜色，并生成去色部件和三项材料判定。"""
    pin = Literal(rules.parse('P-' + '--' * (rules.quadrants - 1)))
    crystal = Literal(rules.parse('cu' + '--' * (rules.quadrants - 1)))
    decoded = []
    for q in range(rules.quadrants):
        if q:
            row = circuit.add('VirtualRotatorCCW', row)
        analyzed = circuit.add('VirtualAnalyzer', row)
        decoded.append(DecodedCell(
            analyzed, Ref(analyzed.node, 1),
            circuit.add('LogicGateCompare', analyzed, Literal(None), config='Bg=='),
            circuit.add('LogicGateCompare', analyzed, pin, config='AQ=='),
            circuit.add('LogicGateCompare', analyzed, crystal, config='AQ==')))
    return tuple(decoded)


def build_decoder(channel_base: int = 1_006_000) -> tuple[Circuit, dict]:
    """生成四象限五层解码部件及频道表，不判断可制作性。"""
    if not 1 <= channel_base < (1 << 24) - 1024:
        raise ValueError("频道基址需要为实例保留后续 1024 个频道，并保持低于 2^24")
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    decoded = decode(circuit, target, enable, Rules(4))
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 1023:
        raise ValueError("解码部件超出其保留频道范围")
    report = {
        "component": "shape_decoder", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": {"valid": channels[decoded.valid],
                    "rows_bottom_to_top": [channels[row] for row in decoded.rows],
                    "cells_bottom_to_top": [[{
                        "shape": channels[cell.shape], "color": channels[cell.color],
                        "occupied": channels[cell.occupied], "pin": channels[cell.pin],
                        "crystal": channels[cell.crystal]} for cell in row] for row in decoded.cells]},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 1023],
        "scope": "保留原始空层的四象限五层逐格解码；不判断目标是否可制作。",
        "cell_encoding": "cells[z][q] 使用从零开始的原层号和原象限；shape 为去色 q0 单格，color 为原颜色。",
        "null_rows": "原始空底层、空中间层及最高层以上的位置输出空信号。",
        "verification": "静态端口、实际占地与几何网络核对；未运行门级模拟或游戏",
        "timing": "组合电路，无完成脉冲；整组输入保持不少于 settling.hold_signal_ticks。",
        "settling": circuit.settling_bound(),
    }
    return circuit, report


def main() -> int:
    """编译生产蓝图及频道说明，不执行目标或门级模拟。"""
    parser = argparse.ArgumentParser(description="生成保留原层号的四象限五层解码部件")
    parser.add_argument("--channel-base", type=int, default=1_006_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_decoder(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"原层号解码部件已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
