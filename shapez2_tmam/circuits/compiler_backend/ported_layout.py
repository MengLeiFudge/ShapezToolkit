"""直接从组合方法生成带多路短距端口的原生电路。"""

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from graphlib import TopologicalSorter
from pathlib import Path
from time import perf_counter

from ...mari.blueprint import DIRECTIONS, Wiring, _kind, _rotate
from ...mari.ports import OUT, PORTS, WEST
from ..circuit import Gate, Literal, Ref, constant
from ..compiler_contract import Program
from ..compiler_frontend import FrontendError, compile_field_methods
from ..foundations import EDGE_MARGIN, FOUNDATION_CHUNKS, TILE_SIZE, foundation_tiles, platform_ground, platform_interior
from ..wired_module import _Board
from . import _write_blueprint
from ._lower import Lowering, _Value
from ._optimize import compact, simplify_null_guards
from ._snapshot_router import _join


_RX = "WireTransmitterReceiver"
_TX = "WireTransmitterSender"
_GLOBAL_RX = 'ControlledSignalReceiver'
_GLOBAL_TX = 'ControlledSignalTransmitter'
_RADIOS = {_GLOBAL_RX, _GLOBAL_TX}
_FOUNDATIONS = (
    "Foundation_1x1",
    "Foundation_1x2",
    "Foundation_1x3",
    "Foundation_2x2",
    "Foundation_1x4",
    "Foundation_L3",
    "Foundation_2x3",
    "Foundation_2x4",
    "Foundation_3x3",
)
_SIDES = "ESWN"
_Site = tuple[int, int, int]


@dataclass(frozen=True)
class Notch:
    """平台建筑坐标和朝外的一侧。"""

    x: int
    y: int
    level: int
    side: str

    def rotation(self, receiver: bool) -> int:
        if self.side not in tuple(_SIDES) or not 0 <= self.level <= 2:
            raise ValueError(f"无效凹口 {self}")
        return (_SIDES.index(self.side) + 2 * receiver) % 4


@dataclass(frozen=True)
class _Unit:
    nodes: tuple[int, ...]
    parents: frozenset[int]
    column: int
    lane: float
    tapped: bool = False

    def offset(self, index: int) -> int:
        return index + int(self.tapped and index != 0)


