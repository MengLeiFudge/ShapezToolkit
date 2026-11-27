"""把已制成的两角、两个半形和尾部单层接成六槽配方。"""

from collections.abc import Sequence

from ...synthesis.physics import Rules
from .recipe import BASE, _base_shape, _packet, _slot


def _join_slots(first: int | None, second: int | None, destination: int | None
                ) -> tuple[int | None, int | None, int | None]:
    first = _slot(first) if first is not None else None
    second = _slot(second) if second is not None else None
    if first is not None and first == second:
        raise ValueError('拼装的两份输入需要不同的槽')
    if destination is None:
        destination = first if first is not None else second
    else:
        destination = _slot(destination)
    return first, second, destination


def join_corner_half_instructions(left_slot: int | None, right_slot: int | None, *,
                                  destination: int | None = None) -> tuple[dict, ...]:
    left, right, target = _join_slots(left_slot, right_slot, destination)
    if left is None:
        return () if right is None else (_packet(4, right, destination=target),)
    if right is None:
        return (_packet(4, left, destination=target),)
    return (_packet(1, left), _packet(1, right), _packet(8, left, right),
            _packet(2, left), _packet(4, left, destination=target))


def join_built_halves_instructions(front_slot: int | None, back_slot: int | None, *, alternate: bool,
                                   destination: int | None = None) -> tuple[dict, ...]:
    front, back, target = _join_slots(front_slot, back_slot, destination)
    if front is None:
        return () if back is None else (_packet(2 if alternate else 3, back, destination=target),)
    if back is None:
        if alternate:
            return (_packet(1, front, destination=target),)
        if target == front:
            return ()
        # 没有直通搬槽指令，两次半转保持原方向。
        return (_packet(3, front), _packet(3, front, destination=target))
    if alternate:
        return (_packet(3, back), _packet(8, front, back), _packet(1, front, destination=target))
    return (_packet(3, back), _packet(8, front, back, destination=target))


def append_five_instructions(rows: Sequence[str | None], *, has_lower: bool,
                             lower_slot: int = 0, upper_slot: int = 1) -> tuple[dict, ...]:
    lower, upper = _slot(lower_slot), _slot(upper_slot)
    if lower == upper:
        raise ValueError('尾料和下料需要不同的槽')
    if len(rows) > 5:
        raise ValueError('尾料最多接收五个原层')
    rules = Rules(4, 5)
    packets = []
    for row in rows:
        if row is None:
            continue
        _base_shape(rules, row)
        if has_lower:
            packets.extend((_packet(BASE, destination=upper, base=row), _packet(7, lower, upper)))
        else:
            packets.append(_packet(BASE, destination=lower, base=row))
            has_lower = True
    return tuple(packets)
