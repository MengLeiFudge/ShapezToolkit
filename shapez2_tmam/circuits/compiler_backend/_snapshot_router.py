"""按真实端口联合试摆、布线，给紧凑锁存板选择门位。"""

from collections import Counter, deque
from collections.abc import Callable
from heapq import heappop, heappush
from itertools import count, product
from random import Random

from ...mari.blueprint import DIRECTIONS, PORTS, _kind


_VIAS = (("Backward", 2), ("Forward", 0), ("Left", 3))
_SHORT_RANGE = range(2, 6)
_SENDER = "WireTransmitterSender"
_RECEIVER = "WireTransmitterReceiver"


def _available(board, site):
    return site not in board.occupied and board.on_ground(*site[:2])


def _short_sites(board):
    endpoints = {_SENDER: set(), _RECEIVER: set()}
    for entry in board.entries:
        kind = _kind(entry)
        if kind in endpoints:
            endpoints[kind].add((entry["X"] - board.origin_x, entry["Y"] - board.origin_y, entry["L"], entry["R"]))
    return endpoints


def _free_pair(endpoints, sender, receiver, turn):
    dx, dy = DIRECTIONS[turn]
    x, y, z = receiver
    if any((x - i * dx, y - i * dy, z, turn) in endpoints[_SENDER] for i in _SHORT_RANGE):
        return False
    x, y, z = sender
    return not any((x + i * dx, y + i * dy, z, turn) in endpoints[_RECEIVER] for i in _SHORT_RANGE)


def _path(board, net, start, targets, facing, estimate, flywire, pads):
    if start in targets:
        return True
    sequence = count()
    queue = [(0, next(sequence), start, 0)]
    previous: dict[tuple, tuple | None] = {start: None}
    distances = {start: 0}
    traces = board.traces
    endpoints = _short_sites(board) if flywire else None

    def reach(site, cost, direction, via=None):
        distance = distances[point] + cost
        if distance < distances.get(site, float("inf")):
            distances[site] = distance
            previous[site] = point, direction, via
            priority = distance + estimate(site) if estimate is not None else distance
            heappush(queue, (priority, next(sequence), site, distance))

    while queue:
        _, _, point, distance = heappop(queue)
        if distance != distances[point]:
            continue
        if point in targets:
            break
        x, y, level = point
        for step in range(4):
            direction = (facing + step) % 4
            dx, dy = DIRECTIONS[direction]
            a, b = x + dx, y + dy
            site = a, b, level
            while _available(board, site):
                wires = traces.get(site, {})
                if not wires or net in wires:
                    if len(wires) <= 1:
                        reach(site, abs(site[0] - x) + abs(site[1] - y), direction)
                    break
                if (site in pads or len(wires) != 1
                        or next(iter(wires.values())) != {(direction + 1) % 4, (direction + 3) % 4}):
                    break
                site = site[0] + dx, site[1] + dy, level
            if not _available(board, (a, b, level)) or traces.get((a, b, level)):
                continue
            if endpoints is not None:
                # 搜索从新接收端回到已驱动线网，因此原生飞线朝向与搜索相反。
                turn = (direction + 2) % 4
                receiver = a, b, level
                for gap in _SHORT_RANGE:
                    sender = a + gap * dx, b + gap * dy, level
                    site = sender[0] + dx, sender[1] + dy, level
                    if (not _available(board, sender) or traces.get(sender) or not _available(board, site)
                            or traces.get(site, {}).keys() - {net}):
                        continue
                    crossed = ((a + i * dx, b + i * dy, level) for i in range(1, gap))
                    if not any(p in board.occupied or traces.get(p, {}).keys() - {net} for p in crossed):
                        continue
                    if _free_pair(endpoints, sender, receiver, turn):
                        reach(site, 4, direction, (sender, receiver, turn))
            for other in sorted((z for z in range(3) if z != level), key=lambda z: abs(z - level)):
                lo, hi = sorted((level, other))
                if any((a, b, z) in board.occupied or traces.get((a, b, z)) for z in range(lo, hi + 1)):
                    continue
                for kind, upper_port in _VIAS:
                    entry, exit_ = (2, upper_port) if level == lo else (upper_port, 2)
                    rotation = (direction + 2 - entry) % 4
                    exit_ = (exit_ + rotation) % 4
                    u, v = DIRECTIONS[exit_]
                    site = a + u, b + v, other
                    if _available(board, site) and not traces.get(site, {}).keys() - {net}:
                        via = f"WireDefault{hi - lo}Up{kind}", a, b, lo, rotation, hi - lo + 1, exit_
                        reach(site, 7 + hi - lo, direction, via)
    else:
        return None

    # 寻路状态只记当前位置。回查换层段，避免这条路径与自身重叠。
    path, occupied = [], set()
    while (edge := previous[point]) is not None:
        origin, direction, via = edge
        if via and len(via) == 3:
            sender, receiver, turn = via
            assert endpoints is not None
            if not _free_pair(endpoints, sender, receiver, turn):
                return False
            endpoints[_SENDER].add((*sender, turn))
            endpoints[_RECEIVER].add((*receiver, turn))
            cells = {point, sender, receiver}
        elif via:
            _, a, b, lo, _, height, _ = via
            cells = {point, *((a, b, z) for z in range(lo, lo + height))}
        else:
            dx, dy = DIRECTIONS[direction]
            length = abs(point[0] - origin[0]) + abs(point[1] - origin[1])
            cells = {(point[0] - dx * i, point[1] - dy * i, point[2]) for i in range(length)}
        if cells & occupied:
            return False
        occupied.update(cells)
        path.append((point, origin, direction, via))
        point = origin
    if start in occupied:
        return False
    for point, origin, direction, via in path:
        if via and len(via) == 3:
            sender, receiver, turn = via
            board.place(_SENDER, *sender, turn)
            board.place(_RECEIVER, *receiver, turn)
            traces[point].setdefault(net, set()).add(turn)
            traces[origin].setdefault(net, set()).add(direction)
        elif via:
            kind, a, b, lo, rotation, height, exit_ = via
            board.place(kind, a, b, lo, rotation, height=height)
            traces[point].setdefault(net, set()).add((exit_ + 2) % 4)
            traces[origin].setdefault(net, set()).add(direction)
        else:
            dx, dy = DIRECTIONS[direction]
            while point != origin:
                traces[point].setdefault(net, set()).add((direction + 2) % 4)
                point = point[0] - dx, point[1] - dy, point[2]
                traces[point].setdefault(net, set()).add(direction)
    return True