class _Netlist:
    feedback_units: tuple[_Unit, ...] | None = None
    feedback_nets: frozenset[int] = frozenset()

    def __init__(self, programs: Mapping[str, Program]):
        if not programs:
            raise ValueError("至少需要一个输出方法")
        lowerings = {name: Lowering(program) for name, program in programs.items()}
        methods = {name: lowerings[name].functions[program.entry] for name, program in programs.items()}
        args = next(iter(methods.values())).inputs
        if any((program.quadrants, program.height) != (4, 5) for program in programs.values()):
            raise ValueError("原生后端需要四象限五层 Program")
        if any(method.inputs != args for method in methods.values()):
            raise ValueError("各输出方法需要相同的命名参数和类型")

        circuit = next(iter(lowerings.values())).circuit
        inputs = {arg.name: circuit.add("ConstantSignal", config=constant(i)) for i, arg in enumerate(args)}
        values = tuple(_Value(arg.type, inputs[arg.name]) for arg in args)
        outputs = {}
        for i, (name, method) in enumerate(methods.items()):
            lowering = lowerings[name]
            lowering.circuit = circuit
            result = lowering.invoke(method.name, values).signal
            outputs[i] = (
                circuit.add("ConstantSignal", config=constant(result.value)) if isinstance(result, Literal) else result
            )

        self._load(circuit, inputs, {name: outputs[i] for i, name in enumerate(methods)},
                   {name: method.name for name, method in methods.items()})

    @classmethod
    def from_circuit(cls, circuit, inputs, outputs, *, feedback=None, transmitters=None):
        model = cls.__new__(cls)
        model._load(circuit, inputs, outputs, dict.fromkeys(outputs, '原生网表'), transmitters)
        if feedback:
            # 开环网表决定试摆顺序，最终走线和验线共用闭环网。
            model.lane_nets = tuple(net for name, net in model.outputs.items() if name not in feedback.values())
            model.feedback_units = model.units()
            model.feedback_nets = frozenset(model.outputs[name] for name in feedback.values())
            for input_, output in feedback.items():
                old = model.inputs.pop(input_)
                new = model.outputs.pop(output)
                model.nets = {ref: new if net == old else net for ref, net in model.nets.items()}
                model.readers[new].extend(model.readers.pop(old))
                model.live.discard(old)
                model.live.add(new)
        return model

    def _load(self, circuit, inputs, outputs, methods, transmitters=None):
        names = tuple(outputs)
        channels = tuple(transmitters or ())
        signals = () if transmitters is None else tuple(transmitters.values())
        if any(type(channel) is not int or not 1 <= channel < 1 << 24 for channel in channels):
            raise ValueError('发射器频道需要为 1 至 2^24−1 的整数')
        outputs = dict(enumerate((*outputs.values(), *signals)))
        # 输入占位与普通常量即使值相同也必须成不同的网。
        circuit, refs = compact(circuit, outputs, distinct=tuple(inputs.values()))
        simplify_null_guards(circuit)
        circuit.retain_outputs(tuple(refs.values()))
        assert circuit.retained_nodes is not None
        self.nets = circuit.channel_map()
        self.gates = {
            node: gate
            for node, gate in enumerate(circuit.gates)
            if node in circuit.retained_nodes and node not in {ref.node for ref in inputs.values()}
        }
        for offset, channel in enumerate(channels, len(names)):
            node = len(circuit.gates) + offset
            self.gates[node] = Gate(_GLOBAL_TX, (Literal(channel), refs[offset]), None)
        self.inputs = {name: self.nets[ref] for name, ref in inputs.items()}
        self.outputs = {name: self.nets[refs[i]] for i, name in enumerate(names)}
        self.writers = defaultdict(set)
        self.readers = defaultdict(list)
        for node, gate in self.gates.items():
            for port in range(len(PORTS[gate.kind][0])):
                self.writers[self.nets[Ref(node, port)]].add(node)
            for arg in gate.inputs:
                if isinstance(arg, Ref):
                    self.readers[self.nets[arg]].append(node)
        self.live = set(self.readers) | set(self.outputs.values())
        self.methods = methods
        roots = tuple(self.outputs.values())
        if len(roots) == 1:
            parallel = defaultdict(list)
            for net in sorted(self.live):
                drivers = tuple(self.gates[n] for n in sorted(self.writers[net]))
                if len(drivers) < 2 or not all(g.kind == "LogicGateIf" and isinstance(g.inputs[0], Literal)
                                               for g in drivers):
                    continue
                signature = frozenset(g.inputs[0] for g in drivers)
                parallel[signature].append(net)
            branches = max(parallel.values(), key=len, default=[])
            if len(branches) > 1:
                roots = tuple(branches)
            elif len(self.gates) > 40:
                merged = self.stack_branches(roots[0])
                roots = merged if 2 <= len(merged) <= 4 else self.parallel_frontier(roots)
        self.lane_nets = roots

    def stack_branches(self, net):
        """沿左右拼合树找支路，旋转仍由公共分发或汇聚侧完成。"""
        pending = [net]
        leaves = []
        while pending:
            if len(pending) + len(leaves) > 4:
                return ()
            root = pending.pop()
            writers = [self.gates[n] for n in self.writers[root]]
            if len(writers) == 1 and writers[0].kind in ('VirtualRotator', 'VirtualRotatorCCW'):
                arg = writers[0].inputs[0]
                if isinstance(arg, Ref):
                    pending.append(self.nets[arg])
                    continue
            stack = [g for g in writers if g.kind == 'VirtualStacker']
            if len(stack) == 1 and all(g.kind in ('VirtualStacker', 'LogicGateIf') for g in writers):
                left, right = stack[0].inputs
                if isinstance(left, Ref) and isinstance(right, Ref):
                    pending.extend((self.nets[right], self.nets[left]))
                    continue
            leaves.append(root)
        return tuple(dict.fromkeys(leaves))

    def parallel_frontier(self, roots):
        """沿汇聚图向上寻找宽度合适的条带根；共享上游仍由各条带共用。"""
        best = roots
        seen = set(roots)
        for _ in range(6):
            upstream = tuple(dict.fromkeys(self.nets[arg] for net in roots for node in sorted(self.writers[net])
                                           for arg in self.gates[node].inputs if isinstance(arg, Ref)
                                           and self.writers[self.nets[arg]]))
            if not upstream or set(upstream) <= seen:
                break
            if len(best) < len(upstream) <= 4:
                best = upstream
            seen.update(upstream)
            roots = upstream
        return best

    def slice(self, nodes, inputs, outputs):
        part = object.__new__(_Netlist)
        part.nets = self.nets
        part.gates = {n: self.gates[n] for n in sorted(nodes)}
        part.inputs, part.outputs = inputs, outputs
        part.writers = defaultdict(set, {net: self.writers[net] & nodes for net in self.writers})
        part.readers = defaultdict(list, {net: [n for n in readers if n in nodes]
                                         for net, readers in self.readers.items()})
        part.live = {net for net in part.readers if part.readers[net]} | set(outputs.values())
        part.lane_nets = tuple(outputs.values())
        part.methods = dict.fromkeys(outputs, "网表分区")
        return part


    def units(self) -> tuple[_Unit, ...]:
        dependencies = {
            node: frozenset(w for arg in gate.inputs if isinstance(arg, Ref) for w in self.writers[self.nets[arg]])
            for node, gate in self.gates.items()
        }
        order = tuple(TopologicalSorter(dependencies).static_order())
        lanes: dict[int, set[int]] = defaultdict(set)
        for lane, net in enumerate(self.lane_nets):
            for node in self.writers[net]:
                lanes[node].add(lane)
        for node in reversed(order):
            for dependency in dependencies[node]:
                lanes[dependency].update(lanes[node])

        owner: dict[int, int] = {}
        units = []
        columns: dict[int, int] = {}
        for node in order:
            if node in owner:
                continue
            chain = [node]
            first = self.gates[node]
            tapped = False
            if _straight(first) or first.kind == "LogicGateCompare":
                while True:
                    tail = chain[-1]
                    net = self.nets[Ref(tail)]
                    next_nodes = self.readers[net]
                    if (len(chain) == 1 and first.kind == "LogicGateCompare"
                            and (len(next_nodes) > 1 or net in self.outputs.values())):
                        inverse = next((n for n in next_nodes if self.gates[n].kind == "LogicGateNot"), None)
                        if inverse is not None:
                            chain.append(inverse)
                            tapped = True
                            break
                    if (
                        len(next_nodes) != 1
                        or self.writers[net] != {tail}
                        or net in self.outputs.values()
                        or not _straight(self.gates[next_nodes[0]])
                    ):
                        break
                    chain.append(next_nodes[0])
            parents = frozenset(owner[w] for w in dependencies[node])
            column = max((columns[parent] for parent in parents), default=0)
            lane = sum(lanes[node]) / len(lanes[node]) if lanes[node] else (len(self.lane_nets) - 1) / 2
            unit = _Unit(tuple(chain), parents, column, lane, tapped)
            units.append(unit)
            columns[node] = column + len(chain)
            owner.update((n, node) for n in chain)
        return tuple(units)

    def repeated_units(self, units):
        """从各输出向上匹配同构后缀。共用网络与朝向预处理留给各行外部。"""
        pending = [tuple(self.lane_nets)]
        seen = set()
        matches = {}
        while pending:
            nets = pending.pop()
            if nets in seen or len(set(nets)) < len(nets):
                continue
            seen.add(nets)
            writers = [sorted(self.writers[net]) for net in nets]
            if len({len(row) for row in writers}) != 1:
                continue
            for nodes in zip(*writers, strict=True):
                gates = tuple(self.gates[n] for n in nodes)
                signatures = {
                    (g.kind, g.config, tuple(a if isinstance(a, Literal) else a.port for a in g.inputs)) for g in gates
                }
                if len(signatures) != 1 or len(set(nodes)) != len(nodes):
                    continue
                matches.update((n, nodes) for n in nodes)
                pending.extend(
                    tuple(self.nets[a] for a in args if isinstance(a, Ref))
                    for args in zip(*(g.inputs for g in gates), strict=True)
                    if isinstance(args[0], Ref)
                )

        by_head = {unit.nodes[0]: unit for unit in units}
        groups = {}
        for unit in units:
            heads = matches.get(unit.nodes[0], ())
            if not heads or any(n not in by_head for n in heads):
                continue
            group = tuple(by_head[n] for n in heads)
            if len({(len(u.nodes), u.tapped) for u in group}) != 1:
                continue
            if any(matches.get(nodes[0]) != nodes for nodes in zip(*(u.nodes for u in group), strict=True)):
                continue
            groups[unit.nodes[0]] = group
        return groups


