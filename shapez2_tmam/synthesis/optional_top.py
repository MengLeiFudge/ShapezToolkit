"""顶针前态的可选顶格只参与半形支撑。"""

from .physics import Shape
from .row_support import _keep_plain
from .shape_methods import analyze_part, rotate_ccw, rotate_cw, shape_literal


def _optional_top_height(height: int, partner_height: int, row: Shape | None, partner_row: Shape | None) -> int:
    own = analyze_part(row)
    partner = analyze_part(partner_row)
    kept = _keep_plain(height >= 5, own, partner_height >= 5, partner)
    missing = kept & (own == shape_literal("Cu------")) & (partner != shape_literal("Ru------")) \
        & (partner != shape_literal("P-------"))
    if height < 0 or missing:
        return -1
    if kept:
        return 5
    return height


def optional_top_q0(h0: int, h1: int, h2: int, h3: int, row: Shape | None, optional: bool) -> int:
    if not optional:
        return h0
    return _optional_top_height(h0, h1, row, rotate_ccw(row))


def optional_top_q1(h0: int, h1: int, h2: int, h3: int, row: Shape | None, optional: bool) -> int:
    if not optional:
        return h1
    return _optional_top_height(h1, h0, rotate_ccw(row), row)


def optional_top_q2(h0: int, h1: int, h2: int, h3: int, row: Shape | None, optional: bool) -> int:
    if not optional:
        return h2
    aligned = rotate_ccw(rotate_ccw(row))
    return _optional_top_height(h2, h3, aligned, rotate_cw(row))


def optional_top_q3(h0: int, h1: int, h2: int, h3: int, row: Shape | None, optional: bool) -> int:
    if not optional:
        return h3
    aligned = rotate_ccw(rotate_ccw(row))
    return _optional_top_height(h3, h2, rotate_cw(row), aligned)


def optional_top_item(h0: int, h1: int, h2: int, h3: int, row: Shape | None, optional: bool) -> Shape | None:
    if optional:
        return None
    return row
