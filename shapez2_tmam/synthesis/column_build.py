"""用连续的原色格逐层回放一根无针的紧柱。"""

from .layer_methods import append_layer, stack
from .physics import Shape
from .shape_methods import (Color, analyze_color, analyze_part, crystal, cut_front, rotate_ccw,
                            rotate_cw, shape_literal)


def dense_column_source(source: Shape | None, pending: Color | None, row: Shape | None) -> Shape | None:
    """追加 q0 单格。连续同色的晶体先以针保留，再统一结晶。"""
    if row is None:
        return source
    if analyze_part(row) == shape_literal("cu------"):
        color = analyze_color(row)
        if (pending is not None) & (pending != color):
            source = crystal(source, pending)
        return append_layer(source, shape_literal("P-CuCuCu"))
    return append_layer(source, stack(shape_literal("--CuCuCu"), row))


def dense_column_pending(source: Shape | None, pending: Color | None, row: Shape | None) -> Color | None:
    if analyze_part(row) == shape_literal("cu------"):
        return analyze_color(row)
    return pending


def dense_column_finish(source: Shape | None, pending: Color | None) -> Shape | None:
    """结晶最后一批针，再两次半切取出紧柱。"""
    if pending is not None:
        source = crystal(source, pending)
    return rotate_ccw(cut_front(rotate_cw(cut_front(source))))