def _join(board, net, site, tree, *, direct=False, flywire=False, protect_pads=False):
    pads = set().union(*board.terminals.values()) if protect_pads else set()
    estimate: Callable[[tuple[int, int, int]], int] | None = None
    if direct:
        xs, ys, levels = zip(*tree)
        left, right = min(xs), max(xs)
        top, bottom = min(ys), max(ys)
        low, high = min(levels), max(levels)

        def distance_to_box(point):
            x, y, z = point
            span = max(left - x, x - right, 0) + max(top - y, y - bottom, 0) + max(low - z, z - high, 0)
            return span // 2 if flywire else span

        estimate = distance_to_box

    for direction in range(4):
        result = _path(board, net, site, tree, direction, estimate, flywire, pads)
        # 换方向只改变同代价的选路顺序，搜索穷尽后无需重试。
        if result is None:
            return False
        if result:
            return True
    return False


def _track(board, net):
    return {site for site, wires in board.traces.items() if len(wires) == 1 and len(wires.get(net, ())) > 1}


def connect_bus(board, net, seed, *, direct=False):
    pads = sorted({p for (name, _), sites in board.terminals.items() if name == net for p in sites})
    Random(seed).shuffle(pads)
    tree = {pads.pop()}
    for site in pads:
        if not _join(board, net, site, tree, direct=direct):
            raise ValueError(f"锁存板母线 {net} 无法接通")
        tree.add(site)
        tree.update(_track(board, net))


