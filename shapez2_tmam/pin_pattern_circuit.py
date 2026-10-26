"""按至多二十个来源模式选址的顶针单列通路，供四列及递归控制共用。"""

from dataclasses import dataclass

from .circuit import Literal, Ref
from .corner_program import CornerProgram
from .pin_column_circuit import ColumnTarget, PinColumn, column_candidate, decode_column
from .pin_slot_circuit import slot_cursor
from .synthesis.pin_patterns import SOURCE_PATTERNS


@dataclass(frozen=True)
class PatternColumn:
    """候选通路及单列合法槽的后继；has_slots不依赖当前槽号。"""

    column: PinColumn
    last_slot: Ref
    has_slots: Ref
    next_slot: Ref


def pattern_column(program: CornerProgram, materials: tuple[Ref, ...], tags: tuple[Ref, ...],
                   slot: Ref, enable: Ref, *, with_landings: bool = False,
                   decoded_target: ColumnTarget | None = None) -> PatternColumn:
    """slot为0～19整数；桶内补空槽或遗漏强制C的模式无效。"""
    if len(materials) != 5 or len(tags) != 5:
        raise ValueError("二十槽单列通路需要五格材料和标签")
    circuit = program.circuit
    target = decoded_target if decoded_target is not None else decode_column(circuit, materials)
    kinds, counts = target.kinds, target.counts[-1]
    addresses = tuple(circuit.add("LogicGateCompare", slot, Literal(index), config="AQ==") for index in range(20))
    floor = (program.not_(kinds[0][2]), kinds[0][2])
    selected: list[tuple[Ref, int, int]] = []
    for occupied, buckets in enumerate(SOURCE_PATTERNS):
        for count, patterns in enumerate(buckets):
            bucket = program.and_(floor[occupied], counts[count])
            for index, (keep, crystals) in enumerate(patterns):
                selected.append((program.and_(bucket, addresses[index]), keep, crystals))
    keep_words = tuple(program.or_(*(chosen for chosen, keep, _ in selected if keep == mask)) for mask in range(16))
    keep_bits = tuple(program.or_(*(chosen for mask, chosen in enumerate(keep_words) if mask & (1 << r))) for r in range(4))
    keep_counts = ((program.one,),) + tuple(tuple(program.or_(*(
        chosen for mask, chosen in enumerate(keep_words) if (mask & ((1 << r) - 1)).bit_count() == count))
        for count in range(r + 1)) for r in range(1, 5))
    crystal_bits = tuple(program.or_(*(chosen for chosen, _, crystals in selected if crystals & (1 << r)))
                         for r in range(4))
    forced = tuple(kinds[r + 1][3] for r in range(4))
    extra = tuple(program.and_(crystal_bits[r], program.not_(forced[r])) for r in range(4))
    separated = tuple(program.not_(program.and_(extra[r], program.or_(*(
        forced[neighbor] for neighbor in (r - 1, r + 1) if 0 <= neighbor < 4)))) for r in range(4))
    valid = program.and_(enable, program.or_(*(chosen for chosen, _, _ in selected)), *separated,
                         *(program.or_(program.not_(forced[r]), crystal_bits[r]) for r in range(4)))
    column = column_candidate(circuit, materials, tags, (*keep_bits, *extra), valid,
                              with_landings=with_landings, decoded_target=target, keep_counts=keep_counts)
    cursor = slot_cursor(program, target, addresses)
    return PatternColumn(column, cursor.last, cursor.has, cursor.next)
