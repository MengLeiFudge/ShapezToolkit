"""把叶端锁存的控制、读高和两组存储叠到三个岛层。"""

from ...mari.blueprint import DIRECTIONS, _rotate
from ._middle_snapshot import middle_snapshot
from ._snapshot_layout import _Layout


_BANK_CELLS = ((0, 0, 2), (11, 0, 2), (24, 0, 2), (0, 7, 0), (12, 7, 0), (23, 7, 2))


def _bank_cell(layout, x, y, turn, source, stored):
    def position(a, b):
        return (x + 9 - a, y + 5 - b) if turn else (x + a, y + b)

    board = layout.board
    boundary = {(a, b, 0) for a in range(x - 1, x + 11) for b in range(y - 1, y + 7)
                if a in (x - 1, x + 10) or b in (y - 1, y + 6)} - board.occupied
    board.occupied.update(boundary)
    incoming, saved, value = (f"{kind}-{stored}" for kind in ("incoming", "saved", "value"))
    layout.radio(incoming, source, *position(8, 1), (2 + turn) % 4, receive=True)
    layout.radio(saved, stored, *position(2, 4), (3 + turn) % 4, receive=True)
    layout.radio(value, stored, *position(6, 4), (1 + turn) % 4, receive=False)
    for level, net, ctl, gate, via, rotation, facing in (
        (1, incoming, "load", (3, 1), (4, 2), 2, 2),
        (2, saved, "retain", (1, 1), (0, 0), 0, 0),
    ):
        layout.gate(("LogicGateIf", (net, ctl), (value,), None), *position(*gate), 0, (rotation + turn) % 4)
        layout.route(net, 0)
        if level == 2:
            layout.route(value, 0)
        side = (facing + turn) % 4
        vx, vy = position(*via)
        board.place(f"WireDefault{level}UpBackward", vx, vy, 0, (side + 2) % 4, height=level + 1)
        for z in (0, level):
            board.pin(ctl, vx, vy, z, side)
        pads = {p for p in board.terminals[ctl, 0] if x <= p[0] < x + 10 and y <= p[1] < y + 6}
        if not board.route(ctl, pads, protect_pads=True):
            raise ValueError(f"存储单元 {stored} 的控制线 {ctl} 无法接通")
    board.occupied.difference_update(boundary)


def _track(board, net, level, points):
    for (x, y), (end_x, end_y) in zip(points, points[1:]):
        dx, dy = (end_x > x) - (x > end_x), (end_y > y) - (y > end_y)
        direction = DIRECTIONS.index((dx, dy))
        while (x, y) != (end_x, end_y):
            board.traces[x, y, level].setdefault(net, set()).add(direction)
            x, y = x + dx, y + dy
            board.traces[x, y, level].setdefault(net, set()).add((direction + 2) % 4)


def _storage_bank(fields, control):
    layout = _Layout("Foundation_1x2")
    board = layout.board
    for (source, stored), (x, y, turn) in zip(fields, _BANK_CELLS, strict=True):
        _bank_cell(layout, x, y, turn, source, stored)
    for net, x, y, via, facing in (("hold", 10, 12, "Left", 3), ("phase", 22, 2, "Forward", 0)):
        layout.radio(net, control.inputs[net], x, y, 0, receive=True)
        # 收发器的数据口直接进换层线，上层再接局部扇出。
        board.traces.pop((x + 2, y, 0))
        board.terminals.pop((net, 0))
        board.place("WireDefault2Up" + via, x + 2, y, 0, height=3)
        board.pin(net, x + 2, y, 2, facing)
    layout.route("load", 1)
    layout.route("retain", 2)
    gates = {outs[0]: gate for gate in control.gates if len(outs := gate[2]) == 1}
    # 两个控制门相邻直连。上层路径与门的朝向一起选定，保留给两层母线的换层出口。
    for net, x, y, z, rotation in (("load", 3, 7, 1, 1), ("holding", 5, 4, 2, 1), ("retain", 3, 8, 2, 3),
                                   ("no_load", 4, 8, 2, 2), ("phase2", 15, 3, 2, 1)):
        layout.gate(gates[net], x, y, z, rotation, direct=("no_load",))
    for net, x, y, rotation, kind, low, high in (("holding", 4, 6, 3, "Forward", 1, 3),
                                                  ("phase2", 2, 9, 1, "Left", 3, 0)):
        board.place("WireDefault1Up" + kind, x, y, 1, rotation, height=2)
        board.pin(net, x, y, 1, low)
        board.pin(net, x, y, 2, high)
    for net, points in (
        ("hold", ((6, 4), (10, 4), (10, 7), (11, 7), (11, 8), (12, 8), (12, 11))),
        ("holding", ((5, 5), (3, 5), (3, 6), (2, 6), (2, 8))),
        ("holding", ((4, 5), (4, 6))),
        ("phase2", ((15, 4), (15, 5), (14, 5), (14, 9), (11, 9), (11, 10), (8, 10), (8, 13), (4, 13), (4, 9), (3, 9))),
        ("phase2", ((4, 9), (5, 9), (5, 8))),
        ("phase", ((16, 3), (20, 3), (20, 0), (25, 0), (25, 2))),
    ):
        _track(board, net, 2, points)
    for net, level in (("holding", 1), ("phase2", 1), ("load", 1), ("retain", 2)):
        layout.route(net, level)
    return layout.finish()


def stacked_snapshot(fields, control, height, column):
    return [
        {**_storage_bank(fields[3:9], control), "Z": -1},
        *middle_snapshot(fields, control, height, column),
        {**_storage_bank(fields[9:], control), "Z": 1},
    ]
