"""在单一岛层装配组合模块，并从原生接线回放公开端口。"""

from __future__ import annotations

from collections import Counter, defaultdict
from base64 import b64decode
from copy import deepcopy
from dataclasses import dataclass, field
from graphlib import TopologicalSorter
from typing import Mapping

from ...mari.blueprint import DIRECTIONS, Wiring, _kind
from ...mari.ports import OPERATIONS, PORTS
from ...mari.signals import Signal, decode_constant, merge, operate
from ..compiler_contract import Program, ValueType
from ..foundations import TILE_SIZE, foundation_origin, foundation_tiles, platform_ground, platform_interior, rotate_cell
from ._snapshot_router import _join
from .ported_layout import Notch, _Netlist, _RoutingBoard, _build_netlist, _crossings, _edge, _local_sources


@dataclass(frozen=True)
class Module:
    programs: Mapping[str, Program]
    platform: tuple[str, int]
    input_side: str | None = None
    rotate: bool = False
    inputs: Mapping[str, Notch] = field(default_factory=dict)
    outputs: Mapping[str, Notch] = field(default_factory=dict)


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


def _turn(port, rotation):
    x, y = rotate_cell(port.x, port.y, rotation)
    side = 'ESWN'[('ESWN'.index(port.side) + rotation) % 4]
    return Notch(x, y, port.level, side)


def _outside(offset, port):
    x, y = offset
    dx, dy = DIRECTIONS['ESWN'.index(port.side)]
    return x + port.x // TILE_SIZE + dx, y + port.y // TILE_SIZE + dy


