"""从原生端口重建短距本地导线，逐端口核对新布置。"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import product

from ..mari.blueprint import DIRECTIONS, PORTS, Wiring, _kind, _rotate
from .compiler_backend._snapshot_router import connect_bus
from .export_wiring_review import _building_cells
from .foundations import FOUNDATION_CHUNKS, TILE_SIZE, foundation_origin, foundation_tiles, platform_ground, platform_interior
from .wired_module import _Board


_RADIOS = {"ControlledSignalReceiver", "ControlledSignalTransmitter", "WireGlobalTransmitterReceiver"}
_SHORT = {"WireTransmitterSender", "WireTransmitterReceiver"}
_PAIR_NOTCH_ROWS = (9, 10, 8, 11, 29, 30, 28, 31)
SHORT_PAIR_CAPACITY = 3 * len(_PAIR_NOTCH_ROWS)


@dataclass(frozen=True)
class _Part:
    index: int
    entry: dict
    ports: tuple
    origin: tuple


def _netlist(platforms, *, keep_ports=False, merge_receivers=True):
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

    replaced = {}
    def merge_output(index, first, pin, target):
        replaced[index] = first
        skip.add(index)
        net, shared = local_net(pin), local_net(target)
        if net != shared:
            aliases[net] = shared

    if merge_receivers:
        receivers = {}
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
                merge_output(index, first, pin, target)
    if len(platforms) > 1 and not keep_ports:
        # 唯一驱动且每个输入的来源相同，才能共用同一逻辑门。
        gates = {}
        for index, (_, entry) in enumerate(wiring.entries):
            if not _kind(entry).startswith("LogicGate"):
                continue
            pin, = wiring.pins[index][0]
            if wiring.drivers[wiring._find(pin)] != [(index, 0)]:
                continue
            inputs = []
            for port in range(len(wiring.pins[index][1])):
                drivers = sources_at(index, port)
                if len(drivers) > 1:
                    break
                if not drivers:
                    inputs.append(None)
                    continue
                driver, output = drivers[0]
                source = wiring.entries[driver][1]
                if _kind(source) == "ConstantSignal":
                    inputs.append(("constant", source["C"]))
                else:
                    inputs.append((replaced.get(driver, driver), output))
            else:
                key = entry["T"], entry.get("C"), tuple(inputs)
                first, target = gates.setdefault(key, (index, pin))
                if first != index:
                    merge_output(index, first, pin, target)
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


def _candidate(board, part, site, used, *, direct=None):
    x, y, z, turn = site
    entry = _entry(part, *site)
    kind = _kind(entry)
    cells = _building_cells(entry, kind)
    if cells is None:
        return None
    body = set(cells)
    if any(p in board.occupied or (p in board.traces and (p != (x, y, z) or direct is None))
           or not board.on_ground(*p[:2]) or not 0 <= p[2] < 3 for p in body):
        return None
    pads, literals = {}, {}
    joined = False
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
            if direct == (net, side) and (dx, dy, dz) == (0, 0, 0) and pad in board.occupied:
                joined = True
                continue
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
    if direct is not None and not joined:
        return None
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


def _radios(board, parts, used, *, left_rail=False):
    width, height = board.width, board.height
    rows = tuple(range(2, height - 1, 4))
    cols = tuple(range(4, width - 3, 4))
    left = ([(1, y, 0, 0) for y in rows] + [(x, 1, 0, 1) for x in cols]
            + [(x, height - 2, 0, 3) for x in cols] + [(width - 2, y, 0, 2) for y in rows])
    right = ([(width - 2, y, 0, 0) for y in rows] + [(x, height - 2, 0, 1) for x in reversed(cols)]
             + [(x, 1, 0, 3) for x in reversed(cols)] + [(1, y, 0, 2) for y in rows])
    for part in parts:
        sends = _kind(part.entry) == "ControlledSignalTransmitter"
        if left_rail:
            sites = ((1 + 6 * column, y, 0, 2 if sends else 0) for column in range(4) for y in rows)
        else:
            sites = right if sends else left
        for site in sites:
            trial = _candidate(board, part, site, used)
            if trial is not None:
                yield part, trial
                break
        else:
            raise ValueError("平台边缘空间不足")


def _logic_sites(board, part, used, lattice):
    preferred = part.origin[2]
    for column in lattice:
        for z in (preferred, (preferred + 1) % 3, (preferred + 2) % 3):
            a, b = column[z]
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


def _verify(old, new, reindex, replaced, *, keep_ports, input_ports=None):
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
        ports = range(len(old.pins[i][1])) if input_ports is None or i not in input_ports else input_ports[i]
        for new_port, old_port in enumerate(ports):
            expected = {source(old, k, p, old_ids) for k, p in sources_at(i, old_port)}
            actual = {source(after, k, p, inverse) for k, p in after._direct_sources(j, new_port)}
            if actual != expected:
                raise ValueError(f"重布线路后端口 {i}/{old_port} 的来源改变")


def _route_buses(board, prefer_short=False, *, direct=False):
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
                connect_bus(board, net, seed, direct=direct)
            except ValueError:
                order.remove(net)
                order.insert(0, net)
                break
        else:
            return board.finish()["Entries"][0]
    raise ValueError(f"紧凑母线 {order[0]} 无法接通")


def _place_on(netlist, foundation, pitch, *, edge_slots=None, stagger=False, prefer_short=False, direct=False,
              input_ports=None, left_rail=False):
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
        notches = platform_ground(foundation) - board.ground
        for part, (sx, sy, z, turn) in zip(ports, edge_slots, strict=True):
            outgoing = _kind(part.entry) == "WireTransmitterSender"
            side = (turn + (2 if outgoing else 0)) % 4
            dx, dy = DIRECTIONS[side]
            x, y = sx - board.origin_x, sy - board.origin_y
            if (sx, sy) not in notches or not 0 <= z < 3 or not board.on_ground(x + dx, y + dy):
                raise ValueError("飞线端点或板内出口不在可建格内")
            net, _ = part.ports[int(outgoing)][0]
            reindex[part.index] = len(board.entries)
            board.entries.append(_entry(part, sx, sy, z, turn))
            board.occupied.add((x, y, z))
            board.pin(net, x, y, z, side)
            targets[net].append((x + dx, y + dy, z))

    # 先为无线和飞线留出端口，再按三层格点的实际余量排门。
    radios = [part for part in parts if _kind(part.entry) in _RADIOS]
    gates = [part for part in parts if _kind(part.entry) not in _RADIOS | _SHORT]
    if len(radios) * 28 + len(parts) - len(radios) > 3 * len(board.ground):
        raise ValueError("器件最低占格超出平台容量")
    for part, trial in _radios(board, radios, used, left_rail=left_rail):
        add(part, trial)
    lattice = tuple(tuple((x + z % 2, y + z // 2) if stagger else (x, y) for z in range(3))
                    for x, y in product(range(2, board.width - 1, pitch), range(2, board.height - 1, pitch)))
    capacity = sum(board.on_ground(x, y) and (x, y, z) not in board.occupied and (x, y, z) not in board.traces
                   for column in lattice for z, (x, y) in enumerate(column))
    if len(gates) > capacity:
        raise ValueError("门数超出本次排布的格点容量")
    for part in gates:
        sites = _logic_sites(board, part, used, lattice)
        trial = min(sites, key=lambda item: _distance(item, targets), default=None)
        if trial is None:
            raise ValueError("门位或端口空间不足")
        add(part, trial)
    new = _route_buses(board, prefer_short, direct=direct)
    _verify(wiring, new, reindex, replaced, keep_ports=edge_slots is not None, input_ports=input_ports)
    return new


def _island_offsets(foundation):
    x, y = foundation_origin(foundation)
    return {(a + x, b + y) for a, b in foundation_tiles(foundation)}


def compact_native_board(platform):
    existing = _island_offsets(platform["T"])
    foundations = tuple(kind for kind in ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3",
                                          "Foundation_L3", "Foundation_2x2", "Foundation_2x3")
                        if _island_offsets(kind) < existing)
    result = fuse_native_boards([platform], foundations) if foundations else None
    return result if result is not None else platform


def short_board_sites(board):
    ports = [e for e in board["B"]["Entries"] if _kind(e) in _SHORT]
    if not ports or board.get("R", 0):
        return []
    old = _island_offsets(board["T"])
    candidates = []
    for foundation in FOUNDATION_CHUNKS:
        offsets = _island_offsets(foundation)
        if len(offsets) >= len(old):
            continue
        notches = platform_ground(foundation) - platform_interior(foundation)
        ax, ay = foundation_origin(foundation)
        for cx, cy in sorted(old):
            dx, dy = cx - ax, cy - ay
            if not {(x + dx, y + dy) for x, y in offsets} <= old:
                continue
            slots = [(e["X"] - TILE_SIZE * dx, e["Y"] - TILE_SIZE * dy, e["L"], e["R"]) for e in ports]
            if all((x, y) in notches for x, y, _, _ in slots):
                candidates.append((len(offsets), foundation, dx, dy, slots))
    return sorted(candidates)


def compact_fixed_short_board(platform):
    netlist = _netlist([platform], keep_ports=True)
    if netlist is None:
        return platform
    for _, foundation, dx, dy, slots in short_board_sites(platform):
        for pitch in (4, 3, 5):
            try:
                result = _place_on(netlist, foundation, pitch, edge_slots=slots, stagger=pitch == 4,
                                   prefer_short=True, direct=True)
            except ValueError:
                continue
            return {**platform, **result, "X": platform["X"] + dx, "Y": platform["Y"] + dy}
    return platform


def fuse_native_boards(platforms, foundations, *, compare_pitches=False, left_rail=False):
    netlist = _netlist(platforms)
    if netlist is None:
        return None
    merged = len(platforms) > 1
    for foundation in sorted(foundations, key=lambda kind: len(foundation_tiles(kind))):
        pitch = 3 if foundation in ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3") else 4
        pitches = (5,) if merged else (4, 5) if compare_pitches else (pitch,)
        candidates = []
        for pitch in pitches:
            try:
                short = merged or foundation == "Foundation_L3" or left_rail
                candidates.append(_place_on(netlist, foundation, pitch, prefer_short=short,
                                            direct=merged or left_rail, left_rail=left_rail))
            except ValueError:
                continue
        if candidates:
            return min(candidates, key=lambda board: len(board["B"]["Entries"]))
    return None


def compact_short_pair(platforms):
    west, east = platforms
    if (any(p["T"] != "Foundation_3x3" or p.get("R", 0) for p in platforms)
            or east.get("X", 0) - west.get("X", 0) != 3
            or any(east.get(k, 0) != west.get(k, 0) for k in ("Y", "Z"))):
        return None
    wiring = Wiring({"Entries": platforms})
    links = sorted(wiring.short_ports.items(), key=lambda pair: pair[1])
    ports = [i for i, (_, e) in enumerate(wiring.entries) if _kind(e) in _SHORT]
    slots = product(_PAIR_NOTCH_ROWS, range(3))
    if not links or len(links) > SHORT_PAIR_CAPACITY or len(ports) != 2 * len(links):
        return None
    assigned, expected = {}, set()
    for (rx, tx), (row, z) in zip(links, slots):
        a, ax, ay, az = wiring.sites[tx]
        b, bx, by, bz = wiring.sites[rx]
        turn = 2 * a
        gap = bx - ax + 3 * TILE_SIZE * (b - a)
        if (a == b or (ay, az) != (by, bz) or gap != 5 * (b - a)
                or any(wiring.entries[i][1].get("R", 0) != turn for i in (rx, tx))):
            return None
        assigned[rx] = assigned[tx] = row, z, turn
        expected.add(((b, row, z), (a, row, z)))
    netlists = []
    for platform in platforms:
        netlist = _netlist([platform], keep_ports=True)
        if netlist is None:
            return None
        netlists.append(netlist)
    layouts = [[assigned[i] for i in ports if wiring.sites[i][0] == board] for board in range(2)]
    result = []
    left = west.get("X", 0) + foundation_origin(west["T"])[0]
    for i, netlist in enumerate(netlists):
        small = ("Foundation_1x3", "Foundation_L3") if i == 0 else ("Foundation_L3", "Foundation_1x3")
        for foundation in (*small, "Foundation_2x2", "Foundation_2x3", "Foundation_3x3"):
            prefer_short = foundation in small
            pitch = 4 if prefer_short or i == 1 else 5
            try:
                left_edge = min(x for x, _ in _island_offsets(foundation)) * TILE_SIZE + 2
                right_edge = left_edge + FOUNDATION_CHUNKS[foundation][0] * TILE_SIZE - 5
                slots = []
                for port, (row, z, turn) in zip((p for p in netlist[1] if _kind(p.entry) in _SHORT),
                                                 layouts[i], strict=True):
                    outgoing = _kind(port.entry) == "WireTransmitterSender"
                    slots.append((right_edge if outgoing == (turn == 0) else left_edge, row, z, turn))
                board = _place_on(netlist, foundation, pitch, edge_slots=slots,
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


def compact_combination(document, *, left_rail=False):
    platforms = document["BP"]["Entries"]
    if left_rail and len(platforms) != 1:
        raise ValueError("单侧收发编排需要单板组合网表")
    if len(platforms) == 2:
        packed = compact_short_pair(platforms)
        return {**document, "BP": {**document["BP"], "Entries": packed}} if packed else document
    if len(platforms) != 1:
        return document
    original, = platforms
    islands = len(foundation_tiles(original["T"]))
    entries = len(original["B"]["Entries"])
    choices = ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3", "Foundation_L3",
               "Foundation_2x2", "Foundation_2x3", "Foundation_3x3")
    foundations = tuple(kind for kind in choices if len(foundation_tiles(kind)) <= islands)
    board = fuse_native_boards(platforms, foundations, compare_pitches=True, left_rail=left_rail)
    if board is None:
        if left_rail:
            raise ValueError("所选组合方法无法在原占地内接通单侧收发布局")
        return document
    score = len(foundation_tiles(board["T"])), len(board["B"]["Entries"])
    if score >= (islands, entries):
        return document
    return {**document, "BP": {**document["BP"], "Entries": [board]}}
