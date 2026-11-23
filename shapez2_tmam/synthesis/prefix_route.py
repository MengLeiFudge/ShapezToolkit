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
