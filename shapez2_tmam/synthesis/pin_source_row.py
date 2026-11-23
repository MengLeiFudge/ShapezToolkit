"""把顶针前态的四个原色格合成一份原层信号。"""

from .column_build import join_built_halves
from .physics import Shape
from .shape_methods import rotate_ccw, rotate_cw, swap_front_a


def _adjacent_labels(left: Shape | None, right: Shape | None) -> Shape | None:
    if right is None:
        return left
    if left is None:
        return rotate_cw(right)
    # q1 与 q2 在标准切线上分开。各输入只有一格，虚拟交换没有跨切面的晶体。
    front = rotate_cw(left)
    back = rotate_cw(rotate_cw(right))
    return rotate_ccw(swap_front_a(front, back))


def pin_source_row(q0: Shape | None, q1: Shape | None, q2: Shape | None, q3: Shape | None) -> Shape | None:
    """输入均为位于 q0 的原色单格，空信号保留为空格。"""
    return join_built_halves(_adjacent_labels(q0, q1), _adjacent_labels(q2, q3), False)
