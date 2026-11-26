"""直接从组合方法生成带多路短距端口的原生电路。"""

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from graphlib import TopologicalSorter
from pathlib import Path

from ...mari.blueprint import DIRECTIONS, Wiring, _kind, _rotate
from ...mari.ports import OUT, PORTS, WEST
from ..circuit import Gate, Literal, Ref, constant
from ..compiler_contract import Program
from ..compiler_frontend import FrontendError, compile_field_methods
from ..foundations import EDGE_MARGIN, FOUNDATION_CHUNKS, TILE_SIZE, platform_ground, platform_interior
from ..wired_module import _Board
from . import _write_blueprint
from ._lower import Lowering, _Value
from ._optimize import compact
from ._snapshot_router import _join


_RX = "WireTransmitterReceiver"
_TX = "WireTransmitterSender"
_FOUNDATIONS = (
    "Foundation_1x1",
    "Foundation_1x2",
    "Foundation_1x3",
    "Foundation_2x2",
    "Foundation_1x4",
    "Foundation_2x3",
    "Foundation_2x4",
    "Foundation_3x3",
)


@dataclass(frozen=True)
class _Unit:
    nodes: tuple[int, ...]
    parents: frozenset[int]
    column: int
    lane: float


class _Netlist:
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

        # 输入占位与普通常量即使值相同也必须成不同的网。
        circuit, refs = compact(circuit, outputs, distinct=tuple(inputs.values()))
        circuit.retain_outputs(tuple(refs.values()))
        assert circuit.retained_nodes is not None
        self.nets = circuit.channel_map()
        self.gates = {
            node: gate
            for node, gate in enumerate(circuit.gates)
            if node in circuit.retained_nodes and node not in {ref.node for ref in inputs.values()}
        }
        self.inputs = {name: self.nets[ref] for name, ref in inputs.items()}
        self.outputs = {name: self.nets[refs[i]] for i, name in enumerate(methods)}
        self.writers = defaultdict(set)
        self.readers = defaultdict(list)
        for node, gate in self.gates.items():
            for port in range(len(PORTS[gate.kind][0])):
                self.writers[self.nets[Ref(node, port)]].add(node)
            for arg in gate.inputs:
                if isinstance(arg, Ref):
                    self.readers[self.nets[arg]].append(node)
        self.live = set(self.readers) | set(self.outputs.values())
        self.methods = {name: method.name for name, method in methods.items()}

    def units(self) -> tuple[_Unit, ...]:
        dependencies = {
            node: frozenset(w for arg in gate.inputs if isinstance(arg, Ref) for w in self.writers[self.nets[arg]])
            for node, gate in self.gates.items()
        }
        order = tuple(TopologicalSorter(dependencies).static_order())
        lanes: dict[int, set[int]] = defaultdict(set)
        for lane, net in enumerate(self.outputs.values()):
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
            if _straight(first):
                while True:
                    tail = chain[-1]
                    net = self.nets[Ref(tail)]
                    next_nodes = self.readers[net]
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
            lane = sum(lanes[node]) / max(1, len(lanes[node]))
            unit = _Unit(tuple(chain), parents, column, lane)
            units.append(unit)
            columns[node] = column + len(chain)
            owner.update((n, node) for n in chain)
        return tuple(units)

    def repeated_units(self, units):
        """从各输出向上匹配同构后缀。共用网络与朝向预处理留给各行外部。"""
        pending = [tuple(self.outputs.values())]
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
            if len({len(u.nodes) for u in group}) != 1:
                continue
            if any(matches.get(nodes[0]) != nodes for nodes in zip(*(u.nodes for u in group), strict=True)):
                continue
            groups[unit.nodes[0]] = group
        return groups


def _straight(gate: Gate) -> bool:
    return PORTS[gate.kind][:2] == (OUT, WEST) and isinstance(gate.inputs[0], Ref)


def _copy_board(board):
    trial = _Board(foundation=board.foundation)
    trial.origin_x, trial.origin_y = board.origin_x, board.origin_y
    trial.ground = board.ground
    trial.occupied = board.occupied.copy()
    trial.entries = board.entries.copy()
    trial.traces = defaultdict(
        dict, {site: {net: sides.copy() for net, sides in nets.items()} for site, nets in board.traces.items()}
    )
    trial.terminals = defaultdict(set, {key: points.copy() for key, points in board.terminals.items()})
    return trial


def _tracks(board):
    points = defaultdict(set)
    for site, nets in board.traces.items():
        if len(nets) == 1:
            points[next(iter(nets))].add(site)
    return points


