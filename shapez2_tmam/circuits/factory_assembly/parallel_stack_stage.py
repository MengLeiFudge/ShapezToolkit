"""把通用加工台选中的堆叠指令送往六机板，再接回收料台。"""

from ..production_line import check_jump
from ..slot_stream_ports import trace, transport_paths
from ..slot_streams import SlotStreams
from ..work_lane import A_X, OUT_X
from .layout import _stack_lane


_RETURN_X = -11
_STACK_ROW = 3
_MERGE_ROW = 30


def _stack_dispatch(work: dict) -> dict:
    lane = SlotStreams()
    old = work['B']['Entries']
    for entry in old:
        x, y, level, rotation = (entry[key] for key in ('X', 'Y', 'L', 'R'))
        if y == _STACK_ROW and level == 0 and 10 <= x <= OUT_X:
            continue
        kind, _, mirror = entry['T'].partition('InternalVariant')
        lane.put(kind, x, y, level, rotation, mirrored=bool(mirror), config=entry.get('C'))
    lane.put('BeltDefaultForward', OUT_X, _STACK_ROW, rotation=1)
    lane.straight(10, 15, _STACK_ROW)
    lane.put('Lift1UpForward', 15, _STACK_ROW)
    lane.straight(10, 12, _STACK_ROW, 1)
    lane.put('BeltDefaultLeft', 12, _STACK_ROW, 1, mirrored=True)
    lane.put('BeltDefaultLeft', 12, _STACK_ROW + 1, 1, 1)
    lane.put('BeltDefaultForward', 13, _STACK_ROW + 1, 1)
    lane.put('Lift1UpForward', 14, _STACK_ROW + 1, 1)
    for level, row, start, drop in ((1, _STACK_ROW, 16, 35), (2, _STACK_ROW + 1, 15, 36)):
        lane.straight(start, 30, row, level)
        lane.put('BeltDefaultLeft', 30, row, level, mirrored=True)
        for y in range(row + 1, 32):
            lane.put('BeltDefaultForward', 30, y, level, 1)
        lane.put('BeltDefaultLeft', 30, 32, level, 1, mirrored=True)
        for x in range(A_X + 1, 30):
            lane.put('BeltDefaultForward', x, 32, level, 2)
        lane.put('BeltDefaultLeft', A_X, 32, level, 2)
        for y in range(33, 37):
            kind = 'Lift1DownForward' if y == drop else 'BeltDefaultForward'
            lane.put(kind, A_X, y, level - int(y > drop), 1)
        lane.put('BeltPortSender', A_X, 37, level - 1, 1, config='KAAAAAA=')
    dispatched = dict(work, B=dict(work['B'], Entries=lane.entries))
    paths = transport_paths(dispatched)
    for level in (0, 1):
        entry = (A_X, -17, level, 3)
        end = (A_X, 37, level, 3)
        trace(paths, entry, {end}, {(A_X, _STACK_ROW, level)})
    trace(paths, (OUT_X, _STACK_ROW, 0, 3), {(37, _MERGE_ROW, 0, 2)}, set())
    return dispatched


def _return_board(*, merge: bool) -> dict:
    lane = SlotStreams()
    lane.put('BeltPortReceiver', -18, _MERGE_ROW, config='AA==')
    lane.straight(-17, _RETURN_X, _MERGE_ROW)
    if merge:
        lane.put('BeltPortReceiver', _RETURN_X, 37, rotation=3, config='AA==')
        for y in range(_MERGE_ROW + 1, 37):
            lane.put('BeltDefaultForward', _RETURN_X, y, rotation=3)
        lane.put('Merger2To1L', _RETURN_X, _MERGE_ROW, rotation=3)
    else:
        lane.put('BeltDefaultLeft', _RETURN_X, _MERGE_ROW)
    for y in range(-17, _MERGE_ROW):
        lane.put('BeltDefaultForward', _RETURN_X, y, rotation=3)
    lane.put('BeltPortSender', _RETURN_X, -18, rotation=3, config='KAAAAAA=')
    board = lane.finish()
    paths = transport_paths(board)
    end = (_RETURN_X, -18, 0, 1)
    trace(paths, (-17, _MERGE_ROW, 0, 2), {end}, set())
    if merge:
        trace(paths, (_RETURN_X, 36, 0, 1), {end}, set())
    return board


def _north_jump(sender: dict, receiver: dict) -> None:
    if (sender.get('X', 0) != receiver.get('X', 0) or sender['Y'] - receiver.get('Y', 0) != 3
            or sender.get('Z', 0) != receiver.get('Z', 0)):
        raise ValueError('堆叠回料的北向带口未以五格间隔对齐')
    for board, kind, y in ((sender, 'Sender', -18), (receiver, 'Receiver', 37)):
        if sum(e['T'] == f'BeltPort{kind}InternalVariant'
               and (e['X'], e['Y'], e['L'], e['R']) == (_RETURN_X, y, 0, 3)
               for e in board['B']['Entries']) != 1:
            raise ValueError(f'堆叠回料缺少唯一的北向 {kind} 带口')


def add_parallel_stack(entries: list[dict], x: int) -> dict:
    islands = {(e.get('X', 0), e.get('Y', 0), e.get('Z', 0)): i for i, e in enumerate(entries)}
    ordinary_index = islands[x, 3, 0]
    ordinary = _stack_dispatch(entries[ordinary_index])
    take = entries[islands[x, 0, 0]]
    receive = entries[islands[x + 3, 0, 0]]
    stack = dict(_stack_lane(), X=x, Y=6)
    relay = dict(_return_board(merge=False), X=x + 3, Y=6)
    merge = dict(_return_board(merge=True), X=x + 3, Y=3)
    for level in (0, 1):
        check_jump(take, ordinary, A_X, 1, level)
        check_jump(ordinary, stack, A_X, 1, level)
    check_jump(ordinary, merge, _MERGE_ROW, 0)
    check_jump(stack, relay, _MERGE_ROW, 0)
    _north_jump(relay, merge)
    _north_jump(merge, receive)
    entries[ordinary_index] = ordinary
    for y, kind, rotation in ((4, 'SpaceBelt_LeftTurn', 0), (3, 'SpaceBelt_Forward', 3), (2, 'SpaceBelt_Forward', 3)):
        old = entries[islands[x + 2, y, 0]]
        if (old['T'], old.get('R', 0)) != (kind, rotation):
            raise ValueError(f'通用工段 {(x, y)} 的原回料桥未对齐')
    old_bridge = {islands[x + 2, y, 0] for y in (2, 3, 4)}
    for i in sorted(old_bridge, reverse=True):
        del entries[i]
    entries.extend((stack, relay, merge))
    return stack