def _straight(gate: Gate) -> bool:
    return PORTS[gate.kind][:2] == (OUT, WEST) and isinstance(gate.inputs[0], Ref)


class _RoutingBoard(_Board):
    def __init__(self, *, foundation):
        super().__init__(foundation=foundation)
        self.short_sites = {_TX: set(), _RX: set()}
        self._owned = set()
        self._tracks = defaultdict(set)
        self.pad_sites = set()
        self.fixed_entries: list[dict] = []
        self.fixed_cells: set[_Site] = set()
        self.reroutes = 0
        self.route_stats = Counter()
        self.route_budget = 140
        self.wide = False
        self.pads = {}

    def fork(self):
        trial = _RoutingBoard(foundation=self.foundation)
        trial.origin_x, trial.origin_y = self.origin_x, self.origin_y
        trial.ground = self.ground
        trial.occupied = self.occupied.copy()
        trial.entries = self.entries.copy()
        trial.traces = self.traces.copy()
        trial._tracks = self._tracks.copy()
        trial.pad_sites = self.pad_sites.copy()
        trial.fixed_entries = self.fixed_entries.copy()
        trial.fixed_cells = self.fixed_cells.copy()
        trial.reroutes = self.reroutes
        trial.route_stats = self.route_stats
        trial.route_budget = self.route_budget
        trial.wide = self.wide
        trial.pads = self.pads.copy()
        trial.short_sites = {kind: sites.copy() for kind, sites in self.short_sites.items()}
        self._owned.clear()
        return trial

    def place(self, kind, x, y, level, rotation=0, config=None, *, radius=0, height=1):
        index = super().place(kind, x, y, level, rotation, config, radius=radius, height=height)
        if kind in self.short_sites:
            self.short_sites[kind].add((x, y, level, rotation))
        return index

    def wire(self, site, net, side):
        if site not in self._owned:
            self.traces[site] = {key: sides.copy() for key, sides in self.traces.get(site, {}).items()}
            self._owned.add(site)
        traces = self.traces[site]
        if net not in traces:
            if not traces:
                self._tracks[net] = self._tracks[net] | {site}
            elif len(traces) == 1:
                prior = next(iter(traces))
                self._tracks[prior] = self._tracks[prior] - {site}
            traces[net] = set()
        traces[net].add(side)

    def pad(self, site, net, side, sink):
        self.wire(site, net, side)
        self.pad_sites.add(site)
        self.pads[site, side] = net, sink

    def tracks(self, net):
        return self._tracks.get(net, set())


def _edge(board, kind, notch, net, ground):
    x, y, z = notch.x, notch.y, notch.level
    rotation = notch.rotation(kind == _RX)
    inward = rotation if kind == _RX else (rotation + 2) % 4
    dx, dy = DIRECTIONS[inward]
    if (x, y) not in ground - board.ground or (x + dx, y + dy) not in board.ground:
        raise ValueError(f"坐标未对准平台凹口 {notch}")
    site = x - board.origin_x, y - board.origin_y, z
    pad = site[0] + dx, site[1] + dy, z
    if site in board.occupied or pad in board.pad_sites:
        raise ValueError(f"端口重复占用凹口 {notch}")
    entry = {"T": kind + "InternalVariant", "X": x, "Y": y, "L": z, "R": rotation}
    board.entries.append(entry)
    board.fixed_entries.append(entry)
    board.fixed_cells.add(site)
    board.occupied.add(site)
    board.short_sites[kind].add((*site, rotation))
    board.pad(pad, net, (inward + 2) % 4, kind == _TX)
    return pad


def _input_spine(board, net, entry, exits):
    """在西边留一条直通母线，让各行从相邻位置取输入。"""
    z = entry.level
    y = entry.y - board.origin_y
    rows = [y, *(position.y - board.origin_y for position in exits if position.level == z)]
    top, bottom = min(rows), max(rows)
    for v in range(top, bottom + 1):
        sides = set()
        if v > top:
            sides.add(3)
        if v < bottom:
            sides.add(1)
        for side in sides:
            board.wire((1, v, z), net, side)
    board.wire((0, y, z), net, 0)
    board.wire((1, y, z), net, 2)


def _open_notches(ground, interior):
    for x, y in sorted(ground - interior):
        for side, (dx, dy) in zip(_SIDES, DIRECTIONS, strict=True):
            if (x - dx, y - dy) in interior:
                for level in range(3):
                    yield Notch(x, y, level, side)


