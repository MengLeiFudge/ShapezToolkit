"""四象限五层标准半形的完整局部判定电路，不枚举半形目录。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref
from .decoder_circuit import DecodedCell, DecodedShape, decode
from ..synthesis.physics import Rules


@dataclass(frozen=True)
class MaterialCell:
    """不需要原生图形编码的逐格材料布尔信号。"""

    occupied: Ref
    pin: Ref
    crystal: Ref


def _combine(circuit: Circuit, kind: str, values: list[Ref]) -> Ref:
    """平衡连接非空布尔列表，避免把判据展开为很长的串联路径。"""
    if not values:
        raise ValueError("布尔连接需要至少一个输入")
    while len(values) > 1:
        values = [circuit.add(kind, values[i], values[i + 1]) if i + 1 < len(values) else values[i]
                  for i in range(0, len(values), 2)]
    return values[0]


def column_admissible(circuit: Circuit, cells: tuple[DecodedCell | MaterialCell, ...]) -> Ref:
    """将五格列条件 A 写为布尔门；不将该必要条件当作全图可制作判据。"""
    if len(cells) != 5:
        raise ValueError("列判据需要五个原层位")
    occupied = [cell.occupied for cell in cells]
    pins = [cell.pin for cell in cells]
    crystals = [cell.crystal for cell in cells]
    empty = [circuit.add("LogicGateNot", value) for value in occupied]
    not_pin = [circuit.add("LogicGateNot", value) for value in pins]
    not_crystal = [circuit.add("LogicGateNot", value) for value in crystals]
    ordinary = []
    for z in range(5):
        special = circuit.add("LogicGateOr", pins[z], crystals[z])
        normal = circuit.add("LogicGateNot", special)
        ordinary.append(circuit.add("LogicGateAnd", occupied[z], normal))
    clauses = []
    for z in range(1, 5):
        clauses.append(circuit.add("LogicGateOr", not_pin[z], occupied[z - 1]))
    prefix = pins[0]
    for z in range(1, 4):
        prefix = circuit.add("LogicGateAnd", prefix, pins[z])
        higher = _combine(circuit, "LogicGateOr", crystals[z + 1:])
        no_higher = circuit.add("LogicGateNot", higher)
        clauses.append(_combine(circuit, "LogicGateOr", [no_higher, not_pin[z], prefix]))
    last_normal = ordinary[0]
    for z in range(1, 5):
        clauses.append(_combine(circuit, "LogicGateOr", [not_crystal[z], occupied[z - 1], last_normal]))
        carried = circuit.add("LogicGateAnd", empty[z], last_normal)
        last_normal = circuit.add("LogicGateOr", ordinary[z], carried)
    for lower in range(3):
        for upper in range(lower + 2, 5):
            filled = _combine(circuit, "LogicGateAnd", occupied[lower + 1:upper])
            if upper - lower == 4:
                # 五层唯一能在两颗 C 之间容纳“两 N 加空格”的区间。
                gap_high = circuit.add("LogicGateAnd", ordinary[2], empty[3])
                gap_low = circuit.add("LogicGateAnd", empty[2], ordinary[3])
                alternatives = circuit.add("LogicGateOr", gap_high, gap_low)
                separated = circuit.add("LogicGateAnd", ordinary[1], alternatives)
                filled = circuit.add("LogicGateOr", filled, separated)
            clauses.append(_combine(circuit, "LogicGateOr", [not_crystal[lower], not_crystal[upper], filled]))
    return _combine(circuit, "LogicGateAnd", clauses)


def half_stable(circuit: Circuit, rows: tuple[tuple[DecodedCell | MaterialCell, ...], ...]) -> Ref:
    """两列各层的非针组沿晶体竖边构成区间，只在区间末端检查支撑。"""
    if not 1 <= len(rows) <= 5 or any(len(row) != 2 for row in rows):
        raise ValueError("半形稳定性需要1～5个原层位，每层两个材料格")
    nonpins = [[circuit.add("LogicGateAnd", cell.occupied, circuit.add("LogicGateNot", cell.pin))
                for cell in row] for row in rows]
    links = [circuit.add("LogicGateOr", *[
        circuit.add("LogicGateAnd", rows[z][q].crystal, rows[z - 1][q].crystal) for q in (0, 1)])
        for z in range(1, len(rows))]
    failures = []
    supported = circuit.add("LogicGateOr", *nonpins[0])
    for z, row in enumerate(rows):
        occupied = circuit.add("LogicGateOr", *nonpins[z])
        if z:
            for q in (0, 1):
                below_empty = circuit.add("LogicGateNot", rows[z - 1][q].occupied)
                failures.append(circuit.add("LogicGateAnd", row[q].pin, below_empty))
            bottom = circuit.add("LogicGateOr", *[
                circuit.add("LogicGateAnd", nonpins[z][q], rows[z - 1][q].occupied) for q in (0, 1)])
            pins_below = circuit.add("LogicGateOr", *[
                circuit.add("LogicGateAnd", nonpins[z][q], rows[z - 1][q].pin) for q in (0, 1)])
            carried = circuit.add("LogicGateAnd", links[z - 1], supported)
            starts = circuit.add("LogicGateNot", links[z - 1])
            starts = circuit.add("LogicGateAnd", starts, bottom)
            supported = circuit.add("LogicGateOr", circuit.add("LogicGateOr", carried, starts), pins_below)
        unsupported = circuit.add("LogicGateAnd", occupied, circuit.add("LogicGateNot", supported))
        if z < len(rows) - 1:
            ends = circuit.add("LogicGateNot", links[z])
            unsupported = circuit.add("LogicGateAnd", unsupported, ends)
        failures.append(unsupported)
    return circuit.add("LogicGateNot", _combine(circuit, "LogicGateOr", failures))


@dataclass(frozen=True)
class HalfFlags:
    """标准半形的完整局部判据与范围标志，均须在目标稳定后读取。"""

    standard: Ref
    stable: Ref
    admissible: Ref
    solved: Ref
    unsolvable: Ref
    unknown: Ref


def classify_half(circuit: Circuit, target: Ref, decoded: DecodedShape) -> HalfFlags:
    """共用原生半切稳定性、两列A及合法颜色范围，避免构造端另设判据。"""
    outside = [row[q].occupied for row in decoded.cells for q in (2, 3)]
    standard = circuit.add("LogicGateNot", _combine(circuit, "LogicGateOr", outside))
    admissible = _combine(circuit, "LogicGateAnd", [
        column_admissible(circuit, tuple(row[q] for row in decoded.cells)) for q in (0, 1)])
    cut = circuit.add("VirtualHalfCutter", target)
    stable = circuit.add("LogicGateCompare", cut, target, config="AQ==")
    uncolored = []
    for row in decoded.cells:
        for q in (0, 1):
            cell = row[q]
            color = circuit.add("LogicGateCompare", cell.color, Literal("color:u"), config="AQ==")
            uncolored.append(circuit.add("LogicGateAnd", color, cell.crystal))
    has_uncolored = _combine(circuit, "LogicGateOr", uncolored)
    colored = circuit.add("LogicGateNot", has_uncolored)
    in_scope = _combine(circuit, "LogicGateAnd", [decoded.valid, standard, colored])
    predicate = circuit.add("LogicGateAnd", stable, admissible)
    solved = circuit.add("LogicGateAnd", in_scope, predicate)
    fails = circuit.add("LogicGateNot", predicate)
    unsolvable = circuit.add("LogicGateAnd", in_scope, fails)
    not_standard = circuit.add("LogicGateNot", standard)
    outside_scope = circuit.add("LogicGateOr", not_standard, has_uncolored)
    unknown = circuit.add("LogicGateAnd", decoded.valid, outside_scope)
    return HalfFlags(standard, stable, admissible, solved, unsolvable, unknown)


def build_half(channel_base: int = 1_008_000) -> tuple[Circuit, dict]:
    """生成标准 q0/q1 半形的三态完整判定及原层号数据。"""
    if not 1 <= channel_base < (1 << 24) - 2048:
        raise ValueError("频道基址需要为实例保留后续 2048 个频道，并保持低于 2^24")
    rules = Rules(4)
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    decoded = decode(circuit, target, enable, rules)
    flags = classify_half(circuit, target, decoded)
    standard, stable, admissible = flags.standard, flags.stable, flags.admissible
    solved, unsolvable, unknown = flags.solved, flags.unsolvable, flags.unknown
    statuses = (circuit.add("LogicGateIf", Literal(1), solved),
                circuit.add("LogicGateIf", Literal(2), unsolvable),
                circuit.add("LogicGateIf", Literal(3), unknown))
    circuit.aliases.append(statuses)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 2047:
        raise ValueError("半形部件超出其保留频道范围")
    report = {
        "component": "standard_half_classifier", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": {"status": channels[statuses[0]], "solvable": channels[solved],
                    "unsolvable": channels[unsolvable], "unknown": channels[unknown],
                    "standard_half": channels[standard], "stable": channels[stable],
                    "columns_admissible": channels[admissible],
                    "rows_bottom_to_top": [channels[row] for row in decoded.rows]},
        "statuses": {"1": "solved", "2": "unsolvable", "3": "unknown",
                     "null": "输入不是非空图形，或 enable 为假"},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 2047],
        "scope": "q2/q3 全空的标准半形完整判定；非标准全图或未界定 cu 供料返回 unknown。",
        "proof": "标准半形可制作 iff 两列满足 A 且自身分组稳定；原生半切与原目标比较检查稳定性。",
        "recipe": "本部件输出判定和原始五层；逐列角制造树由 Python CornerBuilder/Constructor.half 生成，未包含游戏配方流控制器。",
        "verification": "静态端口、实际占地与几何网络核对；未运行门级模拟或游戏",
        "timing": "组合电路，无完成脉冲；整组输入保持不少于 settling.hold_signal_ticks。",
        "settling": circuit.settling_bound(),
    }
    return circuit, report


def main() -> int:
    """编译生产蓝图及频道说明，不运行半形目标或门级模拟。"""
    parser = argparse.ArgumentParser(description="生成四象限五层标准半形判定部件")
    parser.add_argument("--channel-base", type=int, default=1_008_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_half(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"标准半形判定部件已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
