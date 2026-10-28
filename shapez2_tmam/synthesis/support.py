"""支撑可达判K/G类，并用接地屏障与潜在粘合证书识别安全追加范围。"""

from collections import deque

from .physics import PIN, Rules, Shape


def in_support_class(rules: Rules, target: Shape, *, grounded: bool = False, optional_top: bool = False) -> bool:
    """判K或仅地面种子的G；可选模式允许模板最高层普通格不在可达集。"""
    cells = rules.cells(target)
    if any(cell == PIN and z and (z - 1, q) not in cells for (z, q), cell in cells.items()):
        return False
    reachable = {pos for pos, cell in cells.items() if pos[0] == 0 or (not grounded and cell == PIN)}
    queue = deque(reachable)
    while queue:
        z, q = queue.popleft()
        cell = cells[z, q]
        neighbors = [(z + 1, q)]
        if cell != PIN:
            neighbors.extend((z, column) for column in ((q - 1) % rules.quadrants, (q + 1) % rules.quadrants)
                             if cells.get((z, column), PIN) != PIN)
        below = (z - 1, q)
        if cell[0] == "c" and cells.get(below, PIN)[0] == "c":
            neighbors.append(below)
        for pos in neighbors:
            if pos in cells and pos not in reachable:
                reachable.add(pos)
                queue.append(pos)
    return all(pos in reachable or (optional_top and pos[0] == rules.height - 1
                                    and cell != PIN and cell[0] != "c") for pos, cell in cells.items())


def in_addition_class(rules: Rules, target: Shape) -> bool:
    """判K_add充分条件；失败不代表不可制造，也不代表复杂Stack不能约化。"""
    if in_support_class(rules, target):
        return True
    cells = rules.cells(target)
    groups = rules.groups(cells)
    owner = {pos: index for index, group in enumerate(groups) for pos in group}
    ground = {owner[pos] for pos in cells if pos[0] == 0}
    supports: list[set[int]] = [set() for _ in groups]
    dependents: list[set[int]] = [set() for _ in groups]
    for (z, q), index in owner.items():
        below = owner.get((z - 1, q))
        if below is not None and below != index:
            supports[index].add(below)
            dependents[below].add(index)
    if any(not edges and index not in ground for index, edges in enumerate(supports)):
        return False
    tops = rules.column_tops(cells)
    if len({top for top in tops if top >= 0}) == 1:
        return True

    def reach(seeds: set[int]) -> set[int]:
        """沿支撑边反向扩展；同一图用于地面种子和跨潜在组支撑边种子。"""
        reached = set(seeds)
        queue = deque(seeds)
        while queue:
            for above in dependents[queue.popleft()]:
                if above not in reached:
                    reached.add(above)
                    queue.append(above)
        return reached

    grounded = reach(ground)
    n = rules.quadrants
    height = len(target.layers)
    starts = [top + 1 if top >= 0 and owner[top, q] not in grounded else height
              for q, top in enumerate(tops)]
    # 接地屏障只在空列区间端点；提前阻断水平传播不会改变旧Q的潜在分组。
    root = min(range(n), key=lambda q: starts[q])
    for direction in (1, -1):
        for step in range(n):
            q = (root + direction * step) % n
            r = (q + direction) % n
            starts[r] = min(starts[r], max(starts[q], tops[r] + 1))
    analysis = {pos: cell for pos, cell in cells.items() if owner[pos] not in grounded}
    for q, start in enumerate(starts):
        for z in range(start, height):
            neighbors = ((z, (q - 1) % n), (z, (q + 1) % n))
            if not any(pos in cells and cells[pos] != PIN and owner[pos] in grounded for pos in neighbors):
                analysis[z, q] = "Cu"
    potential = {pos: index for index, group in enumerate(rules.groups(analysis)) for pos in group}
    labels = {index: potential[next(iter(group))]
              for index, group in enumerate(groups) if index not in grounded}
    crossing = {index for index in labels
                if any(labels[index] != labels[below] for below in supports[index])}
    return len(reach(grounded | crossing)) == len(groups)
