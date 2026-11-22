"""把目标的 q0 列转成保留五个原层位的材料信号。"""

from .column_rules import _check_column_flags
from .layer_methods import stack
from .physics import Shape
from .shape_methods import (advance_target_rows, analyze_part, read_top_row_at, shape_literal,
                            unstack_lower, unstack_upper)


def _material_marker(row: Shape | None) -> Shape:
    part = analyze_part(row)
    if part is None:
        return shape_literal("Cu------")
    if part == shape_literal("P-------"):
        return shape_literal("Su------")
    if part == shape_literal("cu------"):
        return shape_literal("Wu------")
    return shape_literal("Ru------")


def column_scan_remaining(remaining: Shape | None, word: Shape | None, height: int) -> Shape | None:
    return advance_target_rows(remaining, height)


def column_scan_word(remaining: Shape | None, word: Shape | None, height: int) -> Shape | None:
    marker = _material_marker(read_top_row_at(remaining, height))
    if word is None:
        return marker
    return stack(marker, word)


def column_scan_height(remaining: Shape | None, word: Shape | None, height: int) -> int:
    if height < 1 or height > 5:
        return 0
    return (0, 0, 1, 2, 3, 4)[height]


def column_word_admissible(word: Shape | None) -> bool:
    """检查扫描完成后的五层材料字。"""
    z4 = unstack_upper(word)
    word = unstack_lower(word)
    z3 = unstack_upper(word)
    word = unstack_lower(word)
    z2 = unstack_upper(word)
    word = unstack_lower(word)
    z1 = unstack_upper(word)
    z0 = unstack_lower(word)
    empty = shape_literal("Cu------")
    pin = shape_literal("Su------")
    crystal = shape_literal("Wu------")
    ordinary = shape_literal("Ru------")
    return _check_column_flags(
        z0 == empty, z1 == empty, z2 == empty, z3 == empty,
        z0 == pin, z1 == pin, z2 == pin, z3 == pin, z4 == pin,
        z0 == crystal, z1 == crystal, z2 == crystal, z3 == crystal, z4 == crystal,
        z0 == ordinary, z1 == ordinary, z2 == ordinary, z3 == ordinary,
    )


def column_gap_crystal(word: Shape | None) -> int:
    """返回已通过列 A 检查的晶下间隙上端，无间隙时为 -1。"""
    crystal = shape_literal("Wu------")
    empty = shape_literal("Cu------")
    upper = unstack_upper(word)
    for height in (4, 3, 2):
        word = unstack_lower(word)
        below = unstack_upper(word)
        if (upper == crystal) & (below == empty):
            return height
        upper = below
    return -1


def column_gap_landing(word: Shape | None) -> int:
    """返回唯一一处晶下间隙要移动的普通格层号，无间隙时为 -1。"""
    height = column_gap_crystal(word)
    if height < 0:
        return -1
    word = unstack_lower(unstack_lower(word))
    if (height == 4) & (unstack_upper(word) == shape_literal("Ru------")):
        return 2
    word = unstack_lower(word)
    if (height >= 3) & (unstack_upper(word) == shape_literal("Ru------")):
        return 1
    return 0


def column_gap_needs_pin(word: Shape | None) -> bool:
    """落点下方为空且不触地时，选用顶破构造。"""
    landing = column_gap_landing(word)
    first_two = unstack_lower(unstack_lower(unstack_lower(word)))
    empty = shape_literal("Cu------")
    return ((landing == 1) & (unstack_lower(first_two) == empty)
            | (landing == 2) & (unstack_upper(first_two) == empty))


def corner_helper_column(crystal: int, landing: int, suspended: bool) -> Shape:
    """由晶下间隙生成五层助手的原料信号，格位统一在 q0。"""
    if suspended:
        if crystal == 3:
            return shape_literal("P-------:Cu------:P-------:Cu------:Cu------")
        if landing == 1:
            return shape_literal("P-------:Cu------:P-------:P-------:Cu------")
        return shape_literal("P-------:Cu------:Cu------:P-------:Cu------")
    if crystal == 4:
        return shape_literal("Cu------:Cu------:Cu------:P-------:Cu------")
    if crystal == 3:
        return shape_literal("Cu------:Cu------:P-------:Cu------:Cu------")
    if crystal == 2:
        return shape_literal("Cu------:P-------:Cu------:Cu------:Cu------")
    return shape_literal("Cu------:Cu------:Cu------:Cu------:Cu------")


def column_highest_crystal(word: Shape | None) -> int:
    crystal = shape_literal("Wu------")
    for z in (4, 3, 2, 1, 0):
        if unstack_upper(word) == crystal:
            return z
        word = unstack_lower(word)
    return -1


def _is_raised_source(level: int, crystal: int) -> bool:
    return ((level == 1) & (crystal == 2)
            | (level == 2) & (crystal == 3)
            | (level == 3) & (crystal == 4))


def simple_corner_source(original: Shape | None, moved: Shape | None, level: int,
                         highest: int, crystal: int, landing: int) -> Shape | None:
    """生成直接释放的主列前态单格，传入保留原色的原格和落点原格。"""
    if level < 0 or level > 4:
        return None
    if level > highest:
        return original
    if _is_raised_source(level, crystal):
        return moved
    if level == landing or original is None:
        return shape_literal("cr------")
    return original


def simple_corner_far(original: Shape | None, moved: Shape | None, level: int,
                      highest: int, crystal: int, landing: int) -> Shape | None:
    """在需删除的填充晶体旁提供锚，其余格使用普通料。"""
    if level < 0 or level > 4:
        return None
    if (level <= highest) & (not _is_raised_source(level, crystal)) & ((level == landing) | (original is None)):
        return shape_literal("cr------")
    return shape_literal("Cu------")


def pin_corner_source(above: Shape | None, moved: Shape | None, ground: Shape | None,
                      level: int, highest: int, crystal: int) -> Shape | None:
    """输出顶破前主列的一格，above 是目标上一层的原格。"""
    if level < 0 or level >= highest:
        return None
    if ((crystal == 3) & (level == 1)) | ((crystal == 4) & (level == 2)):
        return moved
    if level >= 2 or ((crystal == 3) & (level >= 1)):
        return above
    ground_source = ((crystal == 3) & (level == 0)) | ((crystal == 4) & (level == 1))
    if ground_source & (ground is not None) & (ground != shape_literal("P-------")):
        return ground
    return shape_literal("cr------")


def pin_corner_base_far(above: Shape | None, moved: Shape | None, ground: Shape | None,
                        level: int, highest: int, crystal: int) -> Shape | None:
    """临时远柱只在被补齐的主列空底段内放晶体。"""
    if level < 0 or level > 4:
        return None
    if ground is None:
        if (level == 0) | ((crystal == 4) & (level == 1)):
            return shape_literal("cr------")
    elif (ground != shape_literal("P-------")) & (crystal == 4) & (level == 0):
        return shape_literal("cr------")
    return shape_literal("Cu------")


def pin_corner_anchor(crystal: int, landing: int) -> Shape:
    if crystal == 3:
        return shape_literal("cr------:Cu------")
    if landing == 1:
        return shape_literal("cr------:cr------:Cu------")
    return shape_literal("Cu------:cr------:Cu------")


def pin_corner_trigger(crystal: int, landing: int) -> Shape:
    if crystal == 3:
        return shape_literal("P-------:P-------:Cu------")
    return shape_literal("P-------:P-------:P-------:Cu------")
