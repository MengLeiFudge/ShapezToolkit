"""以一次格位洪泛判K支撑类，不建立二十份组连通矩阵。"""

from .circuit import Ref
from .corner_program import CornerProgram
from .half_circuit import MaterialCell


def in_support_class(program: CornerProgram, columns: tuple[tuple[MaterialCell, ...], ...], *, grounded: Ref | None = None) -> Ref:
    """四列五层共用K/G洪泛；grounded为真时只以地面作种子。"""
    if len(columns) != 4 or any(len(column) != 5 for column in columns):
        raise ValueError("K支撑筛选需要四列五个原层位")
    nonpins = tuple(tuple(program.and_(cell.occupied, program.not_(cell.pin)) for cell in column)
                    for column in columns)
    pin_seed = program.one if grounded is None else program.not_(grounded)
    reachable = tuple(tuple(cell.occupied if z == 0 else program.and_(cell.pin, pin_seed) for z, cell in enumerate(column))
                      for column in columns)
    # 二十格中每条简单路径最多十九边；只传播原粘连及向下支撑。
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
    clauses = [program.or_(program.not_(cell.occupied), reachable[q][z])
               for q, column in enumerate(columns) for z, cell in enumerate(column)]
    clauses.extend(program.or_(program.not_(column[z].pin), column[z - 1].occupied)
                   for column in columns for z in range(1, 5))
    return program.and_(*clauses)
