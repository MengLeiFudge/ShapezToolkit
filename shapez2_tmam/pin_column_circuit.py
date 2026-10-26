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
    flags: tuple[MaterialCell, ...] = ()
    landings: tuple[tuple[Ref, ...], ...] = ()


def _prefix_counts(circuit: Circuit, bits: list[Ref]) -> list[list[Ref]]:
    """缓存平衡区间的一热卷积；返回每个原前缀的精确计数。"""
    one = circuit.add("ConstantSignal", config=constant(1))
    inverted = [circuit.add("LogicGateNot", bit) for bit in bits]
    intervals: dict[tuple[int, int], list[Ref]] = {}

    def count_interval(lo: int, hi: int) -> list[Ref]:
        if lo == hi:
            return [one]
        if hi - lo == 1:
            return [inverted[lo], bits[lo]]
        key = (lo, hi)
        if key not in intervals:
            middle = (lo + hi) // 2
            left, right = count_interval(lo, middle), count_interval(middle, hi)
            intervals[key] = [_combine(circuit, "LogicGateOr", [
                circuit.add("LogicGateAnd", left[i], right[k - i])
                for i in range(max(0, k - len(right) + 1), min(k + 1, len(left)))])
                for k in range(hi - lo + 1)]
        return intervals[key]

    return [count_interval(0, end) for end in range(len(bits) + 1)]


@dataclass(frozen=True)
class ColumnTarget:
    """同一份目标材料的种类、保留NPC及前缀计数，供选址和路由共用。"""

    kinds: tuple[tuple[Ref, ...], ...]
    retained: tuple[Ref, ...]
    counts: tuple[tuple[Ref, ...], ...]


def column_target(circuit: Circuit, kinds: tuple[tuple[Ref, ...], ...]) -> ColumnTarget:
    """按五格四种类标志建立保留序号；标志须与对应整数材料完全一致。"""
    if len(kinds) != 5 or any(len(row) != 4 for row in kinds):
        raise ValueError("来源目标列需要五格各四种类标志")
    retained = [kinds[0][1]] + [circuit.add("LogicGateOr", row[1], row[2]) for row in kinds[1:]]
    return ColumnTarget(kinds, tuple(retained), tuple(tuple(row) for row in _prefix_counts(circuit, retained)))


def decode_column(circuit: Circuit, materials: tuple[Ref, ...]) -> ColumnTarget:
    """解码材料而不接受它；调用方仍须检查每格属于0～3。"""
    kinds = tuple(tuple(circuit.add("LogicGateCompare", value, Literal(kind), config="AQ==")
                        for kind in range(4)) for value in materials)
    return column_target(circuit, kinds)


def _bus(circuit: Circuit, sources: list[Ref]) -> Ref:
    """仅在声明的有效输入下具有至多一个非空分支。"""
    if not sources:
        raise ValueError("单列路由总线需要至少一个来源")
    circuit.aliases.append(tuple(sources))
    return sources[0]


def column_candidate(circuit: Circuit, materials: tuple[Ref, ...], tags: tuple[Ref, ...],
                     mask_bits: tuple[Ref, ...], enable: Ref, *, with_landings: bool = False,
                     decoded_target: ColumnTarget | None = None,
                     keep_counts: tuple[tuple[Ref, ...], ...] | None = None) -> PinColumn:
    """可共用同目标解码及同keep掩码的表选计数；表无选中时调用方须关闭enable。"""
    if len(materials) != 5 or len(tags) != 5 or len(mask_bits) != 8:
        raise ValueError("单列候选需要五格材料、五个标签和八个控制位")
    target = decoded_target if decoded_target is not None else decode_column(circuit, materials)
    flags = target.kinds
    clauses = [_combine(circuit, "LogicGateOr", list(kinds)) for kinds in flags]
    masks = []
    for value in mask_bits:
        zero = circuit.add("LogicGateCompare", value, Literal(0), config="AQ==")
        one = circuit.add("LogicGateCompare", value, Literal(1), config="AQ==")
        clauses.append(circuit.add("LogicGateOr", zero, one))
        masks.append(one)
    keep, extra_crystals = masks[:4], masks[4:]
    clauses.extend((enable, circuit.add("LogicGateNot", flags[0][3])))
    retained = target.retained
    target_counts = target.counts
    source_counts = keep_counts if keep_counts is not None else _prefix_counts(circuit, keep)
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
    rank_picks = []
    for r in range(4):
        npc_materials = []
        npc_tags = []
        positions = []
        picks = []
        for rank in range(r + 1):
            pick = circuit.add("LogicGateAnd", keep[r], source_counts[r][rank])
            picks.append(pick)
            npc_materials.append(circuit.add("LogicGateIf", compact_materials[rank], pick))
            npc_tags.append(circuit.add("LogicGateIf", compact_tags[rank], pick))
            allowed = [choice for z, choice in selected[rank] if z <= r + 1]
            allowed_position = _combine(circuit, "LogicGateOr", allowed) if allowed else zero
            positions.append(circuit.add("LogicGateAnd", pick, allowed_position))
        rank_picks.append(picks)
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
    landings = []
    if with_landings:
        for picks in rank_picks:
            row = []
            for z in range(5):
                choices = [circuit.add("LogicGateAnd", pick, chosen) for rank, pick in enumerate(picks)
                           for height, chosen in selected[rank] if height == z]
                row.append(_combine(circuit, "LogicGateOr", choices) if choices else zero)
            landings.append(tuple(row))
    return PinColumn(tuple(published_materials), tuple(published_tags), valid,
                     tuple(source_flags) if with_landings else (), tuple(landings))


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
