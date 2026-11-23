"""切向统一与双半形前缀的逐列读取。"""

from .physics import Shape
from .shape_methods import rotate_ccw, rotate_cw


def orient_cut(target: Shape | None, alternate: bool) -> Shape | None:
    """将两种切向都归一为 q0/q1 和 q2/q3。"""
    if alternate:
        return rotate_ccw(target)
    return target


def select_column(target: Shape | None, column: int) -> Shape | None:
    """将当前切向的指定列转到 q0，保留其余列供读层。"""
    if column == 0:
        return target
    if column == 1:
        return rotate_ccw(target)
    if column == 2:
        return rotate_ccw(rotate_ccw(target))
    if column == 3:
        return rotate_cw(target)
    return None


def column_target_q0(target: Shape | None) -> Shape | None:
    return select_column(target, 0)


def column_target_q1(target: Shape | None) -> Shape | None:
    return select_column(target, 1)


def column_target_q2(target: Shape | None) -> Shape | None:
    return select_column(target, 2)


def column_target_q3(target: Shape | None) -> Shape | None:
    return select_column(target, 3)


def closed_prefix_ready(done: bool, h0: int, h1: int, h2: int, h3: int) -> bool:
    return done & (h0 >= 0) & (h1 >= 0) & (h2 >= 0) & (h3 >= 0)


def select_prefix_height(done: bool, h0: int, h1: int, h2: int, h3: int, column: int) -> int:
    """返回供备料板使用的层高。当前切向失败或仍在计算时返回 -1。"""
    if not closed_prefix_ready(done, h0, h1, h2, h3):
        return -1
    if column == 0:
        return h0
    if column == 1:
        return h1
    if column == 2:
        return h2
    if column == 3:
        return h3
    return -1


def checked_prefix_ready(done: bool, h0: int, h1: int, h2: int, h3: int,
                         column: int, a0: bool, a1: bool, a2: bool, a3: bool) -> bool:
    return a0 & a1 & a2 & a3 & closed_prefix_ready(done, h0, h1, h2, h3)


def checked_prefix_height(done: bool, h0: int, h1: int, h2: int, h3: int,
                          column: int, a0: bool, a1: bool, a2: bool, a3: bool) -> int:
    return select_prefix_height(done & a0 & a1 & a2 & a3, h0, h1, h2, h3, column)


def corner_counterclockwise(column: int) -> bool:
    """标准半形的左角朝 q3，右角在旋转前朝 q1。"""
    return (column == 0) | (column == 2)


def select_column_handedness(target: Shape | None, column: int) -> bool:
    return corner_counterclockwise(column)


def place_released_corner(simple: Shape | None, broken: Shape | None, needs_pin: bool,
                          column: int, prefix_height: int) -> Shape | None:
    """选已完成的角并恢复它在标准半形里的位置。"""
    if (prefix_height <= 0) | (column < 0) | (column > 3):
        return None
    if needs_pin:
        corner = broken
    else:
        corner = simple
    if corner_counterclockwise(column):
        return corner
    return rotate_cw(corner)
