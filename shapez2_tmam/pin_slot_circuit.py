"""按固定来源控制字计算合法槽域和直接后继，不运行目标或物理状态。"""

from dataclasses import dataclass
from functools import cache

from .circuit import Literal, Ref
from .corner_program import CornerProgram
from .pin_column_circuit import ColumnTarget
from .synthesis.pin_patterns import SOURCE_PATTERNS


@dataclass(frozen=True)
class SlotCursor:
    """后继回绕到最小合法地址；无合法地址时next为0，has为假。"""

    first: Ref
    next: Ref
    last: Ref
    has: Ref


def valid_slots(program: CornerProgram, target: ColumnTarget, forbidden_crystals: tuple[Ref, ...] = ()) -> tuple[Ref, ...]:
    """单列结构接受，加上由相邻列强制C确定的禁用晶体位置。"""
    kinds, counts = target.kinds, target.counts
    destinations = tuple(tuple(program.and_(target.retained[z], counts[z][rank]) if rank <= z else program.zero
                               for z in range(5)) for rank in range(4))
    pins = tuple(program.or_(*(program.and_(choice, kinds[z][2]) for z, choice in enumerate(row)))
                 for row in destinations)
    forced = tuple(kinds[r + 1][3] for r in range(4))
    valid_target = program.and_(program.not_(kinds[0][3]), *(program.or_(*row) for row in kinds))
    floor = (program.not_(kinds[0][2]), kinds[0][2])
    slots: list[list[Ref]] = [[] for _ in range(20)]

    same_crystal = tuple(program.not_(program.circuit.add("LogicGateXOr", forced[r], forced[r + 1])) for r in range(3))

    @cache
    def positions(keep: int) -> Ref:
        sources = [r for r in range(4) if keep & (1 << r)]
        clauses = [program.or_(*destinations[rank][:r + 2]) for rank, r in enumerate(sources)]
        for r in range(4):
            before = (keep & ((1 << r) - 1)).bit_count()
            clauses.append(program.or_(program.not_(forced[r]), counts[r + 1][before]))
        return program.and_(*clauses)

    @cache
    def crystal_positions(crystals: int) -> Ref:
        clauses = [program.not_(forced[r]) for r in range(4) if not crystals & (1 << r)]
        clauses.extend(same_crystal[r] for r in range(3) if crystals & (3 << r) == 3 << r)
        clauses.extend(program.not_(forbidden) for r, forbidden in enumerate(forbidden_crystals) if crystals & (1 << r))
        return program.and_(*clauses)

    def allowed(keep: int, crystals: int) -> Ref:
        occupied = keep | crystals
        sources = [r for r in range(4) if keep & (1 << r)]
        crystal_rows = [r for r in range(4) if crystals & (1 << r)]
        ordinary_ranks = []
        for r in crystal_rows:
            if r and not occupied & (1 << (r - 1)):
                below = [z for z in range(r) if occupied & (1 << z)]
                if not below or crystals & (1 << below[-1]):
                    return program.zero
                ordinary_ranks.append(sources.index(below[-1]))
        for lower in crystal_rows:
            for upper in crystal_rows:
                if upper > lower + 1 and any(not occupied & (1 << z) for z in range(lower + 1, upper)):
                    return program.zero
        clauses = [program.not_(pins[rank]) for rank in ordinary_ranks]
        for rank, r in enumerate(sources):
            if r and not occupied & (1 << (r - 1)):
                clauses.append(program.not_(pins[rank]))
            if r and any(z > r for z in crystal_rows):
                prefix = (1 << r) - 1
                previous = program.and_(*pins[:rank]) if keep & prefix == prefix else program.zero
                clauses.append(program.or_(program.not_(pins[rank]), previous))
        return program.and_(positions(keep), crystal_positions(crystals), program.and_(*clauses))

    for occupied, buckets in enumerate(SOURCE_PATTERNS):
        for count, patterns in enumerate(buckets):
            bucket = program.and_(valid_target, floor[occupied], counts[-1][count])
            for index, (keep, crystals) in enumerate(patterns):
                slots[index].append(program.and_(bucket, allowed(keep, crystals)))
    return tuple(program.or_(*choices) for choices in slots)


def _prefix_or(program: CornerProgram, values: tuple[Ref, ...]) -> tuple[Ref, ...]:
    """分半共用所有前缀，避免逐个前缀重新展开或串成二十级路径。"""
    if not values:
        return (program.zero,)
    if len(values) == 1:
        return (program.zero, values[0])
    middle = len(values) // 2
    left = _prefix_or(program, values[:middle])
    right = _prefix_or(program, values[middle:])
    return (*left, *(program.or_(left[-1], value) for value in right[1:]))


def slot_cursor(program: CornerProgram, target: ColumnTarget, addresses: tuple[Ref, ...],
                forbidden_crystals: tuple[Ref, ...] = ()) -> SlotCursor:
    """按固定目标约束取下一个合法槽；禁位不依赖其他列当前地址。"""
    valid = valid_slots(program, target, forbidden_crystals)
    if len(addresses) != len(valid):
        raise ValueError("合法槽后继需要二十个原地址标志")
    address_prefix = _prefix_or(program, addresses)
    valid_prefix = _prefix_or(program, valid)
    later = tuple(program.and_(event, address_prefix[i]) for i, event in enumerate(valid))
    later_prefix = _prefix_or(program, later)
    wrap = program.not_(later_prefix[-1])
    first_choices = []
    following_choices = []
    for i, event in enumerate(valid):
        first = program.and_(event, program.not_(valid_prefix[i]))
        following = program.and_(later[i], program.not_(later_prefix[i]))
        first_choices.append(program.circuit.add("LogicGateIf", Literal(i), first))
        following_choices.append(program.circuit.add("LogicGateIf", Literal(i), following))
    has = valid_prefix[-1]
    first_choices.append(program.circuit.add("LogicGateIf", Literal(0), program.not_(has)))
    program.circuit.aliases.extend((tuple(first_choices), tuple(following_choices)))
    first = first_choices[0]
    return SlotCursor(first, program.pick(wrap, first, following_choices[0]), wrap, has)
