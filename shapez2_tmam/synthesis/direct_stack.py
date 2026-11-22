"""单层订单与整份无晶体配方的回放。"""

from .layer_methods import append_five, stack
from .physics import Shape
from .shape_methods import analyze_part, crystal, rotate_ccw, shape_literal, unstack_lower, unstack_upper


def base_order(row: Shape | None) -> Shape | None:
    """基础料只能是单层普通格与针，空信号表示跳过。"""
    if unstack_lower(row) is not None:
        return None
    aligned = row
    crystal = shape_literal("cu------")
    for _ in (0, 1, 2, 3):
        if analyze_part(aligned) == crystal:
            return None
        aligned = rotate_ccw(aligned)
    return row


def verify_direct_stack(target: Shape | None, row0: Shape | None, row1: Shape | None,
                        row2: Shape | None, row3: Shape | None, row4: Shape | None) -> bool:
    """从最低层开始回放通过 base_order 的订单，与完整目标比较。"""
    if target is None:
        return False
    return append_five(None, row0, row1, row2, row3, row4) == target


def check_stack_pair(lower: Shape | None, upper: Shape | None) -> bool:
    """检查上一层的所有新增块是否保持在第二层。"""
    if upper is None:
        return True
    joined = stack(lower, upper)
    return unstack_lower(joined) == lower and unstack_upper(joined) == upper


def has_contiguous_rows(target: Shape | None) -> bool:
    """非空目标的每个原层位都有材料时，原图和填满副本同时拆空。"""
    if target is None:
        return False
    dense = crystal(target, "r")
    for _ in (0, 1, 2, 3, 4):
        target = unstack_lower(target)
        dense = unstack_lower(dense)
        if target is None:
            return dense is None
    return False


def direct_scan_remaining(remaining: Shape | None, upper: Shape | None, valid: bool) -> Shape | None:
    return unstack_lower(remaining)


def direct_scan_upper(remaining: Shape | None, upper: Shape | None, valid: bool) -> Shape | None:
    return unstack_upper(remaining)


def direct_scan_valid(remaining: Shape | None, upper: Shape | None, valid: bool) -> bool:
    if not valid:
        return False
    if remaining is None:
        return True
    row = unstack_upper(remaining)
    return base_order(row) is not None and check_stack_pair(row, upper)
