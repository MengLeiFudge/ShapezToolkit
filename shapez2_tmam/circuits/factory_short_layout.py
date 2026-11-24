"""把单侧飞线的稀疏控制板在同一排岛格内重新走线。"""

from itertools import product
from random import Random

from ..mari.blueprint import Wiring, _kind
from ..mari.signals import decode_constant
from .compiler_backend._middle_snapshot import _radio, _short
from .compiler_backend._snapshot_layout import _Layout
from .compiler_backend._snapshot_router import connect_bus, place_controls
from .foundations import TILE_SIZE, platform_ground


_FOUNDATION = "Foundation_1x3"
_SHORT = {"WireTransmitterSender", "WireTransmitterReceiver"}
_RADIOS = {"ControlledSignalReceiver", "ControlledSignalTransmitter"}


def _net(wiring, node):
    return f"net{wiring._find(node)}"


def _gate_layout(wiring, indices):
    for index in indices:
        entry = wiring.entries[index][1]
        outputs, inputs, _ = wiring.pins[index]
        args = []
        for port, node in enumerate(inputs):
            sources = wiring._direct_sources(index, port)
            arg = _net(wiring, node)
            if len(sources) == 1:
                source = wiring.entries[sources[0][0]][1]
                if _kind(source) == "ConstantSignal":
                    arg = decode_constant(source["C"])
                    if arg is not None and type(arg) is not int:
                        raise ValueError("短距板重排只支持空信号和整数常量")
            args.append(arg)
        yield _kind(entry), tuple(args), tuple(_net(wiring, pin) for pin in outputs), entry.get("C")


def _route(wiring, ports, radios, gates, row, seed):
    layout = _Layout(_FOUNDATION)
    ground = platform_ground(_FOUNDATION)
    board = layout.board
    board.ground = ground
    for index in ports:
        entry = wiring.entries[index][1]
        outputs, inputs, _ = wiring.pins[index]
        net = _net(wiring, (outputs or inputs)[0])
        _short(layout, net, entry["X"] - board.origin_x, entry["Y"] - TILE_SIZE * row - board.origin_y,
               entry["L"], entry["R"], receive=bool(outputs))

    random = Random(seed)
    for index in radios:
        outputs, inputs, _ = wiring.pins[index]
        net = _net(wiring, outputs[0] if outputs else inputs[1])
        (source, _), = wiring._direct_sources(index, 0)
        channel = decode_constant(wiring.entries[source][1]["C"])
        sites = list(product(range(1, board.width - 1), range(1, board.height - 1), range(4)))
        random.shuffle(sites)
        for site in sites:
            trial = _radio(layout, net, channel, bool(outputs), site, 1 + random.randrange(2))
            if trial is not None:
                layout = trial
                break
        else:
            raise ValueError("窄板无法布置无线端口")

    pads = layout.board.terminals
    for name in sorted({net for net, _ in pads}):
        if sum(len(sites) for (net, _), sites in pads.items() if net == name) > 1:
            connect_bus(layout.board, name, seed)
    layout = place_controls(layout, gates, seed)
    result = Wiring(layout.board.finish())
    expected = {**layout.literals, **{pin: layout.drivers[net] for pin, net in layout.inputs.items()}}
    if any(not sources or tuple(sorted(result._direct_sources(*pin))) != tuple(sorted(sources))
           for pin, sources in expected.items()):
        raise ValueError("窄板的实际接点与逻辑网表不符")
    return result.platforms[0]


def reroute_short_board(board):
    if board["T"] != "Foundation_2x3":
        return board
    entries = board["B"]["Entries"]
    kinds = tuple(_kind(entry) for entry in entries)
    ports = [i for i, kind in enumerate(kinds) if kind in _SHORT]
    rows = {entries[i]["Y"] for i in ports}
    if rows not in ({2}, {37}):
        return board
    # 窄板保留原来的北边或南边，再重排板内端口和控制门。
    row = int(rows == {37})
    radios = [i for i, kind in enumerate(kinds) if kind in _RADIOS]
    logic = [i for i, kind in enumerate(kinds) if kind.startswith("LogicGate")]
    if len(radios) > 2 or not 1 <= len(logic) <= 12 or any(
            kind not in _RADIOS and kind != "ConstantSignal" and not kind.startswith(("Wire", "LogicGate"))
            for kind in kinds):
        return board
    wiring = Wiring({"Entries": [board]})
    try:
        gates = tuple(_gate_layout(wiring, logic))
    except ValueError:
        return board
    for seed in range(4):
        try:
            result = _route(wiring, ports, radios, gates, row, seed)
        except ValueError:
            continue
        return {**result, "X": board.get("X", 0), "Y": board.get("Y", 0) + row, "Z": board.get("Z", 0)}
    return board
