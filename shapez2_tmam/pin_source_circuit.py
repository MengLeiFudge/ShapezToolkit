"""四列二十槽及完整顶盖组合的顶针候选，保留原层号与固定标签。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref
from .corner_program import CornerProgram
from .half_circuit import MaterialCell
from .pin_column_circuit import ColumnTarget, decode_column
from .pin_image_circuit import PinImageFlags, image_constraints
from .pin_pattern_circuit import pattern_column


@dataclass(frozen=True)
class PinSource:
    """通过必要筛选的五层前态；valid仍不保证可制作或Pin精确命中。"""

    materials: tuple[tuple[Ref, ...], ...]
    tags: tuple[tuple[Ref, ...], ...]
    valid: Ref
    column_valid: tuple[Ref, ...]
    image: PinImageFlags
    # 横边冲突归入两端较快的列；该槽不变时，全部更快地址均无解。
    slot_conflicts: tuple[Ref, ...]
    last_slots: tuple[Ref, ...]
    has_slots: Ref
    top_pin_allowed: tuple[Ref, ...]
    top_crystal_allowed: tuple[Ref, ...]
    top_crystals: tuple[Ref, ...]
    first_slots: tuple[Ref, ...]
    next_slots: tuple[Ref, ...]


def _crystal_cap_allowed(program: CornerProgram, lower: tuple[MaterialCell, ...]) -> Ref:
    """前四格已满足列A时，只检查在第4层补C新增的条件。"""
    occupied = tuple(cell.occupied for cell in lower)
    pins = tuple(cell.pin for cell in lower)
    crystals = tuple(cell.crystal for cell in lower)
    ordinary = tuple(program.and_(cell.occupied, program.not_(program.or_(cell.pin, cell.crystal)))
                     for cell in lower[:3])
    needle = program.and_(*(program.or_(program.not_(pins[z]), program.and_(*pins[:z])) for z in range(1, 4)))
    supported_gap = program.or_(occupied[3], *ordinary)
    intervals = (program.or_(program.not_(crystals[0]), program.and_(occupied[1], program.or_(occupied[2], occupied[3]))),
                 program.or_(program.not_(crystals[1]), program.and_(occupied[2], occupied[3])),
                 program.or_(program.not_(crystals[2]), occupied[3]))
    return program.and_(needle, supported_gap, *intervals)


def pin_source(program: CornerProgram, materials: tuple[tuple[Ref, ...], ...],
               tags: tuple[tuple[Ref, ...], ...], slots: tuple[Ref, ...],
               top_values: tuple[Ref, ...], enable: Ref, *, excluded_caps: tuple[Ref, ...] | None = None,
               decoded_targets: tuple[ColumnTarget, ...] | None = None) -> PinSource:
    """默认顶格0空1Cu2P3红C；内部搜索可由排除位从最大允许C掩码开始。"""
    if (len(materials) != 4 or len(tags) != 4 or len(slots) != 4 or len(top_values) != 4
            or any(len(column) != 5 for column in (*materials, *tags))):
        raise ValueError("顶针前态需要四列五格材料/标签、四个来源槽号与四个顶格")
    if excluded_caps is not None and len(excluded_caps) != 4:
        raise ValueError("顶晶体排除位需要四列")
    if decoded_targets is not None and len(decoded_targets) != 4:
        raise ValueError("共用目标解码需要四列")
    circuit = program.circuit
    decoded = decoded_targets if decoded_targets is not None else tuple(decode_column(circuit, column) for column in materials)
    patterns = tuple(pattern_column(program, material, tag, slot, enable, with_landings=True, decoded_target=target)
                     for material, tag, slot, target in zip(materials, tags, slots, decoded))
    columns = tuple(pattern.column for pattern in patterns)
    top_pin_allowed = tuple(column.flags[3].occupied for column in columns)
    top_crystal_allowed = tuple(_crystal_cap_allowed(program, column.flags) for column in columns)
    target = tuple(tuple(MaterialCell(program.not_(kinds[0]), kinds[2], kinds[3])
                         for kinds in column.kinds) for column in decoded)
    if excluded_caps is not None:
        top_values = tuple(program.pick(program.and_(allowed, program.not_(column[4].crystal), program.not_(excluded)),
                                        program.const(3), value)
                           for value, allowed, column, excluded in zip(top_values, top_crystal_allowed, target, excluded_caps))
    tops = tuple(tuple(circuit.add("LogicGateCompare", value, Literal(kind), config="AQ==")
                       for kind in range(4)) for value in top_values)
    top_flags = tuple(MaterialCell(program.not_(kinds[0]), kinds[2], kinds[3]) for kinds in tops)
    conflicts: list[list[Ref]] = [[] for _ in range(4)]
    for q in range(4):
        neighbor = (q + 1) % 4
        for r in range(4):
            differs = circuit.add("LogicGateXOr", target[q][r + 1].crystal, target[neighbor][r + 1].crystal)
            conflicts[min(q, neighbor)].append(program.and_(columns[q].flags[r].crystal,
                                                           columns[neighbor].flags[r].crystal, differs))
    slot_conflicts = tuple(program.or_(*values) for values in conflicts)
    image = image_constraints(program, target, columns, tuple(cell.crystal for cell in top_flags))
    valid = program.and_(enable, image.passed, program.not_(program.or_(*slot_conflicts)),
                         *(program.or_(*kinds) for kinds in tops),
                         program.or_(*(cell.occupied for column in target for cell in column)),
                         *(program.or_(program.not_(top.pin), allowed) for top, allowed in zip(top_flags, top_pin_allowed)),
                         *(program.or_(program.not_(top.crystal), allowed) for top, allowed in zip(top_flags, top_crystal_allowed)))
    source_materials = tuple(tuple(circuit.add("LogicGateIf", value, valid) for value in (*column.materials, top))
                             for column, top in zip(columns, top_values))
    source_tags = tuple(tuple(circuit.add("LogicGateIf", value, valid) for value in (*column.tags, top))
                       for column, top in zip(columns, top_values))
    return PinSource(source_materials, source_tags, valid, tuple(column.valid for column in columns), image, slot_conflicts,
                     tuple(pattern.last_slot for pattern in patterns), program.and_(*(pattern.has_slots for pattern in patterns)),
                     top_pin_allowed, top_crystal_allowed, tuple(cell.crystal for cell in top_flags),
                     tuple(pattern.first_slot for pattern in patterns), tuple(pattern.next_slot for pattern in patterns))


def build_pin_source(channel_base: int = 1_194_000) -> tuple[Circuit, dict]:
    """编译四列前态组合部件；外部控制器负责槽号、顶盖和递归。"""
    reserve = 16_384
    if not 1 <= channel_base < (1 << 24) - reserve:
        raise ValueError("频道基址需要保留后续16384个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 64)
    materials = tuple(tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 8 * z + 2 * q))
                            for z in range(5)) for q in range(4))
    tags = tuple(tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 8 * z + 2 * q + 1))
                      for z in range(5)) for q in range(4))
    slots = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 40 + q)) for q in range(4))
    top = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 44 + q)) for q in range(4))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 48))
    source = pin_source(CornerProgram(circuit), materials, tags, slots, top, enable)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("四列顶针前态超出其保留频道范围")
    return circuit, {
        "component": "four_column_pin_source", "quadrants": 4, "height": 5,
        "inputs": {"target_bottom_to_top": [[{"material": channel_base + 8 * z + 2 * q,
                                                "tag": channel_base + 8 * z + 2 * q + 1} for q in range(4)] for z in range(5)],
                   "source_slots": [channel_base + 40 + q for q in range(4)],
                   "source_top_values": [channel_base + 44 + q for q in range(4)], "enable": channel_base + 48},
        "outputs": {"candidate_valid": channels[source.valid],
                    "has_slots": channels[source.has_slots],
                    "first_slots": [channels[value] for value in source.first_slots],
                    "next_slots": [channels[value] for value in source.next_slots],
                    "last_slots": [channels[value] for value in source.last_slots],
                    "source_bottom_to_top": [[{"material": channels[source.materials[q][z]],
                                               "tag": channels[source.tags[q][z]]} for q in range(4)] for z in range(5)]},
        "gate_platforms": len(circuit.gates), "reserved_channels": [channel_base, channel_base + reserve - 1],
        "settling": circuit.settling_bound(),
        "encoding": "材料0空1N2P3C；每列槽号0～19；顶格0空1Cu2P3红C。标签继承固定原目标表，辅助顶格标签同其整数。",
        "scope": "完整覆盖四列及顶盖结构候选，并筛融合/组位移必要条件；仍须真实制造、原生Pin及完整目标比较。没有内部迭代或完成脉冲。",
        "resource_bound": "四份共用二十槽选址和单列路由；按单列合法槽直接后继，跳过非法槽；不保存目标图形目录。",
        "proof": "4q5l/pin-patterns.md；valid-slot-cursor.md；pin-source-conflicts.md；pin-image-constraints.md；pin-column-circuit.md。",
        "verification": "仅静态DAG、端口和实际占地生产编译；未运行目标、候选遍历、制造、模拟或测试",
    }


def main() -> int:
    """只编译生产蓝图。"""
    parser = argparse.ArgumentParser(description="生成四列二十槽及完整顶盖的顶针前态部件")
    parser.add_argument("--channel-base", type=int, default=1_194_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_pin_source(args.channel_base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"四列顶针前态已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
