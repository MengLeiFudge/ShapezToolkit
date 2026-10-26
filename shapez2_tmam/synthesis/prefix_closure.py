"""两列半形与追加块的强制支撑闭包；仅用于四象限零Pin起点。"""

from .corners import CornerBuilder
from .physics import EMPTY, PIN, Rules, Shape
from .support import in_support_class


def minimal_start(rules: Rules, target: Shape, start: int, *, optional_top: bool = False) -> Shape | None:
    """求最小A→S前态；可将第4层普通格作为只在A中保留的可选助手。"""
    if rules.quadrants != 4 or rules.height != 5 or start not in (0, 1):
        raise ValueError("前缀强制闭包需要四象限五层及切向0或1")
    desired = rules.cells(target)
    columns = tuple(tuple(row[q] for row in target.layers) for q in range(4))
    if any(not CornerBuilder.admissible(column) for column in columns):
        return None
    heights = [max((z + 1 for z, cell in enumerate(column) if cell[0] == "c"), default=0)
               for column in columns]
    if not any(heights):
        if not in_support_class(rules, target):
            return None
        return rules.fold({pos: cell for pos, cell in desired.items() if pos[0] == 0})
    while True:
        original = {pos: cell for pos, cell in desired.items() if pos[0] < heights[pos[1]]}
        forced: set[tuple[int, int]] = set()
        for side in (0, 2):
            pair = tuple((start + side + q) % 4 for q in (0, 1))
            links = [False] + [any(columns[q][z][0] == "c" and columns[q][z - 1][0] == "c"
                                   for q in pair) for z in range(1, len(target.layers))]
            lower = 0
            for upper in range(len(target.layers)):
                if upper + 1 < len(target.layers) and links[upper + 1]:
                    continue
                interval = tuple((z, q) for z in range(lower, upper + 1) for q in pair)
                nonpins = tuple(pos for pos in interval if original.get(pos, EMPTY) not in (EMPTY, PIN))
                witnesses = tuple((z, q) for z, q in interval
                                  if desired.get((z, q), EMPTY) not in (EMPTY, PIN)
                                  and (z == 0 or (not links[z] and (z - 1, q) in desired)
                                       or desired.get((z - 1, q)) == PIN))
                if nonpins and not any(pos in original for pos in witnesses):
                    candidates = tuple(pos for pos in witnesses if desired[pos][0] != "c")
                    if not candidates:
                        return None
                    # 两列最高C屏障保证坏组的候选最多位于一列；取该列最低见证。
                    for q in pair:
                        lowest = next((pos for pos in candidates if pos[1] == q), None)
                        if lowest is not None:
                            forced.add(lowest)
                lower = upper + 1
        delta = {pos: cell for pos, cell in desired.items() if pos not in original
                 and not (optional_top and pos[0] == 4 and cell[0] != "c")}
        for block in rules.groups(delta):
            if not any(z == 0 or (z - 1, q) in desired for z, q in block):
                forced.update(block)
        if not forced:
            return rules.fold(original)
        for z, q in forced:
            heights[q] = max(heights[q], z + 1)
