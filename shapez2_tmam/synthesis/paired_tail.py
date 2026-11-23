"""按闭合前缀逐层保留尾料并回放堆叠。"""

from .column_build import join_built_halves
from .direct_stack import direct_order_accepted
from .layer_methods import append_layer
from .material_word import join_material_words
from .physics import Shape
from .shape_methods import (_cut_ground_corner, analyze_part, rotate_ccw, rotate_cw,
                            shape_literal, unstack_lower, unstack_upper)


def _tail_column_mask(height: int) -> Shape:
    # 掩码从顶到底对应原图从底到顶。Ru 跳过原格，Cu 允许上料。
    if height == 0:
        return shape_literal("Cu------:Cu------:Cu------:Cu------:Cu------")
    if height == 1:
        return shape_literal("Cu------:Cu------:Cu------:Cu------:Ru------")
    if height == 2:
        return shape_literal("Cu------:Cu------:Cu------:Ru------:Ru------")
    if height == 3:
        return shape_literal("Cu------:Cu------:Ru------:Ru------:Ru------")
    if height == 4:
        return shape_literal("Cu------:Ru------:Ru------:Ru------:Ru------")
    return shape_literal("Ru------:Ru------:Ru------:Ru------:Ru------")


def tail_mask(h0: int, h1: int, h2: int, h3: int) -> Shape | None:
    """无有效闭包时不产生尾料掩码。"""
    if (h0 < 0) | (h1 < 0) | (h2 < 0) | (h3 < 0):
        return None
    return join_material_words(_tail_column_mask(h0), _tail_column_mask(h1),
                               _tail_column_mask(h2), _tail_column_mask(h3))


def _tail_corner(row: Shape | None, mask: Shape | None) -> Shape | None:
    if analyze_part(mask) != shape_literal("Cu------"):
        return None
    part = analyze_part(row)
    if part is None or part == shape_literal("cu------"):
        return None
    return _cut_ground_corner(row)


def _tail_half(row: Shape | None, mask: Shape | None) -> Shape | None:
    left = _tail_corner(row, mask)
    right = _tail_corner(rotate_ccw(row), rotate_ccw(mask))
    return append_layer(left, rotate_cw(right))


def _tail_layer(row: Shape | None, mask: Shape | None) -> Shape | None:
    front = _tail_half(row, mask)
    back = _tail_half(rotate_ccw(rotate_ccw(row)), rotate_ccw(rotate_ccw(mask)))
    return append_layer(front, rotate_cw(rotate_cw(back)))


def tail_replay_step(replay: Shape | None, mask: Shape | None, row: Shape | None) -> Shape | None:
    return append_layer(replay, _tail_layer(row, unstack_upper(mask)))


def tail_mask_step(replay: Shape | None, mask: Shape | None, row: Shape | None) -> Shape | None:
    return unstack_lower(mask)


def join_oriented_halves(front: Shape | None, back: Shape | None) -> Shape | None:
    return join_built_halves(front, back, False)


def restore_cut(replay: Shape | None, alternate: bool, done: bool, valid: bool,
                target: Shape | None) -> Shape | None:
    if alternate:
        return rotate_cw(replay)
    return replay


def tail_accepted(replay: Shape | None, alternate: bool, done: bool, valid: bool, target: Shape | None) -> bool:
    result = restore_cut(replay, alternate, done, valid, target)
    return direct_order_accepted(target, result, valid, done)
