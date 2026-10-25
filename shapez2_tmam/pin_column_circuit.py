"""由目标单列与八个控制位恢复顶针输入的前四层材料/标签。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .circuit import Circuit, Literal, Ref, constant
from .half_circuit import MaterialCell, _combine, column_admissible


@dataclass(frozen=True)
class PinColumn:
    """前四层的材料/标签通路及本地结构有效标志。"""

    materials: tuple[Ref, ...]
    tags: tuple[Ref, ...]
    valid: Ref


def _prefix_counts(circuit: Circuit, bits: list[Ref]) -> list[list[Ref]]:
    """逐前缀的一热计数；只用布尔门，不依赖整数算术建筑。"""
    counts = [[circuit.add("ConstantSignal", config=constant(1))]]
    for bit in bits:
        previous = counts[-1]
        no = circuit.add("LogicGateNot", bit)
        current = [circuit.add("LogicGateAnd", previous[0], no)]
        for count in range(1, len(previous)):
            unchanged = circuit.add("LogicGateAnd", previous[count], no)
            increased = circuit.add("LogicGateAnd", previous[count - 1], bit)
            current.append(circuit.add("LogicGateOr", unchanged, increased))
        current.append(circuit.add("LogicGateAnd", previous[-1], bit))
        counts.append(current)
    return counts


def _bus(circuit: Circuit, sources: list[Ref]) -> Ref:
    """仅在声明的有效输入下具有至多一个非空分支。"""
    if not sources:
        raise ValueError("单列路由总线需要至少一个来源")
    circuit.aliases.append(tuple(sources))
    return sources[0]


def column_candidate(circuit: Circuit, materials: tuple[Ref, ...], tags: tuple[Ref, ...],
                     mask_bits: tuple[Ref, ...], enable: Ref) -> PinColumn:
    """添加共用单列数据通路；不调用Pin或把本地通过当作全图可解性。"""
    if len(materials) != 5 or len(tags) != 5 or len(mask_bits) != 8:
        raise ValueError("单列候选需要五格材料、五个标签和八个控制位")
    flags = []
    clauses = []
    for value in materials:
        kinds = [circuit.add("LogicGateCompare", value, Literal(kind), config="AQ==") for kind in range(4)]
        flags.append(kinds)
        clauses.append(_combine(circuit, "LogicGateOr", kinds))
    masks = []
    for value in mask_bits:
        zero = circuit.add("LogicGateCompare", value, Literal(0), config="AQ==")
        one = circuit.add("LogicGateCompare", value, Literal(1), config="AQ==")
        clauses.append(circuit.add("LogicGateOr", zero, one))
        masks.append(one)
    keep, extra_crystals = masks[:4], masks[4:]
    clauses.extend((enable, circuit.add("LogicGateNot", flags[0][3])))
    retained = [flags[0][1]] + [circuit.add("LogicGateOr", kinds[1], kinds[2]) for kinds in flags[1:]]
    target_counts = _prefix_counts(circuit, retained)
    source_counts = _prefix_counts(circuit, keep)
    same_count = [circuit.add("LogicGateAnd", target_counts[-1][k], source_counts[-1][k]) for k in range(5)]
    clauses.append(_combine(circuit, "LogicGateOr", same_count))
    barriers = []
    for r in range(4):
        same_side = [circuit.add("LogicGateAnd", source_counts[r][k], target_counts[r + 1][k])
                     for k in range(r + 1)]
        no_crystal = circuit.add("LogicGateNot", flags[r + 1][3])
        barriers.append(circuit.add("LogicGateOr", no_crystal, _combine(circuit, "LogicGateOr", same_side)))
    clauses.append(_combine(circuit, "LogicGateAnd", barriers))
    selected = []
    compact_materials = []
    compact_tags = []
    for rank in range(4):
        choices = [(z, circuit.add("LogicGateAnd", retained[z], target_counts[z][rank]))
                   for z in range(rank, 5)]
        selected.append(choices)
        compact_materials.append(_bus(circuit, [circuit.add("LogicGateIf", materials[z], pick) for z, pick in choices]))
        compact_tags.append(_bus(circuit, [circuit.add("LogicGateIf", tags[z], pick) for z, pick in choices]))
    zero = circuit.add("ConstantSignal", config=constant(0))
    source_materials = []
    source_tags = []
    source_flags = []
    for r in range(4):
        npc_materials = []
        npc_tags = []
        positions = []
        for rank in range(r + 1):
            pick = circuit.add("LogicGateAnd", keep[r], source_counts[r][rank])
            npc_materials.append(circuit.add("LogicGateIf", compact_materials[rank], pick))
            npc_tags.append(circuit.add("LogicGateIf", compact_tags[rank], pick))
            allowed = [choice for z, choice in selected[rank] if z <= r + 1]
            allowed_position = _combine(circuit, "LogicGateOr", allowed) if allowed else zero
            positions.append(circuit.add("LogicGateAnd", pick, allowed_position))
        not_kept = circuit.add("LogicGateNot", keep[r])
        clauses.append(circuit.add("LogicGateOr", not_kept, _combine(circuit, "LogicGateOr", positions)))
        forced = flags[r + 1][3]
        collision = circuit.add("LogicGateAnd", keep[r], forced)
        clauses.append(circuit.add("LogicGateNot", collision))
        reserved = circuit.add("LogicGateOr", keep[r], forced)
        collision = circuit.add("LogicGateAnd", extra_crystals[r], reserved)
        clauses.append(circuit.add("LogicGateNot", collision))
        crystal = circuit.add("LogicGateOr", forced, extra_crystals[r])
        occupied = circuit.add("LogicGateOr", keep[r], crystal)
        empty = circuit.add("LogicGateNot", occupied)
        # 新的IF隔开各级别名；一个Ref不能属于两个别名组。
        npc_material = circuit.add("LogicGateIf", _bus(circuit, npc_materials), keep[r])
        npc_tag = circuit.add("LogicGateIf", _bus(circuit, npc_tags), keep[r])
        pin = circuit.add("LogicGateCompare", npc_material, Literal(2), config="AQ==")
        source_flags.append(MaterialCell(occupied, pin, crystal))
        source_materials.append(_bus(circuit, [npc_material,
            circuit.add("LogicGateIf", Literal(3), crystal),
            circuit.add("LogicGateIf", Literal(0), empty)]))
        source_tags.append(_bus(circuit, [npc_tag,
            circuit.add("LogicGateIf", tags[r + 1], forced),
            circuit.add("LogicGateIf", Literal(3), extra_crystals[r]),
            circuit.add("LogicGateIf", Literal(0), empty)]))
    clauses.append(circuit.add("LogicGateCompare", source_flags[0].occupied, flags[0][2], config="AQ=="))
    empty_cell = MaterialCell(zero, zero, zero)
    clauses.append(column_admissible(circuit, (*source_flags, empty_cell)))
    valid = _combine(circuit, "LogicGateAnd", clauses)
    published_materials = [circuit.add("LogicGateIf", value, valid) for value in source_materials]
    published_tags = [circuit.add("LogicGateIf", value, valid) for value in source_tags]
    return PinColumn(tuple(published_materials), tuple(published_tags), valid)


def build_pin_column(channel_base: int = 1_019_000) -> tuple[Circuit, dict]:
    """生成独立单列候选部件及频道表。"""
    if not 1 <= channel_base < (1 << 24) - 2048:
        raise ValueError("频道基址需要为实例保留后续2048个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    materials = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 2 * z)) for z in range(5))
    tags = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 2 * z + 1)) for z in range(5))
    masks = tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 10 + bit)) for bit in range(8))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 18))
    candidate = column_candidate(circuit, materials, tags, masks, enable)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 2047:
        raise ValueError("顶针单列候选部件超出其保留频道范围")
    return circuit, {
        "component": "pin_column_candidate", "quadrants": 4, "height": 5,
        "inputs": {"target_bottom_to_top": [{"material": channel_base + 2 * z, "tag": channel_base + 2 * z + 1} for z in range(5)],
                   "keep_bits_bottom_to_top": list(range(channel_base + 10, channel_base + 14)),
                   "extra_crystal_bits_bottom_to_top": list(range(channel_base + 14, channel_base + 18)),
                   "enable": channel_base + 18},
        "outputs": {"candidate_valid": channels[candidate.valid],
                    "source_bottom_four": [{"material": channels[kind], "tag": channels[tag]}
                                           for kind, tag in zip(candidate.materials, candidate.tags)]},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 2047],
        "encoding": "材料0空/1普通/2针/3晶体；八控制位须是整数0或1。tag为调用者管理的原目标标签编号，0为空、3为辅助红晶体，保留格继承原tag。",
        "scope": "目标单列到顶针前四层的结构候选；不输出第五层，不检查整图Pin物理或可制作性。candidate_valid不能当作solved。",
        "enumeration": "八位共256种赋值；地面掩码使单列至多20个，有保留C时至多12个。晶体屏障前缀等式再排除穿越来源；四列及第五层仍须外部迭代。",
        "proof": "4q5l/pin-column-circuit.md；Python对应synthesis.inverse.pin_column。",
        "timing": "组合电路，整组输入保持不少于settling.hold_signal_ticks；仅candidate_valid为真时读取四格输出。",
        "settling": circuit.settling_bound(),
        "verification": "静态端口、实际占地与几何网络核对；未运行目标、枚举、门级模拟或游戏",
    }


def main() -> int:
    """编译单列结构候选数据通路，不枚举目标或运行求解。"""
    parser = argparse.ArgumentParser(description="生成直接处理材料格与标签的顶针单列候选部件")
    parser.add_argument("--channel-base", type=int, default=1_019_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_pin_column(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"顶针单列候选部件已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
