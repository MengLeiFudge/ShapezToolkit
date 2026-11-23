"""用单层图形保存四象限 K/G 支撑可达标记。"""

from .layer_methods import append_layer
from .physics import Shape
from .shape_methods import analyze_part, original_rows, rotate_ccw, rotate_cw, shape_literal


def _seed_cell(row: Shape | None, added: Shape | None, reached: Shape | None, previous: Shape | None,
               down: bool, pin_seed: bool) -> Shape | None:
    part = analyze_part(row)
    if part is None:
        return None
    if analyze_part(previous) is not None:
        return shape_literal("Cu------")
    linked = analyze_part(reached) is not None
    if down:
        crystal = shape_literal("cu------")
        linked = linked & (part == crystal) & (analyze_part(added) == crystal)
    elif pin_seed:
        linked = linked | (part == shape_literal("P-------"))
    if linked:
        return shape_literal("Cu------")
    return None


def _seed_half(row: Shape | None, added: Shape | None, reached: Shape | None, previous: Shape | None,
               down: bool, pin_seed: bool) -> Shape | None:
    left = _seed_cell(row, added, reached, previous, down, pin_seed)
    right = _seed_cell(rotate_ccw(row), rotate_ccw(added), rotate_ccw(reached), rotate_ccw(previous), down, pin_seed)
    return append_layer(left, rotate_cw(right))


def support_seed_front(row: Shape | None, added: Shape | None, reached: Shape | None, previous: Shape | None,
                       down: bool, pin_seed: bool) -> Shape | None:
    return _seed_half(row, added, reached, previous, down, pin_seed)


def support_seed_back(row: Shape | None, added: Shape | None, reached: Shape | None, previous: Shape | None,
                      down: bool, pin_seed: bool) -> Shape | None:
    return _seed_half(rotate_ccw(rotate_ccw(row)), rotate_ccw(rotate_ccw(added)), rotate_ccw(rotate_ccw(reached)),
                      rotate_ccw(rotate_ccw(previous)), down, pin_seed)


def support_join_halves(front: Shape | None, back: Shape | None) -> Shape | None:
    return append_layer(front, rotate_cw(rotate_cw(back)))


def support_row_seed(row: Shape | None, added: Shape | None, reached: Shape | None, previous: Shape | None,
                     down: bool, pin_seed: bool) -> Shape | None:
    """向上接已标记的下格，向下仅沿连续晶体接已标记的上格。"""
    return support_join_halves(support_seed_front(row, added, reached, previous, down, pin_seed),
                               support_seed_back(row, added, reached, previous, down, pin_seed))


def _nonpin(row: Shape | None) -> bool:
    part = analyze_part(row)
    return (part is not None) & (part != shape_literal("P-------"))


def _spread_cell(row: Shape | None, seed: Shape | None) -> Shape | None:
    mark = shape_literal("Cu------")
    if analyze_part(seed) is not None:
        return mark
    if not _nonpin(row):
        return None
    left = _nonpin(rotate_ccw(row))
    right = _nonpin(rotate_cw(row))
    if (left & (analyze_part(rotate_ccw(seed)) is not None)) | (right & (analyze_part(rotate_cw(seed)) is not None)):
        return mark
    if (left | right) & _nonpin(rotate_cw(rotate_cw(row))):
        if analyze_part(rotate_cw(rotate_cw(seed))) is not None:
            return mark
    return None


def _spread_half(row: Shape | None, seed: Shape | None) -> Shape | None:
    return append_layer(_spread_cell(row, seed), rotate_cw(_spread_cell(rotate_ccw(row), rotate_ccw(seed))))


def support_spread_front(row: Shape | None, seed: Shape | None) -> Shape | None:
    return _spread_half(row, seed)


def support_spread_back(row: Shape | None, seed: Shape | None) -> Shape | None:
    return _spread_half(rotate_ccw(rotate_ccw(row)), rotate_ccw(rotate_ccw(seed)))


def support_row_spread(row: Shape | None, seed: Shape | None) -> Shape | None:
    """单次闭合四格环的水平支撑边。"""
    return support_join_halves(support_spread_front(row, seed), support_spread_back(row, seed))


def _cell_supported(row: Shape | None, below: Shape | None, reached: Shape | None,
                    ground: bool, optional: bool) -> bool:
    part = analyze_part(row)
    if part is None:
        return True
    if part == shape_literal("P-------"):
        if not (ground | (analyze_part(below) is not None)):
            return False
    elif optional and part != shape_literal("cu------"):
        return True
    return analyze_part(reached) is not None


def _half_supported(row: Shape | None, below: Shape | None, reached: Shape | None,
                    ground: bool, optional: bool) -> bool:
    return (_cell_supported(row, below, reached, ground, optional)
            & _cell_supported(rotate_ccw(row), rotate_ccw(below), rotate_ccw(reached), ground, optional))


def support_row_accepted(row: Shape | None, below: Shape | None, reached: Shape | None,
                         ground: bool, optional: bool) -> bool:
    return (_half_supported(row, below, reached, ground, optional)
            & _half_supported(rotate_ccw(rotate_ccw(row)), rotate_ccw(rotate_ccw(below)),
                              rotate_ccw(rotate_ccw(reached)), ground, optional))


def support_rows_reached(shape: Shape, grounded: bool = False) -> tuple[Shape | None, ...]:
    """列 A 网格按两次上部闭包计算可达集合，前两行只需向上。"""
    row0, row1, row2, row3, row4 = original_rows(shape)
    ground = support_row_seed(row0, None, shape_literal("CuCuCuCu"), None, False, False)

    def up(row, below):
        return support_row_spread(row, support_row_seed(row, None, below, None, False, not grounded))

    def down(row, above, reached, previous):
        return support_row_spread(row, support_row_seed(row, above, reached, previous, True, False))

    def upper_pair(below):
        fourth = up(row3, below)
        fifth = up(row4, fourth)
        return down(row3, row4, fifth, fourth)

    second = up(row1, ground)
    third = up(row2, second)
    fourth = upper_pair(third)
    third = down(row2, row3, fourth, third)
    fourth = upper_pair(third)
    return ground, second, third, fourth, up(row4, fourth)
