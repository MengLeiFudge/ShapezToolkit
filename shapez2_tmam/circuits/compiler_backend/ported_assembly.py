"""在单一岛层装配组合模块，并从原生接线回放公开端口。"""

from collections import Counter, defaultdict
from base64 import b64decode
from copy import deepcopy
from dataclasses import dataclass
from graphlib import TopologicalSorter
from typing import Mapping

from ...mari.blueprint import DIRECTIONS, Wiring, _kind
from ...mari.ports import OPERATIONS, PORTS
from ...mari.signals import Signal, decode_constant, merge, operate
from ..compiler_contract import Block, Function, Program, Reference, Return, ValueType, Variable
from ..foundations import TILE_SIZE, foundation_origin, foundation_tiles, platform_ground, platform_interior, rotate_cell
from .ported_layout import Notch, _Netlist, _build_netlist, build


@dataclass(frozen=True)
class Module:
    programs: Mapping[str, Program]
    platform: tuple[str, int]


Port = tuple[str, str]
Link = tuple[Port, Port]


def _geometry(platform):
    kind, rotation = platform
    ox, oy = foundation_origin(kind, rotation)
    tiles = frozenset((x + ox, y + oy) for x, y in foundation_tiles(kind, rotation))
    inside = platform_interior(kind, rotation)
    notches = []
    for x, y in platform_ground(kind, rotation) - inside:
        for side, (dx, dy) in zip("ESWN", DIRECTIONS, strict=True):
            if (x - dx, y - dy) in inside:
                notches.append((x, y, side))
    return tiles, tuple(sorted(notches)), rotation


def _adjacent(first, second):
    # 东侧优先接下游，其后用南、北、西侧找连续板缝。
    for side in (0, 1, 3, 2):
        dx, dy = DIRECTIONS[side]
        for x, y in sorted(first):
            for a, b in sorted(second):
                yield x + dx - a, y + dy - b


def _pairs(offsets, links, geometry):
    ports = defaultdict(set)
    choices = []
    demands = Counter(frozenset((a, b)) for (a, _), (b, _) in links)
    for (source, _), (dest, _) in links:
        tx, ty = offsets[source]
        rx, ry = offsets[dest]
        receivers = set(geometry[dest][1])
        options = []
        for x, y, side in geometry[source][1]:
            direction = "ESWN".index(side)
            dx, dy = DIRECTIONS[direction]
            a = x + (tx - rx) * TILE_SIZE + 5 * dx
            b = y + (ty - ry) * TILE_SIZE + 5 * dy
            opposite = "ESWN"[(direction + 2) % 4]
            if (a, b, opposite) in receivers:
                turn = geometry[dest][2]
                cx, cy = rotate_cell(a, b, (-turn) % 4)
                offset = cy if (direction - turn) % 2 == 0 else cx
                for level in range(3):
                    key = side != "E", level, abs(offset % TILE_SIZE - 10), x, y
                    options.append((key, Notch(x, y, level, side), Notch(a, b, level, opposite)))
        if len(options) < demands[frozenset((source, dest))]:
            return None
        choices.append(sorted(options, key=lambda option: option[0]))
    allocated = {}

    def assign(todo):
        if not todo:
            return True
        i = min(todo, key=lambda j: (len(choices[j]), j))
        (source, _), (dest, _) = links[i]
        for _, tx, rx in choices[i]:
            a, b = (tx.x, tx.y, tx.level), (rx.x, rx.y, rx.level)
            if a in ports[source] or b in ports[dest]:
                continue
            ports[source].add(a)
            ports[dest].add(b)
            allocated[i] = tx, rx
            if assign(todo - {i}):
                return True
            ports[source].remove(a)
            ports[dest].remove(b)
            del allocated[i]
        return False

    return allocated if assign(set(range(len(links)))) else None


class _FloorplanError(ValueError):
    pass


