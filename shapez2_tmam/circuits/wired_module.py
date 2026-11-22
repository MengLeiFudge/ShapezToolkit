"""组合部件在3×3平台内的本地接线。全局收发器分别对应方法的输入和返回值。"""

from collections import defaultdict, deque
from itertools import product
from math import dist

from .circuit import Circuit, Literal, Ref, _TYPES, constant
from ..mari.blueprint import DIRECTIONS, Wiring
from ..mari.ports import PORTS


class _Board:
    def __init__(self):
        self.entries = []
        self.occupied = set()
        self.traces = defaultdict(dict)
        self.terminals = defaultdict(set)

    def place(self, kind, x, y, level, rotation=0, config=None, *, radius=0, height=1):
        footprint = {(x + dx, y + dy, level + dz) for dx, dy in product(range(-radius, radius + 1), repeat=2)
                     for dz in range(height)}
        if self.occupied & footprint or any(not (0 <= a < 54 and 0 <= b < 54 and 0 <= l < 3)
                                            for a, b, l in footprint):
            raise ValueError(f"建筑占地冲突或越界 {kind}@{(x, y, level)}")
        self.occupied.update(footprint)
        entry = {"T": _TYPES.get(kind, kind + "InternalVariant"), "X": x - 17, "Y": y - 17,
                 "L": level, "R": rotation}
        if config is not None:
            entry["C"] = config
        self.entries.append(entry)
        return len(self.entries) - 1

    def pin(self, net, x, y, level, facing):
        dx, dy = DIRECTIONS[facing]
        site = x + dx, y + dy, level
        if (site in self.occupied or self.traces[site].keys() - {net}
                or not (0 <= site[0] < 54 and 0 <= site[1] < 54)):
            raise ValueError(f"本地端口出口被占用 {site}")
        self.traces[site].setdefault(net, set()).add((facing + 2) % 4)
        self.terminals[net, level].add(site)

    def riser(self, net, low, high):
        pins = self.terminals[net, low] | self.terminals[net, high]
        cx = sum(x for x, _, _ in pins) / len(pins)
        cy = sum(y for _, y, _ in pins) / len(pins)
        for x, y in sorted(product(range(1, 53), repeat=2), key=lambda xy: dist(xy, (cx, cy))):
            if any((x + dx, y + dy, l) in self.occupied or (x + dx, y + dy, l) in self.traces
                   for dx, dy in product(range(-1, 2), repeat=2) for l in range(low, high + 1)):
                continue
            for direction, (dx, dy) in enumerate(DIRECTIONS):
                if any((x + dx, y + dy, l) in self.occupied or (x + dx, y + dy, l) in self.traces
                       for l in (low, high)):
                    continue
                self.place(f"WireDefault{high - low}UpBackward", x, y, low, (direction + 2) % 4, height=high - low + 1)
                for level in (low, high):
                    self.pin(net, x, y, level, direction)
                return
        raise ValueError("平台中没有可用的换层格")

    def route(self, net, terminals):
        """把端口逐一接入同一棵树。两条异网直线正交时才允许共用线桥。"""
        tree = {min(terminals)}
        todo = terminals - tree
        while todo:
            queue = deque(sorted(todo))
            previous = dict.fromkeys(queue)
            while queue:
                site = queue.popleft()
                if site in tree:
                    break
                x, y, level = site
                for direction, (dx, dy) in enumerate(DIRECTIONS):
                    a, b = x + dx, y + dy
                    while 0 <= a < 54 and 0 <= b < 54 and (a, b, level) not in self.occupied:
                        target = a, b, level
                        wires = self.traces.get(target, {})
                        if not wires or net in wires:
                            if target not in previous and len(wires) <= 1:
                                previous[target] = site, direction
                                queue.append(target)
                            break
                        if len(wires) != 1 or next(iter(wires.values())) != {(direction + 1) % 4, (direction + 3) % 4}:
                            break
                        a, b = a + dx, b + dy
            else:
                return False
            while previous[site] is not None:
                source, direction = previous[site]
                dx, dy = DIRECTIONS[direction]
                while site != source:
                    self.traces[site].setdefault(net, set()).add((direction + 2) % 4)
                    site = site[0] - dx, site[1] - dy, site[2]
                    self.traces[site].setdefault(net, set()).add(direction)
                    # 线桥的中间格不能再开第三个口。
                    if len(self.traces[site]) == 1:
                        tree.add(site)
            todo -= tree
        return True

    def finish(self):
        shapes = (("Forward", (0, 2)), ("Left", (2, 3)), ("Junction", (0, 1, 3)), ("Cross", (0, 1, 2, 3)))
        variants = {frozenset((d + r) % 4 for d in ports): (kind, r)
                    for kind, ports in shapes for r in range(4)}
        for (x, y, level), nets in self.traces.items():
            if len(nets) == 2 and {frozenset(s) for s in nets.values()} == {frozenset((0, 2)), frozenset((1, 3))}:
                kind, rotation = "Bridge", 0
            elif len(nets) == 1:
                ports = next(iter(nets.values()))
                if len(ports) == 1:
                    continue
                kind, rotation = variants[frozenset(ports)]
            else:
                raise ValueError(f"线桥混接 {(x, y, level)}")
            self.place("WireDefault" + kind, x, y, level, rotation)
        return {"$type": "Island", "BinaryVersion": 1137, "Entries": [{"T": "Foundation_3x3", "B": {
            "$type": "Building", "BinaryVersion": 1137, "Entries": self.entries}}]}


