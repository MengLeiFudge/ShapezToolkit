"""把本地门网布置到三层 3×3 平台并核对实际输入来源。"""

from collections import defaultdict
from graphlib import TopologicalSorter

from ...mari.blueprint import DIRECTIONS, Wiring
from ...mari.ports import PORTS
from ..circuit import Circuit, Literal, Ref, constant
from ..wired_module import _Board


_GATE_ROWS = range(4, 51, 5)
_GATE_COLUMNS = range(8, 43, 5)
_RADIO_ROWS = range(5, 51, 5)


def _route(board: _Board):
    for net in sorted({net for net, _ in board.terminals}):
        levels = [z for z in range(3) if (net, z) in board.terminals]
        for low, high in zip(levels, levels[1:]):
            board.riser(net, low, high)
    pads = board.traces
    order = sorted(board.terminals, key=lambda key: (-len(board.terminals[key]), key))
    tried = set()
    while len(tried) < 6 and tuple(order) not in tried:
        tried.add(tuple(order))
        board.traces = defaultdict(dict, {p: {net: set(ports) for net, ports in dots.items()}
                                          for p, dots in pads.items()})
        for key in order:
            if not board.route(key[0], board.terminals[key]):
                order.remove(key)
                order.insert(0, key)
                break
        else:
            return board.finish()
    raise ValueError(f"三层平台内无法完成本地信号 {order[0][0]} 的布线")


def layout(circuit: Circuit, outputs: dict[int, Ref]) -> tuple[dict, int]:
    """公开接口使用无线。网表内部按真实端口路由，包括双格交换门。"""
    channels = circuit.channel_map()
    providers = defaultdict(set)
    for ref, net in channels.items():
        providers[net].add(ref.node)
    live = {node for node, gate in enumerate(circuit.gates) if gate.kind == "ControlledSignalReceiver"}
    pending = [node for ref in outputs.values() for node in providers[channels[ref]]]
    while pending:
        node = pending.pop()
        if node not in live:
            live.add(node)
            for arg in circuit.gates[node].inputs:
                if isinstance(arg, Ref):
                    pending.extend(providers[channels[arg]] - live)
    used = {channels[arg] for node in live for arg in circuit.gates[node].inputs if isinstance(arg, Ref)}
    used.update(channels[ref] for ref in outputs.values())

    radios = [node for node in sorted(live) if circuit.gates[node].kind == "ControlledSignalReceiver"]
    gates = sorted(live - set(radios))
    capacity = len(_GATE_ROWS) * len(_GATE_COLUMNS) * 3
    if max(len(radios), len(outputs)) > len(_RADIO_ROWS) or len(gates) > capacity:
        raise LayoutCapacityError(f"三层平台容量不足，{len(gates)}/{capacity} 个门，"
                                  f"接收 {len(radios)}、发射 {len(outputs)}，每侧最多 {len(_RADIO_ROWS)} 个")
    # 保留规则门位，改变门的空间分布以绕开高扇出的布线拥塞。
    rows = (tuple(_GATE_ROWS), tuple(reversed(_GATE_ROWS)))
    columns = (tuple(_GATE_COLUMNS), tuple(reversed(_GATE_COLUMNS)))
    levels = range(3)
    row_sites = [(x, y) for i, y in enumerate(rows[0]) for x in columns[i % 2]]
    col_sites = [(x, y) for i, x in enumerate(columns[0]) for y in rows[i % 2]]
    shapes = (
        [(x, y, z) for x, y in row_sites for z in levels],
        [(x, y, z) for x, y in col_sites for z in levels],
        [(x, y, z) for z in levels for x, y in row_sites],
        [(x, y, z) for z in levels for x, y in col_sites],
        [(x, y, (i + z) % 3) for z in levels for i, (x, y) in enumerate(row_sites)],
        [(x, y, (i + z) % 3) for z in levels for i, (x, y) in enumerate(col_sites)],
    )
    last_error = None
    for sites in shapes:
        try:
            return _place(circuit, channels, (radios, gates), used, sites, outputs)
        except _RoutingError as error:
            last_error = error
    raise LayoutCapacityError(f"三层平台未布通 {len(gates)} 个门，{last_error}") from last_error


class LayoutCapacityError(ValueError):
    pass


class _RoutingError(ValueError):
    pass


def _place(circuit: Circuit, channels: dict[Ref, int], groups: tuple[list[int], list[int]], used: set[int],
           sites: list[tuple[int, int, int]], outputs: dict[int, Ref]) -> tuple[dict, int]:
    radios, gates = groups
    board = _Board()
    drivers = defaultdict(list)
    sinks = {}
    fixed = {}
    for node, y in zip(radios, _RADIO_ROWS):
        channel, = circuit.gates[node].inputs
        assert isinstance(channel, Literal)
        index = board.place("ControlledSignalReceiver", 2, y, 0, radius=1, height=3)
        cfg = board.place("ConstantSignal", 2, y - 2, 0, 1, constant(channel.value))
        fixed[index, 0] = ((cfg, 0),)
        net = channels[Ref(node)]
        drivers[net].append((index, 0))
        if net in used:
            board.pin(net, 3, y, 0, 0)

    for node, (x, y, level) in zip(gates, sites):
        gate = circuit.gates[node]
        index = board.place(gate.kind, x, y, level, config=gate.config)
        if gate.kind == "VirtualHalvesSwapper":
            extra = x, y - 1, level
            if extra in board.occupied:
                raise ValueError(f"交换器占地冲突 {extra}")
            board.occupied.add(extra)
        for category, ports in enumerate(PORTS[gate.kind][:2]):
            for port, (direction, dx, dy, dz) in enumerate(ports):
                px, py, pz = x + dx, y + dy, level + dz
                source = gate.inputs[port] if category else Ref(node, port)
                if isinstance(source, Literal):
                    vx, vy = DIRECTIONS[direction]
                    cfg = board.place("ConstantSignal", px + vx, py + vy, pz,
                                      (direction + 2) % 4, constant(source.value))
                    fixed[index, port] = ((cfg, 0),)
                    continue
                net = channels[source]
                if category:
                    sinks[index, port] = net
                else:
                    drivers[net].append((index, port))
                if net in used:
                    board.pin(net, px, py, pz, direction)

    transmitters = []
    rows = (25,) if len(outputs) == 1 else _RADIO_ROWS
    for (channel, ref), y in zip(outputs.items(), rows):
        out = board.place("ControlledSignalTransmitter", 50, y, 0, radius=1, height=3)
        cfg = board.place("ConstantSignal", 50, y - 2, 0, 1, constant(channel))
        fixed[out, 0] = ((cfg, 0),)
        net = channels[ref]
        board.pin(net, 49, y, 0, 2)
        sinks[out, 1] = net
        transmitters.append(out)

    try:
        blueprint = _route(board)
    except ValueError as error:
        raise _RoutingError(str(error)) from error
    wiring = Wiring(blueprint)
    dependencies = defaultdict(set)
    expected = {**fixed, **{pin: tuple(sorted(drivers[net])) for pin, net in sinks.items()}}
    for (index, port), sources in expected.items():
        actual = wiring.sources(index, port)
        if not sources or actual != sources:
            raise ValueError(f"端口 {wiring.sites[index]}/{port} 期望 {sources}，实际接到 {actual}")
        dependencies[index].update(source for source, _ in sources)
    depths = {}
    for index in TopologicalSorter(dependencies).static_order():
        depths[index] = 1 + max((depths[src] for src in dependencies[index]), default=0)
    return {"V": 1137, "BP": blueprint}, max(depths[out] for out in transmitters)