def public_port_access(wiring):
    """逐一检查未配对短距口前方的岛格，从原生平台锚点和旋转还原。"""
    occupied = {}
    for i, p in enumerate(wiring.platforms):
        tiles, _, _ = _geometry((p['T'], p.get('R', 0)))
        occupied.update({(p.get('X', 0) + x, p.get('Y', 0) + y, p.get('Z', 0)): i for x, y in tiles})
    paired = wiring.short_ports.keys() | set(wiring.short_ports.values())
    result = []
    for i, (board, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if i in paired or kind not in ('WireTransmitterReceiver', 'WireTransmitterSender'):
            continue
        p = wiring.platforms[board]
        _, x, y, layer = wiring.sites[i]
        side = 'ESWN'[(entry.get('R', 0) + 2 * (kind == 'WireTransmitterReceiver')) % 4]
        facing = _outside((p.get('X', 0), p.get('Y', 0)), Notch(x, y, layer, side)) + (p.get('Z', 0),)
        result.append({'board': board, 'notch': (x, y, layer, side), 'adjacent_island': facing,
                       'blocked_by': occupied.get(facing)})
    return result


def require_public_access(wiring):
    access = public_port_access(wiring)
    blocked = [port for port in access if port['blocked_by'] is not None]
    if blocked:
        raise ValueError(f'{len(blocked)} 个公开端口被平台阻挡：{blocked}')
    return access


def _pairs(offsets, links, geometry, input_sides, corridors, fixed_inputs, fixed_outputs):
    def rotate_ports(entries):
        return {(name, signal): _turn(port, geometry[name][2])
                for name, ports in entries.items() for signal, port in ports.items()}

    input_pads = rotate_ports(fixed_inputs)
    output_pads = rotate_ports(fixed_outputs)
    used_outputs, used_inputs = map(set, zip(*links)) if links else (set(), set())
    ports = defaultdict(set)
    for fixed, connected in ((input_pads, used_inputs), (output_pads, used_outputs)):
        for (name, _), port in ((key, pad) for key, pad in fixed.items() if key not in connected):
            ports[name].add((port.x, port.y, port.level))

    choices = []
    for (source, output), (dest, input_) in links:
        lane = corridors.get(dest, {}).get(input_, corridors.get(source, {}).get(output))
        source_pad = output_pads.get((source, output))
        dest_pad = input_pads.get((dest, input_))
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
            if (a, b, opposite) in receivers and input_sides.get(dest, opposite) == opposite:
                turn = geometry[dest][2]
                cx, cy = rotate_cell(a, b, (-turn) % 4)
                offset = cy if (direction - turn) % 2 == 0 else cx
                for level in range(3):
                    send = Notch(x, y, level, side)
                    recv = Notch(a, b, level, opposite)
                    if (source_pad is None or send == source_pad) and (dest_pad is None or recv == dest_pad):
                        key = side != 'E', 0 if lane is None else (level - lane) % 3, level, abs(offset % TILE_SIZE - 10), x, y
                        options.append((key, send, recv))
        if not options:
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


def _outline(occupied):
    width = max(x for x, _ in occupied) - min(x for x, _ in occupied) + 1
    height = max(y for _, y in occupied) - min(y for _, y in occupied) + 1
    return width, height


def _compact_plan(width, height, platforms, shapes, neighbours, public, finish):
    cells = {(x, y): 1 << (x * height + y) for x in range(width) for y in range(height)}
    choices = {}
    for name, variants in platforms.items():
        poses = []
        for platform in variants:
            tiles = shapes[platform][0]
            ox, oy = min(x for x, _ in tiles), min(y for _, y in tiles)
            for x, y in cells:
                anchor = x - ox, y - oy
                body = frozenset((a + anchor[0], b + anchor[1]) for a, b in tiles)
                if not body <= cells.keys():
                    continue
                rim = {(a + dx, b + dy) for a, b in body for dx, dy in DIRECTIONS} - body
                poses.append((sum(cells[p] for p in body), sum(cells.get(p, 0) for p in rim),
                              bool(rim - cells.keys()), anchor, platform))
        choices[name] = sorted(poses, key=lambda p: (public[name] != p[2], p[4][1], p[3]))
    chosen = {}
    trials = 0

    def search(used):
        nonlocal trials
        if len(chosen) == len(choices):
            return finish({n: p[3] for n, p in chosen.items()}, {n: p[4] for n, p in chosen.items()})
        domains = {}
        for name, poses in choices.items():
            if name in chosen:
                continue
            attached = [chosen[n][0] for n in neighbours[name] if n in chosen]
            options = [p for p in poses if not p[0] & used and all(p[1] & near for near in attached)
                       and (not public[name] or p[2] or p[1] & ~used)]
            if not options:
                return None
            domains[name] = options
        name = min(domains, key=lambda n: (len(domains[n]), -len(neighbours[n]), n))
        for pose in domains[name]:
            trials += 1
            if trials > 10000:
                break
            mask = used | pose[0]
            if any(public[n] and not p[2] and not p[1] & ~mask for n, p in chosen.items()):
                continue
            chosen[name] = pose
            answer = search(mask)
            if answer is not None:
                return answer
            del chosen[name]
        return None

    return search(0)


def _floorplan(modules, links, dependencies, inputs, outputs):
    platforms = {}
    for name, module in modules.items():
        kind, rotation = module.platform
        if not getattr(module, 'rotate', False):
            platforms[name] = (module.platform,)
            continue
        # 没有固定凹口或入线侧时，同形转向在排板阶段等价。
        fixed_orientation = isinstance(module, Module) and (module.inputs or module.outputs or module.input_side)
        rotations = range(4) if fixed_orientation or kind == 'Foundation_L3' else range(1 + (kind in (
            'Foundation_1x2', 'Foundation_1x3', 'Foundation_1x4', 'Foundation_2x3', 'Foundation_2x4')))
        platforms[name] = tuple((kind, r) for r in rotations)
    shapes = {p: _geometry(p) for choices in platforms.values() for p in choices}
    selected = {}
    corridors = {n: {key: i % 3 for i, key in enumerate(m.signals)}
                 for n, m in modules.items() if isinstance(m, _Corridor)}
    linked_out, linked_in = map(set, zip(*links)) if links else (set(), set())
    public_inputs = {n: tuple(p for p in fields if (n, p) not in linked_in) for n, fields in inputs.items()}
    public_outputs = {n: tuple(p for p in fields if (n, p) not in linked_out) for n, fields in outputs.items()}
    fixed = {n: (getattr(m, 'inputs', {}) if isinstance(m, Module) else {},
                 getattr(m, 'outputs', {}) if isinstance(m, Module) else {}) for n, m in modules.items()}

    def blocked_edges(offset, platform, occupied):
        return frozenset((x, y, side) for x, y, side in shapes[platform][1]
                         if _outside(offset, Notch(x, y, 0, side)) in occupied)

    def outlets_clear(name, offset, platform, occupied):
        blocked = blocked_edges(offset, platform, occupied)
        specs = tuple(_turn(ports[field], platform[1])
                      for fields, ports in zip((public_inputs[name], public_outputs[name]), fixed[name], strict=True)
                      for field in fields if field in ports)
        clear = set(shapes[platform][1]) - blocked
        return (all((p.x, p.y, p.side) in clear for p in specs)
                and len(public_inputs[name]) + len(public_outputs[name]) <= 3 * len(clear))
    neighbours = defaultdict(set)
    incoming = defaultdict(set)
    fixed_neighbours = defaultdict(list)
    for (source, signal), (dest, _) in links:
        neighbours[source].add(dest)
        neighbours[dest].add(source)
        incoming[dest].add(source)
        m = modules[source]
        if isinstance(m, Module) and signal in m.outputs:
            fixed_neighbours[dest].append((source, m.outputs[signal]))

    for name, variants in platforms.items():
        body = shapes[variants[0]][0]
        rim = {(x + dx, y + dy) for x, y in body for dx, dy in DIRECTIONS} - body
        if len(neighbours[name]) > len(rim):
            raise _FloorplanError(f'{name} 有 {len(neighbours[name])} 个相邻模块，周边只有 {len(rim)} 个可接岛格')

    def complete(offsets, selected):
        occupied = {(offsets[n][0] + x, offsets[n][1] + y) for n, p in selected.items() for x, y in shapes[p][0]}
        if any(not outlets_clear(n, offsets[n], selected[n], occupied) for n in modules):
            return None
        geometry = {n: shapes[p] for n, p in selected.items()}
        sides = {n: 'ESWN'[('ESWN'.index(m.input_side) + selected[n][1]) % 4]
                 for n, m in modules.items() if isinstance(m, Module) and m.input_side is not None}
        notches = _pairs(offsets, links, geometry, sides, corridors,
                         {n: pads[0] for n, pads in fixed.items()}, {n: pads[1] for n, pads in fixed.items()})
        if notches is not None:
            return offsets.copy(), notches, selected.copy()
        return None

    offsets: dict[str, tuple[int, int]] = {}
    tiles: dict[str, set[tuple[int, int]]] = {}
    trials = 0
    total = sum(len(shapes[variants[0]][0]) for variants in platforms.values())
    best = []
    max_width = max_height = total
    limit = 12000

    def place(occupied):
        nonlocal trials
        if len(offsets) == len(modules):
            width, height = _outline(occupied)
            score = width * height, max(width, height)
            if not best or score < best[0][0]:
                result = complete(offsets, selected)
                if result is not None:
                    best[:] = [(score, *result)]
            return
        if trials >= limit:
            return
        members = [m for m in modules if m not in offsets and dependencies[m] <= offsets.keys()]
        name = max(members, key=lambda m: (len(neighbours[m] & offsets.keys()), len(neighbours[m] - offsets.keys()),
                                            len(shapes[platforms[m][0]][0])))
        adjacent = sorted(neighbours[name] & offsets.keys())
        options = []
        for platform in platforms[name]:
            module = modules[name]
            side = None if not isinstance(module, Module) or module.input_side is None else (
                'ESWN'.index(module.input_side) + platform[1]) % 4
            shape = shapes[platform][0]
            if adjacent:
                candidates = dict.fromkeys(_adjacent(tiles[adjacent[0]], shape))
            elif occupied:
                candidates = dict.fromkeys(_adjacent(occupied, shape))
            else:
                candidates = {(0, 0): None}
            for x, y in candidates:
                body = {(x + a, y + b) for a, b in shape}
                if body & occupied or any(not any((a + dx, b + dy) in tiles[m]
                                                 for a, b in body for dx, dy in DIRECTIONS) for m in adjacent):
                    continue
                if side is not None:
                    dx, dy = DIRECTIONS[side]
                    if any(not any((a + dx, b + dy) in tiles[m] for a, b in body)
                           for m in adjacent if m in incoming[name]):
                        continue
                for source, endpoint in fixed_neighbours[name]:
                    if source not in offsets:
                        continue
                    rotation = selected[source][1]
                    dx, dy = DIRECTIONS[('ESWN'.index(endpoint.side) + rotation) % 4]
                    a, b = rotate_cell(endpoint.x, endpoint.y, rotation)
                    tx, ty = offsets[source]
                    if (tx + a // TILE_SIZE + dx, ty + b // TILE_SIZE + dy) not in body:
                        break
                else:
                    used = occupied | body
                    if not outlets_clear(name, (x, y), platform, used):
                        continue
                    if any(not outlets_clear(m, offsets[m], selected[m], used) for m in adjacent):
                        continue
                    w, h = _outline(used)
                    if w <= max_width and h <= max_height and (not best or (w * h, max(w, h)) < best[0][0]):
                        options.append(((max(w * h, total), max(w, h)), platform, (x, y), body, used))
        for _, platform, pos, body, used in sorted(options, key=lambda item: item[0]):
            selected[name] = platform
            trials += 1
            if trials > limit:
                return
            offsets[name], tiles[name] = pos, body
            place(used)
            del offsets[name], tiles[name], selected[name]

    # 先比外框面积，再比最长边。给紧凑外框单独留搜索预算。
    bounds = sorted((w * h, max(w, h), w, h) for w in range(2, total + 1)
                    for h in range(max(2, w - 3), min(total, w + 3) + 1) if w * h >= total)
    if corridors and not any(isinstance(m, Module) and (m.input_side or m.inputs or m.outputs) for m in modules.values()):
        public = {n: bool(public_inputs[n] or public_outputs[n]) for n in modules}
        for _, _, w, h in bounds[:8]:
            result = _compact_plan(w, h, platforms, shapes, neighbours, public, complete)
            if result is not None:
                return result
    for area, _, max_width, max_height in bounds[:8]:
        limit = trials + 2500
        place(set())
        if best and best[0][0][0] <= area:
            return best[0][1:]
    max_width = max_height = total
    limit = trials + 12000
    place(set())
    if not best:
        raise _FloorplanError(f"现有平台未找到可接通的平面排法，共尝试 {trials} 个位置")
    return best[0][1:]


def _index(wiring, platform, port):
    return wiring.lookup[(platform, port['X'], port['Y'], port['L'])]


def _wire_corridor(foundation, mapping, inputs, outputs):
    ground = platform_ground(foundation)
    base = _RoutingBoard(foundation=foundation)
    base.ground = platform_interior(foundation)
    base.origin_x = min(x for x, _ in base.ground)
    base.origin_y = min(y for _, y in base.ground)
    base.route_budget = 1600
    nets = {name: i for i, name in enumerate(inputs)}
    sources = {nets[name]: _edge(base, 'WireTransmitterReceiver', port, nets[name], ground)
               for name, port in inputs.items()}
    taps = defaultdict(list)
    for name, port in outputs.items():
        net = nets[mapping[name]]
        taps[net].append(_edge(base, 'WireTransmitterSender', port, net, ground))
    order = sorted(sources, key=lambda n: (-len(taps[n]), sources[n]))
    layouts = []
    history = Counter()
    ripups = 0
    for net_order in (order, order[::-1], sorted(sources), sorted(sources, key=lambda n: sources[n][2])):
        board = base.fork()
        for net in net_order:
            seed = sources[net]
            tree = {seed}
            for tap in sorted(taps[net], key=lambda p: sum(abs(a - b) for a, b in zip(p, seed, strict=True))):
                if not _join(board, net, tap, tree, direct=True, flywire=True, protect_pads=True,
                             preferred_level=seed[2], history=history):
                    break
                tree = (tree | board.tracks(net) | {tap}) - (board.pad_sites - tree - {tap})
            else:
                continue
            history.update(p for p in board.traces if p not in board.pad_sites)
            ripups += 1
            break
        else:
            island = board.finish()
            wiring = Wiring(island)
            def to_port(p, receive):
                return {'X': p.x, 'Y': p.y, 'L': p.level, 'R': p.rotation(receive)}
            rx = {n: to_port(p, True) for n, p in inputs.items()}
            tx = {n: to_port(p, False) for n, p in outputs.items()}
            paired = wiring.short_ports.keys() | set(wiring.short_ports.values())
            edge_ids = {_index(wiring, 0, port) for port in (*rx.values(), *tx.values())}
            if not paired & edge_ids and all(
                _local_sources(wiring, _index(wiring, 0, port), 0) == {(_index(wiring, 0, rx[mapping[name]]), 0)}
                for name, port in tx.items()
            ):
                layers = {name: [sum(p[2] == z for p in board.tracks(net)) for z in range(3)]
                          for name, net in nets.items()}
                report = {
                    'foundation': foundation, 'rotation': 0, 'inputs': rx, 'outputs': tx,
                    'signal_count': len(rx), 'logic_gates': 0, 'island_tiles': len(foundation_tiles(foundation)),
                    'building_entries': len(wiring.entries), 'direct_macros': [], 'tapped_macros': [],
                    'replicated_units': [], 'flywire_crossings': _crossings(board, wiring),
                    'ripups': int(bool(ripups)), 'ripup_attempts': ripups, 'tracks_by_layer': layers,
                }
                off_layer = sum(sum(layers[name]) - layers[name][sources[net][2]] for name, net in nets.items())
                layouts.append(((off_layer, len(wiring.entries)), island, report))
    if not layouts:
        raise ValueError(f'{foundation} 的 {len(inputs)} 路走廊无法原生接通')
    _, island, report = min(layouts, key=lambda item: item[0])
    return {'V': 1137, 'BP': island}, report


def _rotate_template(entry, report, rotation):
    if not rotation:
        return entry, report
    entry, report = deepcopy((entry, report))
    entry['R'] = (entry.get('R', 0) + rotation) % 4
    report['rotation'] = entry['R']

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


def assemble(modules: Mapping[str, Module | _PhysicalModule], links: tuple[Link, ...], *, through: tuple[Port, ...] = ()) -> tuple[dict, dict]:
    """按端口图总装，必要时经条形走廊分支；未连接端口保留为公开端口。"""
    shared = bool(through)
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

    # 同一个来源或同一组下游共用条形板，便于在一条板缝并排取值。
    destinations = {port: frozenset(b for a, (b, _) in links if a == port) for port in dict.fromkeys(through)}
    groups: list[list[Port]] = [list(destinations)] if shared else []
    if not shared:
        for port, sinks in destinations.items():
            group = next((g for g in groups if any(p[0] == port[0] or destinations[p] == sinks for p in g)), None)
            if group is None:
                groups.append([port])
            else:
                group.append(port)

    # 指定多路共用时优先横排分支，自动单源扇出则先沿纵向展开。
    rotations = (1, 0) if shared and len(destinations) > 1 else (0, 1)
    last = None
    for length in (2, 3, 4):
        for rotation in rotations:
            extended: dict[str, Module | _PhysicalModule | _Corridor] = dict(modules)
            incoming = []
            relays = {}
            for group in groups:
                name = f'bus:{group[0][0]}.{group[0][1]}'
                while name in extended:
                    name += ':'
                types = {}
                for n, source in enumerate(group):
                    a, field = source
                    signal = f'signal{n}'
                    module = modules[a]
                    if isinstance(module, _PhysicalModule):
                        types[signal] = module.outputs[field]
                    else:
                        program = module.programs[field]
                        types[signal] = next(f.result for f in program.functions if f.name == program.entry)
                    incoming.append((source, (name, signal)))
                    relays[source] = name, signal
                extended[name] = _Corridor(types, (f'Foundation_1x{length}', rotation))
            extended_links = tuple(incoming) + tuple((relays.get(source, source), dest) for source, dest in links)
            try:
                bp, report = _assemble(extended, extended_links)
            except ValueError as error:
                last = error
                continue
            report['corridors'] = tuple(dict.fromkeys(name for name, _ in relays.values()))
            return bp, report
    raise ValueError(f'走廊无法接通：{last}') from last


@dataclass(frozen=True)
class _Corridor:
    signals: Mapping[str, ValueType]
    platform: tuple[str, int]


@dataclass(frozen=True)
class _PhysicalModule:
    model: _Netlist
    inputs: Mapping[str, ValueType]
    outputs: Mapping[str, ValueType]
    platform: tuple[str, int]
    rotate: bool = False


def _assemble(modules, links, *, feedback=()):
    feedback = set(feedback)
    if feedback - set(links):
        raise ValueError('反馈端口须在实接连接图内')
    if not modules:
        raise ValueError("至少需要一个模块")
    inputs = {}
    outputs = {}
    for name, module in modules.items():
        if isinstance(module, _Corridor):
            inputs[name] = outputs[name] = module.signals
            continue
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
    offsets, notches, platforms = _floorplan(modules, links, dependencies, inputs, outputs)
    occupied = {(offsets[n][0] + x, offsets[n][1] + y)
                for n, platform in platforms.items() for x, y in _geometry(platform)[0]}
    in_ports = defaultdict(dict)
    out_ports = defaultdict(dict)
    programs = {name: dict(m.programs) for name, m in modules.items() if isinstance(m, Module)}
    corridor_outputs: dict[str, dict[str, str]] = {n: {} for n, m in modules.items() if isinstance(m, _Corridor)}
    physical_links = []
    for i, (source, dest) in enumerate(links):
        a, output = source
        b, input_ = dest
        tx, rx = notches[i]
        name = output
        if a in corridor_outputs:
            name = f'{output}:{i}'
            corridor_outputs[a][name] = output
        elif name in out_ports[a]:
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
        foundation, rotation = platforms[module]
        def normalize(ports):
            return {name: _turn(p, (-rotation) % 4) for name, p in ports.items()}
        incoming, outgoing = normalize(in_ports[module]), normalize(out_ports[module])
        if isinstance(descriptor, Module):
            incoming = {**descriptor.inputs, **incoming}
            outgoing = {**descriptor.outputs, **outgoing}
        frame = 0
        if isinstance(descriptor, _Corridor):
            bp, report = _wire_corridor(foundation, corridor_outputs[module], incoming, outgoing)
        else:
            model = descriptor.model if isinstance(descriptor, _PhysicalModule) else None
            logic = model if model is not None else tuple(programs[module].items())
            blocked = frozenset(_turn(port, (-rotation) % 4)
                                for x, y, side in _geometry((foundation, rotation))[1]
                                for z in range(3) for port in (Notch(x, y, z, side),)
                                if _outside(offsets[module], port) in occupied)
            frames = (0,)
            if isinstance(descriptor, _PhysicalModule) and len(incoming) == 1 and len(descriptor.outputs) >= 8:
                side = next(iter(incoming.values())).side
                facing_west = (2 - 'ESWN'.index(side)) % 4
                frames = tuple(dict.fromkeys((facing_west, 0, 1, 2, 3)))
            last = None
            for frame in frames:
                ins = {name: _turn(port, frame) for name, port in incoming.items()}
                outs = {name: _turn(port, frame) for name, port in outgoing.items()}
                blocked_ports = frozenset(_turn(port, frame) for port in blocked)
                spec = (foundation, frame, logic, tuple(sorted(ins.items())), tuple(sorted(outs.items())), blocked_ports)
                if spec not in cache:
                    model = _Netlist(programs[module]) if model is None else model
                    try:
                        cache[spec] = _build_netlist(model, platform=(foundation, frame), input_ports=ins,
                                                     output_ports=outs, blocked=blocked_ports)
                    except ValueError as error:
                        last = error
                        continue
                bp, report = cache[spec]
                break
            else:
                raise ValueError(f'{module} 无法布通：{last}') from last
        entry, reports[module] = _rotate_template(bp['BP']['Entries'][0], report, (rotation - frame) % 4)
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
    access = require_public_access(wiring)
    sent = {a for a, _ in physical_links}
    ports = {direction: {f"{name}.{port}": (indices[name], spec)
                         for name, report in reports.items() for port, spec in report[direction].items()
                         if (name, port) not in skips}
             for direction, skips in (('inputs', seen), ('outputs', sent))}
    return {'V': 1137, 'BP': island}, {
        **ports, 'modules': reports, 'unique_layouts': len(cache), 'cross_flywires': len(actual),
        'public_access': access,
        'ripup_attempts': sum(report['ripup_attempts'] for _, report in cache.values()),
        'building_entries': len(wiring.entries), 'island_tiles': sum(r['island_tiles'] for r in reports.values()),
        'ripups': sum(report['ripups'] for _, report in cache.values()),
        'feedback': [(indices[b], reports[b]['inputs'][p]) for _, (b, p) in sorted(feedback)],
        'outline': _outline({(offsets[m][0] + x, offsets[m][1] + y) for m in modules
                             for x, y in _geometry(platforms[m])[0]}),
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