def _input_slots(ground, interior, x, count, used):
    clear = [port for port in _open_notches(ground, interior) if port not in used]
    slots = sorted((p for p in clear if p.side == 'W' and p.x == x), key=lambda p: (p.level, p.y))
    if count > len(clear):
        raise ValueError(f'只剩 {len(clear)} 个朝向空地的输入凹口')
    if count > len(slots):
        return tuple((slots + sorted((p for p in clear if p not in slots), key=lambda p: (p.level, p.x, p.y)))[:count])
    first_layer = [p for p in slots if p.level == 0]
    if count <= len(first_layer):
        return tuple(first_layer[(2 * i + 1) * len(first_layer) // (2 * count)] for i in range(count))
    return tuple(slots[:count])


def _proposal(board, model, unit, x, y, z, turn):
    if not 0 <= z <= 2:
        return None
    chain = unit.nodes
    body = {(x + unit.offset(i), y, z) for i in range(len(chain))}
    for i, node in enumerate(chain):
        kind = model.gates[node].kind
        if kind in _RADIOS:
            if z != 0:
                return None
            body.update((x + dx, y + dy, level) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for level in range(3))
        elif kind == 'VirtualHalvesSwapper':
            dx, dy = _rotate(0, -1, turn)
            body.add((x + unit.offset(i) + dx, y + dy, z))
    if any(not board.on_ground(a, b) or p in board.occupied or board.traces.get(p) for p in body for a, b, _ in (p,)):
        return None
    pads = {}
    literals = {}
    for i, node in enumerate(chain):
        gate = model.gates[node]
        for category, ports in enumerate(PORTS[gate.kind][:2]):
            if (category == 0 and i != len(chain) - 1 and not unit.tapped) or (category == 1 and i != 0):
                continue
            for port, (facing, a, b, level) in enumerate(ports):
                arg = gate.inputs[port] if category else Ref(node, port)
                net = model.nets[arg] if isinstance(arg, Ref) else None
                if category == 0 and net not in model.live:
                    continue
                side = (facing + turn) % 4
                dx, dy = DIRECTIONS[side]
                a, b = _rotate(a, b, turn)
                p = x + unit.offset(i) + a + dx, y + b + dy, z + level
                if p in body or p in pads or p in literals or p in board.occupied or not board.on_ground(*p[:2]):
                    return None
                wires = board.traces.get(p, {})
                if isinstance(arg, Literal):
                    if wires:
                        return None
                    literals[p] = (constant(arg.value), (side + 2) % 4)
                elif wires.keys() - {net}:
                    return None
                else:
                    pads[p] = (net, (side + 2) % 4, category == 1)
    return body, pads, literals


def _bare_board(board):
    trial = _RoutingBoard(foundation=board.foundation)
    trial.origin_x, trial.origin_y = board.origin_x, board.origin_y
    trial.ground = board.ground
    trial.fixed_entries = board.fixed_entries.copy()
    trial.fixed_cells = board.fixed_cells.copy()
    trial.entries = trial.fixed_entries.copy()
    trial.occupied = trial.fixed_cells.copy()
    trial.reroutes = board.reroutes
    trial.route_stats = board.route_stats
    trial.route_budget = 800 if board.wide else 300
    trial.wide = board.wide
    for entry in trial.entries:
        kind = _kind(entry)
        if kind in trial.short_sites:
            trial.short_sites[kind].add((entry['X'] - trial.origin_x, entry['Y'] - trial.origin_y,
                                         entry['L'], entry['R']))
    for (site, side), (net, sink) in board.pads.items():
        trial.pad(site, net, side, sink)
    return trial


def _reroute(board, model, failed):
    """保留器件和凹口，先接失败网，再按历史拥塞代价重布。"""
    board.route_stats['ripup_attempts'] += 1
    bare = _bare_board(board)
    if _blocked_net(bare) is not None:
        return None
    terminals = defaultdict(dict)
    for (site, _), (net, sink) in board.pads.items():
        contacts = terminals[net]
        contacts[site] = contacts.get(site, True) and sink
    history = Counter()
    previous = board
    order = sorted(terminals, key=lambda n: (n != failed, -len(terminals[n]), n))
    for _ in range(3):
        for site in previous.tracks(failed) - board.pad_sites:
            history[site] += 1
        trial = bare.fork()
        for net in order:
            pins = sorted(terminals[net], key=lambda p: (terminals[net][p], p))
            tree = {pins[0]}
            unique = len(model.writers[net]) + int(net in model.inputs.values()) == 1
            for site in pins[1:]:
                flywire = unique and net not in model.feedback_nets and not terminals[net][pins[0]] and terminals[net][site]
                if not _join(trial, net, site, tree, direct=True, flywire=flywire,
                             protect_pads=True, history=history):
                    break
                tree.add(site)
                tree.update(p for p in trial.tracks(net) if p not in terminals[net])
            else:
                continue
            failed = net
            previous = trial
            order = [net, *(other for other in order if other != net)]
            break
        else:
            stuck = _blocked_net(trial)
            if stuck is None:
                trial.reroutes = board.reroutes + 1
                return trial
            for site in trial.traces.keys() - board.pad_sites:
                if any((site[0] + dx, site[1] + dy, site[2]) in board.pad_sites for dx, dy in DIRECTIONS):
                    history[site] += 1
            previous = trial
    return None


def _blocked_net(board, *, extend=False):
    for site in board.pad_sites:
        nets = board.traces[site]
        if len(nets) != 1:
            continue
        net, sides = next(iter(nets.items()))
        if len(sides) != 1:
            continue
        x, y, level = site
        def free(point):
            return (board.on_ground(*point[:2]) and point not in board.occupied
                    and not board.traces.get(point, {}).keys() - {net})

        exits = []
        for direction, (dx, dy) in enumerate(DIRECTIONS):
            dest = x + dx, y + dy, level
            if not free(dest):
                continue
            room = sum(free((dest[0] + a, dest[1] + b, level))
                       for j, (a, b) in enumerate(DIRECTIONS) if j != (direction + 2) % 4)
            room += sum((dest[0], dest[1], z) not in board.occupied and not board.traces.get((dest[0], dest[1], z))
                        for z in (level - 1, level + 1) if 0 <= z < 3)
            exits.append((room, direction, dest))
        if exits:
            if extend:
                _, direction, dest = max(exits)
                board.wire(site, net, direction)
                board.wire(dest, net, (direction + 2) % 4)
            continue
        return net
    return None


def _attach(board, model, unit, site, plan, driven, *, reroute=False, rebuild=False):
    trial = board.fork()
    entry_start = len(trial.entries)
    x, y, z, turn = site
    body, pads, literals = plan
    for i, node in enumerate(unit.nodes):
        gate = model.gates[node]
        radio = gate.kind in _RADIOS
        trial.place(gate.kind, x + unit.offset(i), y, z, turn, gate.config, radius=int(radio), height=3 if radio else 1)
    trial.occupied.update(body)
    for p, (config, facing) in literals.items():
        a, b, level = p
        trial.place("ConstantSignal", a, b, level, facing, config)
    trial.fixed_entries.extend(trial.entries[entry_start:])
    trial.fixed_cells.update(body | literals.keys())
    tapped = (x + 1, y, z) if unit.tapped else None
    trees = {net: trial.tracks(net) for net, _, _ in pads.values()}
    for p, (net, side, sink) in pads.items():
        if p == tapped:
            trial.pad(p, net, 0, True)
        trial.pad(p, net, side, sink)
    if rebuild:
        return _reroute(trial, model, None)
    for p, (net, _, sink) in sorted(pads.items(), key=lambda item: (not item[1][2], len(trees[item[1][0]]))):
        tree = trees[net]
        unique = len(model.writers[net]) + int(net in model.inputs.values()) == 1
        flywire = sink and unique and net in driven and net not in model.feedback_nets
        if tree and not _join(trial, net, p, tree, direct=True, flywire=flywire,
                              protect_pads=True):
            return _reroute(trial, model, net) if reroute else None
        trees[net] = tree | {p}
    blocked = _blocked_net(trial, extend=trial.wide)
    if blocked is None:
        return trial
    if reroute:
        trial.route_stats['blocked_pad_ripups'] += 1
        return _reroute(trial, model, blocked)
    return None


class _PlacementError(ValueError):
    pass


def _put_group(board, model, group, ideal, driven, *, rebuild=False):
    unit, _, _ = group[0]
    offsets = tuple((dy, dz) for _, dy, dz in group)
    tracks = board.tracks
    tx, ty, preferred_layer = ideal
    xs = sorted({a - board.origin_x for a, _ in board.ground}, key=lambda x: (abs(x - tx), x))
    ys = sorted({b - board.origin_y for _, b in board.ground}, key=lambda y: (abs(y - ty), y))
    candidates = []
    distance = {}
    levels = range(-min(dz for _, dz in offsets), 3 - max(dz for _, dz in offsets))
    if not board.wide:
        x_sites, y_sites = xs[:9], ys[:9]
    elif rebuild or len(group) == 1:
        x_sites, y_sites = xs[:17], ys[:17]
    else:
        x_sites = [x for x in xs if x % 3 == tx % 3][:9]
        y_sites = ys[::2][:7]
    for x in x_sites:
        for y in y_sites:
            for z in levels:
                for turn in (0,) if len(unit.nodes) > 1 else (0, 1, 3, 2):
                    plan = _proposal(board, model, unit, x, y, z, turn)
                    if plan is None:
                        continue
                    if any(_proposal(board, model, replica, x, y + dy, z + dz, turn) is None
                           for replica, dy, dz in group[1:]):
                        continue
                    score = 0
                    for p, (net, _, _) in plan[1].items():
                        if not tracks(net):
                            continue
                        key = net, p
                        if key not in distance:
                            a, b, c = p
                            distance[key] = min(abs(a - u) + abs(b - v) + 4 * abs(c - w) for u, v, w in tracks(net))
                        score += distance[key]
                    align = 2 * abs(x - tx) + 3 * abs(y - ty) + 8 * abs(z - preferred_layer)
                    if board.wide:
                        # 给长条带的端口留出局部转向空隙。
                        occupied = board.occupied
                        align += 6 * sum((x + dx, y + dy, z) in occupied
                                         for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)))
                    candidates.append(((score + align, align, turn != 0), (x, y, z, turn), plan))
    ranked = sorted(candidates)
    # 同一低层候选连续堵塞时，给其余层保留少量试摆机会。
    alternatives = [c for c in ranked if c[1][2] != preferred_layer][:12]
    ranked = list(dict.fromkeys(c[1] for c in ranked[:24] + alternatives + ranked[24:]))
    geometry = {site: (rank, site, plan) for rank, site, plan in candidates}
    ranked = [geometry[site] for site in ranked]
    if rebuild:
        budgets = ((True, 4),)
    elif len(group) > 1 and len(model.outputs) == 1:
        budgets = ((False, 10),)
    else:
        budgets = ((False, 36), (True, 2))
    for reroute, limit in budgets:
        best = None
        successes = 0
        for rank, site, plan in ranked[:limit]:
            trial = _attach(board, model, unit, site, plan, driven, reroute=reroute, rebuild=rebuild)
            if trial is None:
                continue
            x, y, z, turn = site
            sites = [site]
            for replica, dy, dz in group[1:]:
                shifted = (x, y + dy, z + dz, turn)
                replica_plan = _proposal(trial, model, replica, *shifted)
                if replica_plan is None:
                    break
                trial = _attach(trial, model, replica, shifted, replica_plan, driven, reroute=reroute)
                if trial is None:
                    break
                sites.append(shifted)
            if trial is None or len(sites) != len(group):
                continue
            growth = len(trial.entries) + len(trial.traces) - len(board.entries) - len(board.traces)
            score = growth + rank[1], rank
            if best is None or score < best[0]:
                best = score, trial, sites
            successes += 1
            if successes == (1 if len(model.gates) > 100 else 3) or reroute:
                break
        if best is not None:
            return best[1:]
    if len(group) == 1 and not rebuild and len(model.gates) > 50:
        return _put_group(_bare_board(board), model, group, ideal, driven, rebuild=True)
    raise _PlacementError(f"逻辑器件 {unit.nodes} 在列 {unit.column} 无法摆放并接通，有 {len(candidates)} 个候选")