def wired_module(circuit: Circuit, outputs: dict[str, int], *, exports: dict[int, int] | None = None) -> dict:
    """单平台组合部件。核对每个输入的全部几何驱动，包括共用母线的互斥输出。"""
    board = _Board()
    channels = circuit.channel_map()
    drivers = defaultdict(list)
    expected = {}
    constants = {}
    used = {channels[value] for gate in circuit.gates for value in gate.inputs if isinstance(value, Ref)}
    used.update(outputs.values())
    # 门的相邻格留给常量和导线。连续的小组放在同层，公开接口集中在两侧。
    sites = iter((13 + 7 * (col if row % 2 == 0 else 3 - col), 10 + 6 * row, l)
                 for row in range(7) for l in range(3) for col in range(4))
    receivers = iter(range(13, 50, 5))
    transmitters = iter(range(17, 50, 5))

    def radio(kind, channel):
        receive = kind == "ControlledSignalReceiver"
        x, y = (6, next(receivers)) if receive else (42, next(transmitters))
        i = board.place(kind, x, y, 0, radius=1, height=3)
        sender = board.place("ConstantSignal", x, y - 2, 0, 1, constant(channel))
        constants[i, 0] = ((sender, 0),)
        return i, x, y

    input_count = sum(gate.kind == "ControlledSignalReceiver" for gate in circuit.gates)
    if input_count > len(range(13, 50, 5)) or len(set(outputs.values())) > len(range(17, 50, 5)):
        raise ValueError("单平台接口超出收发器排布范围")
    if len(circuit.gates) - input_count > 7 * 3 * 4:
        raise ValueError("单平台门数超出三层门阵列容量")
    for node, gate in enumerate(circuit.gates):
        if gate.kind == "ControlledSignalReceiver":
            source, = gate.inputs
            if not isinstance(source, Literal) or not isinstance(source.value, int):
                raise ValueError("本地组合部件的输入需要固定频道")
            index, x, y = radio(gate.kind, source.value)
            net = channels[Ref(node)]
            drivers[net].append((index, 0))
            if net in used:
                board.pin(net, x + 1, y, 0, 0)
            continue
        if gate.kind == "VirtualHalvesSwapper":
            raise ValueError("本地门阵列尚未布局双格交换器")
        x, y, level = next(sites)
        index = board.place(gate.kind, x, y, level, config=gate.config)
        for category, ports in enumerate(PORTS[gate.kind][:2]):
            for port, (direction, dx, dy, dz) in enumerate(ports):
                source = gate.inputs[port] if category else Ref(node, port)
                if isinstance(source, Literal):
                    vx, vy = DIRECTIONS[direction]
                    sender = board.place("ConstantSignal", x + vx, y + vy, level,
                                         (direction + 2) % 4, constant(source.value))
                    constants[index, port] = ((sender, 0),)
                    continue
                net = channels[source]
                if category:
                    expected[index, port] = net
                else:
                    drivers[net].append((index, port))
                if net in used:
                    board.pin(net, x + dx, y + dy, level + dz, direction)
    for net in dict.fromkeys(outputs.values()):
        index, x, y = radio("ControlledSignalTransmitter", net if exports is None else exports[net])
        board.pin(net, x - 1, y, 0, 2)
        expected[index, 1] = net
    for net in sorted(used):
        levels = [level for level in range(3) if (net, level) in board.terminals]
        for low, high in zip(levels, levels[1:]):
            board.riser(net, low, high)
    pads = {p: {net: set(ports) for net, ports in nets.items()} for p, nets in board.traces.items()}
    order = sorted(board.terminals, key=lambda key: (-len(board.terminals[key]), key))
    tried = set()
    while tuple(order) not in tried and len(tried) < len(order):
        tried.add(tuple(order))
        board.traces = defaultdict(dict, {p: {net: set(ports) for net, ports in nets.items()}
                                          for p, nets in pads.items()})
        for key in order:
            if not board.route(key[0], board.terminals[key]):
                order.remove(key)
                order.insert(0, key)
                break
        else:
            break
    else:
        raise ValueError(f"本地信号 {order[0]} 无法完成布线")
    blueprint = board.finish()
    wiring = Wiring(blueprint)
    for pin, sources in {**constants, **{pin: tuple(sorted(drivers[net])) for pin, net in expected.items()}}.items():
        if not sources or wiring.sources(*pin) != sources:
            raise ValueError(f"本地端口 {pin} 的实际来源 {wiring.sources(*pin)}，应为 {sources}")
    return {"V": 1137, "BP": blueprint}


