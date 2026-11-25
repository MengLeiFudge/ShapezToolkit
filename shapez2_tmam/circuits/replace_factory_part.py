"""在已压缩的整厂电路里替换一个全局信号接口部件。"""

import argparse
import json
from collections import Counter
from itertools import product
from pathlib import Path

from ..mari.blueprint import Wiring, _kind
from .circuit import encode_document
from .compile_factory_dense import _compact_singles, _short_wiring
from .compile_factory_v1 import _check_short_pairs, _footprint, _groups, _measure_placement
from .compiler_backend.prefix_scan_wiring import _native_island, _report
from .compiler_frontend.pin_candidate_closure import _radio_ports
from .factory_circuit_packing import compact_platforms, shrink_short_groups


def _pairs(wiring):
    return {id(wiring.entries[rx][1]): id(wiring.entries[tx][1]) for rx, tx in wiring.short_ports.items()}


def _links(wiring):
    return [(wiring.entries[rx][0], wiring.entries[tx][0]) for rx, tx in wiring.short_ports.items()]


def _live_entries(wiring, transmitters):
    pending = list(transmitters)
    kept, nets = set(), set()
    while pending:
        index = pending.pop()
        if index in kept:
            continue
        kept.add(index)
        if _kind(wiring.entries[index][1]) == "WireTransmitterReceiver":
            pending.append(wiring.short_ports[index])
        for pin in wiring.pins[index][1]:
            net = wiring._find(pin)
            if net not in nets:
                nets.add(net)
                pending.extend(source for source, _ in wiring.drivers[net])
    kept.update(i for i, (_, _, pins) in wiring.pins.items() if any(wiring._find(pin) in nets for pin in pins))
    return kept


def _check_retained_inputs(before, boards):
    after = Wiring({"Entries": boards})
    old_indices = {id(entry): i for i, (_, entry) in enumerate(before.entries)}
    for i, (_, entry) in enumerate(after.entries):
        if not after.pins[i][1]:
            continue
        old = old_indices[id(entry)]
        for port in range(len(after.pins[i][1])):
            drivers = {(old_indices[id(after.entries[source][1])], pin)
                       for source, pin in after._direct_sources(i, port)}
            if drivers != set(before._direct_sources(old, port)):
                raise ValueError("替换部件改变了共用平台上保留建筑的输入驱动")


def _strip_part(boards, old_ports, public):
    wiring = _short_wiring(boards)
    kept, receivers, senders, removed = {}, Counter(), Counter(), Counter()
    pairs = {}
    for group in _groups(len(boards), _links(wiring)):
        original = [boards[i] for i in group]
        local = Wiring({"Entries": original})
        ports = tuple(_radio_ports(local, by_entry=True))
        retired = {i for i, tx, ch, _ in ports if tx and ch in old_ports}
        remaining = {i for i, tx, _, _ in ports if tx} - retired
        if retired:
            if any(_kind(entry) == "WireGlobalTransmitterReceiver" for _, entry in local.entries):
                raise ValueError("共用平台有无法静态判定方向的全局收发器")
            removed.update(ch for i, tx, ch, _ in ports if i in retired)
            active = _live_entries(local, remaining)
            if retired & active:
                raise ValueError("待替换的发射器被保留电路直接依赖")
            entries = [[] for _ in group]
            for i, (pi, entry) in enumerate(local.entries):
                if i in active:
                    entries[pi].append(entry)
            retained = {i: {**board, "B": {**board["B"], "Entries": es}}
                        for i, board, es in zip(group, original, entries, strict=True) if es}
            if retained:
                _check_retained_inputs(local, list(retained.values()))
            live_ports = [port for port in ports if port[0] in active]
            for rx, tx in local.short_ports.items():
                if rx in active:
                    pairs[id(local.entries[rx][1])] = id(local.entries[tx][1])
        else:
            retained = dict(zip(group, original, strict=True))
            live_ports = ports
            pairs.update(_pairs(local))
        kept.update(retained)
        receivers.update(ch for _, tx, ch, _ in live_ports if not tx)
        senders.update(ch for _, tx, ch, _ in live_ports if tx)
    if removed != Counter(old_ports):
        raise ValueError(f"原部件发射频道不一致，缺少 {sorted(old_ports - removed.keys())}")
    if private := receivers.keys() & (old_ports - public):
        raise ValueError(f"这些原部件内部频道仍被保留电路使用 {sorted(private)}")
    return kept, receivers, senders, pairs


def _pack_part(wiring, occupied):
    boards = wiring.platforms
    links = _links(wiring)
    groups = list(_groups(len(boards), links))
    shrunk = shrink_short_groups(boards, groups, 100)
    packed, _, _ = compact_platforms(shrunk, 100, baseline=boards)
    moved = {}
    for i in {i for group in links for i in group}:
        old, new = ([e for e in b["B"]["Entries"] if _kind(e).startswith("WireTransmitter")]
                    for b in (boards[i], shrunk[i]))
        moved.update((id(a), id(b)) for a, b in zip(old, new, strict=True))
    pairs = {moved.get(rx, rx): moved.get(tx, tx) for rx, tx in _pairs(wiring).items()}
    indices = {id(board): i for i, board in enumerate(packed)}
    links = [(indices[id(shrunk[a])], indices[id(shrunk[b])]) for a, b in links]
    footprints = tuple(map(_footprint, packed))
    groups = list(_groups(len(packed), links))
    groups.sort(key=lambda g: -sum(len(footprints[i]) for i in g))
    x0, y0, z0 = map(min, zip(*occupied, strict=True))
    x1, y1, z1 = map(max, zip(*occupied, strict=True))
    for group in groups:
        tiles = set.union(*(footprints[i] for i in group))
        base_x, base_y, base_z = map(min, zip(*tiles, strict=True))
        local = {(x - base_x, y - base_y, z - base_z) for x, y, z in tiles}
        w, h, levels = map(max, zip(*local, strict=True))
        sites = product(range(y0, y1 + 1), range(x0, x1 - w + 1), range(z0, z1 - levels + 1))
        for y, x, z in sites:
            shifted = {(a + x, b + y, c + z) for a, b, c in local}
            if shifted.isdisjoint(occupied):
                break
        else:
            raise ValueError("现有整厂外框内放不下替换部件")
        occupied.update(shifted)
        y1 = max(y1, y + h)
        for i in group:
            board = packed[i]
            packed[i] = {**board, "X": board.get("X", 0) + x - base_x,
                         "Y": board.get("Y", 0) + y - base_y, "Z": board.get("Z", 0) + z - base_z}
    _check_short_pairs(packed, pairs)
    return packed, pairs


