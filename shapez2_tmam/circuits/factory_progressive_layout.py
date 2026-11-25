"""按已接通的母线逐个摆放器件，并在原占地内寻找更小的平台。"""

import argparse
from collections import Counter, defaultdict
from copy import copy
from itertools import product
import logging
from pathlib import Path

from ..mari.blueprint import DIRECTIONS, _kind
from .compile_factory_v1 import _footprint, _measure_placement
from .compiler_backend import _write_blueprint
from .compiler_backend._snapshot_router import _join
from .compiler_backend.prefix_scan_wiring import _native_island
from .export_wiring_review import _building_cells
from .factory_dense_layout import _RADIOS, _SHORT, _candidate, _island_offsets, _netlist, _place, _route_buses, _verify
from .factory_link_audit import audit
from .factory_unicast_wiring import _pairs
from .foundations import FOUNDATION_CHUNKS, TILE_SIZE, platform_ground, platform_interior
from .wired_module import _Board


_TRIALS = 8
_LOG = logging.getLogger(__name__)


def _clone(board):
    trial = copy(board)
    trial.occupied = board.occupied.copy()
    trial.entries = board.entries.copy()
    trial.terminals = defaultdict(set, {key: sites.copy() for key, sites in board.terminals.items()})
    trial.traces = defaultdict(dict, {site: {net: sides.copy() for net, sides in nets.items()}
                                     for site, nets in board.traces.items()})
    return trial


def _tracks(board):
    tracks = defaultdict(set)
    for site, nets in board.traces.items():
        if len(nets) == 1:
            net = next(iter(nets))
            tracks[net].add(site)
    return tracks


def _distance(site, target):
    x, y, z = site
    a, b, c = target
    return abs(x - a) + abs(y - b) + 4 * abs(z - c)


def _sites(part, board, tracks):
    if _kind(part.entry) in _RADIOS:
        turn = 2 if _kind(part.entry) == "ControlledSignalTransmitter" else 0
        for column in range(4):
            for y in range(2, board.height - 2, 4):
                yield 1 + 6 * column, y, 0, turn
        return
    nets = {net for ports in part.ports for net, _ in ports if net in tracks}
    points = set().union(*(tracks[net] for net in nets))
    sites = points | {(x, y, z) for x, y, z in product(
        range(2, board.width - 1, 3), range(2, board.height - 1, 3), range(3))
        if board.on_ground(x, y)}
    for x, y, z in sorted(sites):
        if (x, y, z) not in board.occupied:
            for turn in range(4):
                yield x, y, z, turn


def _open_tap(board, net, sites):
    def free(pad):
        return (board.on_ground(*pad[:2]) and pad not in board.occupied
                and not board.traces.get(pad, {}).keys() - {net} and pad not in sites)

    for x, y, z in sites:
        for dx, dy in DIRECTIONS:
            a, b = x + dx, y + dy
            if not free((a, b, z)):
                continue
            if any((a + u, b + v) != (x, y) and free((a + u, b + v, z)) for u, v in DIRECTIONS):
                return True
            if any(free((a, b, level)) and any(free((a + u, b + v, level)) for u, v in DIRECTIONS)
                   for level in (z - 1, z + 1) if 0 <= level < 3):
                return True
    return False


def _clear_routes(board):
    base = _clone(board)
    base.entries = [entry for entry in base.entries if not _kind(entry).startswith(("Wire1Up", "Wire2Up"))]
    base.occupied.clear()
    for entry in base.entries:
        body = _building_cells(entry, _kind(entry))
        if body is None:
            raise ValueError(f"缺少建筑占地定义 {entry['T']}")
        base.occupied.update((x - board.origin_x, y - board.origin_y, z) for x, y, z in body)
    base.traces.clear()
    for (net, _), sites in base.terminals.items():
        for x, y, z in sites:
            sides = {side for side in board.traces[x, y, z][net]
                     if (x + DIRECTIONS[side][0], y + DIRECTIONS[side][1], z) in base.occupied}
            if not sides:
                raise ValueError(f"信号 {net} 的已放端口没有建筑")
            base.traces[x, y, z][net] = sides
    return base


