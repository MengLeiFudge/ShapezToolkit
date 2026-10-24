"""四象限五层中，一段单层 N/P 上料堆叠的逐层配方与最短配方。

只解决已知 K 下料到目标之间的追加段，不判定含晶体目标的完整可制作性。
证明、状态界和游戏电路取舍见 4q5l/compact-synthesis.md。
"""

from collections import deque

from .mari.shapes import EMPTY, PIN, Shape


_Column = tuple[tuple[int, str], ...]


def _in_support_class(shape: Shape) -> bool:
    """检查每个粘连组能否到达地面或含独立顶针的支撑环，即支撑类 K。"""
    cells = {(z, q): cell for z, row in enumerate(shape.layers)
             for q, cell in enumerate(row) if cell != EMPTY}
    owner: dict[tuple[int, int], int] = {}
    groups: list[set[tuple[int, int]]] = []
    for pos in cells:
        if pos in owner:
            continue
        index = len(groups)
        group = {pos}
        owner[pos] = index
        pending = [pos]
        while pending:
            z, q = pending.pop()
            cell = cells[z, q]
            if cell == PIN:
                continue
            neighbors = [(z, (q - 1) % 4), (z, (q + 1) % 4)]
            if cell[0] == "c":
                neighbors.extend((r, q) for r in (z - 1, z + 1)
                                 if cells.get((r, q), EMPTY)[0] == "c")
            for neighbor in neighbors:
                if neighbor not in owner and cells.get(neighbor, EMPTY) not in (EMPTY, PIN):
                    owner[neighbor] = index
                    group.add(neighbor)
                    pending.append(neighbor)
        groups.append(group)

    ground = {owner[pos] for pos in cells if pos[0] == 0}
    pins = {owner[pos] for pos, cell in cells.items() if cell == PIN}
    reach: list[set[int]] = [set() for _ in groups]
    for (z, q), index in owner.items():
        below = owner.get((z - 1, q))
        if below is not None and below != index:
            reach[index].add(below)
    # 不预置自达边；只有真实非空支撑环才能使一个针节点到达自身。
    for middle in range(len(groups)):
        for destinations in reach:
            if middle in destinations:
                destinations.update(reach[middle])
    roots = ground | {index for index in pins if index in reach[index]}
    return all(index in roots or bool(destinations & roots)
               for index, destinations in enumerate(reach))


def _can_append(columns: tuple[_Column, ...], counts: tuple[int, ...], mask: int) -> bool:
    """检查所选列的下一目标格能否作为一份单层上料落到各自目标高度。"""
    selected = {q for q in range(4) if mask & (1 << q)}
    if any(counts[q] == len(columns[q]) for q in selected):
        return False
    heights = [columns[q][counts[q] - 1][0] if counts[q] else -1 for q in range(4)]
    pending = selected.copy()
    while pending:
        q = min(pending)
        pending.remove(q)
        group = {q}
        # 普通块按上料中的环邻接分组，不能借用下料同层的普通格连接。
        if columns[q][counts[q]][1] != PIN:
            queue = [q]
            while queue:
                current = queue.pop()
                for neighbor in ((current - 1) % 4, (current + 1) % 4):
                    if neighbor in pending and columns[neighbor][counts[neighbor]][1] != PIN:
                        pending.remove(neighbor)
                        group.add(neighbor)
                        queue.append(neighbor)
        landing = 1 + max(heights[j] for j in group)
        if any(columns[j][counts[j]][0] != landing for j in group):
            return False
    return True


def _prepare(lower: Shape | None, target: Shape) -> tuple[tuple[_Column, ...], tuple[int, ...]] | None:
    """校验 K 下料及每列前缀，排除需要增加晶体、移除或修改旧格的目标。"""
    if lower is not None and not _in_support_class(lower):
        raise ValueError("下料不属于支撑类 K，不能使用连续堆叠规划")
    columns = tuple(tuple((z, row[q]) for z, row in enumerate(target.layers)
                          if row[q] != EMPTY) for q in range(4))
    initial = []
    for q, column in enumerate(columns):
        old = ()
        if lower is not None:
            old = tuple((z, row[q]) for z, row in enumerate(lower.layers) if row[q] != EMPTY)
        if column[:len(old)] != old or any(cell[0] == "c" for _, cell in column[len(old):]):
            return None
        initial.append(len(old))
    return columns, tuple(initial)


def plan_layer_stacks(lower: Shape | None, target: Shape) -> tuple[Shape, ...] | None:
    """按目标高度逐层追加，至多五份单层上料，不保存候选状态表。

    输入、返回值和失败语义与 plan_stacks 相同；本函数不要求上料份数最少。
    对 lower=None 的无晶体目标，首份直接取为原料，随后至多四次堆叠。
    """
    prepared = _prepare(lower, target)
    if prepared is None:
        return None
    columns, counts = prepared
    layers = []
    for z in range(len(target.layers)):
        mask = sum(1 << q for q in range(4)
                   if counts[q] < len(columns[q]) and columns[q][counts[q]][0] == z)
        if not mask:
            continue
        if not _can_append(columns, counts, mask):
            return None
        row = tuple(columns[q][counts[q]][1] if mask & (1 << q) else EMPTY for q in range(4))
        layers.append(Shape((row,)))
        counts = tuple(counts[q] + int(bool(mask & (1 << q))) for q in range(4))
    return tuple(layers)


def plan_stacks(lower: Shape | None, target: Shape) -> tuple[Shape, ...] | None:
    """返回从 K 下料追加到目标所需的最少单层上料，保留所有种类和颜色。

    图形应由 Shape.from_key 解析。lower=None 表示尚未取料，此时返回序列
    的第一份直接作为基础物品，其余依次堆叠；不向机器传入空物品。
    非空 lower 不属于 K 时抛 ValueError，避免把稳定性当作 K。

    返回空元组表示无需追加；None 表示不存在这种单层 N/P 追加方案，
    不表示目标通过切割、顶针等其他方法也不可制作。lower=None 且目标
    无晶体时，此函数也给出完整的可制作判定和基础原料到目标的配方。
    每段至多 1296 个前缀状态，每状态至多 15 个选择，不运行物理模拟。
    """
    prepared = _prepare(lower, target)
    if prepared is None:
        return None
    columns, start = prepared
    goal = tuple(len(column) for column in columns)
    parents: dict[tuple[int, ...], tuple[tuple[int, ...], int] | None] = {start: None}
    pending = deque([start])
    while pending:
        counts = pending.popleft()
        if counts == goal:
            layers = []
            while (parent := parents[counts]) is not None:
                previous, mask = parent
                row = tuple(columns[q][previous[q]][1] if mask & (1 << q) else EMPTY
                            for q in range(4))
                layers.append(Shape((row,)))
                counts = previous
            return tuple(reversed(layers))
        for mask in range(1, 1 << 4):
            if not _can_append(columns, counts, mask):
                continue
            following = tuple(counts[q] + int(bool(mask & (1 << q))) for q in range(4))
            if following not in parents:
                parents[following] = counts, mask
                pending.append(following)
    return None
