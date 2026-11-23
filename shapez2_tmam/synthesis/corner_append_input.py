"""依据列 A 前缀准备两种释放路线的逐层追加料。"""

from .column_build import pin_corner_upper_layer
from .physics import Shape
from .shape_methods import rotate_ccw, rotate_cw, shape_literal, unstack_lower, unstack_upper
from .layer_methods import append_layer


def corner_ground_pins(word: Shape | None) -> int:
    """计紧柱制作后须补回的底部针，材料字保留五个层位。"""
    pin = shape_literal("Su------")
    z0 = unstack_lower(unstack_lower(unstack_lower(unstack_lower(word))))
    if z0 != pin:
        return 0
    z1 = unstack_lower(unstack_lower(unstack_lower(word)))
    if unstack_upper(z1) != pin:
        return 1
    z2 = unstack_lower(unstack_lower(word))
    if unstack_upper(z2) != pin:
        return 2
    z3 = unstack_lower(word)
    if unstack_upper(z3) != pin:
        return 3
    if unstack_upper(word) != pin:
        return 4
    return 5


def corner_requires_far(word: Shape | None, highest: int, landing: int) -> bool:
    """普通落点移位或晶层以下有空位时才制造远侧碎晶锚。"""
    if landing >= 0:
        return True
    empty = shape_literal("Cu------")
    for z in (4, 3, 2, 1, 0):
        if (z <= highest) & (unstack_upper(word) == empty):
            return True
        word = unstack_lower(word)
    return False


def simple_corner_upper_layer(original: Shape | None, level: int, highest: int,
                              crystal_level: int, landing: int, counterclockwise: bool) -> Shape | None:
    """追加近侧助手的一层以及主柱最高晶层以上的原色格。"""
    if level < 0 or level > 4:
        return None
    helper = shape_literal("Cu------")
    if ((level == 1) & (crystal_level == 2) | (level == 2) & (crystal_level == 3)
            | (level == 3) & (crystal_level == 4)):
        helper = shape_literal("P-------")
    if counterclockwise:
        helper = rotate_ccw(helper)
    else:
        helper = rotate_cw(helper)
    if level > highest:
        return append_layer(helper, original)
    return helper


def corner_append_feed(upper: Shape | None, level: int, crystal_level: int, mode: int) -> Shape | None:
    if mode == 1:
        return shape_literal("Cu------")
    if mode == 2:
        trigger = (crystal_level == 3 and level == 2) | (crystal_level == 4 and level == 3)
        if trigger:
            return shape_literal("Cu------")
        if (level < 2) | ((crystal_level == 4) & (level == 2)):
            return shape_literal("P-------")
        return None
    return upper


def corner_append_layer(original: Shape | None, level: int, highest: int, crystal_level: int,
                        landing: int, counterclockwise: bool, needs_pin: bool) -> Shape | None:
    if needs_pin:
        return pin_corner_upper_layer(original, level, highest, crystal_level, landing, counterclockwise)
    return simple_corner_upper_layer(original, level, highest, crystal_level, landing, counterclockwise)
