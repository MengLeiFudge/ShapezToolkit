"""单层订单与整份无晶体配方的回放。"""

from .direct_recipe import direct_recipe_length
from .layer_methods import append_five, append_layer, stack
from .physics import Shape
from .shape_methods import analyze_part, rotate_ccw, shape_literal, target_height, unstack_lower, unstack_upper


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


def direct_base_at_depth(target: Shape | None, depth: int) -> Shape | None:
    """读出已通过纯堆叠判定的目标所需的单层基础料。"""
    for index in (0, 1, 2, 3, 4):
        if depth == index:
            return unstack_upper(target)
        target = unstack_lower(target)
    return None


def verify_direct_stack(target: Shape | None, row0: Shape | None, row1: Shape | None,
                        row2: Shape | None, row3: Shape | None, row4: Shape | None) -> bool:
    """从最低层开始回放通过 base_order 的订单，与完整目标比较。"""
    if target is None:
        return False
    return append_five(None, row0, row1, row2, row3, row4) == target


def direct_replay_ready(target: Shape | None) -> bool:
    """叠上隔空的整圈晶体以重新结算原图，并检查原图稳定。"""
    return (target is not None) & (stack(target, shape_literal("crcrcrcr")) == target)


def direct_scan_target(target: Shape | None) -> Shape | None:
    return target


def direct_scan_remaining(remaining: Shape | None, valid: bool, replay: Shape | None) -> Shape | None:
    return unstack_lower(remaining)


def direct_scan_valid(remaining: Shape | None, valid: bool, replay: Shape | None) -> bool:
    return valid & ((remaining is None) | (base_order(unstack_upper(remaining)) is not None))


def direct_scan_replay(remaining: Shape | None, valid: bool, replay: Shape | None) -> Shape | None:
    """将新读出的下料层加到已回放的上部下方。"""
    return append_layer(unstack_upper(remaining), replay)


def direct_order_accepted(target: Shape | None, replay: Shape | None, valid: bool, done: bool) -> bool:
    return done & valid & (target is not None) & (replay == target)


def direct_order_length(target: Shape | None, replay: Shape | None, valid: bool, done: bool) -> int:
    return direct_recipe_length(target_height(target))


def direct_order_replay(target: Shape | None, replay: Shape | None, valid: bool, done: bool) -> Shape | None:
    return replay
