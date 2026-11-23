"""将中层的阶段控制、双字段锁存和选列高度分别压到 1×1。"""

from itertools import product
from random import Random

from ...mari.blueprint import DIRECTIONS, Wiring, _rotate
from ..circuit import constant
from ..foundations import platform_ground
from ._snapshot_layout import _Layout
from ._snapshot_router import connect_bus, place_controls


# 同岛层相邻凹口相距五格。端口选择决定本地母线朝向。
_EAST = (("load", 5, 1), ("retain", 6, 2))
_SOUTH = (("load", 5, 2), ("retain", 8, 0))


def _small():
    layout = _Layout("Foundation_1x1")
    layout.board.ground = platform_ground("Foundation_1x1")
    return layout


def _short(layout, name, x, y, z, direction, *, receive):
    suffix = "Receiver" if receive else "Sender"
    index = layout.board.place("WireTransmitter" + suffix, x, y, z, direction)
    layout.board.pin(name, x, y, z, direction if receive else (direction + 2) % 4)
    if receive:
        layout.drivers[name].append((index, 0))
    else:
        layout.inputs[index, 0] = name
    return index


def _cell(layout, field, saved, left, top, turn):
    def site(x, y):
        a, b = _rotate(x - 3, y - 3, turn)
        return left + 3 + a, top + 3 + b

    source, stored = field
    incoming, value = f"incoming-{stored}", f"value-{stored}"
    board = layout.board
    # 收发器沿 7×7 单元转角排布，保存回读和发送共用一枚频道常量。
    rx = board.place("ControlledSignalReceiver", *site(1, 1), 0, (1 + turn) % 4, radius=1, height=3)
    cfg = board.place("ConstantSignal", *site(3, 0), 0, (1 + turn) % 4, constant(stored))
    board.place("WireDefaultJunction", *site(3, 1), 0, (3 + turn) % 4)
    tx = board.place("ControlledSignalTransmitter", *site(5, 1), 0, (3 + turn) % 4, radius=1, height=3)
    layout.literals[rx, 0] = layout.literals[tx, 0] = ((cfg, 0),)
    layout.drivers[saved].append((rx, 0))
    layout.inputs[tx, 1] = value
    raw = board.place("ControlledSignalReceiver", *site(2, 5), 0, turn, radius=1, height=3)
    cfg = board.place("ConstantSignal", *site(2, 3), 0, (1 + turn) % 4, constant(source))
    layout.drivers[incoming].append((raw, 0))
    layout.literals[raw, 0] = ((cfg, 0),)

    for x, y, lo, hi, rotation, kind in (
        (1, 3, 0, 2, 1, "Left"), (5, 3, 0, 2, 1, "Left"),
        (4, 5, 0, 2, 0, "Forward"), (3, 3, 0, 2, 2, "Forward"),
        (6, 6, 0, 2, 0, "Left"), (4, 4, 1, 2, 2, "Backward"), (4, 6, 0, 1, 2, "Backward"),
    ):
        board.place(f"WireDefault{hi - lo}Up{kind}", *site(x, y), lo,
                    (rotation + turn) % 4, height=hi - lo + 1)
    layout.gate(("LogicGateIf", (saved, "retain"), (value,), None), *site(5, 5), 0, (1 + turn) % 4)
    layout.gate(("LogicGateIf", (incoming, "load"), (value,), None), *site(5, 5), 1, (1 + turn) % 4)
    for net, x, y, z, directions in (
        (saved, 2, 3, 2, (0, 2)), (saved, 4, 3, 0, (1, 2)),
        (saved, 4, 4, 0, (0, 3)), (saved, 5, 4, 0, (1, 2)),
        (incoming, 5, 4, 1, (1, 2)), (incoming, 5, 4, 2, (1, 2)),
        (incoming, 5, 5, 2, (2, 3)), (value, 5, 6, 0, (0, 2, 3)),
        (value, 5, 6, 1, (2, 3)), (value, 6, 3, 2, (1, 2)),
        (value, 6, 4, 2, (1, 3)), (value, 6, 5, 2, (1, 3)),
    ):
        p = (*site(x, y), z)
        if p in board.occupied or board.traces[p].keys() - {net}:
            raise ValueError("紧凑锁存单元的本地走线重叠")
        board.traces[p][net] = {(d + turn) % 4 for d in directions}
    for net, x, y, z in ((saved, 2, 3, 2), (value, 6, 3, 2), (incoming, 5, 5, 2)):
        board.terminals[net, z].add((*site(x, y), z))