def _connect_part(board, part, used, tracks, preferred_level, remaining, origin):
    candidates, distances = [], {}
    radio = _kind(part.entry) in _RADIOS
    for site in _sites(part, board, tracks):
        center = site[:3]
        direct = None
        if center in board.traces:
            nets = board.traces[center]
            if len(nets) != 1:
                continue
            net, sides = next(iter(nets.items()))
            if remaining[net] != 0 or len(sides) != 1 or tracks[net] != {center}:
                continue
            direct = net, next(iter(sides))
        trial = _candidate(board, part, site, used, direct=direct)
        if trial is None:
            continue
        pads = trial[2]
        length = 0
        for pad, (net, _) in pads.items():
            if net in tracks:
                key = net, pad
                if key not in distances:
                    distances[key] = min(_distance(pad, tap) for tap in tracks[net])
                length += distances[key]
        x, y, z, _ = site
        if radio:
            rank = (x, length, y)
        else:
            level_gap = abs(z - preferred_level)
            drift = abs(x - origin[0]) + abs(y - origin[1])
            rank = (2 * length + drift + 3 * level_gap, level_gap, drift)
        candidates.append((rank, site, trial, direct))
    best = None
    failed_nets = Counter()
    bands = Counter()
    candidate_order = []
    for rank, site, trial, direct in sorted(candidates):
        x, y, z, _ = site
        band = x // 3, y // 3, z
        bias = bands[band] * 12
        bands[band] += 1
        key = (rank[0], rank[1] + bias, rank[2]) if radio else (rank[0] + bias, rank[1], rank[2])
        candidate_order.append((key, site, rank, trial, direct))
    candidate_order.sort()
    for tried, (_, site, rank, trial, direct) in enumerate(candidate_order[:3 * _TRIALS], 1):
        if tried > _TRIALS and best is not None:
            break
        attempt = _clone(board)
        if direct is not None:
            center = site[:3]
            del attempt.traces[center]
            attempt.terminals[direct[0], site[2]].discard(center)
        _place(attempt, trial)
        device = attempt.entries[len(board.entries)]
        attached = [(pad, net) for pad, (net, _) in trial[2].items() if net in tracks]
        attached.sort(key=lambda item: distances[item[1], item[0]], reverse=True)
        for pad, net in attached:
            if not _join(attempt, net, pad, tracks[net], direct=True):
                failed_nets[net] += 1
                break
        else:
            fresh = _tracks(attempt)
            if any(len(sites) <= 3 and remaining[net] > 0 and not _open_tap(attempt, net, sites)
                   for net, sites in fresh.items()):
                continue
            added = len(attempt.traces) - len(board.traces) + len(attempt.entries) - len(board.entries)
            score = (rank[0] if radio else 0, added, rank)
            if best is None or score < best[0]:
                best = score, attempt, device
            if added <= len(trial[2]) + len(trial[3]) + 1:
                break
    if best is None:
        base = _clear_routes(board)
        for _, site, _, _, direct in candidate_order[:2]:
            trial = _candidate(base, part, site, used, direct=direct)
            if trial is None:
                continue
            attempt = _clone(base)
            if direct is not None:
                del attempt.traces[site[:3]]
                attempt.terminals[direct[0], site[2]].discard(site[:3])
            _place(attempt, trial)
            device = attempt.entries[len(base.entries)]
            try:
                _route_buses(attempt, prefer_short=True, direct=True)
            except ValueError:
                continue
            # finish 会把线路实体加入占格，回到可增量接线的形式。
            attempt.entries = [entry for entry in attempt.entries
                               if _kind(entry) in _SHORT or not _kind(entry).startswith("Wire")
                               or _kind(entry).startswith(("Wire1Up", "Wire2Up"))]
            attempt.occupied.difference_update(attempt.traces)
            return attempt, device
    if best is None:
        raise ValueError(f"器件 {part.index}（{_kind(part.entry)}）试摆 {min(len(candidates), 3 * _TRIALS)} 处均未接通，"
                         f"失败母线与接入点数 {[(net, count, len(tracks[net])) for net, count in failed_nets.items()]}")
    return best[1], best[2]