def _channels(fields):
    if isinstance(fields, dict):
        return set().union(*map(_channels, fields.values()))
    if isinstance(fields, list):
        return set().union(*map(_channels, fields))
    return {fields}


def build(source: Path, previous: Path, replacement: Path, name: str):
    island, report = _native_island(source), _report(source)
    old, new = (Wiring(_native_island(path)) for path in (previous, replacement))
    old_ports, new_ports = (tuple(_radio_ports(wiring)) for wiring in (old, new))
    old_tx, new_tx = ({ch for _, tx, ch, _ in ports if tx} for ports in (old_ports, new_ports))
    old_api, new_api = _report(previous), _report(replacement)
    public = _channels(old_api["outputs"])
    if (old_api["inputs"] != new_api["inputs"] or old_api["outputs"] != new_api["outputs"]
            or not public <= old_tx & new_tx or name not in report["parts"]):
        raise ValueError("新旧部件接口不一致，或整厂没有指定部件")
    kept, receivers, senders, pairs = _strip_part(island["Entries"], old_tx, public)
    retained = list(kept.values())
    tiles = set.union(*map(_footprint, retained))
    added, new_pairs = _pack_part(new, tiles)
    packed_ports = tuple(_radio_ports(Wiring({"Entries": added})))
    if Counter((tx, ch) for _, tx, ch, _ in new_ports) != Counter((tx, ch) for _, tx, ch, _ in packed_ports):
        raise ValueError("替换部件压缩后收发频道发生变化")
    receivers.update(ch for _, tx, ch, _ in packed_ports if not tx)
    senders.update(ch for _, tx, ch, _ in packed_ports if tx)
    if (any(count != 1 for count in senders.values())
            or receivers.keys() - senders.keys() != set(report["external_inputs"])):
        raise ValueError("替换后发射频道冲突或整厂输入变化")
    names = (part for part, count in report["parts"].items() for _ in range(count))
    parts = {part: [] for part in report["parts"]}
    for i, part in enumerate(names):
        if i in kept:
            parts[part].append(kept[i])
    parts[name].extend(added)
    platforms = [board for group in parts.values() for board in group]
    counts = {part: len(group) for part, group in parts.items() if group}
    unchanged = {id(board) for board in island["Entries"]}
    attempted = {i for i, board in enumerate(platforms) if id(board) in unchanged}
    changed = len(platforms) - len(attempted)
    island_cells = sum(len(_footprint(board)) for board in added)
    print(f"替换部件占 {island_cells} 岛格，正在重布 {changed} 块受影响平台", flush=True)
    smaller, receiver_delta = _compact_singles(platforms, attempted, changed, 6)
    print(f"局部重布缩小 {smaller} 块平台，开始核对整图", flush=True)
    footprints = tuple(map(_footprint, platforms))
    tiles = set.union(*footprints)
    area = len(tiles)
    if area != sum(map(len, footprints)):
        raise ValueError("局部重布后平台占地重叠")
    buildings = _check_short_pairs(platforms, pairs | new_pairs)
    cost = (area, buildings)
    if cost >= (report["island_cells"], report["building_entries"]) or len(platforms) > report["platforms"]:
        raise ValueError(f"替换后使用 {area} 岛格和 {len(platforms)} 块平台，整厂未缩小")
    xs, ys, zs = map(set, zip(*tiles, strict=True))
    report.pop("dense_layout", None)
    report["occupancy"].update(_measure_placement(platforms, counts, xs, ys))
    report.update(parts=counts, island_cells=area, platforms=len(platforms), building_entries=buildings,
                  platform_sizes=dict(Counter(board["T"] for board in platforms)),
                  footprint_chunks=[max(xs) - min(xs) + 1, max(ys) - min(ys) + 1], island_levels=sorted(zs),
                  short_range_links=len(pairs | new_pairs), global_receivers=receivers.total() + receiver_delta,
                  global_transmitters=senders.total())
    return {"V": 1137, "BP": {**island, "Entries": platforms}}, report


def main() -> int:
    parser = argparse.ArgumentParser(description="替换整厂的一个电路部件，局部缩板并保留其他部件的布局")
    for name in ("source", "previous", "replacement"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--part", required=True, help="整厂接口表中的部件名称")
    parser.add_argument("--output", type=Path, required=True, help="新的 .spz2bp 蓝图路径")
    args = parser.parse_args()
    if args.output.suffix != ".spz2bp" or args.output.resolve() in {
            p.resolve() for p in (args.source, args.previous, args.replacement)}:
        parser.error("请指定一份新的 .spz2bp 蓝图路径")
    try:
        document, report = build(args.source, args.previous, args.replacement, args.part)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document, format_version=5), encoding="utf-8")
        args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(f"替换后整厂占 {report['island_cells']} 岛格、{report['building_entries']} 个建筑")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
