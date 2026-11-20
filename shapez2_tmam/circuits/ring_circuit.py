"""四列圆环的行连通闭包，以及与顶边相连的晶体格。"""

from .circuit import Ref
from .corner_program import CornerProgram


def row_reach(program: CornerProgram, occupied: tuple[Ref, ...], seeds: tuple[Ref, ...]) -> tuple[Ref, ...]:
    """四格环连通距离至多二；未参与水平连接的种子只保留自身。"""
    if len(occupied) != 4 or len(seeds) != 4:
        raise ValueError("四列行闭包需要四个占用位及四个种子位")
    reached = []
    for q in range(4):
        paths = [seeds[q]]
        for other in range(4):
            if other == q:
                continue
            middle = program.or_(occupied[(q - 1) % 4], occupied[(q + 1) % 4]) if (q - other) % 4 == 2 else program.one
            connected = program.and_(occupied[q], occupied[other], middle)
            paths.append(program.and_(connected, seeds[other]))
        reached.append(program.or_(*paths))
    return tuple(reached)


def top_connected(program: CornerProgram, crystals: tuple[tuple[Ref, ...], ...]) -> tuple[tuple[Ref, ...], ...]:
    """任意正高度四列C网格，先向下扫描，再向上补齐其余分支；不需要往复迭代。"""
    if not crystals or any(len(row) != 4 for row in crystals):
        raise ValueError("顶边晶体连通需要非空的四列原层位网格")
    down = [(program.zero,) * 4 for _ in crystals]
    down[-1] = crystals[-1]
    for z in range(len(crystals) - 2, -1, -1):
        down[z] = row_reach(program, crystals[z], tuple(program.and_(crystals[z][q], down[z + 1][q]) for q in range(4)))
    reached = [down[0]]
    for z in range(1, len(crystals)):
        reached.append(crystals[z] if z == len(crystals) - 1 else row_reach(program, crystals[z], tuple(
            program.or_(down[z][q], program.and_(crystals[z][q], reached[z - 1][q])) for q in range(4))))
    return tuple(reached)
