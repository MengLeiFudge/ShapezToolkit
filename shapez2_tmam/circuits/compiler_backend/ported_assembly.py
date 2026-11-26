"""在单一岛层装配组合模块，并从原生接线回放公开端口。"""

from collections import defaultdict
from base64 import b64decode
from dataclasses import dataclass
from graphlib import TopologicalSorter
from typing import Mapping

from ...mari.blueprint import DIRECTIONS, Wiring, _kind
from ...mari.ports import OPERATIONS, PORTS
from ...mari.signals import Signal, decode_constant, merge, operate
from ..compiler_contract import Program
from ..foundations import TILE_SIZE, foundation_origin, foundation_tiles, platform_ground, platform_interior
from .ported_layout import Notch, build


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
    return tiles, tuple(sorted(notches))


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
                offset = y if dx else x
                for level in range(3):
                    key = side != "E", level, abs(offset % TILE_SIZE - 10), x, y
                    options.append((key, Notch(x, y, level, side), Notch(a, b, level, opposite)))
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
                raise ValueError("平面排板尝试超过 12000 个位置")
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
        raise ValueError("现有平台无法让全部连接占用相邻对向凹口")
    return offsets, notches


def _index(wiring, platform, port):
    return wiring.lookup[(platform, port['X'], port['Y'], port['L'])]


def assemble(modules: Mapping[str, Module], links: tuple[Link, ...]) -> tuple[dict, dict]:
    """连接输出名和输入名。未连接的端口保留为总装件公开端口。"""
    if not modules:
        raise ValueError("至少需要一个模块")
    inputs = {}
    outputs = {}
    for name, module in modules.items():
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
        dependencies[b].add(a)
    tuple(TopologicalSorter(dependencies).static_order())
    offsets, notches = _floorplan(modules, links, dependencies)
    in_ports = defaultdict(dict)
    out_ports = defaultdict(dict)
    programs = {name: dict(module.programs) for name, module in modules.items()}
    physical_links = []
    for i, (source, dest) in enumerate(links):
        a, output = source
        b, input_ = dest
        tx, rx = notches[i]
        name = output
        if name in out_ports[a]:
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
        spec = (descriptor.platform, tuple(programs[module].items()), tuple(sorted(in_ports[module].items())),
                tuple(sorted(out_ports[module].items())))
        if spec not in cache:
            cache[spec] = build(programs[module], platform=descriptor.platform,
                                input_ports=in_ports[module], output_ports=out_ports[module])
        bp, report = cache[spec]
        x, y = offsets[module]
        reports[module] = report
        entries.append(dict(bp['BP']['Entries'][0], X=x, Y=y, Z=0))
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
    }


class Simulation:
    """用原生端口、飞线和门配置计算稳定信号。"""

    def __init__(self, wiring: Wiring, inputs: Mapping[str, int], outputs: Mapping[str, int]):
        self.inputs = dict(inputs)
        self.outputs = dict(outputs)
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
