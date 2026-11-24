"""收紧稀疏电路板并将同一部件的线路装入共用平台。"""

from dataclasses import dataclass

from ..mari.blueprint import PORTS, _kind, _rotate
from .export_wiring_review import _building_cells
from .factory_short_layout import reroute_short_board
from .foundations import FOUNDATION_CHUNKS, TILE_SIZE, platform_ground


_SIZE = 56
_PLANE = _SIZE ** 2
_FOUNDATIONS = sorted((name for name in FOUNDATION_CHUNKS if name != "Foundation_L3"),
                      key=lambda name: len(platform_ground(name)))
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


def _mask(cells):
    return sum(1 << (z * _PLANE + y * _SIZE + x) for x, y, z in cells)


@dataclass
class _Piece:
    entries: list
    cells: set
    width: int
    height: int
    turns: int
    mask: int


def _variants(entries):
    cells = set(p for area in _cells(entries) for p in area)
    for turns in (0, 1):
        rotated = {(*_rotate(x, y, turns), z) for x, y, z in cells}
        left = min(x for x, _, _ in rotated)
        top = min(y for _, y, _ in rotated)
        body = {(x - left, y - top, z) for x, y, z in rotated}
        shifted = []
        for entry in entries:
            x, y = _rotate(entry["X"], entry["Y"], turns)
            shifted.append({**entry, "X": x - left, "Y": y - top, "R": (entry["R"] + turns) % 4})
        yield _Piece(shifted, body, 1 + max(x for x, _, _ in body), 1 + max(y for _, y, _ in body), turns, _mask(body))


@dataclass
class _Bin:
    entries: list
    cells: set
    blocked: int = 0
    width: int = 0
    height: int = 0

    def origins(self):
        # 先贴已有局部版块的边界，再考虑其间的空位。
        points = {(0, 0), (self.width + 1, 0), (0, self.height + 1)}
        points.update((x, y) for y in range(0, min(54, self.height + 1), 7)
                      for x in range(0, min(54, self.width + 1), 7))
        return points

    def add(self, piece, x, y):
        body = {(a + x, b + y, z) for a, b, z in piece.cells}
        halo = {(a + dx, b + dy, z) for a, b, z in body for dx, dy in ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0))
                if 0 <= a + dx < _SIZE and 0 <= b + dy < _SIZE}
        self.entries.extend({**entry, "X": entry["X"] + x, "Y": entry["Y"] + y} for entry in piece.entries)
        self.cells.update(body)
        self.blocked |= _mask(halo)
        self.width, self.height = max(self.width, x + piece.width), max(self.height, y + piece.height)


def _fit(bin_, variants):
    candidates = []
    for piece in variants:
        for x, y in bin_.origins():
            width, height = max(bin_.width, x + piece.width), max(bin_.height, y + piece.height)
            if width > 54 or height > 54:
                continue
            score = ((width + 25) // 20) * ((height + 25) // 20), width * height, max(width, height)
            candidates.append((score, piece.turns, y, x, piece))
    for score, _, y, x, piece in sorted(candidates):
        if not bin_.blocked & (piece.mask << (y * _SIZE + x)):
            return score, piece, x, y
    return None


def _finish(bin_):
    base = {"$type": "Building", "BinaryVersion": 1137}
    variants = tuple(_variants(bin_.entries))
    assert len(variants[0].cells) == len(bin_.cells)
    for foundation in _FOUNDATIONS:
        ground = platform_ground(foundation)
        width, length = FOUNDATION_CHUNKS[foundation]
        for piece in variants:
            if piece.width > 20 * width - 6 or piece.height > 20 * length - 6:
                continue
            left, top = 3 - 20 * ((width - 1) // 2), 3 - 20 * ((length - 1) // 2)
            assert all((x + left, y + top) in ground for x, y, _ in piece.cells)
            entries = [{**e, "X": e["X"] + left, "Y": e["Y"] + top} for e in piece.entries]
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
        width, height = FOUNDATION_CHUNKS[foundation]
        ground = platform_ground(foundation)
        for x in range(old_x - 1 + (width - 1) // 2, old_x + 3 - width + (width - 1) // 2):
            for y in range(old_y - 1 + (height - 1) // 2, old_y + 3 - height + (height - 1) // 2):
                dx = delta[0] + TILE_SIZE * (old_x - x)
                dy = delta[1] + TILE_SIZE * (old_y - y)
                if all((u + dx, v + dy) in ground for u, v in plane):
                    buildings = [{**e, "X": e["X"] + dx, "Y": e["Y"] + dy} for e in tight]
                    return {**board, "T": foundation, "X": x, "Y": y, "B": {**board["B"], "Entries": buildings}}
    return board


def _fits_ground(board):
    ground = platform_ground(board["T"])
    return all((x, y) in ground for body in _cells(board["B"]["Entries"]) for x, y, _ in body)


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


def compact_platforms(platforms, threshold, *, baseline=None):
    untouched, sparse = [], []
    before = []
    original = platforms if baseline is None else baseline
    for index, platform in enumerate(platforms):
        entries = platform["B"]["Entries"]
        cells = _cells(entries)
        count = sum(map(len, cells)) if cells is not None else 0
        capacity = 3 * len(platform_ground(platform["T"]))
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
        tight = _contract(entries)
        variants = tuple(_variants(tight))
        if max(variants[0].width, variants[0].height) > 54:
            untouched.append((platform, count))
            continue
        sparse.append((variants, count, index))
    sparse.sort(key=lambda item: (-item[0][0].width * item[0][0].height, -item[1], item[2]))
    bins = []
    for variants, _, _ in sparse:
        best = None
        # 只看最近的箱，限制大分册的布局时间。
        for bin_ in reversed(bins[-8:]):
            fit = _fit(bin_, variants)
            if fit is not None and (best is None or fit[0] < best[0][0]):
                best = fit, bin_
        if best is None:
            bin_ = _Bin([], set())
            bins.append(bin_)
            fit = _fit(bin_, variants)
            if fit is None:
                raise ValueError("稀疏板无法摆入空的 3×3 平台")
        else:
            fit, bin_ = best
        _, piece, x, y = fit
        bin_.add(piece, x, y)
    packed = [*untouched, *map(_finish, bins)]
    after = [(count, 3 * len(platform_ground(board["T"]))) for board, count in packed]
    return [p for p, _ in packed], before, after
