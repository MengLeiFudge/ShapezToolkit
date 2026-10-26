"""规范化顶针族的精确物理匹配；不以物理匹配替代前态可制作性。"""

from .corners import CornerBuilder
from .physics import EMPTY, PIN, Position, Rules, Shape


def pin_base_possible(target: Shape) -> bool:
    """列A来源的Pin/S尾部必要条件：低层保留C下方有新增针及不动格。"""
    for z, row in enumerate(target.layers[:3]):
        for q, cell in enumerate(row):
            if cell[0] != "c":
                continue
            if z == 0 or target.layers[0][q] != PIN:
                return False
            if z == 2 and target.layers[1][q] == EMPTY:
                return False
    return True


def pin_image_matches(rules: Rules, lower: tuple[tuple[str, ...], ...],
                       top_crystals: int, target: Shape) -> bool:
    """以最大静止集合及块支撑确认Pin结果；不运行前态制造或重力。"""
    if rules.quadrants != 4 or len(lower) != 4 or any(len(row) != 4 for row in lower):
        raise ValueError("顶针像精确判据需要四象限、前四层来源")
    if not 0 <= top_crystals < 16:
        raise ValueError("顶层晶体掩码需要在0～15之间")
    desired = rules.cells(target)
    original = {(r, q): cell for r, row in enumerate(lower) for q, cell in enumerate(row) if cell != EMPTY}
    original.update({(4, q): "cr" for q in range(4) if top_crystals & (1 << q)})
    if any(cell[0] == "c" for (z, _), cell in desired.items() if z == 0):
        return False
    for q in range(4):
        if ((0, q) in original) != (desired.get((0, q)) == PIN):
            return False
    deleted = set().union(*(group for group in rules.groups(original, fused=True)
                            if any(z == 4 for z, _ in group)))
    for (z, q), cell in desired.items():
        if cell[0] == "c" and (original.get((z - 1, q)) != cell or (z - 1, q) in deleted):
            return False
    landings: dict[Position, int] = {}
    for q in range(4):
        sources = [(r, row[q]) for r, row in enumerate(lower) if row[q] != EMPTY and row[q][0] != "c"]
        retained = sorted((z, cell) for (z, column), cell in desired.items() if column == q
                          and cell[0] != "c" and not (z == 0 and cell == PIN))
        if len(sources) != len(retained):
            return False
        for (r, source), (z, cell) in zip(sources, retained):
            if source != cell or z > r + 1:
                return False
            if any(z < height <= r + 1 and column == q and crystal[0] == "c"
                   for (height, column), crystal in desired.items()):
                return False
            landings[r + 1, q] = z
    live = {(r + 1, q): cell for (r, q), cell in original.items() if r < 4 and (r, q) not in deleted}
    live.update({(0, q): PIN for q in range(4) if (0, q) in original})
    fixed = {pos for pos, cell in live.items() if pos[0] == 0 or (
        desired.get(pos, EMPTY)[0] == "c" if cell[0] == "c" else landings[pos] == pos[0])}
    groups = rules.groups(live)
    owner = {pos: index for index, group in enumerate(groups) for pos in group}
    ground = {owner[pos] for pos in live if pos[0] == 0}
    edges = [set() for _ in groups]
    for (z, q), index in owner.items():
        below = owner.get((z - 1, q))
        if below is not None and below != index:
            edges[index].add(below)
    # 列A使Pin活图的最大静止集合等于地面可达；任意网格仍用一般最大不动点。
    admissible = all(CornerBuilder.admissible(tuple(original.get((z, q), EMPTY) for z in range(5)))
                     for q in range(4))
    stationary = set(ground) if admissible else set(range(len(groups)))
    while True:
        following = {index for index in range(len(groups)) if index in ground or edges[index] & stationary}
        if following == stationary:
            break
        stationary = following
    if fixed != {pos for index in stationary for pos in groups[index]}:
        return False
    moving = {pos: cell for pos, cell in live.items() if pos not in fixed and cell[0] != "c"}
    for block in rules.groups(moving):
        heights = {landings[pos] for pos in block}
        if len(heights) != 1:
            return False
        height = next(iter(heights))
        if height and not any((height - 1, q) in desired for _, q in block):
            return False
    return True