def _radio(layout, name, channel, receive, site, level):
    x, y, rotation = site
    direction = rotation if receive else (rotation + 2) % 4
    dx, dy = DIRECTIONS[direction]
    a, b = x + 2 * dx, y + 2 * dy
    for z in (level, 3 - level):
        for kind, turn in (("Forward", 0), ("Left", 3), ("Backward", 2)):
            trial = layout.copy()
            board = trial.board
            try:
                trial.radio(name, channel, x, y, rotation, receive=receive)
                board.traces.pop((a, b, 0))
                board.terminals.pop((name, 0))
                board.place(f"WireDefault{z}Up{kind}", a, b, 0, direction, height=z + 1)
                board.pin(name, a, b, z, (direction + turn) % 4)
            except ValueError:
                continue
            if not any(board.traces.get(p) for p in board.occupied - layout.board.occupied):
                return trial
    return None


def _place_radios(layout, radios, random, prefer_edge):
    sites = list(product(range(1, 13), range(1, 13), range(4)))
    random.shuffle(radios)
    for name, channel, receive in radios:
        random.shuffle(sites)
        if prefer_edge:
            sites.sort(key=lambda p: min(p[0], p[1], 13 - p[0], 13 - p[1]) + random.random() * 3)
        for site in sites:
            trial = _radio(layout, name, channel, receive, site, 1 + random.randrange(2))
            if trial is not None:
                layout = trial
                break
        else:
            raise ValueError(f"紧凑锁存板无法摆放频道 {channel}")
    return layout


def _capture_board(control, seed):
    layout = _small()
    for name, y, z in _EAST:
        _short(layout, name, 14, y, z, 0, receive=False)
    for name, x, z in _SOUTH:
        _short(layout, name, x, 14, z, 1, receive=False)
    ports = [(n, ch, True) for n, ch in control.inputs.items()]
    ports.extend((n, ch, False) for n, ch in control.outputs.items())
    layout = _place_radios(layout, ports, Random(seed), seed % 2)
    for name in (("load", "retain") if seed % 2 else ("retain", "load")):
        connect_bus(layout.board, name, seed)
    return place_controls(layout, control.gates, seed)


def _register_board(fields, seed):
    layout = _small()
    random = Random(seed)
    for field, slot in zip(fields, random.sample(range(4), 2), strict=True):
        _cell(layout, field, f"saved-{field[1]}", 7 * (slot % 2), 7 * (slot // 2), random.randrange(4))
    for name, y, z in _EAST:
        _short(layout, name, -1, y, z, 0, receive=True)
    for name in (("load", "retain") if seed % 2 else ("retain", "load")):
        connect_bus(layout.board, name, seed)
    return layout


def _height_board(fields, height, column, seed):
    layout = _small()
    random = Random(seed)
    slot = random.randrange(4)
    _cell(layout, fields[2], "height0", 7 * (slot % 2), 7 * (slot // 2), random.randrange(4))
    for name, x, z in _SOUTH:
        _short(layout, name, x, -1, z, 1, receive=True)
    for name in (("load", "retain") if seed % 2 else ("retain", "load")):
        connect_bus(layout.board, name, seed)
    ports = [("column", column, True), *((f"height{i}", fields[i + 2][1], True) for i in (1, 2, 3)),
             ("current_height", height.outputs["current_height"], False)]
    layout = _place_radios(layout, ports, random, seed % 2)
    return place_controls(layout, height.gates, seed)


def middle_snapshot(fields, control, height, column):
    # 从已布通的摆放顺序开始。门位和路径仍由真实端口共同决定。
    layouts = (_capture_board(control, 45), _register_board(fields[:2], 82),
               _height_board(fields, height, column, 30))
    entries = []
    expected = {}
    offset = 0
    for (x, y), layout in zip(((0, 0), (1, 0), (0, 1)), layouts, strict=True):
        platform, = layout.board.finish()["Entries"]
        entries.append(dict(platform, X=x, Y=y))
        pins = {**layout.literals, **{p: layout.drivers[n] for p, n in layout.inputs.items()}}
        expected.update({(offset + i, pin): {(offset + j, out) for j, out in sources}
                         for (i, pin), sources in pins.items()})
        offset += len(platform["B"]["Entries"])
    wiring = Wiring({"Entries": entries})
    senders = [i for (i, pin), _ in layouts[0].inputs.items() if pin == 0 and i < 4]
    receivers = [i for i, (_, entry) in enumerate(wiring.entries)
                 if entry["T"] == "WireTransmitterReceiverInternalVariant"]
    if len(senders) != 4 or wiring.short_ports != dict(zip(receivers, senders, strict=True)):
        raise ValueError("中层的原生飞线配对与布局不符")
    for pin, sources in expected.items():
        if not sources or set(wiring._direct_sources(*pin)) != sources:
            raise ValueError(f"中层锁存板的端口 {pin} 接线与逻辑网表不符")
    return entries
