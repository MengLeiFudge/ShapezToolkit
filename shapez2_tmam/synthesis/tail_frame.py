"""从一层顶针逆推记录恢复正向追加料。"""

from .layer_methods import append_layer
from .paired_tail import _tail_corner
from .physics import Shape
from .shape_methods import analyze_part, original_rows, pin, rotate_ccw, rotate_cw, shape_literal


def tail_pin_matches(source: Shape | None, pushed: Shape | None) -> bool:
    return (source is not None) & (pushed is not None) & (pin(source) == pushed)


def _missing_corner(target: Shape | None, pushed: Shape | None) -> Shape | None:
    if analyze_part(pushed) is not None:
        return None
    return _tail_corner(target, shape_literal("Cu------"))


def _missing_half(target: Shape | None, pushed: Shape | None) -> Shape | None:
    left = _missing_corner(target, pushed)
    right = _missing_corner(rotate_ccw(target), rotate_ccw(pushed))
    return append_layer(left, rotate_cw(right))


def tail_frame_row(target: Shape | None, pushed: Shape | None) -> Shape | None:
    """按同一原层取尚未放入的普通格和针。"""
    front = _missing_half(target, pushed)
    back = _missing_half(rotate_ccw(rotate_ccw(target)), rotate_ccw(rotate_ccw(pushed)))
    return append_layer(front, rotate_cw(rotate_cw(back)))


def tail_frame_level(step: int) -> int:
    if step >= 1 and step <= 10:
        return (-1, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4)[step]
    return -1


def tail_frame_opcode(step: int, row: Shape | None) -> int:
    if step == 0:
        return 6
    if row is None or step < 1 or step > 10:
        return 0
    if (step == 1) | (step == 3) | (step == 5) | (step == 7) | (step == 9):
        return 14
    return 7


def tail_frame_a(step: int, row: Shape | None) -> int:
    return 0


def tail_frame_b(step: int, row: Shape | None) -> int:
    return 1


def tail_frame_destination(step: int, row: Shape | None) -> int:
    if tail_frame_opcode(step, row) == 14:
        return 1
    return 0


def tail_frame_base(step: int, row: Shape | None) -> Shape | None:
    return row


def tail_frame_active(step: int, row: Shape | None) -> bool:
    return tail_frame_opcode(step, row) != 0


def tail_frame_uses_a(step: int, row: Shape | None) -> bool:
    opcode = tail_frame_opcode(step, row)
    return (opcode == 6) | (opcode == 7)


def tail_frame_uses_b(step: int, row: Shape | None) -> bool:
    return tail_frame_opcode(step, row) == 7


def tail_frame_uses_base(step: int, row: Shape | None) -> bool:
    return tail_frame_opcode(step, row) == 14


def tail_frame_replay(source: Shape | None, pushed: Shape | None, target: Shape | None) -> bool:
    """软件用同一层方法核对正向顶针和堆叠的实际产物。"""
    if target is None or not tail_pin_matches(source, pushed):
        return False
    result = pushed
    for wanted, existing in zip(original_rows(target), original_rows(pushed), strict=True):
        result = append_layer(result, tail_frame_row(wanted, existing))
    return result == target