def _groups(parts, nets, anchors):
    by_index = {part.index: part for part in parts}
    by_net = defaultdict(set)
    for index, ports in nets.items():
        for net in ports:
            by_net[net].add(index)
    buses = {net for net, users in by_net.items() if len(users) >= 5}
    todo = set(by_index)
    groups = []
    while todo:
        group = []
        frontier = [min(todo)]
        todo.remove(frontier[0])
        anchor_count = 0
        while frontier:
            index = frontier.pop()
            group.append(by_index[index])
            anchor_count += len(nets[index] & anchors)
            for net in nets[index] - buses:
                attached = by_net[net] & todo
                todo.difference_update(attached)
                frontier.extend(sorted(attached))
        groups.append((-anchor_count, len(group), min(p.index for p in group), group))
    return [group for _, _, _, group in sorted(groups, key=lambda row: row[:3])]


def _layout(netlist, platform, first_level, *, keep_ports):
    wiring, parts, used, replaced = netlist
    foundation = platform["T"]
    board = _Board(foundation=foundation)
    board.ground = platform_interior(foundation)
    notches = platform_ground(foundation) - board.ground
    old = wiring.platforms[0]
    dx, dy = (TILE_SIZE * (old.get(key, 0) - platform.get(key, 0)) for key in ("X", "Y"))
    reindex, pending = {}, []
    for part in parts:
        kind = _kind(part.entry)
        if kind not in _SHORT:
            pending.append(part)
            continue
        x, y, z = part.origin
        x, y = x + dx, y + dy
        if (x, y) not in notches:
            raise ValueError("平台边界无法保留原飞线端口")
        turn = part.entry.get("R", 0)
        sends = kind == "WireTransmitterSender"
        side = (turn + 2 * sends) % 4
        net, _ = part.ports[int(sends)][0]
        board.entries.append({**part.entry, "X": x, "Y": y})
        reindex[part.index] = id(board.entries[-1])
        board.occupied.add((x - board.origin_x, y - board.origin_y, z))
        board.pin(net, x - board.origin_x, y - board.origin_y, z, side)
    nets = {part.index: {net for ports in part.ports for net, _ in ports if net in used} for part in pending}
    fanout = Counter(net for values in nets.values() for net in values)
    remaining = fanout.copy()
    for lane, group in enumerate(_groups(pending, nets, _tracks(board).keys())):
        level = (first_level + lane) % 3
        while group:
            tracks = _tracks(board)

            def priority(part):
                ports = nets[part.index]
                kind = _kind(part.entry)
                role = 2 if kind == "ControlledSignalReceiver" else int(kind not in _RADIOS)
                inputs = {net for net, _ in part.ports[1] if net in used}
                return (role, -len(inputs - tracks.keys()), len(ports & tracks.keys()),
                        -part.index, sum(fanout[net] for net in ports))

            failures = []
            for part in sorted(group, key=priority, reverse=True)[:4]:
                left = remaining.copy()
                left.subtract(nets[part.index])
                try:
                    x, y, _ = part.origin
                    region = x + dx - board.origin_x, y + dy - board.origin_y
                    placed = _connect_part(board, part, used, tracks, level, left, region)
                except ValueError as error:
                    failures.append(str(error))
                    continue
                group.remove(part)
                placed, device = placed
                reindex[part.index] = id(device)
                board, remaining = placed, left
                if len(reindex) % 12 == 0:
                    _LOG.debug("%s 已摆放并接线 %d/%d 个器件", foundation, len(reindex), len(parts))
                break
            else:
                raise ValueError(" / ".join(failures))
    result = board.finish()["Entries"][0]
    indices = {id(entry): i for i, entry in enumerate(result["B"]["Entries"])}
    _verify(wiring, result, {i: indices[entry] for i, entry in reindex.items()}, replaced, keep_ports=keep_ports)
    return {**platform, "B": result["B"]}


