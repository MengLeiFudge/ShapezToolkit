"""四象限五层的半形起点与堆叠所需前缀。"""

from .corners import CornerBuilder
from .physics import EMPTY, PIN, Position, Rules, Shape
from .row_support import addition_needs_lower, advance_stack_height
from .support import in_support_class


def _row_states(desired: dict[Position, str], z: int, added: dict[int, str]) -> tuple[int, ...]:
    states = [0] * 4
    for q, cell in added.items():
        supported = z == 0 or (z - 1, q) in desired
        states[q] = (3 if cell == PIN else 1) + int(supported)
    return tuple(states)


def close_stack_prefix(desired: dict[Position, str], heights: list[int], layers: int) -> None:
    """四象限保晶前缀从上至下纳入每层缺少下挡的新增块。"""
    for z in range(layers - 1, -1, -1):
        added = {q: desired[z, q] for q in range(4) if z >= heights[q] and (z, q) in desired}
        row = _row_states(desired, z, added)
        for q in added:
            heights[q] = advance_stack_height(heights[q], z + 1, row[q],
                                              row[q - 1], row[(q + 1) % 4], row[(q + 2) % 4])


def unanchored_additions(rules: Rules, desired: dict[Position, str], lower: dict[Position, str],
                         *, optional_top: bool = False) -> set[Position]:
    """找出没有直接下挡的新增块；这些块的每一格都须预置在下料。"""
    delta = {pos: cell for pos, cell in desired.items() if pos not in lower
             and not (optional_top and pos[0] == rules.height - 1 and cell[0] != "c")}
    if rules.quadrants == 4 and all(cell[0] != "c" for cell in delta.values()):
        rows: dict[int, dict[int, str]] = {}
        for (z, q), cell in delta.items():
            rows.setdefault(z, {})[q] = cell
        forced = set()
        for z, added in rows.items():
            row = _row_states(desired, z, added)
            forced.update((z, q) for q in added
                          if addition_needs_lower(row[q], row[q - 1], row[(q + 1) % 4], row[(q + 2) % 4]))
        return forced
    forced = set()
    for block in rules.groups(delta):
        if not any(z == 0 or (z - 1, q) in desired for z, q in block):
            forced.update(block)
    return forced


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
        forced.update(unanchored_additions(rules, desired, original, optional_top=optional_top))
        if not forced:
            return rules.fold(original)
        for z, q in forced:
            heights[q] = max(heights[q], z + 1)
