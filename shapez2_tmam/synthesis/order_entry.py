"""从五层原色行取得尾针搜索深度与供料范围。"""

from .physics import Shape
from .shape_methods import analyze_color, analyze_part, rotate_ccw, shape_literal


def _crystal(row: Shape | None) -> bool:
    return analyze_part(row) == shape_literal("cu------")


def _uncolored(row: Shape | None) -> bool:
    return _crystal(row) & (analyze_color(row) == "u")


def order_row_crystal(row: Shape | None) -> bool:
    second = rotate_ccw(row)
    third = rotate_ccw(second)
    fourth = rotate_ccw(third)
    return _crystal(row) | _crystal(second) | _crystal(third) | _crystal(fourth)


def order_row_unknown(row: Shape | None) -> bool:
    second = rotate_ccw(row)
    third = rotate_ccw(second)
    fourth = rotate_ccw(third)
    return _uncolored(row) | _uncolored(second) | _uncolored(third) | _uncolored(fourth)


def order_pin_budget(z2: bool, z3: bool, z4: bool) -> int:
    if z4:
        return 3
    if z3:
        return 2
    if z2:
        return 1
    return 0


def order_nonempty(row0: Shape | None, row1: Shape | None, row2: Shape | None,
                   row3: Shape | None, row4: Shape | None) -> bool:
    return (row0 is not None) | (row1 is not None) | (row2 is not None) | (row3 is not None) | (row4 is not None)


def order_unknown(u0: bool, u1: bool, u2: bool, u3: bool, u4: bool) -> bool:
    return u0 | u1 | u2 | u3 | u4
