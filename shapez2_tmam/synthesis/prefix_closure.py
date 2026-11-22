"""四象限五层的半形起点与堆叠所需前缀。"""

from .corners import CornerBuilder
from .physics import EMPTY, PIN, Position, Rules, Shape
from .row_support import addition_needs_lower, advance_stack_height, plain_anchor_height, plain_support_missing
from .shape_methods import original_rows, pack_stack_row
from .support import in_support_class


def _row_states(desired: dict[Position, str], z: int, added: dict[int, str]) -> tuple[int, ...]:
    states = [0] * 4
    for q, cell in added.items():
        supported = z == 0 or (z - 1, q) in desired
        states[q] = (3 if cell == PIN else 1) + int(supported)
    return tuple(states)


def stack_scan_rows(target: Shape) -> tuple[Shape | None, ...]:
    """将支持判定的五行按扫描顺序编码为单层信号。"""
    rows = original_rows(target)
    return tuple(pack_stack_row(rows[z], rows[z - 1] if z > 0 else None, z == 0)
                 for z in range(4, -1, -1))


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


def _crystal_witnesses(left: tuple[str, ...], right: tuple[str, ...]) -> list[tuple[int, int]]:
    """记录每个含晶区间内两列的最低支撑见证。"""
    witness = [6, 6]
    thresholds = []
    linked = False
    has_crystal = False
    for z, (a, b) in enumerate(zip(left, right, strict=True)):
        has_crystal |= a[0] == "c" or b[0] == "c"
        for i, (cell, column) in enumerate(((a, left), (b, right))):
            if cell in (EMPTY, PIN):
                continue
            if z == 0 or column[z - 1] == PIN or (not linked and column[z - 1] != EMPTY):
                witness[i] = min(witness[i], z + 1)
        linked = (z + 1 < len(left)
                  and ((a[0] == "c" and left[z + 1][0] == "c")
                       or (b[0] == "c" and right[z + 1][0] == "c")))
        if not linked:
            if has_crystal:
                thresholds.append((witness[0], witness[1]))
            witness = [6, 6]
            has_crystal = False
    return thresholds


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
    pairs = tuple(((start + side) % 4, (start + side + 1) % 4) for side in (0, 2))
    for q, r in pairs:
        for witness_q, witness_r in _crystal_witnesses(columns[q], columns[r]):
            if heights[q] >= witness_q or heights[r] >= witness_r:
                continue
            if witness_q == witness_r == 6:
                return None
            if witness_q <= 5:
                heights[q] = max(heights[q], witness_q)
            if witness_r <= 5:
                heights[r] = max(heights[r], witness_r)

    for z in range(len(target.layers) - 1, -1, -1):
        added = {q: column[z] for q, column in enumerate(columns) if column[z] != EMPTY and column[z][0] != "c"}
        row = _row_states(desired, z, added)
        plain_pairs = [(q, r) for q, r in pairs if columns[q][z][0] != "c" and columns[r][z][0] != "c"]
        for q, r in plain_pairs:
            for own, neighbor in ((q, r), (r, q)):
                heights[own] = plain_anchor_height(heights[own], heights[neighbor], z + 1, row[own], row[neighbor])
        if not (optional_top and z == rules.height - 1):
            delta = tuple(state if heights[q] <= z else 0 for q, state in enumerate(row))
            heights = [advance_stack_height(heights[q], z + 1, delta[q], delta[q - 1],
                                            delta[(q + 1) % 4], delta[(q + 2) % 4]) for q in range(4)]
        for q, r in plain_pairs:
            if (plain_support_missing(heights[q], z + 1, row[q], row[r])
                    or plain_support_missing(heights[r], z + 1, row[r], row[q])):
                return None
    return rules.fold({pos: cell for pos, cell in desired.items() if pos[0] < heights[pos[1]]})
