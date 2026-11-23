"""共用四列的五层材料编码，保留原层号和象限。"""

from .layer_methods import append_layer
from .physics import Shape
from .shape_methods import rotate_ccw, rotate_cw, shape_literal, unstack_lower, unstack_upper


def join_material_words(q0: Shape | None, q1: Shape | None, q2: Shape | None, q3: Shape | None) -> Shape | None:
    """四份材料字各占 q0、各层都有普通标记。合并后每个原格仍在原层。"""
    front = append_layer(q0, rotate_cw(q1))
    back = append_layer(rotate_cw(rotate_cw(q2)), rotate_ccw(q3))
    return append_layer(front, back)


def material_word_prefix(word: Shape | None, height: int) -> Shape | None:
    """返回该层及下方的全部材料，层高从 1 起算。"""
    if height < 1 or height > 5:
        return None
    for current in (5, 4, 3, 2):
        if current == height:
            return word
        word = unstack_lower(word)
    return word


def material_word_row(word: Shape | None, height: int) -> Shape | None:
    return unstack_upper(material_word_prefix(word, height))


def select_material_column(q0: Shape | None, q1: Shape | None, q2: Shape | None, q3: Shape | None,
                           column: int) -> Shape | None:
    if column == 0:
        return q0
    if column == 1:
        return q1
    if column == 2:
        return q2
    if column == 3:
        return q3
    return None


def _empty_material_suffix(height: int) -> Shape | None:
    if height == 0:
        return shape_literal("Cu------:Cu------:Cu------:Cu------:Cu------")
    if height == 1:
        return shape_literal("Cu------:Cu------:Cu------:Cu------")
    if height == 2:
        return shape_literal("Cu------:Cu------:Cu------")
    if height == 3:
        return shape_literal("Cu------:Cu------")
    if height == 4:
        return shape_literal("Cu------")
    return None


def prefix_material_word(q0: Shape | None, q1: Shape | None, q2: Shape | None, q3: Shape | None,
                         column: int, height: int) -> Shape | None:
    """复用已读好的材料字。前缀以上填空材料标记，仍保留五个原层位。"""
    word = select_material_column(q0, q1, q2, q3, column)
    if word is None or height < 0 or height > 5:
        return None
    return append_layer(material_word_prefix(word, height), _empty_material_suffix(height))