def method_platforms(circuit: Circuit, channels: dict[Ref, int]) -> list[dict]:
    """只在方法的真实参数与返回值处连接主网表，内部保留全部原生端口索引。"""
    result = []
    for nodes, returns in circuit.method_ranges:
        exported = set(returns)
        for node, gate in enumerate(circuit.gates):
            if node in nodes:
                continue
            if any(isinstance(ref, Ref) and ref.node in nodes and ref not in exported for ref in gate.inputs):
                raise ValueError("方法内部信号被外部直接引用")
        if any(ref.node in nodes for group in circuit.aliases for ref in group):
            raise ValueError("独立方法的内部频道与外部共用别名")
        local = Circuit()
        sources = {}
        for node in nodes:
            gate = circuit.gates[node]
            inputs = []
            for value in gate.inputs:
                if isinstance(value, Literal):
                    inputs.append(value)
                    continue
                if value not in sources:
                    if value.node in nodes:
                        raise ValueError("本地组合方法存在前向引用")
                    sources[value] = local.add("ControlledSignalReceiver", Literal(channels[value]))
                inputs.append(sources[value])
            placed = local.add(gate.kind, *inputs, config=gate.config)
            for port in range(len(PORTS[gate.kind][0])):
                sources[Ref(node, port)] = Ref(placed.node, port)
        wires = local.channel_map()
        exports = {wires[sources[ref]]: channels[ref] for ref in returns}
        document = wired_module(local, {str(net): net for net in exports}, exports=exports)
        result.extend(document["BP"]["Entries"])
    return result