def _floorplan(modules, links, dependencies):
    geometry = {name: _geometry(module.platform) for name, module in modules.items()}
    neighbours = defaultdict(set)
    for (source, _), (dest, _) in links:
        neighbours[source].add(dest)
        neighbours[dest].add(source)
    offsets: dict[str, tuple[int, int]] = {}
    tiles: dict[str, set[tuple[int, int]]] = {}
    trials = 0

    def place():
        nonlocal trials
        if len(offsets) == len(modules):
            return _pairs(offsets, links, geometry)
        members = [m for m in modules if m not in offsets and dependencies[m] <= offsets.keys()]
        name = max(members, key=lambda m: (len(neighbours[m] & offsets.keys()), len(geometry[m][0])))
        occupied = set().union(*tiles.values())
        adjacent = sorted(neighbours[name] & offsets.keys())
        if adjacent:
            seed = adjacent[0]
            candidates = dict.fromkeys(_adjacent(tiles[seed], geometry[name][0]))
        else:
            candidates = {(max((x for x, _ in occupied), default=-2) + 2, 0): None}
        for x, y in candidates:
            trials += 1
            if trials > 12000:
                raise _FloorplanError("平面排板尝试超过 12000 个位置")
            body = {(x + a, y + b) for a, b in geometry[name][0]}
            if body & occupied or any(not any((a + dx, b + dy) in tiles[m]
                                             for a, b in body for dx, dy in DIRECTIONS) for m in adjacent):
                continue
            offsets[name] = x, y
            tiles[name] = body
            found = place()
            if found is not None:
                return found
            del offsets[name], tiles[name]
        return None

    notches = place()
    if notches is None:
        raise _FloorplanError("现有平台无法让全部连接占用相邻对向凹口")
    return offsets, notches


def _index(wiring, platform, port):
    return wiring.lookup[(platform, port['X'], port['Y'], port['L'])]


def _rotate_template(entry, report, rotation):
    if not rotation:
        return entry, report
    entry, report = deepcopy((entry, report))
    entry['R'] = rotation
    report['rotation'] = rotation

    def turn(item):
        item['X'], item['Y'] = rotate_cell(item['X'], item['Y'], rotation)
        item['R'] = (item['R'] + rotation) % 4

    def site(point):
        x, y, z = point
        return (*rotate_cell(x, y, rotation), z)

    for item in entry['B']['Entries']:
        turn(item)
    for direction in ('inputs', 'outputs'):
        for port in report[direction].values():
            turn(port)
    for field in ('direct_macros', 'replicated_units', 'tapped_macros'):
        report[field] = [[site(p) for p in group] for group in report[field]]
    for link in report['flywire_crossings']:
        for key in ('sender', 'receiver'):
            link[key] = site(link[key])
        link['obstacles'] = [site(p) for p in link['obstacles']]
    return entry, report


def assemble(modules: Mapping[str, Module], links: tuple[Link, ...], *, through: tuple[Port, ...] = ()) -> tuple[dict, dict]:
    """按端口图总装，必要时经条形走廊分支；未连接端口保留为公开端口。"""
    if not through:
        try:
            return _assemble(modules, links)
        except _FloorplanError:
            counts = defaultdict(int)
            for source, _ in links:
                counts[source] += 1
            through = tuple(p for p, n in counts.items() if n > 1)
            if not through:
                raise
    selected = set(through)
    if selected - {source for source, _ in links}:
        raise ValueError('走廊入口必须是连接图中已使用的输出')

    last = None
    for length in (2, 3, 4):
        for rotation in (0, 1):
            extended = dict(modules)
            relays = {}
            for a, field in dict.fromkeys(through):
                program = modules[a].programs[field]
                result = next(f.result for f in program.functions if f.name == program.entry)
                name = f'bus:{a}.{field}'
                while name in extended:
                    name += ':'
                fn = Function('relay', (Variable('signal', result),), result, (),
                              (Block('entry', (), Return(Reference('signal'))),), 1)
                extended[name] = Module({'pass': Program(fn.name, (fn,))}, (f'Foundation_1x{length}', rotation))
                relays[a, field] = name
            extended_links = tuple((source, (name, 'signal')) for source, name in relays.items()) + tuple(
                ((relays[source], 'pass') if source in relays else source, dest) for source, dest in links
            )
            try:
                bp, report = _assemble(extended, extended_links)
            except ValueError as error:
                last = error
                continue
            report['corridors'] = tuple(relays.values())
            return bp, report
    raise ValueError(f'走廊无法接通：{last}') from last