def _edge(board, kind, coordinate, net):
    x, y, z = coordinate
    board.entries.append({"T": kind + "InternalVariant", "X": x, "Y": y, "L": z, "R": 0})
    x, y = x - board.origin_x, y - board.origin_y
    side = 0 if kind == _RX else 2
    board.occupied.add((x, y, z))
    board.pin(net, x, y, z, side)
    return x + (1 if kind == _RX else -1), y, z


def _input_spine(board, net, entry, exits):
    """在西边留一条直通母线，让各行从相邻位置取输入。"""
    _, row, z = entry
    y = row - board.origin_y
    rows = [y, *(position[1] - board.origin_y for position in exits)]
    top, bottom = min(rows), max(rows)
    for v in range(top, bottom + 1):
        sides = set()
        if v > top:
            sides.add(3)
        if v < bottom:
            sides.add(1)
        board.traces[1, v, z].setdefault(net, set()).update(sides)
    board.traces[0, y, z][net].add(0)
    board.traces[1, y, z][net].add(2)


def _slots(ground, interior, x, count):
    side = 1 if x < min(a for a, _ in interior) else -1
    rows = sorted(y for a, y in ground - interior if a == x and (a + side, y) in interior)
    if count > 3 * len(rows):
        raise ValueError(f"平台边缘最多容纳 {3 * len(rows)} 路飞线端口")
    rows_by_height = [(x, y, z) for z in range(3) for y in rows]
    if count <= len(rows):
        return tuple(rows_by_height[(2 * i + 1) * len(rows) // (2 * count)] for i in range(count))
    return tuple(rows_by_height[:count])


def _proposal(board, model, unit, x, y, z, turn):
    chain = unit.nodes
    body = {(x + i, y, z) for i in range(len(chain))}
    for i, node in enumerate(chain):
        if model.gates[node].kind == "VirtualHalvesSwapper":
            dx, dy = _rotate(0, -1, turn)
            body.add((x + i + dx, y + dy, z))
    if any(not board.on_ground(a, b) or p in board.occupied or board.traces.get(p) for p in body for a, b, _ in (p,)):
        return None
    pads = {}
    literals = {}
    for i, node in enumerate(chain):
        gate = model.gates[node]
        for category, ports in enumerate(PORTS[gate.kind][:2]):
            if (category == 0 and i != len(chain) - 1) or (category == 1 and i != 0):
                continue
            for port, (facing, a, b, level) in enumerate(ports):
                arg = gate.inputs[port] if category else Ref(node, port)
                net = model.nets[arg] if isinstance(arg, Ref) else None
                if category == 0 and net not in model.live:
                    continue
                side = (facing + turn) % 4
                dx, dy = DIRECTIONS[side]
                a, b = _rotate(a, b, turn)
                p = x + i + a + dx, y + b + dy, z + level
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


def _attach(board, model, unit, site, plan, tracks, driven):
    trial = _copy_board(board)
    x, y, z, turn = site
    body, pads, literals = plan
    for i, node in enumerate(unit.nodes):
        gate = model.gates[node]
        trial.place(gate.kind, x + i, y, z, turn, gate.config)
    trial.occupied.update(body)
    for p, (config, facing) in literals.items():
        a, b, level = p
        trial.place("ConstantSignal", a, b, level, facing, config)
    own = defaultdict(set)
    for p, (net, side, _) in pads.items():
        trial.traces[p].setdefault(net, set()).add(side)
        trial.terminals[net, p[2]].add(p)
    for p, (net, _, sink) in pads.items():
        tree = tracks[net] | own[net]
        unique_source = len(model.writers[net]) + int(net in model.inputs.values()) == 1
        flywire = sink and unique_source and net in driven
        if tree and not _join(trial, net, p, tree, direct=True, flywire=flywire, protect_pads=True):
            return None
        own[net].add(p)
    return trial


def _put_group(board, model, group, ideal, driven):
    unit, _ = group[0]
    tracks = _tracks(board)
    tx, ty, preferred_layer = ideal
    xs = sorted({a - board.origin_x for a, _ in board.ground}, key=lambda x: (abs(x - tx), x))
    ys = sorted({b - board.origin_y for _, b in board.ground}, key=lambda y: (abs(y - ty), y))
    candidates = []
    distance = {}
    for x in xs[:9]:
        for y in ys[:9]:
            for z in range(3):
                for turn in (0,) if len(unit.nodes) > 1 else (0, 1, 3, 2):
                    plan = _proposal(board, model, unit, x, y, z, turn)
                    if plan is None:
                        continue
                    score = 0
                    for p, (net, _, _) in plan[1].items():
                        if not tracks[net]:
                            continue
                        key = net, p
                        if key not in distance:
                            a, b, c = p
                            distance[key] = min(abs(a - u) + abs(b - v) + 4 * abs(c - w) for u, v, w in tracks[net])
                        score += distance[key]
                    align = 2 * abs(x - tx) + 3 * abs(y - ty) + 3 * abs(z - preferred_layer)
                    candidates.append(((score + align, align, turn != 0), (x, y, z, turn), plan))
    best = None
    limit = 24 if len(group) > 1 else 14
    for rank, site, plan in sorted(candidates)[:limit]:
        trial = _attach(board, model, unit, site, plan, tracks, driven)
        if trial is None:
            continue
        x, y, z, turn = site
        sites = [site]
        for replica, dy in group[1:]:
            shifted = (x, y + dy, z, turn)
            replica_plan = _proposal(trial, model, replica, *shifted)
            if replica_plan is None:
                break
            routed = _attach(trial, model, replica, shifted, replica_plan, _tracks(trial), driven)
            if routed is None:
                break
            trial = routed
            sites.append(shifted)
        if len(sites) != len(group):
            continue
        growth = len(trial.entries) + len(trial.traces) - len(board.entries) - len(board.traces)
        score = growth + rank[1], rank
        if best is None or score < best[0]:
            best = score, trial, sites
        if best and growth <= len(unit.nodes) + len(plan[2]) + 2:
            break
    if best is None:
        raise ValueError(f"逻辑器件 {unit.nodes} 在列 {unit.column} 无法摆放并接通，有 {len(candidates)} 个候选")
    return best[1:]


def _verify(island, model, coordinates, input_indices, output_indices):
    wiring = Wiring(island)
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

    def sources(index, port):
        todo = list(wiring._direct_sources(index, port))
        visited, actual = set(), set()
        while todo:
            source = todo.pop()
            if source in visited:
                continue
            visited.add(source)
            idx, _ = source
            if idx in wiring.short_ports:
                todo.extend(wiring._direct_sources(wiring.short_ports[idx], 0))
            else:
                actual.add(source)
        return actual

    for node, gate in model.gates.items():
        for port, arg in enumerate(gate.inputs):
            index = positions[node]
            actual = sources(index, port)
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
        if sources(index, 0) != drivers[model.outputs[name]]:
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
            if (sx + i * dx - board.origin_x, sy + i * dy - board.origin_y, z) in board.occupied
        ]
        if not obstacles:
            raise ValueError(f"短距跳线 {(sx, sy, z)} 未越过占用格")
        crossings.append({"sender": (sx, sy, z), "receiver": (rx, ry, z), "obstacles": obstacles})
    return crossings


def _layout(model, units, foundation, rotation, stride, *, spine=False, repeat=1):
    board = _Board(foundation=foundation)
    ground = platform_ground(foundation, rotation)
    board.ground = platform_interior(foundation, rotation)
    left, right = min(x for x, _ in ground), max(x for x, _ in ground)
    top, bottom = min(y for _, y in board.ground), max(y for _, y in board.ground)
    board.origin_x, board.origin_y = left + 1, top
    inputs = dict(zip(model.inputs, _slots(ground, board.ground, left, len(model.inputs)), strict=True))
    outputs = dict(zip(model.outputs, _slots(ground, board.ground, right, len(model.outputs)), strict=True))
    input_indices = {}
    output_indices = {}
    edge_pads = defaultdict(set)
    for name, site in inputs.items():
        input_indices[name] = len(board.entries)
        net = model.inputs[name]
        pad = _edge(board, _RX, site, net)
        edge_pads[net].add(pad)
    for name, site in outputs.items():
        output_indices[name] = len(board.entries)
        net = model.outputs[name]
        pad = _edge(board, _TX, site, net)
        if edge_pads[net] and not _join(board, net, pad, edge_pads[net], direct=True, protect_pads=True):
            raise ValueError(f"无法连接共用信号的输出端口 {name}")
        edge_pads[net].add(pad)

    if spine and len(model.inputs) == 1 and len(outputs) > 1:
        (net,) = model.inputs.values()
        _input_spine(board, net, next(iter(inputs.values())), tuple(outputs.values()))

    coordinates = {}
    driven = set(model.inputs.values())
    extent = max((unit.column + len(unit.nodes) for unit in units), default=1)
    span = right - left - 4
    height = bottom - top + 1
    repeated = model.repeated_units(units) if repeat and len(outputs) > 1 else {}
    repeated = {head: group for head, group in repeated.items() if len(group[0].nodes) >= repeat}
    pending = sorted(units, key=lambda u: (u.column, u.lane, u.nodes[0]))
    placed = set()
    replicated = []

    def lane_row(unit):
        return round((unit.lane + 0.5) * height / len(outputs))

    while pending:
        ready = [unit for unit in pending if unit.parents <= placed]
        ready_set = set(ready)
        unit = next(
            (u for u in ready if u.nodes[0] not in repeated or ready_set.issuperset(repeated[u.nodes[0]])), ready[0]
        )
        group = repeated.get(unit.nodes[0], (unit,))
        if not ready_set.issuperset(group):
            group = (unit,)
        y = lane_row(group[0])
        column = max(u.column for u in group)
        x = 2 + min(span * column // extent, stride * column)
        replicas = tuple((u, lane_row(u) - y) for u in group)
        try:
            board, sites = _put_group(board, model, replicas, (x, y, 0), driven)
        except ValueError:
            if len(group) == 1:
                raise
            group = (unit,)
            x = 2 + min(span * unit.column // extent, stride * unit.column)
            board, sites = _put_group(board, model, ((unit, 0),), (x, lane_row(unit), 0), driven)
        if len(group) > 1:
            replicated.append([u.nodes[0] for u in group])
        for u, (x, y, z, _) in zip(group, sites, strict=True):
            placed.add(u.nodes[0])
            pending.remove(u)
            for i, node in enumerate(u.nodes):
                coordinates[node] = x + i + board.origin_x, y + board.origin_y, z
                driven.update(model.nets[Ref(node, port)] for port in range(len(PORTS[model.gates[node].kind][0])))
    island = board.finish()
    if rotation:
        island["Entries"][0]["R"] = rotation
    wiring = _verify(island, model, coordinates, input_indices, output_indices)
    return {"V": 1137, "BP": island}, {
        "methods": model.methods,
        "foundation": foundation,
        "rotation": rotation,
        "island_tiles": FOUNDATION_CHUNKS[foundation][0] * FOUNDATION_CHUNKS[foundation][1],
        "input_spine": spine and len(model.inputs) == 1 and len(outputs) > 1,
        "logic_gates": len(model.gates),
        "building_entries": len(wiring.entries),
        "global_radios": 0,
        "local_flywires": len(wiring.short_ports),
        "flywire_crossings": _crossings(board, wiring),
        "inputs": {name: dict(zip(("X", "Y", "L"), site, strict=True), R=0) for name, site in inputs.items()},
        "outputs": {name: dict(zip(("X", "Y", "L"), site, strict=True), R=0) for name, site in outputs.items()},
        "replicated_units": [[coordinates[node] for node in group] for group in replicated],
        "direct_macros": [[coordinates[node] for node in unit.nodes] for unit in units if len(unit.nodes) > 1],
    }


def build(programs: Mapping[str, Program], *, platform: tuple[str, int] | None = None) -> tuple[dict, dict]:
    model = _Netlist(programs)
    units = model.units()
    platforms = []
    if platform is not None:
        platforms.append(platform)
    else:
        for foundation in _FOUNDATIONS:
            width, height = FOUNDATION_CHUNKS[foundation]
            rotations = (0, 1) if width != height else (0,)
            platforms.extend((foundation, rotation) for rotation in rotations)
    # 先为串联链留转接格，为各行留分支空间，再按岛格比较。
    width_hint = max((unit.column + len(unit.nodes) for unit in units), default=1) + 4
    height_hint = 5 * len(model.outputs)

    def platform_rank(candidate):
        kind, rotation = candidate
        w, h = FOUNDATION_CHUNKS[kind]
        if rotation % 2:
            w, h = h, w
        narrow = w * TILE_SIZE - 2 * EDGE_MARGIN < width_hint or h * TILE_SIZE - 2 * EDGE_MARGIN < height_hint
        return narrow, w * h

    errors = []
    best = None
    best_rank = (True, float("inf"))
    for foundation, rotation in sorted(platforms, key=platform_rank):
        width, height = FOUNDATION_CHUNKS[foundation]
        rank = platform_rank((foundation, rotation))
        if best is not None and rank > best_rank:
            break
        if len(model.outputs) > 1:
            spine = len(model.inputs) == 1
            if min(width, height) >= 2 and max(width, height) >= 3:
                options = ((3, spine, 1), (2, spine, 2), (2, spine, 0))
            else:
                options = ((2, spine, 2), (2, spine, 0), (3, spine, 0))
        else:
            options = ((2, False, 0), (3, False, 0))
        for stride, spine, repeat in options:
            try:
                candidate = _layout(model, units, foundation, rotation, stride, spine=spine, repeat=repeat)
            except ValueError as error:
                errors.append(f"{foundation}/{rotation}/{stride}/{int(spine)}/{repeat} {error}")
                continue
            if best is None or candidate[1]["building_entries"] < best[1]["building_entries"]:
                best = candidate
                best_rank = rank
            break
    if best is None:
        raise ValueError("有线布局失败。" + "；".join(errors))
    return best


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
        _write_blueprint(*build(programs, platform=platform), args.output)
    except (OSError, FrontendError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
