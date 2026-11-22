"""四象限纯普通格与针的逐层支撑判定。"""

from .physics import Shape
from .shape_methods import analyze_part, rotate_ccw, shape_literal


def _unsupported(pin: bool, ordinary: bool, near_anchor: bool, far_anchor: bool, bridge: bool) -> bool:
    return pin or (ordinary and not near_anchor and not (far_anchor and bridge))


def addition_needs_lower(cell: int, left: int, right: int, opposite: int) -> bool:
    """状态 0 表示无新增格，1/2 表示普通格，3/4 表示针；2 和 4 有直接下挡。"""
    return _unsupported(cell == 3, cell == 1, left == 2 or right == 2,
                        opposite == 2, left == 1 or right == 1)


def advance_stack_height(height: int, row_height: int, cell: int,
                         left: int, right: int, opposite: int) -> int:
    """更新本列前缀；row_height 是当前层号加一，四格状态用更新前的高度。"""
    if addition_needs_lower(cell, left, right, opposite):
        return row_height
    return height


def stack_scan_q0(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    """更新 q0 的前缀高度。row 为当前层的支撑代码，row_height 从 5 降至 1。"""
    q1 = rotate_ccw(row)
    q2 = rotate_ccw(q1)
    q3 = rotate_ccw(q2)
    cell = analyze_part(row)
    left = analyze_part(q3)
    right = analyze_part(q1)
    opposite = analyze_part(q2)
    loose = shape_literal("Cu------")
    anchored = shape_literal("Ru------")
    left_new = h3 < row_height
    right_new = h1 < row_height
    near_anchor = (left_new and left == anchored) or (right_new and right == anchored)
    far_anchor = h2 < row_height and opposite == anchored
    bridge = (left_new and left == loose) or (right_new and right == loose)
    if h0 < row_height and _unsupported(cell == shape_literal("Su------"), cell == loose,
                                        near_anchor, far_anchor, bridge):
        return row_height
    return h0


def stack_scan_q1(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    return stack_scan_q0(h1, h2, h3, h0, rotate_ccw(row), row_height)


def stack_scan_q2(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    return stack_scan_q0(h2, h3, h0, h1, rotate_ccw(rotate_ccw(row)), row_height)


def stack_scan_q3(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    return stack_scan_q0(h3, h0, h1, h2, rotate_ccw(rotate_ccw(rotate_ccw(row))), row_height)
