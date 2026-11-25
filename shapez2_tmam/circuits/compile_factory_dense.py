"""分批重布原生整厂电路，保留各块电路的原生端口关系。"""

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from itertools import chain, combinations, product

from ..mari.blueprint import Wiring, _kind
from .circuit import encode_document
from .compile_factory_v1 import _check_short_pairs, _footprint, _groups, _measure_placement
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.prefix_scan_wiring import _native_island, _report
from .factory_dense_layout import SHORT_PAIR_CAPACITY, _SHORT, compact_native_board, compact_short_pair, fuse_native_boards
from .foundations import FOUNDATION_CHUNKS, foundation_tiles


def _eligible(board):
    return board["T"] != "Foundation_1x1" and not any(_kind(e) in _SHORT for e in board["B"]["Entries"])


def _radio_delta(before, after):
    old_rx, old_tx = _radio_channels(before)
    new_rx, new_tx = _radio_channels(after)
    if old_tx != new_tx or old_rx.keys() != new_rx.keys() or not new_rx <= old_rx:
        raise ValueError("重布后无线频道接口发生变化")
    return sum(new_rx.values()) - sum(old_rx.values())


def _compact_singles(platforms, attempted, count, workers):
    choices = [i for i, board in enumerate(platforms) if i not in attempted and _eligible(board)]
    choices.sort(key=lambda i: len(platforms[i]["B"]["Entries"]) / len(_footprint(platforms[i])))
    choices = choices[:count]
    changed = receiver_delta = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = pool.map(compact_native_board, (platforms[i] for i in choices))
        for i, new in zip(choices, results, strict=True):
            attempted.add(i)
            old = platforms[i]
            if new["T"] == old["T"]:
                continue
            board = {**old, "T": new["T"], "B": new["B"]}
            if _footprint(board) < _footprint(old):
                receiver_delta += _radio_delta(Wiring({"Entries": [old]}), Wiring({"Entries": [board]}))
                platforms[i] = board
                changed += 1
    return changed, receiver_delta


def _merge_singles(boards):
    area = sum(len(_footprint(board)) for board in boards)
    kinds = [kind for kind in FOUNDATION_CHUNKS if len(foundation_tiles(kind)) < area]
    return fuse_native_boards(boards, kinds)


def _merge_site(board, originals, occupied, bounds):
    offsets = _footprint(board)
    xs, ys, zs = bounds
    anchors = sorted(originals, key=lambda p: -len(_footprint(p)))
    original_sites = ((p["X"], p["Y"], p["Z"]) for p in anchors)
    other_sites = ((x, y, z) for z, y, x in product(zs, ys, xs))
    for x, y, z in chain(original_sites, other_sites):
        tiles = {(x + dx, y + dy, z + dz) for dx, dy, dz in offsets}
        if tiles.isdisjoint(occupied) and all(a in xs and b in ys and c in zs for a, b, c in tiles):
            return {**anchors[0], **board, "X": x, "Y": y, "Z": z}, tiles
    return None


def _compact_detached(platforms, parts, attempted, count, workers):
    choices = []
    footprints = tuple(map(_footprint, platforms))
    areas = list(map(len, footprints))
    occupied = set().union(*footprints)
    bounds = tuple(range(min(axis), max(axis) + 1) for axis in zip(*occupied, strict=True))
    costs = [len(board["B"]["Entries"]) for board in platforms]
    start = 0
    for name, size in parts.items():
        eligible = [i for i in range(start, start + size) if i not in attempted
                    and areas[i] >= 3 and _eligible(platforms[i])]
        inputs = {}
        for i in eligible:
            rx, tx = _radio_channels(Wiring({"Entries": [platforms[i]]}))
            inputs[i] = set(rx)
            costs[i] += 26 * (rx.total() + tx.total())
        for a, b in combinations(eligible, 2):
            shared = len(inputs[a] & inputs[b])
            estimated = costs[a] + costs[b] - 27 * shared
            choices.append((estimated / max(areas[a], areas[b]), -shared, estimated, name, a, b))
        start += size
    ranked = sorted(choices)
    choices, used = [], set()
    for _, _, _, name, a, b in ranked:
        if a in used or b in used:
            continue
        choices.append((name, a, b))
        used.update((a, b))
        if len(choices) == count:
            break
    retired = set()
    rebuilt = set()
    receiver_delta = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        groups = ([platforms[a], platforms[b]] for _, a, b in choices)
        for (name, a, b), board in zip(choices, pool.map(_merge_singles, groups), strict=True):
            attempted.update((a, b))
            if board is None:
                continue
            old = [platforms[a], platforms[b]]
            cleared = footprints[a] | footprints[b]
            occupied.difference_update(cleared)
            placed = _merge_site(board, old, occupied, bounds)
            if placed is None:
                occupied.update(cleared)
                continue
            platforms[a], tiles = placed
            occupied.update(tiles)
            receiver_delta += _radio_delta(Wiring({"Entries": old}), Wiring({"Entries": [platforms[a]]}))
            rebuilt.add(a)
            retired.add(b)
            parts[name] -= 1
    return retired, rebuilt, receiver_delta


