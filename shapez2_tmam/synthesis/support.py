"""以格位可达性判断K支撑类；四象限可用作制造前必要筛选。"""

from .physics import PIN, Rules, Shape


def in_support_class(rules: Rules, target: Shape, *, grounded: bool = False) -> bool:
    """默认精确判K；grounded模式只以地面作种子，精确判G。"""
    cells = rules.cells(target)
    if any(cell == PIN and z and (z - 1, q) not in cells for (z, q), cell in cells.items()):
        return False
    reachable = {pos for pos, cell in cells.items() if pos[0] == 0 or (not grounded and cell == PIN)}
    for _ in range(max(0, len(cells) - 1)):
        following = set(reachable)
        for (z, q), cell in cells.items():
            if (z, q) in reachable:
                continue
            supported = (z - 1, q) in reachable
            if cell != PIN:
                supported |= any((z, neighbor) in reachable and cells[(z, neighbor)] != PIN
                                 for neighbor in ((q - 1) % rules.quadrants, (q + 1) % rules.quadrants))
                above = (z + 1, q)
                supported |= cell[0] == "c" and above in reachable and cells[above][0] == "c"
            if supported:
                following.add((z, q))
        if following == reachable:
            break
        reachable = following
    return len(reachable) == len(cells)
