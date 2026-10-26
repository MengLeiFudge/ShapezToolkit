"""以格位可达性判断K支撑类；四象限可用作制造前必要筛选。"""

from .physics import PIN, Rules, Shape


def in_support_class(rules: Rules, target: Shape, *, grounded: bool = False, optional_top: bool = False) -> bool:
    """判K或仅地面种子的G；可选模式允许模板最高层普通格不在可达集。"""
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
    return all(pos in reachable or (optional_top and pos[0] == rules.height - 1
                                    and cell != PIN and cell[0] != "c") for pos, cell in cells.items())
