"""四象限纯普通格与针的逐层支撑判定。"""

from .physics import Shape
from .shape_methods import analyze_part, rotate_ccw, shape_literal


def _unsupported(pin: bool, ordinary: bool, near_anchor: bool, far_anchor: bool, bridge: bool) -> bool:
    return pin | (ordinary & (not near_anchor) & (not (far_anchor & bridge)))


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


def plain_anchor_height(height: int, partner_height: int, row_height: int, cell: int, partner: int) -> int:
    if (height >= 0) & (height < row_height) & (cell == 2) & (partner == 1) & (partner_height >= row_height):
        return row_height
    return height


def plain_support_missing(height: int, row_height: int, cell: int, partner: int) -> bool:
    return (height >= row_height) & (cell == 1) & (partner != 2) & (partner != 5)


def _keep_plain(keep: bool, part: Shape | None, partner_keep: bool, partner: Shape | None) -> bool:
    return keep | ((part == shape_literal("Ru------")) & partner_keep & (partner == shape_literal("Cu------")))


def _close_prefix_row(h0: int, h1: int, h2: int, h3: int, row: Shape | None,
                      row_height: int, partner_ccw: bool) -> int:
    row1 = rotate_ccw(row)
    row2 = rotate_ccw(row1)
    row3 = rotate_ccw(row2)
    s0 = analyze_part(row)
    s1 = analyze_part(row1)
    s2 = analyze_part(row2)
    s3 = analyze_part(row3)
    k0 = h0 >= row_height
    k1 = h1 >= row_height
    k2 = h2 >= row_height
    k3 = h3 >= row_height
    if partner_ccw:
        own = _keep_plain(k0, s0, k1, s1)
        near = _keep_plain(k1, s1, k0, s0)
        far = _keep_plain(k2, s2, k3, s3)
        other = _keep_plain(k3, s3, k2, s2)
        partner = s1
    else:
        own = _keep_plain(k0, s0, k3, s3)
        near = _keep_plain(k1, s1, k2, s2)
        far = _keep_plain(k2, s2, k1, s1)
        other = _keep_plain(k3, s3, k0, s0)
        partner = s3
    loose = shape_literal("Cu------")
    anchored = shape_literal("Ru------")
    near_anchor = ((not near) & (s1 == anchored)) | ((not other) & (s3 == anchored))
    far_anchor = (not far) & (s2 == anchored)
    bridge = ((not near) & (s1 == loose)) | ((not other) & (s3 == loose))
    required = own | _unsupported(s0 == shape_literal("Su------"), s0 == loose, near_anchor, far_anchor, bridge)
    missing = required & (s0 == loose) & (partner != anchored) & (partner != shape_literal("P-------"))
    if (h0 < 0) | missing:
        return -1
    if required & (h0 < row_height):
        return row_height
    return h0


def prefix_scan_q0(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    return _close_prefix_row(h0, h1, h2, h3, row, row_height, True)


def prefix_scan_q1(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    return _close_prefix_row(h1, h2, h3, h0, rotate_ccw(row), row_height, False)


def prefix_scan_q2(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    return prefix_scan_q0(h2, h3, h0, h1, rotate_ccw(rotate_ccw(row)), row_height)


def prefix_scan_q3(h0: int, h1: int, h2: int, h3: int, row: Shape | None, row_height: int) -> int:
    return prefix_scan_q1(h2, h3, h0, h1, rotate_ccw(rotate_ccw(row)), row_height)
