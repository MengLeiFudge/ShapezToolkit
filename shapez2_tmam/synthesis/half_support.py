"""两列半形按层检查针支撑与普通块、晶体组的支撑。"""

from .physics import Shape
from .shape_methods import advance_target_rows, analyze_part, read_top_row_at, rotate_ccw, shape_literal


def half_support_row(lower0: int, lower1: int, upper0: int, upper1: int,
                     supported_below: bool, ground: bool, continues: bool, side_support: bool) -> int:
    """返回本段是否已有支撑。-1 表示本层针或结束的组缺少支撑。"""
    if (not ground) & (((upper0 == 2) & (lower0 == 0)) | ((upper1 == 2) & (lower1 == 0))):
        return -1
    linked = ((lower0 == 3) & (upper0 == 3)) | ((lower1 == 3) & (upper1 == 3))
    attached0 = (upper0 == 1) | (upper0 == 3)
    attached1 = (upper1 == 1) | (upper1 == 3)
    witness0 = attached0 & ((lower0 == 2) | ((not linked) & (lower0 != 0)))
    witness1 = attached1 & ((lower1 == 2) | ((not linked) & (lower1 != 0)))
    supported = ground | side_support | (linked & supported_below) | witness0 | witness1
    if supported:
        return 1
    if (attached0 | attached1) & (not continues):
        return -1
    return 0


def half_scan_remaining(remaining: Shape | None, upper: Shape | None, status: int, height: int) -> Shape | None:
    return advance_target_rows(remaining, height)


def half_scan_upper(remaining: Shape | None, upper: Shape | None, status: int, height: int) -> Shape | None:
    return read_top_row_at(remaining, height)


def half_scan_height(remaining: Shape | None, upper: Shape | None, status: int, height: int) -> int:
    if height < 1 or height > 5:
        return 0
    return (0, 0, 1, 2, 3, 4)[height]


def half_scan_status(remaining: Shape | None, upper: Shape | None, status: int, height: int) -> int:
    """向下结算标准半形。-1 拒绝，1 表示当前组已有支撑，0 表示仍须检查。"""
    if status < 0:
        return -1
    if height == 0:
        return 1
    lower = read_top_row_at(remaining, height)
    lower0 = analyze_part(lower)
    lower1 = analyze_part(rotate_ccw(lower))
    upper0 = analyze_part(upper)
    upper1 = analyze_part(rotate_ccw(upper))
    pin = shape_literal("P-------")
    crystal = shape_literal("cu------")
    if ((upper0 == pin) & (lower0 is None)) | ((upper1 == pin) & (lower1 is None)):
        return -1
    linked = ((lower0 == crystal) & (upper0 == crystal)) | ((lower1 == crystal) & (upper1 == crystal))
    attached0 = (upper0 is not None) & (upper0 != pin)
    attached1 = (upper1 is not None) & (upper1 != pin)
    witness0 = attached0 & ((lower0 == pin) | ((not linked) & (lower0 is not None)))
    witness1 = attached1 & ((lower1 == pin) | ((not linked) & (lower1 is not None)))
    supported = (status == 1) | witness0 | witness1
    if linked:
        if supported:
            return 1
        return 0
    if (attached0 | attached1) & (not supported):
        return -1
    return 0
