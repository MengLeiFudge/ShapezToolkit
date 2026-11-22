"""用连续的原色格逐层回放一根无针的紧柱。"""

from .layer_methods import append_five, append_layer, stack
from .physics import Shape
from .shape_methods import (Color, analyze_color, analyze_part, crystal, cut_front, pin, rotate_ccw,
                            rotate_cw, shape_literal, swap_front_a)


def dense_column_base(source: Shape | None, pending: Color | None, row: Shape | None) -> Shape | None:
    """填实另外三格，使结晶只作用于 q0 的针。"""
    if row is None:
        return None
    if analyze_part(row) == shape_literal("cu------"):
        return shape_literal("P-CuCuCu")
    return stack(shape_literal("--CuCuCu"), row)


def dense_column_flush(source: Shape | None, pending: Color | None, row: Shape | None) -> Color | None:
    if analyze_part(row) == shape_literal("cu------") and pending != analyze_color(row):
        return pending
    return None


def dense_column_needs_stack(source: Shape | None, pending: Color | None, row: Shape | None) -> bool:
    return (source is not None) & (row is not None)


def dense_column_source(source: Shape | None, pending: Color | None, row: Shape | None) -> Shape | None:
    """回放实际基础料、换色时的结晶，以及逐层堆叠。"""
    dye = dense_column_flush(source, pending, row)
    if dye is not None:
        source = crystal(source, dye)
    return append_layer(source, dense_column_base(source, pending, row))


def dense_column_pending(source: Shape | None, pending: Color | None, row: Shape | None) -> Color | None:
    if analyze_part(row) == shape_literal("cu------"):
        return analyze_color(row)
    return pending


def dense_column_finish(source: Shape | None, pending: Color | None) -> Shape | None:
    """结晶最后一批针，再两次半切取出紧柱。"""
    if pending is not None:
        source = crystal(source, pending)
    return rotate_ccw(cut_front(rotate_cw(cut_front(source))))


def _orient_neighbor(source: Shape | None, counterclockwise: bool) -> Shape | None:
    if counterclockwise:
        return rotate_ccw(source)
    return rotate_cw(source)


def _cut_corner_side(source: Shape | None, counterclockwise: bool) -> Shape | None:
    if counterclockwise:
        return rotate_ccw(cut_front(rotate_cw(source)))
    return cut_front(source)


def _swap_corner_sides(front: Shape | None, back: Shape | None, counterclockwise: bool) -> Shape | None:
    if counterclockwise:
        return rotate_ccw(swap_front_a(rotate_cw(front), rotate_cw(back)))
    return swap_front_a(front, back)


def simple_corner_release(retained: Shape | None, far: Shape | None, counterclockwise: bool) -> Shape | None:
    """把位于 q0 的远锚转到助手对侧，带走主列填充晶体。"""
    if far is None:
        return retained
    supported = _swap_corner_sides(retained, _orient_neighbor(far, not counterclockwise), counterclockwise)
    return _cut_corner_side(supported, counterclockwise)


def pin_corner_release(initial: Shape | None, anchor: Shape | None,
                       complement: Shape | None, counterclockwise: bool) -> Shape | None:
    """重放底部碎晶、两次支撑交接和顶破。输入近锚在 q0。"""
    near_supported = _cut_corner_side(initial, counterclockwise)
    full_post = shape_literal("Cu------:Cu------:Cu------:Cu------:Cu------")
    far = _orient_neighbor(full_post, not counterclockwise)
    both = _swap_corner_sides(near_supported, far, counterclockwise)
    away = _cut_corner_side(both, not counterclockwise)
    near_anchor = _orient_neighbor(anchor, counterclockwise)
    transferred = _swap_corner_sides(away, near_anchor, not counterclockwise)
    retained = _cut_corner_side(transferred, counterclockwise)
    return pin(_swap_corner_sides(retained, complement, counterclockwise))


def pin_corner_complement(trigger: Shape | None, counterclockwise: bool) -> Shape | None:
    """把位于 q0 的顶针柱接到助手对侧，触顶晶体柱置于 q2。"""
    spine = shape_literal("----cr--:----cr--:----cr--:----cr--:----cr--")
    if counterclockwise:
        return swap_front_a(rotate_cw(trigger), spine)
    paired = swap_front_a(rotate_ccw(spine), rotate_ccw(rotate_ccw(trigger)))
    return rotate_cw(paired)


def pin_corner_upper_layer(original: Shape | None, level: int, highest: int,
                           crystal_level: int, landing: int, counterclockwise: bool) -> Shape | None:
    """供给顶破后的指定原层。原格在 q0，助手料放在所选邻列。"""
    if level <= landing or level > 4:
        return None
    helper = shape_literal("Cu------")
    if level < crystal_level:
        helper = shape_literal("P-------")
    helper = _orient_neighbor(helper, counterclockwise)
    if level > highest and original is not None:
        return stack(original, helper)
    return helper


def pin_corner_finish(source: Shape | None, row0: Shape | None, row1: Shape | None, row2: Shape | None,
                      row3: Shape | None, row4: Shape | None, counterclockwise: bool) -> Shape | None:
    return _cut_corner_side(append_five(source, row0, row1, row2, row3, row4), counterclockwise)


def join_corner_half(left: Shape | None, right: Shape | None) -> Shape | None:
    """左角主列 q0、助手 q3；右角主列 q1、助手 q2。"""
    if left is None:
        return cut_front(right)
    if right is None:
        return cut_front(left)
    joined = swap_front_a(rotate_cw(left), rotate_cw(right))
    return cut_front(rotate_ccw(joined))


def join_built_halves(front: Shape | None, back: Shape | None, alternate: bool) -> Shape | None:
    """合并两个标准半形，按切向恢复目标的原方向。"""
    back = rotate_cw(rotate_cw(back))
    if front is None:
        joined = back
    elif back is None:
        joined = front
    else:
        joined = swap_front_a(front, back)
    if alternate:
        return rotate_cw(joined)
    return joined