def _compact_pairs(wiring, platforms, attempted, count, workers):
    pairs = {id(wiring.entries[rx][1]): id(wiring.entries[tx][1]) for rx, tx in wiring.short_ports.items()}
    links = [(wiring.entries[rx][0], wiring.entries[tx][0]) for rx, tx in wiring.short_ports.items()]
    outgoing = Counter(links)
    choices = []
    for group in _groups(len(platforms), links):
        if len(group) != 2 or any(i in attempted for i in group):
            continue
        west, east = sorted(group, key=lambda i: platforms[i]["X"])
        a, b = platforms[west], platforms[east]
        wire_count = outgoing[east, west] + outgoing[west, east]
        if (any(p["T"] != "Foundation_3x3" or p.get("R", 0) for p in (a, b))
                or b["X"] - a["X"] != 3 or any(a[k] != b[k] for k in ("Y", "Z"))
                or not 0 < wire_count <= SHORT_PAIR_CAPACITY):
            continue
        choices.append((west, east))
    choices.sort(key=lambda pair: (outgoing[pair] + outgoing[pair[::-1]],
                                   sum(len(platforms[i]["B"]["Entries"]) for i in pair)))
    choices = choices[:count]
    changed = receiver_delta = 0
    if choices:
        print(f"重布 {len(choices)} 组相邻双板", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for group, result in zip(choices, pool.map(compact_short_pair,
                                                  ([platforms[i] for i in group] for group in choices)), strict=True):
            attempted.update(group)
            if result is None:
                continue
            original = [platforms[i] for i in group]
            if not set.union(*(map(_footprint, result))) < set.union(*(map(_footprint, original))):
                continue
            before_ports = Wiring({"Entries": original})
            after_ports = Wiring({"Entries": result})
            receiver_delta += _radio_delta(before_ports, after_ports)
            for rx, tx in before_ports.short_ports.items():
                del pairs[id(before_ports.entries[rx][1])]
            pairs.update({id(after_ports.entries[rx][1]): id(after_ports.entries[tx][1])
                          for rx, tx in after_ports.short_ports.items()})
            for i, board in zip(group, result, strict=True):
                platforms[i] = board
            changed += 1
    return pairs, changed, receiver_delta, len(choices)


def _short_wiring(platforms):
    boards = [{**board, "B": {"Entries": [entry for entry in board["B"]["Entries"] if _kind(entry) in _SHORT]}}
              for board in platforms]
    return Wiring({"Entries": boards})


def build(source: Path, *, count: int, workers: int, mode: str = "single", rounds: int = 1) -> tuple[dict, dict]:
    island = _native_island(source)
    report = _report(source)
    platforms = list(island["Entries"])
    wiring = _short_wiring(platforms)
    history = report.get("dense_layout", {})
    attempted = set(history.get("attempted", ()))
    pair_attempts = set(history.get("pair_attempted", ()))
    merge_attempts = set(history.get("merge_channel_attempted", ()))
    pairs = {id(wiring.entries[rx][1]): id(wiring.entries[tx][1]) for rx, tx in wiring.short_ports.items()}
    changed = receiver_delta = pair_count = 0
    for round_index in range(rounds):
        before = len(attempted), len(pair_attempts), len(merge_attempts)
        if mode == "pairs":
            if round_index:
                wiring = _short_wiring(platforms)
            pairs, updates, delta, tried = _compact_pairs(wiring, platforms, pair_attempts, count, workers)
            pair_count += tried
        elif mode == "merge":
            retired, rebuilt, delta = _compact_detached(platforms, report["parts"], merge_attempts, count, workers)
            updates = len(retired)
            kept = [i for i in range(len(platforms)) if i not in retired]
            attempted = {j for j, i in enumerate(kept) if i in attempted and i not in rebuilt}
            pair_attempts = {j for j, i in enumerate(kept) if i in pair_attempts}
            merge_attempts = {j for j, i in enumerate(kept) if i in merge_attempts}
            platforms = [platforms[i] for i in kept]
        else:
            updates, delta = _compact_singles(platforms, attempted, count, workers)
        if before == (len(attempted), len(pair_attempts), len(merge_attempts)) and not updates:
            break
        changed += updates
        receiver_delta += delta
        if rounds > 1:
            area = sum(len(_footprint(board)) for board in platforms)
            print(f"第 {round_index + 1} 轮缩小 {updates} 处，当前 {area} 岛格", flush=True)
    document = {"V": 1137, "BP": {**island, "Entries": platforms}}
    buildings = _check_short_pairs(platforms, pairs)
    footprints = tuple(map(_footprint, platforms))
    tiles = set().union(*footprints)
    if len(tiles) != sum(map(len, footprints)):
        raise ValueError("重布线后平台占地重叠")
    xs, ys, zs = (set(axis) for axis in zip(*tiles, strict=True))
    report["occupancy"].update(_measure_placement(platforms, report["parts"], xs, ys))
    sizes = {}
    for board in platforms:
        sizes[board["T"]] = sizes.get(board["T"], 0) + 1
    report.update(island_cells=len(tiles), platforms=len(platforms), platform_sizes=sizes, building_entries=buildings,
                  short_range_links=len(pairs), global_receivers=report["global_receivers"] + receiver_delta,
                  footprint_chunks=[max(xs) - min(xs) + 1, max(ys) - min(ys) + 1], island_levels=sorted(zs),
                  dense_layout={"attempted": sorted(attempted), "changed": changed,
                                "remaining": sum(i not in attempted and _eligible(b) for i, b in enumerate(platforms)),
                                "pair_attempted": sorted(pair_attempts),
                                "merge_channel_attempted": sorted(merge_attempts),
                                "pair_groups_tried": pair_count})
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="重布整厂电路，输出缩板结果与实际岛格数")
    parser.add_argument("source", type=Path, help="原生整厂蓝图及其同名接口表")
    parser.add_argument("--count", type=int, default=24, help="本批最多尝试的单板或双板组数")
    parser.add_argument("--workers", type=int, default=6, help="并行布线进程数")
    parser.add_argument("--rounds", type=int, default=1, help="在内存中连续布线的轮数，末轮后统一验线并导出")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pairs", action="store_const", dest="mode", const="pairs", help="重布相邻双板，保留跨板飞线")
    mode.add_argument("--merge", action="store_const", dest="mode", const="merge", help="合并同一部件内的独立板")
    parser.set_defaults(mode="single")
    parser.add_argument("--output", type=Path, required=True, help="输出原生 .spz2bp 文件")
    args = parser.parse_args()
    if min(args.rounds, args.count) < 1 or not 1 <= args.workers <= 16 or args.output.suffix != ".spz2bp":
        parser.error("轮数和每批数量须为正，并行进程数须为 1 至 16，输出须使用 .spz2bp 后缀")
    if args.source.resolve() == args.output.resolve():
        parser.error("请为重布结果指定单独的输出路径")
    try:
        document, report = build(args.source, count=args.count, workers=args.workers, mode=args.mode, rounds=args.rounds)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document, format_version=5), encoding="utf-8")
        args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    unit = "块平台" if args.mode == "single" else "组双板"
    print(f"缩小 {report['dense_layout']['changed']} {unit}，总占地 {report['island_cells']} 岛格")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
