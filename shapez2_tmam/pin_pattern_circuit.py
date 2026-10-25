"""按至多二十个来源模式选址的顶针单列通路，供四列及递归控制共用。"""

from .circuit import Literal, Ref
from .corner_program import CornerProgram
from .pin_column_circuit import PinColumn, _prefix_counts, column_candidate
from .synthesis.pin_patterns import SOURCE_PATTERNS


def pattern_column(program: CornerProgram, materials: tuple[Ref, ...], tags: tuple[Ref, ...],
                   slot: Ref, enable: Ref, *, with_landings: bool = False) -> PinColumn:
    """slot为0～19整数；桶内补空槽或遗漏强制C的模式无效。"""
    if len(materials) != 5 or len(tags) != 5:
        raise ValueError("二十槽单列通路需要五格材料和标签")
    circuit = program.circuit
    kinds = tuple(tuple(circuit.add("LogicGateCompare", value, Literal(kind), config="AQ==")
                        for kind in range(4)) for value in materials)
    retained = [kinds[0][1]] + [program.or_(row[1], row[2]) for row in kinds[1:]]
    counts = _prefix_counts(circuit, retained)[-1]
    addresses = tuple(circuit.add("LogicGateCompare", slot, Literal(index), config="AQ==") for index in range(20))
    floor = (program.not_(kinds[0][2]), kinds[0][2])
    selected: list[tuple[Ref, int, int]] = []
    for occupied, buckets in enumerate(SOURCE_PATTERNS):
        for count, patterns in enumerate(buckets):
            bucket = program.and_(floor[occupied], counts[count])
            for index, (keep, crystals) in enumerate(patterns):
                selected.append((program.and_(bucket, addresses[index]), keep, crystals))
    keep_bits = tuple(program.or_(*(chosen for chosen, keep, _ in selected if keep & (1 << r))) for r in range(4))
    crystal_bits = tuple(program.or_(*(chosen for chosen, _, crystals in selected if crystals & (1 << r)))
                         for r in range(4))
    forced = tuple(kinds[r + 1][3] for r in range(4))
    valid = program.and_(enable, program.or_(*(chosen for chosen, _, _ in selected)),
                         *(program.or_(program.not_(forced[r]), crystal_bits[r]) for r in range(4)))
    extra = tuple(program.and_(crystal_bits[r], program.not_(forced[r])) for r in range(4))
    return column_candidate(circuit, materials, tags, (*keep_bits, *extra), valid,
                            with_landings=with_landings)
