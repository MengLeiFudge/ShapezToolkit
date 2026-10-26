"""四列二十槽及完整顶盖组合的顶针候选，保留原层号与固定标签。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref
from .corner_program import CornerProgram
from .half_circuit import MaterialCell, column_admissible
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
    slot_addresses: tuple[tuple[Ref, ...], ...]


def pin_source(program: CornerProgram, materials: tuple[tuple[Ref, ...], ...],
               tags: tuple[tuple[Ref, ...], ...], slots: tuple[Ref, ...],
               top_values: tuple[Ref, ...], enable: Ref) -> PinSource:
    """四列各选0～19槽；顶格0空1Cu2P3红C；不执行目标或制造流程。"""
    if (len(materials) != 4 or len(tags) != 4 or len(slots) != 4 or len(top_values) != 4
            or any(len(column) != 5 for column in (*materials, *tags))):
        raise ValueError("顶针前态需要四列五格材料/标签、四个来源槽号与四个顶格")
    circuit = program.circuit
    patterns = tuple(pattern_column(program, material, tag, slot, enable, with_landings=True)
                     for material, tag, slot in zip(materials, tags, slots))
    columns = tuple(pattern.column for pattern in patterns)
    tops = tuple(tuple(circuit.add("LogicGateCompare", value, Literal(kind), config="AQ==")
                       for kind in range(4)) for value in top_values)
    top_flags = tuple(MaterialCell(program.not_(kinds[0]), kinds[2], kinds[3]) for kinds in tops)
    top_pin_allowed = tuple(column.flags[3].occupied for column in columns)
    cap = MaterialCell(program.one, program.zero, program.one)
    top_crystal_allowed = tuple(column_admissible(circuit, (*column.flags, cap)) for column in columns)
    target = tuple(tuple(MaterialCell(
        program.not_(circuit.add("LogicGateCompare", value, Literal(0), config="AQ==")),
        circuit.add("LogicGateCompare", value, Literal(2), config="AQ=="),
        circuit.add("LogicGateCompare", value, Literal(3), config="AQ==")) for value in column) for column in materials)
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
                     top_pin_allowed, top_crystal_allowed, tuple(pattern.addresses for pattern in patterns))


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
                    "source_bottom_to_top": [[{"material": channels[source.materials[q][z]],
                                               "tag": channels[source.tags[q][z]]} for q in range(4)] for z in range(5)]},
        "gate_platforms": len(circuit.gates), "reserved_channels": [channel_base, channel_base + reserve - 1],
        "settling": circuit.settling_bound(),
        "encoding": "材料0空1N2P3C；每列槽号0～19；顶格0空1Cu2P3红C。标签继承固定原目标表，辅助顶格标签同其整数。",
        "scope": "完整覆盖四列及顶盖结构候选，并筛融合/组位移必要条件；仍须真实制造、原生Pin及完整目标比较。没有内部迭代或完成脉冲。",
        "resource_bound": "四份共用二十槽选址和单列路由；每列最多20个槽而非256个控制字；不保存候选表或完整图形目录。",
        "proof": "4q5l/pin-patterns.md；pin-source-conflicts.md；pin-image-constraints.md；pin-column-circuit.md。",
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
