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
    while tuple(order) not in tried:
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
        raise ValueError("本地门网超过单块三层 3×3 平台容量")
    # 紧邻行之间每隔一层换层，给各层保留可供换层线使用的纵向通道。
    rows = (tuple(_GATE_ROWS), tuple(reversed(_GATE_ROWS)))
    sites = ((x, y, level) for i, x in enumerate(_GATE_COLUMNS) for y in rows[i % 2]
             for level in range(3))
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

    blueprint = _route(board)
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
