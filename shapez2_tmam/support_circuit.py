"""四象限K/G支撑可达性；列A网格使用有限逐行闭包。"""

from .circuit import Ref
from .corner_program import CornerProgram
from .half_circuit import MaterialCell
from .ring_circuit import row_reach


def _admissible_reach(program: CornerProgram, columns: tuple[tuple[MaterialCell, ...], ...],
                      nonpins: tuple[tuple[Ref, ...], ...], pin_seed: Ref) -> tuple[tuple[Ref, ...], ...]:
    """列A使第二行C已接地；剩余三行按每行至多两个分量求闭包。"""
    def upward(z: int, below: tuple[Ref, ...]) -> tuple[Ref, ...]:
        seeds = tuple(program.or_(program.and_(columns[q][z].occupied, below[q]),
                                  program.and_(columns[q][z].pin, pin_seed)) for q in range(4))
        return row_reach(program, tuple(nonpins[q][z] for q in range(4)), seeds)

    def downward(z: int, old: tuple[Ref, ...], above: tuple[Ref, ...]) -> tuple[Ref, ...]:
        seeds = tuple(program.or_(old[q], program.and_(columns[q][z].crystal,
                      columns[q][z + 1].crystal, above[q])) for q in range(4))
        return row_reach(program, tuple(nonpins[q][z] for q in range(4)), seeds)

    def upper_pair(below: tuple[Ref, ...]) -> tuple[Ref, ...]:
        """返回上部两行闭包的下行；上行由一次upward恢复。"""
        lower = upward(3, below)
        upper = upward(4, lower)
        return downward(3, lower, upper)

    ground = tuple(column[0].occupied for column in columns)
    second = upward(1, ground)
    middle = upward(2, second)
    lower = upper_pair(middle)
    middle = downward(2, middle, lower)
    lower = upper_pair(middle)
    rows = (ground, second, middle, lower, upward(4, lower))
    return tuple(tuple(row[q] for row in rows) for q in range(4))


def in_support_class(program: CornerProgram, columns: tuple[tuple[MaterialCell, ...], ...], *,
                     grounded: Ref | None = None, optional_top: Ref | None = None, admissible: bool = False) -> Ref:
    """共用K/G通路；admissible要求调用端另行保证列A，可选顶格仅放宽末端。"""
    if len(columns) != 4 or any(len(column) != 5 for column in columns):
        raise ValueError("K支撑筛选需要四列五个原层位")
    nonpins = tuple(tuple(program.and_(cell.occupied, program.not_(cell.pin)) for cell in column)
                    for column in columns)
    pin_seed = program.one if grounded is None else program.not_(grounded)
    if admissible:
        reachable = _admissible_reach(program, columns, nonpins, pin_seed)
    else:
        reachable = tuple(tuple(cell.occupied if z == 0 else program.and_(cell.pin, pin_seed) for z, cell in enumerate(column))
                          for column in columns)
        # 任意网格仍用十九边简单路径界，不依赖列A。
        for _ in range(19):
            following = []
            for q, column in enumerate(columns):
                values = [reachable[q][0]]
                for z in range(1, 5):
                    paths = [reachable[q][z - 1]]
                    paths.extend(program.and_(nonpins[neighbor][z], reachable[neighbor][z])
                                 for neighbor in ((q - 1) % 4, (q + 1) % 4))
                    if z < 4:
                        paths.append(program.and_(column[z].crystal, column[z + 1].crystal, reachable[q][z + 1]))
                    pin_support = program.zero if grounded is None else program.and_(column[z].pin, reachable[q][z - 1])
                    values.append(program.or_(reachable[q][z], pin_support, program.and_(nonpins[q][z], program.or_(*paths))))
                following.append(tuple(values))
            reachable = tuple(following)
    clauses = []
    for q, column in enumerate(columns):
        for z, cell in enumerate(column):
            optional = (program.and_(optional_top, nonpins[q][z], program.not_(cell.crystal))
                        if optional_top is not None and z == 4 else program.zero)
            clauses.append(program.or_(program.not_(cell.occupied), reachable[q][z], optional))
    clauses.extend(program.or_(program.not_(column[z].pin), column[z - 1].occupied)
                   for column in columns for z in range(1, 5))
    return program.and_(*clauses)