@dataclass(frozen=True)
class _PhysicalModule:
    model: _Netlist
    inputs: Mapping[str, ValueType]
    outputs: Mapping[str, ValueType]
    platform: tuple[str, int]


def _assemble(modules, links, *, feedback=()):
    feedback = set(feedback)
    if feedback - set(links):
        raise ValueError('反馈端口须在实接连接图内')
    if not modules:
        raise ValueError("至少需要一个模块")
    inputs = {}
    outputs = {}
    for name, module in modules.items():
        if isinstance(module, _PhysicalModule):
            inputs[name], outputs[name] = module.inputs, module.outputs
            continue
        if not module.programs:
            raise ValueError(f"{name} 没有输出方法")
        methods = {field: next(f for f in program.functions if f.name == program.entry)
                   for field, program in module.programs.items()}
        signature = next(iter(methods.values())).inputs
        if any(method.inputs != signature for method in methods.values()):
            raise ValueError(f"{name} 的字段方法需要相同入参")
        inputs[name] = {arg.name: arg.type for arg in signature}
        outputs[name] = {field: method.result for field, method in methods.items()}
    seen = set()
    dependencies = {name: set() for name in modules}
    for source, dest in links:
        a, output = source
        b, input_ = dest
        if output not in outputs.get(a, {}) or input_ not in inputs.get(b, {}):
            raise ValueError(f"未知模块端口：{source} → {dest}")
        if outputs[a][output] != inputs[b][input_]:
            raise ValueError(f"模块端口类型不一致：{source} → {dest}")
        if dest in seen:
            raise ValueError(f"输入端口有多个来源：{dest}")
        seen.add(dest)
        if (source, dest) not in feedback:
            dependencies[b].add(a)
    tuple(TopologicalSorter(dependencies).static_order())
    offsets, notches = _floorplan(modules, links, dependencies)
    in_ports = defaultdict(dict)
    out_ports = defaultdict(dict)
    programs = {name: dict(m.programs) for name, m in modules.items() if isinstance(m, Module)}
    physical_links = []
    for i, (source, dest) in enumerate(links):
        a, output = source
        b, input_ = dest
        tx, rx = notches[i]
        name = output
        if name in out_ports[a]:
            if a not in programs:
                raise ValueError(f'原生单元 {a}.{name} 需要单独的分发板')
            name = f"{output}:{i}"
            while name in programs[a]:
                name += ':'
            programs[a][name] = programs[a][output]
        out_ports[a][name] = tx
        in_ports[b][input_] = rx
        physical_links.append(((a, name), dest))
    entries = []
    reports = {}
    cache = {}
    for module, descriptor in modules.items():
        foundation, rotation = descriptor.platform
        def normalize(ports):
            if not rotation:
                return ports
            return {name: Notch(*rotate_cell(p.x, p.y, (-rotation) % 4), p.level,
                                'ESWN'[('ESWN'.index(p.side) - rotation) % 4]) for name, p in ports.items()}
        incoming, outgoing = normalize(in_ports[module]), normalize(out_ports[module])
        model = descriptor.model if isinstance(descriptor, _PhysicalModule) else None
        logic = model if model is not None else tuple(programs[module].items())
        spec = (foundation, logic, tuple(sorted(incoming.items())), tuple(sorted(outgoing.items())))
        if spec not in cache:
            if model is not None:
                cache[spec] = _build_netlist(model, platform=(foundation, 0), input_ports=incoming, output_ports=outgoing)
            else:
                cache[spec] = build(programs[module], platform=(foundation, 0), input_ports=incoming, output_ports=outgoing)
        bp, report = cache[spec]
        entry, reports[module] = _rotate_template(bp['BP']['Entries'][0], report, rotation)
        x, y = offsets[module]
        entries.append(dict(entry, X=x, Y=y, Z=0))
    island = {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': entries}
    wiring = Wiring(island)
    indices = {name: i for i, name in enumerate(modules)}
    expected = {_index(wiring, indices[b], reports[b]['inputs'][p]):
                _index(wiring, indices[a], reports[a]['outputs'][q])
                for (a, q), (b, p) in physical_links}
    actual = {rx: tx for rx, tx in wiring.short_ports.items() if wiring.sites[rx][0] != wiring.sites[tx][0]}
    if actual != expected:
        raise ValueError(f"跨板短距配对与连接图不一致：{actual} ≠ {expected}")
    sent = {a for a, _ in physical_links}
    ports = {direction: {f"{name}.{port}": (indices[name], spec)
                         for name, report in reports.items() for port, spec in report[direction].items()
                         if (name, port) not in skips}
             for direction, skips in (('inputs', seen), ('outputs', sent))}
    return {'V': 1137, 'BP': island}, {
        **ports, 'modules': reports, 'unique_layouts': len(cache), 'cross_flywires': len(actual),
        'ripup_attempts': sum(report['ripup_attempts'] for _, report in cache.values()),
        'building_entries': len(wiring.entries), 'island_tiles': sum(r['island_tiles'] for r in reports.values()),
        'ripups': sum(report['ripups'] for _, report in cache.values()),
        'feedback': [(indices[b], reports[b]['inputs'][p]) for _, (b, p) in sorted(feedback)],
    }


def _native_graph(wiring, inputs, outputs):
    external = set(inputs.values())
    pending = list(outputs.values())
    gates = {}
    while pending:
        idx = pending.pop()
        if idx in gates or idx in external:
            continue
        entry = wiring.entries[idx][1]
        kind = _kind(entry)
        config = 0
        if kind == 'ConstantSignal':
            args = ()
            config = decode_constant(entry['C'])
        elif kind == 'WireTransmitterReceiver':
            if idx not in wiring.short_ports:
                raise ValueError(f"存在未声明的输入 {wiring.sites[idx]}")
            args = (((wiring.short_ports[idx], 0),),)
        else:
            args = tuple(tuple(wiring._direct_sources(idx, p)) for p in range(len(PORTS[kind][1])))
            if kind == 'LogicGateCompare':
                config = int.from_bytes(b64decode(entry['C']), 'little')
        gates[idx] = kind, config, args
        pending.extend(src for arg in args for src, _ in arg)
    return gates


class Simulation:
    """用原生端口、飞线和门配置计算稳定信号。"""

    def __init__(self, wiring: Wiring, inputs: Mapping[str, int], outputs: Mapping[str, int]):
        self.inputs = dict(inputs)
        self.outputs = dict(outputs)
        external = set(inputs.values())
        gates = _native_graph(wiring, inputs, outputs)
        order = TopologicalSorter({idx: {src for arg in args for src, _ in arg if src not in external}
                                   for idx, (_, _, args) in gates.items()}).static_order()
        self.gates = [(i, *gates[i]) for i in order]

    @classmethod
    def from_assembly(cls, blueprint, report):
        wiring = Wiring(blueprint['BP'])
        return cls(wiring, *({name: _index(wiring, i, p) for name, (i, p) in report[direction].items()}
                             for direction in ('inputs', 'outputs')))

    def run(self, values: Mapping[str, Signal]) -> dict[str, Signal]:
        if values.keys() != self.inputs.keys():
            raise ValueError("门级回放需要提供全部公开输入")
        result: dict[int, tuple[Signal, ...]] = {idx: (values[name],) for name, idx in self.inputs.items()}
        for idx, kind, config, args in self.gates:
            if kind == 'ConstantSignal':
                result[idx] = (config,)
                continue
            signals = tuple(merge(result[src][port] for src, port in arg) for arg in args)
            result[idx] = signals if kind.startswith('WireTransmitter') else operate(OPERATIONS[kind], signals, config)
        return {name: result[idx][0] for name, idx in self.outputs.items()}
