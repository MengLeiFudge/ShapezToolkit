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


def simple_corner_release(retained: Shape | None, far: Shape | None) -> Shape | None:
    """远锚统一在 q0，转到 q3 后带走主列填充晶体。"""
    if far is None:
        return retained
    return cut_front(swap_front_a(retained, rotate_ccw(far)))


def pin_corner_release(initial: Shape | None, anchor: Shape | None,
                       complement: Shape | None) -> Shape | None:
    """重放底部碎晶、两次支撑交接和顶破。输入近锚在 q0。"""
    near_supported = cut_front(initial)
    far = shape_literal("------Cu:------Cu:------Cu:------Cu:------Cu")
    both = swap_front_a(near_supported, far)
    away = cut_front(rotate_cw(both))
    near_anchor = rotate_cw(rotate_cw(anchor))
    transferred = swap_front_a(away, near_anchor)
    retained = cut_front(rotate_ccw(transferred))
    return pin(swap_front_a(retained, complement))


def pin_corner_complement(trigger: Shape | None) -> Shape | None:
    """把位于 q0 的顶针柱接到 q3，保留 q2 的触顶晶体柱。"""
    spine = shape_literal("--cr----:--cr----:--cr----:--cr----:--cr----")
    return rotate_cw(swap_front_a(spine, rotate_ccw(rotate_ccw(trigger))))


def pin_corner_upper_layer(original: Shape | None, level: int, highest: int,
                           crystal_level: int, landing: int) -> Shape | None:
    """供给顶破后的指定原层。original 在 q0，助手料放 q1。"""
    if level <= landing or level > 4:
        return None
    helper = shape_literal("--Cu----")
    if level < crystal_level:
        helper = shape_literal("--P-----")
    if level > highest and original is not None:
        return stack(original, helper)
    return helper


def pin_corner_finish(source: Shape | None, row0: Shape | None, row1: Shape | None,
                      row2: Shape | None, row3: Shape | None, row4: Shape | None) -> Shape | None:
    return cut_front(append_five(source, row0, row1, row2, row3, row4))


def join_corner_half(left: Shape | None, right: Shape | None) -> Shape | None:
    """左角主列 q0、助手 q3；右角主列 q1、助手 q2。"""
    if left is None:
        return cut_front(right)
    if right is None:
        return cut_front(left)
    joined = swap_front_a(rotate_cw(left), rotate_cw(right))
    return cut_front(rotate_ccw(joined))
