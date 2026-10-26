"""以支撑可达队列判断K/G类；四象限可用作制造前必要筛选。"""

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
