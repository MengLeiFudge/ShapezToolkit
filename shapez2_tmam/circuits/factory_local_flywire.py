"""把单源长直线换成同板短距飞线，核对竞争配对及最终来源。"""

from collections import defaultdict, deque
from graphlib import TopologicalSorter

from ..mari.blueprint import DIRECTIONS, PORTS, Wiring, _kind, _rotate
from .foundations import TILE_SIZE

_SENDER = "WireTransmitterSender"
_RECEIVER = "WireTransmitterReceiver"
_RANGE = range(2, 6)


def _world_sites(wiring):
    sites = []
    for board, x, y, z in wiring.sites:
        platform = wiring.platforms[board]
        sites.append((x + TILE_SIZE * platform.get("X", 0), y + TILE_SIZE * platform.get("Y", 0),
                      z + TILE_SIZE * platform.get("Z", 0)))
    return sites


def _wire_distances(wiring, sites):
    positions = defaultdict(list)
    adjacent = defaultdict(set)
    starts = []
    for i, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        x, y, z = sites[i]
        turns = entry.get("R", 0)
        for category in (0, 2):
            for j, (direction, dx, dy, dz) in enumerate(PORTS[kind][category]):
                pin = wiring.pins[i][category][j]
                root = wiring._find(pin)
                if len(wiring.drivers[root]) != 1:
                    continue
                if category == 0:
                    vertex = (i, j)
                    starts.append(vertex)
                else:
                    vertex = (i, j // 2 if kind == "WireBridge" else 0)
                if entry["T"].endswith("Mirrored"):
                    dy, direction = -dy, -direction % 4
                dx, dy = _rotate(dx, dy, turns)
                positions[root, x + dx, y + dy, z + dz, (direction + turns) % 4].append(vertex)
    for (root, x, y, z, direction), vertices in positions.items():
        dx, dy = DIRECTIONS[direction]
        others = positions.get((root, x + dx, y + dy, z, (direction + 2) % 4), ())
        for vertex in vertices:
            adjacent[vertex].update(others)
    distances = dict.fromkeys(starts, 0)
    queue = deque(starts)
    while queue:
        vertex = queue.popleft()
        for other in adjacent[vertex]:
            if other not in distances:
                distances[other] = distances[vertex] + 1
                queue.append(other)
    return {i: depth for (i, branch), depth in distances.items() if branch == 0}


def _candidates(wiring, distances):
    lines = defaultdict(dict)
    for i, (board, x, y, z) in enumerate(wiring.sites):
        entry = wiring.entries[i][1]
        if i not in distances or _kind(entry) != "WireForward":
            continue
        axis = entry.get("R", 0) % 2
        along, across = (x, y) if axis == 0 else (y, x)
        lines[board, z, axis, across][along] = i
    for length in (6, 5, 4):
        for (_, _, axis, _), line in lines.items():
            for start in sorted(line):
                span = tuple(line.get(p, -1) for p in range(start, start + length))
                if -1 in span:
                    continue
                deltas = {distances[b] - distances[a] for a, b in zip(span, span[1:])}
                if deltas == {1}:
                    yield span, axis
                elif deltas == {-1}:
                    yield span[::-1], axis + 2


def _shift(position, direction, gap):
    x, y, z = position
    dx, dy = DIRECTIONS[direction]
    return x + dx * gap, y + dy * gap, z, direction


def _rewrite(wiring, sites):
    bounds = {_SENDER: set(), _RECEIVER: set()}
    for i, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind in bounds:
            bounds[kind].add((*sites[i], entry.get("R", 0)))
    occupied = set()
    replacements = {}
    pairs = {wiring.sites[rx]: wiring.sites[tx] for rx, tx in wiring.short_ports.items()}
    for span, direction in _candidates(wiring, _wire_distances(wiring, sites)):
        if occupied.intersection(span):
            continue
        first, last = span[0], span[-1]
        start, end = sites[first], sites[last]
        if (any(_shift(start, direction, n) in bounds[_RECEIVER] for n in _RANGE)
                or any(_shift(end, direction, -n) in bounds[_SENDER] for n in _RANGE)):
            continue
        bounds[_SENDER].add((*start, direction))
        bounds[_RECEIVER].add((*end, direction))
        pairs[wiring.sites[last]] = wiring.sites[first]
        replacements.update(dict.fromkeys(span[1:-1]))
        for i, kind in ((first, _SENDER), (last, _RECEIVER)):
            replacements[i] = {**wiring.entries[i][1], "T": kind + "InternalVariant", "R": direction}
        occupied.update(span)
    if not replacements:
        return wiring.platforms, pairs
    entries = [[] for _ in wiring.platforms]
    for i, (board, original) in enumerate(wiring.entries):
        entry = replacements.get(i, original)
        if entry is not None:
            entries[board].append(entry)
    return ([{**board, "B": {**board["B"], "Entries": new}}
             for board, new in zip(wiring.platforms, entries, strict=True)], pairs)


def _sources(wiring, inputs):
    return {
        (site, port): {(*wiring.sites[source], out) for source, out in wiring.sources(wiring.lookup[site], port)}
        for site, port in inputs
    }


def shorten_local_wires(document):
    original = Wiring(document["BP"])
    entries, expected_pairs = _rewrite(original, _world_sites(original))
    if entries is original.platforms:
        return document, None
    blueprint = {**document["BP"], "Entries": entries}
    inputs = [(site, port) for i, site in enumerate(original.sites) for port in range(len(original.pins[i][1]))]
    try:
        wiring = Wiring(blueprint)
        pairs = {wiring.sites[rx]: wiring.sites[tx] for rx, tx in wiring.short_ports.items()}
        if pairs != expected_pairs or _sources(wiring, inputs) != _sources(original, inputs):
            return document, None
        depth = signal_depth(wiring)
    except ValueError:
        return document, None
    return {**document, "BP": blueprint}, depth


def signal_depth(wiring):
    deps = defaultdict(set, {rx: {tx} for rx, tx in wiring.short_ports.items()})
    outputs = []
    for i, (_, entry) in enumerate(wiring.entries):
        if _kind(entry) == "ControlledSignalTransmitter":
            outputs.append(i)
        for port in range(len(wiring.pins[i][1])):
            deps[i].update(source for source, _ in wiring._direct_sources(i, port))
    depths = {}
    for index in TopologicalSorter(deps).static_order():
        depths[index] = 1 + max((depths[d] for d in deps[index]), default=0)
    return max(depths[i] for i in outputs)
