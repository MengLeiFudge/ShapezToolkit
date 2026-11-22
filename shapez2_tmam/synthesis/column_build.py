"""用连续的原色格逐层回放一根无针的紧柱。"""

from .layer_methods import append_layer, stack
from .physics import Shape
from .shape_methods import (Color, analyze_color, analyze_part, crystal, cut_front, rotate_ccw,
                            rotate_cw, shape_literal)


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