def _local_sources(wiring, index, port):
    todo = list(wiring._direct_sources(index, port))
    visited, drivers = set(), set()
    while todo:
        source = todo.pop()
        if source in visited:
            continue
        visited.add(source)
        owner, _ = source
        if owner in wiring.short_ports:
            todo.extend(wiring._direct_sources(wiring.short_ports[owner], 0))
        else:
            drivers.add(source)
    return drivers


def _verify(island, model, coordinates, inputs, outputs):
    wiring = Wiring(island)
    input_indices = {name: wiring.lookup[0, p.x, p.y, p.level] for name, p in inputs.items()}
    output_indices = {name: wiring.lookup[0, p.x, p.y, p.level] for name, p in outputs.items()}
    open_ports = set(input_indices.values()) | set(output_indices.values())
    paired = set(wiring.short_ports) | set(wiring.short_ports.values())
    if open_ports & paired:
        raise ValueError("板缝端口与板内飞线产生竞争")
    shorts = {i for i, (_, entry) in enumerate(wiring.entries) if _kind(entry) in {_RX, _TX}}
    if shorts != open_ports | paired:
        raise ValueError("存在悬空的板内飞线端点")
    positions = {n: wiring.lookup[(0, *pos)] for n, pos in coordinates.items()}
    drivers = defaultdict(set, {model.inputs[name]: {(i, 0)} for name, i in input_indices.items()})
    for node, gate in model.gates.items():
        for port in range(len(PORTS[gate.kind][0])):
            drivers[model.nets[Ref(node, port)]].add((positions[node], port))

    for node, gate in model.gates.items():
        for port, arg in enumerate(gate.inputs):
            index = positions[node]
            actual = _local_sources(wiring, index, port)
            if isinstance(arg, Ref):
                matches = actual == drivers[model.nets[arg]]
            else:
                matches = len(actual) == 1 and all(
                    _kind(wiring.entries[i][1]) == "ConstantSignal" and wiring.entries[i][1]["C"] == constant(arg.value)
                    for i, _ in actual
                )
            if not matches:
                expected = drivers[model.nets[arg]] if isinstance(arg, Ref) else arg.value
                raise ValueError(f"门 {node} {wiring.sites[index]}/{port} 的驱动 {actual} 与网表 {expected} 不一致")
    for name, index in output_indices.items():
        if _local_sources(wiring, index, 0) != drivers[model.outputs[name]]:
            raise ValueError(f"输出 {name} 的驱动与网表不一致")
    return wiring


