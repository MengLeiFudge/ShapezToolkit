"""顶针逆像的制造前必要筛选：融合删除、同组F/M一致及移动NPC落点。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref
from .corner_program import CornerProgram
from .half_circuit import MaterialCell
from .pin_column_circuit import PinColumn, column_candidate


@dataclass(frozen=True)
class PinImageFlags:
    """passed只表示必要条件通过；claimed_fixed尚未证明是最大静止集合。"""

    passed: Ref
    deleted: tuple[tuple[Ref, ...], ...]
    claimed_fixed: tuple[tuple[Ref, ...], ...]
    live: tuple[tuple[MaterialCell, ...], ...]


def image_constraints(program: CornerProgram, target: tuple[tuple[MaterialCell, ...], ...],
                      columns: tuple[PinColumn, ...], top_bits: tuple[Ref, ...]) -> PinImageFlags:
    """四列来源已按序映射到目标；不运行原生Pin，也不保证候选可制作。"""
    if len(target) != 4 or any(len(column) != 5 for column in target) or len(columns) != 4 or len(top_bits) != 4:
        raise ValueError("顶针像筛选需要四列五层目标、四列来源及四个顶层晶体位")
    if any(len(column.flags) != 4 or len(column.landings) != 4 or any(len(row) != 5 for row in column.landings)
           for column in columns):
        raise ValueError("顶针像筛选需要启用with_landings的完整来源元数据")
    circuit = program.circuit
    clauses = [column.valid for column in columns]
    top = []
    for bit in top_bits:
        zero = circuit.add("LogicGateCompare", bit, Literal(0), config="AQ==")
        one = circuit.add("LogicGateCompare", bit, Literal(1), config="AQ==")
        clauses.append(program.or_(zero, one))
        top.append(one)
    crystals = tuple(tuple(columns[q].flags[z].crystal if z < 4 else top[q] for q in range(4)) for z in range(5))
    deleted = tuple(tuple(top[q] if z == 4 else program.zero for q in range(4)) for z in range(5))
    # 20个晶体格，简单路径至多19条边；融合不经过普通块或针。
    for _ in range(19):
        following = []
        for z in range(5):
            row = []
            for q in range(4):
                neighbors = [deleted[z][(q - 1) % 4], deleted[z][(q + 1) % 4]]
                neighbors.extend(deleted[r][q] for r in (z - 1, z + 1) if 0 <= r < 5)
                row.append(program.or_(deleted[z][q], program.and_(crystals[z][q], program.or_(*neighbors))))
            following.append(tuple(row))
        deleted = tuple(following)
    live = [tuple(MaterialCell(column.flags[0].occupied, column.flags[0].occupied, program.zero)
                  for column in columns)]
    fixed = [tuple(column.flags[0].occupied for column in columns)]
    for r in range(4):
        row = []
        fixed_row = []
        for q, column in enumerate(columns):
            source = column.flags[r]
            retained = target[q][r + 1].crystal
            clauses.append(program.or_(program.not_(retained), program.not_(deleted[r][q])))
            survives = program.not_(program.and_(source.crystal, deleted[r][q]))
            occupied = program.and_(source.occupied, survives)
            row.append(MaterialCell(occupied, source.pin, program.and_(source.crystal, survives)))
            fixed_row.append(program.and_(occupied, program.or_(retained, column.landings[r][r + 1])))
        live.append(tuple(row))
        fixed.append(tuple(fixed_row))
    nonpins = tuple(tuple(program.and_(cell.occupied, program.not_(cell.pin)) for cell in row) for row in live)
    for z in range(5):
        for q in range(4):
            next_q = (q + 1) % 4
            horizontal = program.and_(nonpins[z][q], nonpins[z][next_q])
            equal = circuit.add("LogicGateCompare", fixed[z][q], fixed[z][next_q], config="AQ==")
            clauses.append(program.or_(program.not_(horizontal), equal))
            if z:
                vertical = program.and_(live[z][q].crystal, live[z - 1][q].crystal)
                equal = circuit.add("LogicGateCompare", fixed[z][q], fixed[z - 1][q], config="AQ==")
                clauses.append(program.or_(program.not_(vertical), equal))
                blocked = program.and_(live[z][q].occupied, program.not_(fixed[z][q]), fixed[z - 1][q])
                clauses.append(program.not_(blocked))
    for r in range(4):
        moving = tuple(program.and_(nonpins[r + 1][q], program.not_(live[r + 1][q].crystal),
                                   program.not_(fixed[r + 1][q])) for q in range(4))
        support = tuple(program.or_(*(program.and_(columns[q].landings[r][z],
                        target[q][z - 1].occupied if z else program.one) for z in range(5))) for q in range(4))
        supported = tuple(program.and_(moving[q], support[q]) for q in range(4))
        for q in range(4):
            next_q = (q + 1) % 4
            same_height = program.or_(*(program.and_(columns[q].landings[r][z], columns[next_q].landings[r][z])
                                        for z in range(5)))
            adjacent = program.and_(moving[q], moving[next_q])
            clauses.append(program.or_(program.not_(adjacent), same_height))
            pin = program.and_(live[r + 1][q].pin, program.not_(fixed[r + 1][q]))
            clauses.append(program.or_(program.not_(pin), support[q]))
        for _ in range(3):
            supported = tuple(program.or_(supported[q], program.and_(moving[q], program.or_(
                supported[(q - 1) % 4], supported[(q + 1) % 4]))) for q in range(4))
        clauses.extend(program.or_(program.not_(moving[q]), supported[q]) for q in range(4))
    return PinImageFlags(program.and_(*clauses), deleted, tuple(fixed), tuple(live))


def build_pin_image(channel_base: int = 1_144_000) -> tuple[Circuit, dict]:
    """静态编译四列逆像族的必要条件，不枚举控制字或求解目标。"""
    reserve = 16_384
    if not 1 <= channel_base < (1 << 24) - reserve:
        raise ValueError("频道基址需要保留后续16384个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 64)
    materials = tuple(tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 4 * z + q))
                            for z in range(5)) for q in range(4))
    masks = tuple(tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 20 + 8 * q + bit))
                        for bit in range(8)) for q in range(4))
    top = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 52 + q)) for q in range(4))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 56))
    program = CornerProgram(circuit)
    columns = tuple(column_candidate(circuit, column, column, mask, enable, with_landings=True)
                    for column, mask in zip(materials, masks))
    target = []
    for column in materials:
        cells = []
        for value in column:
            empty = circuit.add("LogicGateCompare", value, Literal(0), config="AQ==")
            pin = circuit.add("LogicGateCompare", value, Literal(2), config="AQ==")
            crystal = circuit.add("LogicGateCompare", value, Literal(3), config="AQ==")
            cells.append(MaterialCell(program.not_(empty), pin, crystal))
        target.append(tuple(cells))
    flags = image_constraints(program, tuple(target), columns, top)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("顶针像筛选超出其保留频道范围")
    return circuit, {
        "component": "pin_image_necessary_conditions", "quadrants": 4, "height": 5,
        "inputs": {"target_materials_bottom_to_top": [[channel_base + 4 * z + q for q in range(4)] for z in range(5)],
                   "column_mask_bits": [[channel_base + 20 + 8 * q + bit for bit in range(8)] for q in range(4)],
                   "top_crystal_bits": [channel_base + 52 + q for q in range(4)], "enable": channel_base + 56},
        "outputs": {"necessary_pass": channels[flags.passed],
                    "deleted_crystals_in_source": [[channels[value] for value in row] for row in flags.deleted],
                    "claimed_fixed_after_push": [[channels[value] for value in row] for row in flags.claimed_fixed]},
        "gate_platforms": len(circuit.gates), "reserved_channels": [channel_base, channel_base + reserve - 1],
        "settling": circuit.settling_bound(),
        "encoding": "目标材料0空1N2P3C；每列控制前四位keep、后四位extraC；顶层只输入C掩码，顶层NPC不影响本次Pin物理。",
        "protocol": "组合筛选，无完成脉冲；全组输入保持settling规定时间再读。必要条件通过后仍须制造前态并原生Pin比较。",
        "scope": "拒绝融合删除保留C、同粘连组F/M矛盾、M被F直接阻挡或移动NPC块落点/支撑矛盾。未证明F最大性或前态可制作性。",
        "proof": "4q5l/pin-image-constraints.md；pin-inverse.md静止组及落点定理。",
        "verification": "仅静态DAG、端口、别名及实际占地生产编译；未执行目标、控制字枚举、物理模拟或测试",
    }


def main() -> int:
    """只生成生产蓝图。"""
    parser = argparse.ArgumentParser(description="生成四列顶针逆像的制造前必要筛选电路")
    parser.add_argument("--channel-base", type=int, default=1_144_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_pin_image(args.channel_base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"顶针像必要筛选已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
