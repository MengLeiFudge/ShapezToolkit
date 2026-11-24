"""收紧稀疏电路板并将同一部件的线路装入共用平台。"""

from dataclasses import dataclass
from functools import cache

from ..mari.blueprint import PORTS, _kind, _rotate
from .export_wiring_review import _building_cells
from .factory_short_layout import reroute_short_board
from .factory_wire_compaction import compact_axis
from .foundations import (EDGE_MARGIN, FOUNDATION_CHUNKS, IRREGULAR_FOUNDATIONS, TILE_SIZE,
                          foundation_origin, foundation_tiles, platform_ground, platform_interior)


_SIZE = 56
_PLANE = _SIZE ** 2
_FOUNDATIONS = sorted(FOUNDATION_CHUNKS, key=lambda name: (len(foundation_tiles(name)), len(platform_ground(name))))
_SHORT = {"WireTransmitterSender", "WireTransmitterReceiver"}


def _cells(entries):
    cells = []
    for entry in entries:
        footprint = _building_cells(entry, _kind(entry))
        if footprint is None:
            return None
        cells.append(tuple(footprint))
    return cells


def _ports_on_axis(entries, axis, positions):
    ports = {}
    for entry in entries:
        rotation = entry["R"]
        x, y, z = (entry[key] for key in ("X", "Y", "L"))
        if (x, y)[axis] not in positions:
            continue
        for category, pins in enumerate(PORTS[_kind(entry)]):
            for direction, px, py, level in pins:
                if entry["T"].endswith("Mirrored"):
                    py, direction = -py, -direction % 4
                direction = (direction + rotation) % 4
                if direction % 2 == axis:
                    dx, dy = _rotate(px, py, rotation)
                    coordinates = x + dx, y + dy
                    ports[coordinates[axis], coordinates[1 - axis], z + level, direction] = category
    return ports


def _safe_cuts(entries, axis, cuts):
    if not cuts:
        return cuts
    runs = []
    for site in sorted(cuts):
        if runs and runs[-1][1] == site - 1:
            runs[-1][1] = site
        else:
            runs.append([site, site])
    # 接点最多偏离原点一格。只解读截面和两侧真实端口。
    positions = {site + delta for a, b in runs for site in (a - 1, b + 1) for delta in (-1, 0, 1)}
    ports = _ports_on_axis(entries, axis, positions)
    through = {(entry[("X", "Y")[axis]], entry[("Y", "X")[axis]], entry["L"])
               for entry in entries if entry[("X", "Y")[axis]] in cuts}
    for a, b in runs:
        for site, side, z, direction in ports:
            if site != a - 1 or direction != axis:
                continue
            near, far = (site, side, z, axis), (b + 1, side, z, axis + 2)
            if far not in ports:
                continue
            joined = ports[near] != ports[far] or ports[near] == 2
            was_joined = all((value, side, z) in through for value in range(a, b + 1))
            if joined != was_joined:
                cuts.difference_update(range(a, b + 1))
                break
    return cuts


def _contract(entries, axes=(0, 1)):
    for axis in axes:
        key = ("X", "Y")[axis]
        cells = _cells(entries)
        low, high = min(p[axis] for body in cells for p in body), max(p[axis] for body in cells for p in body)
        blocked = {p[axis] for entry, body in zip(entries, cells, strict=True)
                   if _kind(entry) != "WireForward" or entry["R"] % 2 != axis for p in body}
        cuts = _safe_cuts(entries, axis, set(range(low + 1, high)) - blocked)
        if not cuts:
            continue
        position = {v: v - sum(c < v for c in cuts) for v in range(low, high + 1) if v not in cuts}
        entries = [{**entry, key: position[entry[key]]} for entry in entries if entry[key] not in cuts]
    return entries


def _components(entries, cells):
    owners = {pos: i for i, body in enumerate(cells) for pos in body}
    parent = list(range(len(entries)))

    def root(i):
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for (x, y, z), i in owners.items():
        for neighbor in ((x + 1, y, z), (x, y + 1, z)):
            j = owners.get(neighbor)
            if j is not None and i != j:
                parent[root(j)] = root(i)
    groups = {}
    for i, entry in enumerate(entries):
        groups.setdefault(root(i), []).append(entry)
    return groups.values()


