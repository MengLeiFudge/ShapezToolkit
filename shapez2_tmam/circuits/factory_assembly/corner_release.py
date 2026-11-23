"""生成含晶角释放的六字段指令，返回顺序即连续工段顺序。

主形、锚柱和补形来自调用方的活槽，方向与 synthesis.column_build 一致。
未用操作数用 None 表示空信号。有效槽号沿用整数，包括槽 0。
结果写回主槽。用过的锚柱、补形和临时槽在释放后可复用。
顶破的 reserved_slots 指调用方还需保留的其他活槽，另留两个空槽搭远柱。
"""

from collections.abc import Iterable

from ..slot_streams import SLOT_ROWS
from .recipe import BASE, _slot


def _packet(opcode: int, a: int | None = None, b: int | None = None, *, destination: int | None = None,
            base: str | None = None) -> dict:
    return {'opcode': opcode, 'a': a, 'b': b, 'destination': a if destination is None else destination,
            'base': base, 'color': None}


def simple_corner_instructions(retained_slot: int, far_slot: int | None = None, *,
                               counterclockwise: bool) -> tuple[dict, ...]:
    retained = _slot(retained_slot)
    if far_slot is None:
        return ()
    far = _slot(far_slot)
    if retained == far:
        raise ValueError('主形和远锚需要不同的槽')
    if counterclockwise:
        # 远锚连续转两次。交换与半切共用转正方向。
        return (_packet(1, retained), _packet(3, far), _packet(8, retained, far),
                _packet(4, retained), _packet(2, retained))
    return (_packet(2, far), _packet(8, retained, far), _packet(4, retained))


def pin_corner_instructions(initial_slot: int, anchor_slot: int, complement_slot: int, *,
                            counterclockwise: bool, reserved_slots: Iterable[int] = ()) -> tuple[dict, ...]:
    initial, anchor, complement = (_slot(slot) for slot in (initial_slot, anchor_slot, complement_slot))
    inputs = {initial, anchor, complement}
    reserved = {_slot(slot) for slot in reserved_slots}
    if len(inputs) != 3 or inputs & reserved:
        raise ValueError('主形、近锚、补形和其他活槽须分开')
    free = [slot for slot in range(len(SLOT_ROWS)) if slot not in inputs and slot not in reserved]
    if len(free) < 2:
        raise ValueError('顶破释放需要两个空槽搭建五层远柱')
    far, upper = free[:2]

    # 远柱由五份单层叠成。基础料直接取第一次交换所需朝向。
    base = '----Cu--' if counterclockwise else '------Cu'
    post = [_packet(BASE, destination=far, base=base)]
    for _ in range(4):
        post.extend((_packet(BASE, destination=upper, base=base), _packet(7, far, upper)))

    if counterclockwise:
        # 首次半切的朝向保留到与远柱交换。末次半切与补形交换也共用朝向。
        return (_packet(1, initial), _packet(4, initial), *post,
                _packet(8, initial, far), _packet(2, initial), _packet(4, initial),
                _packet(2, anchor), _packet(8, initial, anchor),
                _packet(1, initial), _packet(4, initial), _packet(1, complement),
                _packet(8, initial, complement), _packet(2, initial), _packet(6, initial))

    # 远侧半切后的主形留在转正方向，近锚转半圈后接手支撑。
    return (_packet(4, initial), *post,
            _packet(8, initial, far), _packet(1, initial), _packet(4, initial),
            _packet(3, anchor), _packet(8, initial, anchor), _packet(2, initial), _packet(4, initial),
            _packet(8, initial, complement), _packet(6, initial))