def _foundations(original):
    occupied = {(x, y) for x, y, _ in _footprint(original)}
    candidates = []
    for kind in FOUNDATION_CHUNKS:
        offsets = _island_offsets(kind)
        a, b = min(offsets)
        for x, y in occupied:
            origin = x - a, y - b
            if {(origin[0] + u, origin[1] + v) for u, v in offsets} <= occupied:
                candidates.append((len(offsets), {**original, "T": kind, "X": origin[0], "Y": origin[1]}))
    return [p for _, p in sorted(candidates, key=lambda item: (item[0], item[1]["T"], item[1]["Y"], item[1]["X"]))]


def repack_board(original, *, keep_size=False):
    netlist = _netlist([original])
    keep_ports = netlist is None
    if keep_ports:
        netlist = _netlist([original], keep_ports=True)
    if netlist is None:
        raise ValueError("平台含无法重布线的建筑")
    radios = sum(_kind(part.entry) in _RADIOS for part in netlist[1])
    fixed_ports = any(_kind(part.entry) in _SHORT for part in netlist[1])
    tried = set()
    failure = "无线口和逻辑门超出当前占地"
    candidates = (original,) if keep_size else _foundations(original)
    for candidate in candidates:
        foundation = candidate["T"]
        if not fixed_ports and foundation in tried:
            continue
        tried.add(foundation)
        width, height = FOUNDATION_CHUNKS[foundation]
        if radios > min(4, (TILE_SIZE * width - 6) // 6 + 1) * len(range(2, TILE_SIZE * height - 8, 4)):
            continue
        if 28 * radios + len(netlist[1]) - radios > 3 * len(platform_interior(foundation)):
            continue
        try:
            return _layout(netlist, candidate, 1, keep_ports=keep_ports)
        except ValueError as error:
            failure = str(error)
    raise ValueError(f"平台无法逐个摆放并接线：{failure}")


def _world_pairs(platforms):
    def world(site):
        i, x, y, z, turn = site
        p = platforms[i]
        return i, p.get("X", 0) * TILE_SIZE + x, p.get("Y", 0) * TILE_SIZE + y, p.get("Z", 0), z, turn

    return {(world(rx), world(tx)) for rx, tx in _pairs(platforms) if rx[0] != tx[0]}


def main() -> int:
    parser = argparse.ArgumentParser(description="从已有接线逐个试摆器件并缩减平台")
    parser.add_argument("source", type=Path, help="原生 .spz2bp 蓝图")
    parser.add_argument("--board", type=int, nargs="+", required=True, help="待重布的平台编号，从 1 开始")
    parser.add_argument("--keep-size", action="store_true", help="在原平台轮廓内试摆，跳过缩板搜索")
    parser.add_argument("--output", type=Path, required=True, help="候选蓝图输出路径")
    args = parser.parse_args()
    try:
        if args.source.resolve() == args.output.resolve():
            raise ValueError("候选蓝图须使用独立输出路径")
        island = _native_island(args.source)
        before = [{"X": 0, "Y": 0, "Z": 0, **board} for board in island["Entries"]]
        after = list(before)
        for i in dict.fromkeys(args.board):
            if not 1 <= i <= len(before):
                raise ValueError(f"平台编号 {i} 不在 1～{len(before)} 内")
            try:
                after[i - 1] = repack_board(before[i - 1], keep_size=args.keep_size)
            except ValueError as error:
                raise ValueError(f"平台 {i}：{error}") from error
        if _world_pairs(before) != _world_pairs(after):
            raise ValueError("重布前后的飞线配对不一致")
        xs, ys, _ = zip(*set().union(*map(_footprint, after)))
        placement = _measure_placement(after, {"电路": len(after)}, xs, ys)
        report = {"before": audit(before), "after": audit(after), "placement": placement,
                  "buildings_before": sum(len(p["B"]["Entries"]) for p in before),
                  "buildings_after": sum(len(p["B"]["Entries"]) for p in after),
                  "island_tiles_before": sum(map(len, map(_footprint, before))),
                  "island_tiles_after": sum(map(len, map(_footprint, after)))}
        _write_blueprint({"V": island["BinaryVersion"], "BP": {**island, "Entries": after}}, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