def _crossings(board, wiring):
    crossings = []
    for receiver, sender in wiring.short_ports.items():
        _, sx, sy, z = wiring.sites[sender]
        _, rx, ry, _ = wiring.sites[receiver]
        dx, dy = DIRECTIONS[wiring.entries[sender][1]["R"]]
        gap = abs(rx - sx) + abs(ry - sy)
        obstacles = [
            (sx + i * dx, sy + i * dy, z)
            for i in range(1, gap)
            if (p := (sx + i * dx - board.origin_x, sy + i * dy - board.origin_y, z)) in board.occupied
            or p in board.traces
        ]
        if not obstacles:
            raise ValueError(f"短距跳线 {(sx, sy, z)} 未越过占用格")
        crossings.append({"sender": (sx, sy, z), "receiver": (rx, ry, z), "obstacles": obstacles})
    return crossings


def _layout(model, units, foundation, rotation, stride, lanes, input_ports, output_ports, *, front=2, blocked=()):
    board = _RoutingBoard(foundation=foundation)
    parallel = len(model.lane_nets) > len(model.outputs)
    if parallel or len(input_ports) + len(output_ports) >= 9 or any(g.kind in _RADIOS for g in model.gates.values()):
        board.wide = True
        board.route_budget = 220
    ground = platform_ground(foundation, rotation)
    board.ground = platform_interior(foundation, rotation)
    left, right = min(x for x, _ in ground), max(x for x, _ in ground)
    top = min(y for _, y in board.ground)
    board.origin_x, board.origin_y = left + 1, top
    dots = sorted(y for x, y in ground - board.ground if x == right and (x - 1, y) in board.ground)
    used = set(output_ports.values()) | set(input_ports.values()) | set(blocked)
    outputs = dict(output_ports)
    output_lanes = (lanes[-1],) if len(model.outputs) == 1 else lanes[:len(model.outputs)]
    for name, (y, z) in zip(model.outputs, output_lanes, strict=True):
        if name in outputs:
            continue
        free = (Notch(right, r, level, "E") for r in dots for level in range(3))
        choices = [port for port in free if port not in used]
        if not choices:
            choices = [p for p in _open_notches(ground, board.ground) if p not in used]
        if not choices:
            raise ValueError('没有朝向空地的输出凹口')
        port = min(choices, key=lambda p: (abs(p.y - top - y) + 4 * abs(z - p.level), abs(z - p.level), p.y))
        outputs[name] = port
        used.add(port)
    missing = [name for name in model.inputs if name not in input_ports]
    slots = _input_slots(ground, board.ground, left, len(missing), used)
    inputs = dict(zip(missing, slots, strict=True))
    inputs.update(input_ports)
    outputs = {name: outputs[name] for name in model.outputs}
    edge_pads = defaultdict(set)
    for name, site in inputs.items():
        net = model.inputs[name]
        pad = _edge(board, _RX, site, net, ground)
        edge_pads[net].add(pad)
    for name, site in outputs.items():
        net = model.outputs[name]
        pad = _edge(board, _TX, site, net, ground)
        if edge_pads[net] and not _join(board, net, pad, edge_pads[net], direct=True, protect_pads=True):
            raise ValueError(f"无法连接共用信号的输出端口 {name}")
        edge_pads[net].add(pad)

    single_west = len(inputs) == 1 and next(iter(inputs.values())).side == 'W'
    spine = (single_west and len(outputs) > 1 and not output_ports and foundation != 'Foundation_L3'
             and (not input_ports or len(outputs) >= 8))
    if spine:
        (net,) = model.inputs.values()
        _input_spine(board, net, next(iter(inputs.values())), tuple(outputs.values()))

    coordinates = {}
    driven = set(model.inputs.values())
    extent = max((unit.column + len(unit.nodes) for unit in units), default=1)
    span = right - left - 4
    repeated = model.repeated_units(units) if len(model.lane_nets) > 1 else {}
    pending = sorted(units, key=lambda u: (u.column, u.lane, u.nodes[0]))
    placed = set()
    replicated = []

    def lane_site(unit):
        lower = int(unit.lane)
        y, z = lanes[lower]
        if unit.lane != lower:
            upper_y, upper_z = lanes[lower + 1]
            if z == upper_z:
                return (y + upper_y) // 2, z
            return (y + upper_y) // 2, 2
        return y, z

    def ideal(group):
        first = group[0]
        y, z = lane_site(first)
        column = max(u.column for u in group)
        x = front + min(span * column // extent, stride * column)
        if parallel:
            x = 5 + (span - 9) * column // extent
        if len(inputs) + len(outputs) >= 9:
            signals = {model.nets[arg] for n in first.nodes for arg in model.gates[n].inputs if isinstance(arg, Ref)}
            points = [min(board.tracks(net), key=lambda p: abs(p[0] - x) + abs(p[1] - y) + 5 * abs(p[2] - z))
                      for net in sorted(signals) if board.tracks(net)]
            if points:
                x = sum(p[0] for p in points) // len(points) + 2
                y = sum(p[1] for p in points) // len(points)
                z = sum(p[2] for p in points) // len(points)
        return x, y, z


    while pending:
        ready = [unit for unit in pending if unit.parents <= placed]
        ready_set = set(ready)
        unit = next(
            (u for u in ready if u.nodes[0] not in repeated or ready_set.issuperset(repeated[u.nodes[0]])), ready[0]
        )
        group = repeated.get(unit.nodes[0], (unit,))
        if not ready_set.issuperset(group):
            group = (unit,)
        x, y, z = ideal(group)
        row, level = lane_site(group[0])
        replicas = tuple((u, ay - row, az - level) for u in group for ay, az in (lane_site(u),))
        try:
            board, sites = _put_group(board, model, replicas, (x, y, z), driven)
        except _PlacementError:
            if len(group) == 1:
                raise
            group = (unit,)
            board, sites = _put_group(board, model, ((unit, 0, 0),), ideal(group), driven)
        if len(group) > 1:
            replicated.append([u.nodes[0] for u in group])
        for u, (x, y, z, _) in zip(group, sites, strict=True):
            placed.add(u.nodes[0])
            pending.remove(u)
            for i, node in enumerate(u.nodes):
                coordinates[node] = x + u.offset(i) + board.origin_x, y + board.origin_y, z
                driven.update(model.nets[Ref(node, port)] for port in range(len(PORTS[model.gates[node].kind][0])))
    island = board.finish()
    if rotation:
        island["Entries"][0]["R"] = rotation
    wiring = _verify(island, model, coordinates, inputs, outputs)
    return {"V": 1137, "BP": island}, {
        "methods": model.methods,
        "foundation": foundation,
        "rotation": rotation,
        "island_tiles": len(foundation_tiles(foundation, rotation)),
        "input_spine": spine,
        "ripups": board.reroutes,
        "ripup_attempts": board.route_stats['ripup_attempts'],
        "blocked_pad_ripups": board.route_stats['blocked_pad_ripups'],
        "logic_gates": len(model.gates),
        "building_entries": len(wiring.entries),
        'global_radios': sum(g.kind in _RADIOS for g in model.gates.values()),
        "local_flywires": len(wiring.short_ports),
        "flywire_crossings": _crossings(board, wiring),
        "inputs": {name: {"X": p.x, "Y": p.y, "L": p.level, "R": p.rotation(True)} for name, p in inputs.items()},
        "outputs": {name: {"X": p.x, "Y": p.y, "L": p.level, "R": p.rotation(False)} for name, p in outputs.items()},
        "replicated_units": [[coordinates[node] for node in group] for group in replicated],
        "direct_macros": [[coordinates[node] for node in unit.nodes]
                          for unit in units if len(unit.nodes) > 1 and not unit.tapped],
        "tapped_macros": [[coordinates[node] for node in unit.nodes] for unit in units if unit.tapped],
    }


def _lane_options(height, count):
    steps = (8, 6, 5) if height < 22 else (6, 8, 5)
    if count >= 9:
        steps += (3, 2)
    rows = (count, (count + 1) // 2, (count + 2) // 3)
    for step in steps:
        for per_layer in (rows[::-1] if count >= 9 else rows):
            used = 4 + (per_layer - 1) * step
            if used <= height:
                start = max(2, (min(height, 24) - used) // 2 + 2)
                yield tuple((start + i % per_layer * step, i // per_layer) for i in range(count))


def build(
    programs: Mapping[str, Program],
    *,
    platform: tuple[str, int] | None = None,
    input_ports: Mapping[str, Notch] | None = None,
    output_ports: Mapping[str, Notch] | None = None,
) -> tuple[dict, dict]:
    start = perf_counter()
    return _build_netlist(_Netlist(programs), platform=platform, input_ports=input_ports, output_ports=output_ports,
                          start=start)


def _build_netlist(model, *, platform, input_ports, output_ports, start=None, blocked=()):
    if start is None:
        start = perf_counter()
    units = model.feedback_units
    if units is None:
        units = model.units()
    input_ports = {} if input_ports is None else input_ports
    output_ports = {} if output_ports is None else output_ports
    if input_ports.keys() - model.inputs.keys() or output_ports.keys() - model.outputs.keys():
        raise ValueError("指定了未知的输入或输出端口")
    platforms = [platform] if platform is not None else [
        (kind, r)
        for kind in _FOUNDATIONS
        for r in range(2 if len(set(FOUNDATION_CHUNKS[kind])) > 1 else 1)
    ]
    depth = max((unit.column + len(unit.nodes) for unit in units), default=1)

    def rank(candidate):
        kind, rotation = candidate
        tiles = foundation_tiles(kind, rotation)
        w = (1 + max(x for x, _ in tiles)) * TILE_SIZE - 2 * EDGE_MARGIN
        h = (1 + max(y for _, y in tiles)) * TILE_SIZE - 2 * EDGE_MARGIN
        return max(depth + 4 - w, 0) > 0, len(tiles), h

    errors = []
    if platform is None and not (input_ports or output_ports) and len(model.lane_nets) in (2, 4) and len(model.outputs) == 1:
        from .ported_partition import build_partition
        try:
            bp, report = build_partition(model)
        except ValueError as error:
            errors.append(str(error))
        else:
            report['layout_seconds'] = round(perf_counter() - start, 4)
            return bp, report
    best = None
    for foundation, rotation in sorted(platforms, key=rank):
        _, islands, height = rank((foundation, rotation))
        if best is not None and islands > best[1]['island_tiles']:
            break
        profiles = list(dict.fromkeys(_lane_options(height, len(model.lane_nets))))
        if profiles and output_ports and len(model.outputs) == len(model.lane_nets):
            top = min(y for _, y in platform_interior(foundation, rotation))
            preferred = profiles[0]
            aligned = tuple((output_ports[name].y - top, output_ports[name].level) if name in output_ports else site
                            for name, site in zip(model.outputs, preferred, strict=True))
            if aligned:
                profiles.insert(0, aligned)
        small = len(units) < 28 and len(model.lane_nets) == 1
        plans = [(lanes, 2) for lanes in profiles]
        if small:
            plans = [(((y + dy, level),), front) for (y, level), in profiles
                     for dy, front in ((1, 0), (0, 2), (1, 2), (-1, 2), (0, 0))]
        found = 0
        for lanes, front in plans:
            for stride in ((2, 1, 3) if found == 0 else (2,)):
                try:
                    bp, report = _layout(model, units, foundation, rotation, stride, lanes, input_ports, output_ports,
                                         front=front, blocked=blocked)
                except ValueError as error:
                    errors.append(f"{foundation}/{rotation}/{stride} {error}")
                    continue
                report['lane_centers'] = lanes
                found += 1
                if best is None or (islands, report['building_entries']) < (best[1]['island_tiles'], best[1]['building_entries']):
                    best = bp, report
                break
            if found >= (3 if small else 1):
                break
    if best is None:
        raise ValueError("有线布局失败。" + "；".join(errors[-8:]))
    best[1]['layout_seconds'] = round(perf_counter() - start, 4)
    return best


def _notches(items):
    ports = {}
    for item in items:
        name, value = item.split("=", 1)
        x, y, level, side = value.split(",")
        if name in ports:
            raise ValueError(f"重复指定端口 {name}")
        ports[name] = Notch(int(x), int(y), int(level), side.upper())
    return ports


def main() -> int:
    parser = argparse.ArgumentParser(description="将组合方法编译为有线多端口原生蓝图")
    parser.add_argument("source", type=Path, help="Python 源文件")
    parser.add_argument(
        "--field", action="append", metavar="字段=方法", required=True, help="按输出凹口顺序指定，可重复"
    )
    parser.add_argument(
        "--platform",
        choices=[f"{s.removeprefix('Foundation_')}/{r}" for s in _FOUNDATIONS for r in range(4)],
        help="限定平台和朝向，例如 1x4/1",
    )
    parser.add_argument("--input-notch", action="append", default=[], metavar="名称=X,Y,L,N", help="指定输入凹口")
    parser.add_argument("--output-notch", action="append", default=[], metavar="名称=X,Y,L,E", help="指定输出凹口")
    parser.add_argument("--output", type=Path, required=True, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        fields = dict(item.split("=", 1) for item in args.field)
        if len(fields) != len(args.field):
            raise ValueError("输出字段名须唯一")
        programs, _ = compile_field_methods(args.source, fields)
        platform = None
        if args.platform:
            shape, rotation = args.platform.split("/")
            platform = "Foundation_" + shape, int(rotation)
        bp, report = build(programs, platform=platform, input_ports=_notches(args.input_notch),
                           output_ports=_notches(args.output_notch))
        _write_blueprint(bp, report, args.output)
    except (OSError, FrontendError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
