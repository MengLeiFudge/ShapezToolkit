"""从定向后的五份原层读取角备料所需的带色单格。"""

from .column_scan import pin_corner_base_far, pin_corner_source, simple_corner_far, simple_corner_source
from .dense_input import dense_input_row
from .physics import Shape
from .prefix_route import select_column
from .shape_methods import read_labeled_corner


def corner_label_at(row0: Shape | None, row1: Shape | None, row2: Shape | None,
                    row3: Shape | None, row4: Shape | None, column: int, level: int,
                    height: int) -> Shape | None:
    """层号从零起算，前缀外为空。所有结果统一放在 q0。"""
    if (level < 0) | (level >= height):
        return None
    row = dense_input_row(row0, row1, row2, row3, row4, level)
    return read_labeled_corner(select_column(row, column))


def corner_source_query(level: int, needs_pin: bool) -> int:
    if not needs_pin:
        return level
    if level == 0:
        return 1
    if level == 1:
        return 2
    if level == 2:
        return 3
    if level == 3:
        return 4
    return -1


def corner_work_label(row0: Shape | None, row1: Shape | None, row2: Shape | None,
                      row3: Shape | None, row4: Shape | None, column: int, level: int,
                      height: int, needs_pin: bool) -> Shape | None:
    level = corner_source_query(level, needs_pin)
    return corner_label_at(row0, row1, row2, row3, row4, column, level, height)


def corner_gap_label(row0: Shape | None, row1: Shape | None, row2: Shape | None,
                     column: int, landing: int, height: int) -> Shape | None:
    # 晶下至少有一空层，五层内落点最高为第三层。
    return corner_label_at(row0, row1, row2, None, None, column, landing, height)


def corner_ground_label(row0: Shape | None, column: int, height: int) -> Shape | None:
    return corner_label_at(row0, None, None, None, None, column, 0, height)


def corner_main_input(original: Shape | None, moved: Shape | None, ground: Shape | None,
                      level: int, height: int, highest: int, crystal: int, landing: int,
                      needs_pin: bool) -> Shape | None:
    if (level < 0) | (level >= height) | (level > 4):
        return None
    if needs_pin:
        return pin_corner_source(original, moved, ground, level, highest, crystal)
    return simple_corner_source(original, moved, level, highest, crystal, landing)


def corner_far_input(original: Shape | None, moved: Shape | None, ground: Shape | None,
                     level: int, height: int, highest: int, crystal: int, landing: int,
                     needs_pin: bool) -> Shape | None:
    if (height <= 0) | (level < 0) | (level > 4):
        return None
    if needs_pin:
        return pin_corner_base_far(original, moved, ground, level, highest, crystal)
    return simple_corner_far(original, moved, level, highest, crystal, landing)