def _distance_map(board, net, targets):
    queue = deque(targets)
    distances = dict.fromkeys(targets, 0)
    while queue:
        x, y, z = queue.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            site = x + dx, y + dy, z + dz
            if not 0 <= site[2] < 3 or site in distances or not _available(board, site):
                continue
            wires = board.traces.get(site)
            if wires and wires.keys() - {net} and (len(wires) > 1 or len(next(iter(wires.values()))) != 2):
                continue
            distances[site] = distances[x, y, z] + (4 if dz else 1)
            queue.append(site)
    return distances


def _sites(board, pads, gate, fanout, random):
    kind, args, outputs, _ = gate
    names = (*outputs, *args)
    directions = tuple(d for ports in PORTS[kind][:2] for d, _, _, _ in ports)
    levels = (0, 1, 2)
    if outputs in (("load",), ("retain",)):
        net, = outputs
        levels = tuple(z for name, z in board.terminals if name == net and z > 0) or (1 if net == "load" else 2,)
    targets = {name: (_track(board, name) | {p for p in pads[name] if p[2] > 0})
               if name in ("load", "retain") else pads[name] for name in names if isinstance(name, str)}
    distances = {name: _distance_map(board, name, sites) for name, sites in targets.items() if sites}
    positions = sorted((x - board.origin_x, y - board.origin_y) for x, y in board.ground)
    for z in levels:
        for (x, y), rotation in product(positions, range(4)):
            center = x, y, z
            if center in board.occupied:
                continue
            existing = board.traces.get(center, {})
            direct = set()
            score = 0
            for name, direction in zip(names, directions, strict=True):
                side = (direction + rotation) % 4
                dx, dy = DIRECTIONS[side]
                a, b = x + dx, y + dy
                site = a, b, z
                if not board.on_ground(a, b):
                    break
                if site in board.occupied:
                    if (isinstance(name, str) and fanout[name] == 2 and pads[name] == [center]
                            and existing == {name: {side}}):
                        direct.add(name)
                        score -= 8
                        continue
                    break
                wires = board.traces.get(site, {})
                if wires and (not isinstance(name, str) or wires.keys() != {name}):
                    break
                if isinstance(name, str) and pads[name]:
                    score += distances[name].get(site, 125) if name in distances else 0
                if isinstance(name, str) and not wires:
                    free = sum((a + u, b + v, z) not in board.occupied and not board.traces.get((a + u, b + v, z))
                               for u, v in DIRECTIONS) - 1
                    if not free:
                        break
                    score += (3 - free) * 2
            else:
                if not existing.keys() - direct:
                    yield score + random.random() * 20, x, y, z, rotation, direct


def place_controls(layout, gates, seed):
    random = Random(seed)
    fanout = Counter(net for gate in gates for net in (*gate[1], *gate[2]) if isinstance(net, str))
    remaining = list(gates)
    while remaining:
        board = layout.board
        pads = {net: [p for z in range(3) for p in board.terminals.get((net, z), ())] for net in fanout}

        def priority(gate):
            nets = [net for net in (*gate[2], *gate[1]) if isinstance(net, str)]
            return sum((8 if pads[net] else 0) + fanout[net] for net in nets) + random.random() * 12

        gate = max(remaining, key=priority)
        remaining.remove(gate)
        bands = Counter()
        candidates = []
        for candidate in sorted(_sites(board, pads, gate, fanout, random)):
            score, x, y, z, _, _ = candidate
            band = x // 3, y // 3, z
            candidates.append((score + 13 * bands[band], candidate))
            bands[band] += 1
        for _, (_, x, y, z, rotation, direct) in sorted(candidates)[:20]:
            trial = layout.copy()
            for net in direct:
                trial.board.traces.pop((x, y, z))
                trial.board.terminals.pop((net, z))
            try:
                trial.gate(gate, x, y, z, rotation, direct=direct)
            except ValueError:
                continue
            for net in dict.fromkeys((*gate[2], *gate[1])):
                if net in direct or not pads.get(net):
                    continue
                track = _track(board, net)
                if net in ("load", "retain"):
                    track = {p for p in track if p[2] > 0}
                tree = track | set(pads[net])
                if not all(_join(trial.board, net, p, tree) for p in trial.board.terminals[net, z] - tree):
                    break
            else:
                layout = trial
                break
        else:
            raise ValueError(f"紧凑锁存板无法摆放并接通 {gate[2]}")
    return layout
