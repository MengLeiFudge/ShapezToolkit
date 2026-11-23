"""选择紧柱调用和逐层追加的当前角原料。"""

from .physics import Shape
from .shape_methods import shape_literal


def _anchor_row(level: int, crystal: int, landing: int) -> Shape | None:
    if crystal == 3:
        if level == 0:
            return shape_literal("cr------")
        if level == 1:
            return shape_literal("Cu------")
    if crystal == 4:
        if level == 0 and landing == 1:
            return shape_literal("cr------")
        if level == 1:
            return shape_literal("cr------")
        if (level == 0) | (level == 2):
            return shape_literal("Cu------")
    return None


def corner_dense_row(main: Shape | None, far: Shape | None, role: int, level: int,
                     highest: int, pins: int, crystal: int, landing: int, needs_pin: bool) -> Shape | None:
    if role == 1:
        return far
    if role == 2:
        return _anchor_row(level, crystal, landing)
    if role == 3:
        return shape_literal("cr------")
    if role == 0:
        if needs_pin:
            return main
        if (level >= pins) & (level <= highest):
            return main
    return None


def dispatch_append_row(tail: Shape | None, corner: Shape | None, kind: int) -> Shape | None:
    if kind == 4:
        return tail
    if kind == 1:
        return corner
    return None


def copy_level(level: int) -> int:
    return level


def dispatch_append_lower(kind: int, lower: int, upper: int, initial: int,
                          corner_lower: int, corner_upper: int, corner_initial: int) -> int:
    if kind == 1:
        return corner_lower
    return lower


def dispatch_append_upper(kind: int, lower: int, upper: int, initial: int,
                          corner_lower: int, corner_upper: int, corner_initial: int) -> int:
    if kind == 1:
        return corner_upper
    return upper


def dispatch_append_initial(kind: int, lower: int, upper: int, initial: int,
                            corner_lower: int, corner_upper: int, corner_initial: int) -> int:
    if kind == 1:
        return corner_initial
    return initial
