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
    """判含接地屏障的K_X充分条件；失败不表示不可制造或不能约化。"""
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
    analysis = {pos: cell for pos, cell in cells.items() if owner[pos] not in grounded}
    reachable: set[int] = set()
    for z in range(height):
        reachable.update(q for q, top in enumerate(tops)
                         if top >= 0 and top + 1 == z and owner[top, q] not in grounded)
        barriers = {q for q, top in enumerate(tops) if top < z and any(
            pos in cells and cells[pos] != PIN and owner[pos] in grounded
            for pos in ((z, (q - 1) % n), (z, (q + 1) % n)))}
        # 屏障位置可以由针向上承接，但在本层不能作为无接地N横向传播。
        queue = deque(reachable - barriers)
        while queue:
            q = queue.popleft()
            for r in ((q - 1) % n, (q + 1) % n):
                if tops[r] < z and r not in barriers and r not in reachable:
                    reachable.add(r)
                    queue.append(r)
        analysis.update({(z, q): "Cu" for q in reachable - barriers})
    potential = {pos: index for index, group in enumerate(rules.groups(analysis)) for pos in group}
    labels = {index: potential[next(iter(group))]
              for index, group in enumerate(groups) if index not in grounded}
    crossing = {index for index in labels
                if any(labels[index] != labels[below] for below in supports[index])}
    return len(reach(grounded | crossing)) == len(groups)