def _mask(cells):
    bits = bytearray((3 * _PLANE + 7) // 8)
    for x, y, z in cells:
        index = z * _PLANE + y * _SIZE + x
        bits[index // 8] |= 1 << (index % 8)
    return int.from_bytes(bits, 'little')


@dataclass
class _Piece:
    entries: list
    cells: set
    width: int
    height: int
    levels: int
    mask: int


def _variants(entries, turns_to_try=(0, 1)):
    cells = set(p for area in _cells(entries) for p in area)
    floor = min(z for _, _, z in cells)
    levels = max(z for _, _, z in cells) - floor + 1
    for turns in turns_to_try:
        rotated = {(*_rotate(x, y, turns), z) for x, y, z in cells}
        left = min(x for x, _, _ in rotated)
        top = min(y for _, y, _ in rotated)
        body = {(x - left, y - top, z - floor) for x, y, z in rotated}
        shifted = []
        for entry in entries:
            x, y = _rotate(entry["X"], entry["Y"], turns)
            shifted.append({**entry, "X": x - left, "Y": y - top, "L": entry["L"] - floor,
                            "R": (entry["R"] + turns) % 4})
        yield _Piece(shifted, body, 1 + max(x for x, _, _ in body), 1 + max(y for _, y, _ in body), levels, _mask(body))


@dataclass
class _Bin:
    entries: list
    cells: set
    blocked: int = 0
    width: int = 0
    height: int = 0

    @property
    def island_cells(self):
        return _island_cells(self.width, self.height) if self.entries else 0

    def add(self, piece, x, y, z):
        body = {(a + x, b + y, c + z) for a, b, c in piece.cells}
        self.entries.extend({**e, "X": e["X"] + x, "Y": e["Y"] + y, "L": e["L"] + z} for e in piece.entries)
        self.cells.update(body)
        mask = piece.mask << (z * _PLANE + y * _SIZE + x)
        self.blocked |= mask | (mask >> 1) | (mask << 1) | (mask >> _SIZE) | (mask << _SIZE)
        self.width, self.height = max(self.width, x + piece.width), max(self.height, y + piece.height)


def _island_cells(width, height):
    span = 2 * EDGE_MARGIN + TILE_SIZE - 1
    return ((width + span) // TILE_SIZE) * ((height + span) // TILE_SIZE)


def _fit(bin_, variants, limit):
    current = bin_.island_cells
    for island_cells, width, height in _packing_sizes(bin_.width, bin_.height):
        if island_cells - current > limit:
            break
        free = 3 * width * height - len(bin_.cells)
        for piece in variants:
            if len(piece.cells) > free or piece.width > width or piece.height > height:
                continue
            for z in range(4 - piece.levels):
                for y in range(height - piece.height + 1):
                    mask = piece.mask << (z * _PLANE + y * _SIZE)
                    for x in range(width - piece.width + 1):
                        if not bin_.blocked & (mask << x):
                            w, h = max(bin_.width, x + piece.width), max(bin_.height, y + piece.height)
                            return (island_cells - current, w * h, max(w, h)), piece, x, y, z
    return None


@cache
def _packing_sizes(width, height):
    spans = tuple(TILE_SIZE * i - 2 * EDGE_MARGIN for i in range(1, 4))
    return sorted((_island_cells(w, h), w, h) for w in spans for h in spans if w >= width and h >= height)


def _finish(bin_):
    base = {"$type": "Building", "BinaryVersion": 1137}
    variants = tuple(_variants(bin_.entries, range(4)))
    assert len(variants[0].cells) == len(bin_.cells)
    for foundation in _FOUNDATIONS:
        ground = platform_interior(foundation)
        width, length = FOUNDATION_CHUNKS[foundation]
        x, y = foundation_origin(foundation)
        left, top = EDGE_MARGIN + x * TILE_SIZE, EDGE_MARGIN + y * TILE_SIZE
        for piece in variants:
            dx = width * TILE_SIZE - 2 * EDGE_MARGIN - piece.width
            dy = length * TILE_SIZE - 2 * EDGE_MARGIN - piece.height
            if dx < 0 or dy < 0:
                continue
            shifts = ((0, 0),)
            if foundation in IRREGULAR_FOUNDATIONS:
                shifts = tuple(dict.fromkeys((u, v) for u in (0, dx, dx // 2) for v in (0, dy, dy // 2)))
            for u, v in shifts:
                ox, oy = left + u, top + v
                if not all((a + ox, b + oy) in ground for a, b, _ in piece.cells):
                    continue
                entries = [{**e, "X": e["X"] + ox, "Y": e["Y"] + oy} for e in piece.entries]
                return {"T": foundation, "B": {**base, "Entries": entries}}, len(piece.cells)
    raise ValueError("压缩后的电路超出平台可建格")


def _turn_group_board(board):
    entries = [{**e, "X": TILE_SIZE - 1 - e["Y"], "Y": e["X"], "R": (e["R"] + 1) % 4}
               for e in board["B"]["Entries"]]
    return {**board, "X": -board.get("Y", 0), "Y": board.get("X", 0),
            "B": {**board["B"], "Entries": entries}}


def _shrink_short_board(board):
    entries = board["B"]["Entries"]
    ports = [e for e in entries if _kind(e) in _SHORT]
    if not ports:
        return board
    # 沿端口所在的边保留原坐标，只裁垂直方向的直通线。
    axes = {e["R"] % 2 for e in ports}
    tight = _contract(entries, tuple(axes)) if len(axes) == 1 else entries
    tight_ports = [e for e in tight if _kind(e) in _SHORT]
    a, b = ports[0], tight_ports[0]
    delta = (a["X"] - b["X"], a["Y"] - b["Y"])
    if any((old["X"] - new["X"], old["Y"] - new["Y"]) != delta
           for old, new in zip(ports, tight_ports, strict=True)):
        return board
    plane = {(x, y) for body in _cells(tight) for x, y, _ in body}
    old_x, old_y = board.get("X", 0), board.get("Y", 0)
    for foundation in _FOUNDATIONS:
        if foundation == "Foundation_3x3":
            break
        if foundation in IRREGULAR_FOUNDATIONS:
            continue
        width, height = FOUNDATION_CHUNKS[foundation]
        ground = platform_ground(foundation)
        interior = platform_interior(foundation)
        for x in range(old_x - 1 + (width - 1) // 2, old_x + 3 - width + (width - 1) // 2):
            for y in range(old_y - 1 + (height - 1) // 2, old_y + 3 - height + (height - 1) // 2):
                dx = delta[0] + TILE_SIZE * (old_x - x)
                dy = delta[1] + TILE_SIZE * (old_y - y)
                if all((u + dx, v + dy) in ground for u, v in plane):
                    buildings = [{**e, "X": e["X"] + dx, "Y": e["Y"] + dy} for e in tight]
                    candidate = {**board, "T": foundation, "X": x, "Y": y, "B": {**board["B"], "Entries": buildings}}
                    if _fits_ground(candidate, interior):
                        return candidate
    return board


def _fits_ground(board, interior=None):
    if interior is None:
        interior = platform_interior(board["T"])
    notches = platform_ground(board["T"]) - interior
    entries = board["B"]["Entries"]
    return all((x, y) in (notches if _kind(entry) in _SHORT else interior) and 0 <= z < 3
               for entry, body in zip(entries, _cells(entries), strict=True) for x, y, z in body)


def shrink_short_groups(platforms, groups, threshold):
    packed = list(platforms)
    limit = threshold * 3 * len(platform_ground("Foundation_3x3"))
    for indices in groups:
        if len(indices) < 2 or any(platforms[i]["T"] != "Foundation_3x3" for i in indices):
            continue
        boards = [platforms[i] for i in indices]
        sparse = [100 * sum(map(len, _cells(board["B"]["Entries"]))) < limit for board in boards]
        if not any(sparse):
            continue
        best = boards
        cost = sum(len(platform_ground(b["T"])) for b in boards)
        for group in (boards, [_turn_group_board(b) for b in boards]):
            candidate = [_shrink_short_board(b) if reduce else b for b, reduce in zip(group, sparse, strict=True)]
            area = sum(len(platform_ground(b["T"])) for b in candidate)
            if area < cost and all(_fits_ground(b) for b in candidate):
                best, cost = candidate, area
        for i, board in zip(indices, best, strict=True):
            if board["T"] == "Foundation_2x3" and 20 * sum(map(len, _cells(board["B"]["Entries"]))) < 3 * len(platform_ground(board["T"])):
                board = reroute_short_board(board)
            packed[i] = board
    return packed


def _compact_piece(entries):
    choices = []
    for axis in (0, 1):
        tight = compact_axis(compact_axis(compact_axis(entries, axis), 1 - axis), axis)
        if not tight:
            continue
        variants = tuple(_variants(tight, range(4)))
        piece = variants[0]
        if max(piece.width, piece.height) <= 54:
            score = (_island_cells(piece.width, piece.height), piece.width * piece.height, len(piece.cells))
            choices.append((score, variants))
    return min(choices, key=lambda choice: choice[0])[1] if choices else None


def _pack_pieces(ordered):
    bins = []
    for variants in ordered:
        area = _island_cells(variants[0].width, variants[0].height)
        best, target = None, None
        for bin_ in reversed(bins):
            fit = _fit(bin_, variants, area if best is None else best[0][0])
            if fit is not None and (best is None or fit[0] < best[0]):
                best, target = fit, bin_
        if target is None:
            target = _Bin([], set())
            best = _fit(target, variants, area)
            bins.append(target)
        _, piece, x, y, z = best
        target.add(piece, x, y, z)
    return list(map(_finish, bins))


def _platform_cost(platforms):
    return sum(len(foundation_tiles(p["T"])) for p in platforms), len(platforms)


def compact_platforms(platforms, threshold, *, baseline=None):
    untouched, sparse = [], []
    before, unchanged = [], []
    original = platforms if baseline is None else baseline
    for index, platform in enumerate(platforms):
        entries = platform["B"]["Entries"]
        cells = _cells(entries)
        count = sum(map(len, cells)) if cells is not None else 0
        capacity = 3 * len(platform_ground(platform["T"]))
        unchanged.append((count, capacity))
        old = original[index]
        if old is platform:
            before.append((count, capacity))
        else:
            before.append((sum(map(len, _cells(old["B"]["Entries"]))), 3 * len(platform_ground(old["T"]))))
        if (not entries or cells is None or 100 * count >= threshold * capacity
                or platform["T"] != "Foundation_3x3"
                or any(_kind(entry) in _SHORT for entry in entries)):
            untouched.append((platform, count))
            continue
        pieces = [_compact_piece(group) for group in _components(entries, cells)]
        if any(piece is None for piece in pieces):
            untouched.append((platform, count))
            continue
        sparse.extend(pieces)
    original_cost = _platform_cost(platforms)
    best = [(p, count) for p, (count, _) in zip(platforms, unchanged, strict=True)]
    best_cost = original_cost
    if sparse:
        by_size = sorted(sparse, key=lambda pair: (-pair[0].width * pair[0].height, -len(pair[0].cells)))
        by_island = sorted(by_size, key=lambda pair: -_island_cells(pair[0].width, pair[0].height))
        orders = (by_size,) if all(a is b for a, b in zip(by_size, by_island, strict=True)) else (by_size, by_island)
        for order in orders:
            packed = [*untouched, *_pack_pieces(order)]
            cost = _platform_cost([p for p, _ in packed])
            if cost < best_cost and cost[1] <= original_cost[1]:
                best, best_cost = packed, cost
    after = [(count, 3 * len(platform_ground(board["T"]))) for board, count in best]
    return [p for p, _ in best], before, after
