"""从原生端口重建短距本地导线，逐端口核对新布置。"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import product

from ..mari.blueprint import DIRECTIONS, PORTS, Wiring, _kind, _rotate
from .compiler_backend._snapshot_router import connect_bus
from .export_wiring_review import _building_cells
from .foundations import FOUNDATION_CHUNKS, foundation_origin, foundation_tiles, platform_ground, platform_interior
from .wired_module import _Board


_RADIOS = {"ControlledSignalReceiver", "ControlledSignalTransmitter", "WireGlobalTransmitterReceiver"}
_SHORT = {"WireTransmitterSender", "WireTransmitterReceiver"}


@dataclass(frozen=True)
class _Part:
    index: int
    entry: dict
    ports: tuple
    origin: tuple


def _netlist(platforms, *, keep_ports=False):
    wiring = Wiring({"Entries": platforms})
    sources_at = wiring._direct_sources if keep_ports else wiring.sources
    pairs = {} if keep_ports else wiring.short_ports
    skip = {i for pair in pairs.items() for i in pair}
    aliases = {}

    def local_net(node):
        net = wiring._find(node)
        while net in aliases:
            net = aliases[net]
        return net

    for rx, tx in pairs.items():
        receiving = local_net(wiring.pins[rx][0][0])
        sending = local_net(wiring.pins[tx][1][0])
        if receiving != sending:
            aliases[receiving] = sending
    receivers, replaced = {}, {}
    for index, (_, entry) in enumerate(wiring.entries):
        if _kind(entry) != "ControlledSignalReceiver":
            continue
        sources = sources_at(index, 0)
        if len(sources) != 1:
            continue
        config = wiring.entries[sources[0][0]][1]
        if _kind(config) != "ConstantSignal":
            continue
        pin = wiring.pins[index][0][0]
        root = wiring._find(pin)
        if wiring.drivers[root] != [(index, 0)]:
            continue
        key = entry["T"], entry.get("C"), config["C"]
        first, target = receivers.setdefault(key, (index, pin))
        if first != index:
            replaced[index] = first
            skip.add(index)
            net, shared = local_net(pin), local_net(target)
            if net != shared:
                aliases[net] = shared
    parts = []
    active = set()
    for index, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if index in skip:
            continue
        if kind in _SHORT and not keep_ports or not any(wiring.pins[index]):
            return None
        if kind == "ConstantSignal" or not any(wiring.pins[index][:2]):
            continue
        inputs = []
        for pin, node in enumerate(wiring.pins[index][1]):
            sources = sources_at(index, pin)
            cfg = wiring.entries[sources[0][0]][1] if len(sources) == 1 else None
            if cfg is not None and _kind(cfg) == "ConstantSignal":
                inputs.append((None, cfg["C"]))
            else:
                if any(_kind(wiring.entries[i][1]) == "ConstantSignal" for i, _ in sources):
                    return None
                inputs.append((local_net(node) if sources else None, None))
                active.update(sources)
        prefix = tuple((local_net(node), None) for node in wiring.pins[index][0])
        parts.append(_Part(index, entry, (prefix, tuple(inputs)), wiring.sites[index][1:]))
    used = {local_net(wiring.pins[i][0][port]) for i, port in active}
    return wiring, parts, used, replaced


def _entry(part, x, y, z, turn):
    return {**part.entry, "X": x, "Y": y, "L": z, "R": turn}


def _candidate(board, part, site, used):
    x, y, z, turn = site
    entry = _entry(part, *site)
    kind = _kind(entry)
    cells = _building_cells(entry, kind)
    if cells is None:
        return None
    body = set(cells)
    if any(p in board.occupied or p in board.traces or not board.on_ground(*p[:2]) or not 0 <= p[2] < 3 for p in body):
        return None
    pads, literals = {}, {}
    for category, (ports, nets) in enumerate(zip(PORTS[kind], part.ports)):
        for i, ((d, dx, dy, dz), (net, value)) in enumerate(zip(ports, nets, strict=True)):
            if category == 0 and net not in used or category == 1 and net not in used and value is None:
                continue
            if entry["T"].endswith("Mirrored"):
                dy, d = -dy, -d % 4
            dx, dy = _rotate(dx, dy, turn)
            side = (d + turn) % 4
            ax, ay = DIRECTIONS[side]
            pad = (x + dx + ax, y + dy + ay, z + dz)
            if not board.on_ground(*pad[:2]) or pad in body or pad in board.occupied or pad in literals or pad in pads:
                return None
            if value is not None:
                if pad in board.traces:
                    return None
                literals[pad] = (i, value, (side + 2) % 4)
            else:
                if board.traces.get(pad, {}).keys() - {net}:
                    return None
                pads[pad] = (net, (side + 2) % 4)
    for (a, b, level), (net, side) in pads.items():
        if not any((neighbor := (a + dx, b + dy, level)) not in board.occupied
                   and neighbor not in body and neighbor not in literals
                   and board.on_ground(a + dx, b + dy)
                   and ((a + dx, b + dy, level) not in pads or pads[a + dx, b + dy, level][0] == net)
                   for direction, (dx, dy) in enumerate(DIRECTIONS) if direction != side):
            return None
    return entry, body, pads, literals


def _place(board, trial):
    entry, body, pads, literals = trial
    board.occupied.update(body)
    board.entries.append({**entry, "X": entry["X"] + board.origin_x, "Y": entry["Y"] + board.origin_y})
    for (x, y, z), (_, value, rotation) in literals.items():
        board.place("ConstantSignal", x, y, z, rotation, value)
    for (x, y, z), (net, side) in pads.items():
        board.traces[x, y, z].setdefault(net, set()).add(side)
        board.terminals[net, z].add((x, y, z))


def _radios(board, parts, used):
    width, height = board.width, board.height
    rows = tuple(range(2, height - 1, 4))
    cols = tuple(range(4, width - 3, 4))
    left = ([(1, y, 0, 0) for y in rows] + [(x, 1, 0, 1) for x in cols]
            + [(x, height - 2, 0, 3) for x in cols] + [(width - 2, y, 0, 2) for y in rows])
    right = ([(width - 2, y, 0, 0) for y in rows] + [(x, height - 2, 0, 1) for x in reversed(cols)]
             + [(x, 1, 0, 3) for x in reversed(cols)] + [(1, y, 0, 2) for y in rows])
    for part in parts:
        sites = right if _kind(part.entry) == "ControlledSignalTransmitter" else left
        for site in sites:
            trial = _candidate(board, part, site, used)
            if trial is not None:
                yield part, trial
                break
        else:
            raise ValueError("平台边缘空间不足")


def _logic_sites(board, part, used, *, pitch, stagger):
    # 门位留出紧邻端口的导线格，错开格点时给上下层留不同的直通路。
    sides = [(x, y) for x in range(2, board.width - 1, pitch) for y in range(2, board.height - 1, pitch)]
    preferred = part.origin[2]
    for x, y in sides:
        for z in (preferred, (preferred + 1) % 3, (preferred + 2) % 3):
            a, b = (x + z % 2, y + z // 2) if stagger else (x, y)
            if (a, b, z) in board.occupied or (a, b, z) in board.traces:
                continue
            for turn in range(4):
                trial = _candidate(board, part, (a, b, z, turn), used)
                if trial is not None:
                    yield trial


def _distance(trial, targets):
    cost = 0
    for (x, y, z), (net, _) in trial[2].items():
        points = targets.get(net)
        if points:
            cost += min(abs(x - a) + abs(y - b) + 4 * abs(z - c) for a, b, c in points)
        else:
            cost += 1
    return cost


def _verify(old, new, reindex, replaced, *, keep_ports):
    after = Wiring({"Entries": [new]})
    inverse = {j: i for i, j in reindex.items()}

    def source(wiring, i, port, mapping):
        entry = wiring.entries[i][1]
        if _kind(entry) == "ConstantSignal":
            return "constant", entry["C"]
        return mapping[i], port

    old_ids = {i: i for i in reindex} | replaced
    sources_at = old._direct_sources if keep_ports else old.sources
    for i, j in reindex.items():
        for port in range(len(old.pins[i][1])):
            expected = {source(old, k, p, old_ids) for k, p in sources_at(i, port)}
            actual = {source(after, k, p, inverse) for k, p in after._direct_sources(j, port)}
            if actual != expected:
                raise ValueError(f"重布线路后端口 {i}/{port} 的来源改变")


def _route_buses(board, prefer_short=False):
    terminals = defaultdict(set)
    for (net, _), points in board.terminals.items():
        terminals[net].update(points)

    def priority(net):
        points = terminals[net]
        if prefer_short:
            span = sum(max(axis) - min(axis) for axis in zip(*points))
            return span, -len(points), net
        return -len(points), net

    order = sorted((net for net, points in terminals.items() if len(points) > 1), key=priority)
    pads = {p: {net: set(ports) for net, ports in nets.items()} for p, nets in board.traces.items()}
    occupied = board.occupied.copy()
    original = board.entries.copy()
    attempts = set()
    for seed in range(4):
        if tuple(order) in attempts:
            order.reverse()
        attempts.add(tuple(order))
        board.entries = original.copy()
        board.occupied = occupied.copy()
        board.traces = defaultdict(dict, {p: {net: set(ports) for net, ports in nets.items()} for p, nets in pads.items()})
        for net in order:
            try:
                connect_bus(board, net, seed)
            except ValueError:
                order.remove(net)
                order.insert(0, net)
                break
        else:
            return board.finish()["Entries"][0]
    raise ValueError(f"紧凑母线 {order[0]} 无法接通")


def _place_on(netlist, foundation, pitch, *, edge_slots=None, stagger=False, prefer_short=False):
    wiring, parts, used, replaced = netlist
    board = _Board(foundation=foundation)
    board.ground = platform_interior(foundation)
    reindex, targets = {}, defaultdict(list)

    def add(part, trial):
        reindex[part.index] = len(board.entries)
        _place(board, trial)
        for pad, (net, _) in trial[2].items():
            targets[net].append(pad)

    if edge_slots is not None:
        ports = [p for p in parts if _kind(p.entry) in _SHORT]
        for part, (row, z) in zip(ports, edge_slots, strict=True):
            outgoing = _kind(part.entry) == "WireTransmitterSender"
            x, pad_x, side = (board.width, board.width - 1, 0) if outgoing else (-1, 0, 2)
            y = row - board.origin_y
            site = x + board.origin_x, row
            if site not in platform_ground(foundation) - board.ground or not 0 <= z < 3:
                raise ValueError("飞线端点不在平台缺口内")
            net, _ = part.ports[int(outgoing)][0]
            reindex[part.index] = len(board.entries)
            board.entries.append(_entry(part, *site, z, 0))
            board.pin(net, x, y, z, (side + 2) % 4)
            targets[net].append((pad_x, y, z))

    radios = [part for part in parts if _kind(part.entry) in _RADIOS]
    if len(radios) * 28 + len(parts) - len(radios) > 3 * len(board.ground):
        raise ValueError("器件最低占格超出平台容量")
    for part, trial in _radios(board, radios, used):
        add(part, trial)
    for part in (p for p in parts if _kind(p.entry) not in _RADIOS | _SHORT):
        sites = _logic_sites(board, part, used, pitch=pitch, stagger=stagger)
        trial = min(sites, key=lambda item: _distance(item, targets), default=None)
        if trial is None:
            raise ValueError("门位或端口空间不足")
        add(part, trial)
    new = _route_buses(board, prefer_short)
    _verify(wiring, new, reindex, replaced, keep_ports=edge_slots is not None)
    return new


def _island_offsets(foundation):
    x, y = foundation_origin(foundation)
    return {(a + x, b + y) for a, b in foundation_tiles(foundation)}


def compact_native_board(platform):
    existing = _island_offsets(platform["T"])
    foundations = tuple(kind for kind in ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3",
                                          "Foundation_2x2", "Foundation_2x3")
                        if _island_offsets(kind) < existing)
    result = fuse_native_boards([platform], foundations) if foundations else None
    return result if result is not None else platform


def fuse_native_boards(platforms, foundations, *, compare_pitches=False):
    netlist = _netlist(platforms)
    if netlist is None:
        return None
    for foundation in sorted(foundations, key=lambda kind: len(foundation_tiles(kind))):
        pitch = 3 if foundation in ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3") else 4
        pitches = (4, 5) if compare_pitches else (pitch,)
        candidates = []
        for pitch in pitches:
            try:
                candidates.append(_place_on(netlist, foundation, pitch, prefer_short=foundation == "Foundation_L3"))
            except ValueError:
                continue
        if candidates:
            return min(candidates, key=lambda board: len(board["B"]["Entries"]))
    return None


def _compact_pair(platforms):
    west, east = platforms
    if (any(p["T"] != "Foundation_3x3" or p.get("R", 0) for p in platforms)
            or east.get("X", 0) - west.get("X", 0) != 3
            or any(east.get(k, 0) != west.get(k, 0) for k in ("Y", "Z"))):
        return None
    wiring = Wiring({"Entries": platforms})
    links = sorted(wiring.short_ports.items(), key=lambda pair: pair[1])
    ports = [i for i, (_, e) in enumerate(wiring.entries) if _kind(e) in _SHORT]
    slots = tuple(product((9, 10, 8, 11), range(3)))
    if not links or len(links) > len(slots) or len(ports) != 2 * len(links):
        return None
    if any(wiring.sites[tx][0] != 0 or wiring.sites[rx][0] != 1
           or any(wiring.entries[i][1].get("R", 0) for i in (rx, tx)) for rx, tx in links):
        return None
    assigned = {i: slot for pair, slot in zip(links, slots) for i in pair}
    netlists = [_netlist([board], keep_ports=True) for board in platforms]
    if any(netlist is None for netlist in netlists):
        return None
    layouts = [[assigned[i] for i in ports if wiring.sites[i][0] == board] for board in range(2)]
    expected = {((1, y, z), (0, y, z)) for y, z in assigned.values()}
    result = []
    left = west.get("X", 0) + foundation_origin(west["T"])[0]
    for i, netlist in enumerate(netlists):
        small = ("Foundation_1x3", "Foundation_L3") if i == 0 else ("Foundation_L3", "Foundation_1x3")
        for foundation in (*small, "Foundation_2x2", "Foundation_2x3", "Foundation_3x3"):
            prefer_short = foundation in small
            pitch = 4 if prefer_short or i == 1 else 5
            try:
                board = _place_on(netlist, foundation, pitch, edge_slots=layouts[i],
                                  stagger=pitch == 4, prefer_short=prefer_short)
            except ValueError:
                continue
            anchor = left - foundation_origin(foundation)[0]
            result.append({**platforms[i], **board, "X": anchor})
            left += FOUNDATION_CHUNKS[foundation][0]
            break
        else:
            return None
    if all(board["T"] == "Foundation_3x3" for board in result):
        return None
    after = Wiring({"Entries": result})

    def slot(index):
        board, _, y, z = after.sites[index]
        return board, y, z

    actual = {(slot(rx), slot(tx)) for rx, tx in after.short_ports.items()}
    return result if actual == expected else None


def compact_combination(document):
    platforms = document["BP"]["Entries"]
    if len(platforms) == 2:
        packed = _compact_pair(platforms)
        return {**document, "BP": {**document["BP"], "Entries": packed}} if packed else document
    if len(platforms) != 1:
        return document
    original, = platforms
    islands = len(foundation_tiles(original["T"]))
    entries = len(original["B"]["Entries"])
    choices = ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3", "Foundation_L3",
               "Foundation_2x2", "Foundation_2x3", "Foundation_3x3")
    foundations = tuple(kind for kind in choices if len(foundation_tiles(kind)) <= islands)
    board = fuse_native_boards(platforms, foundations, compare_pitches=True)
    if board is None:
        return document
    score = len(foundation_tiles(board["T"])), len(board["B"]["Entries"])
    if score >= (islands, entries):
        return document
    return {**document, "BP": {**document["BP"], "Entries": [board]}}
