"""把已核对时序的同岛层单播从无线改接短距端口。"""

import argparse
from collections import defaultdict
from dataclasses import replace
from itertools import product
from pathlib import Path

from ..mari.blueprint import DIRECTIONS, PORTS, _kind
from .compile_factory_dense import _short_wiring
from .compile_factory_v1 import _footprint
from .compiler_backend import _write_blueprint
from .compiler_backend._snapshot_router import _join as _route_to
from .compiler_backend.prefix_scan_wiring import _native_island
from .compiler_frontend.pin_candidate_closure import _radio_ports
from .export_wiring_review import _building_cells
from .factory_dense_layout import _SHORT, _netlist, _place_on, _verify
from .factory_link_audit import audit
from .foundations import TILE_SIZE, platform_ground, platform_interior
from .wired_module import _Board


_FLAT_WIRES = {"WireBridge", "WireCross", "WireForward", "WireJunction", "WireLeft"}


def _offset(board):
    return board.get("X", 0) * TILE_SIZE, board.get("Y", 0) * TILE_SIZE


def _slot(entry):
    return entry["X"], entry["Y"], entry.get("L", 0), entry.get("R", 0)


def _pairs(platforms):
    wiring = _short_wiring(platforms)
    sites = [(i, *_slot(entry)) for i, entry in wiring.entries]
    return {(sites[rx], sites[tx]) for rx, tx in wiring.short_ports.items()}


def _adjacent(footprint):
    return {(x + dx, y + dy, z) for x, y, z in footprint for dx, dy in DIRECTIONS} - footprint


def _join(platforms, link_groups, pairs):
    footprints = list(map(_footprint, platforms))
    occupied = set().union(*footprints)
    x0, y0, _ = map(min, zip(*occupied))
    x1, y1, _ = map(max, zip(*occupied))
    fixed = {site[0] for pair in pairs for site in pair}
    moved = {}
    for a, b in link_groups:
        if not _adjacent(footprints[a]) & footprints[b]:
            candidates = []
            for i, j in ((b, a), (a, b)):
                if i in fixed:
                    continue
                empty = occupied - footprints[i]
                local = footprints[i]
                offsets = {(x - u, y - v) for x, y, z in _adjacent(footprints[j]) for u, v, _ in local}
                for dx, dy in offsets:
                    tiles = {(x + dx, y + dy, z) for x, y, z in local}
                    if tiles.isdisjoint(empty) and all(x0 <= x <= x1 and y0 <= y <= y1 for x, y, _ in tiles):
                        candidates.append((abs(dx) + abs(dy), i, dx, dy))
            if not candidates:
                raise ValueError(f"第 {a + 1}、{b + 1} 块平台在当前外框内无法平移到相邻位置")
            _, i, dx, dy = min(candidates)
            board = platforms[i]
            platforms[i] = {**board, "X": board.get("X", 0) + dx, "Y": board.get("Y", 0) + dy}
            occupied.difference_update(footprints[i])
            footprints[i] = _footprint(platforms[i])
            occupied.update(footprints[i])
            moved[i + 1] = dx, dy
        fixed.update((a, b))
    return moved


def _notches(board, occupied):
    ground = platform_interior(board["T"])
    return {(x, y, z) for (x, y), z in product(platform_ground(board["T"]) - ground, range(3))
            if (x, y, z) not in occupied}


def _edge(source, target, used_source, used_target, origins):
    ax, ay = _offset(source)
    bx, by = _offset(target)
    available = _notches(target, used_target)
    choices = []
    for x, y, z in _notches(source, used_source):
        for turn, (dx, dy) in enumerate(DIRECTIONS):
            u, v = x + ax - bx + 5 * dx, y + ay - by + 5 * dy
            if ((u, v, z) not in available or (x - dx, y - dy) not in platform_interior(source["T"])
                    or (u + dx, v + dy) not in platform_interior(target["T"])):
                continue
            first, second = (x, y, z, turn), (u, v, z, turn)
            cost = sum(abs(value - previous) for site, origin in zip((first, second), origins, strict=True)
                       for value, previous in zip(site[:3], origin, strict=True))
            choices.append((cost, first, second))
    if not choices:
        raise ValueError("相邻两板没有可用的相对飞线端口")
    _, first, second = min(choices)
    return first, second


def _graft(platform, wiring, endpoints):
    board = _Board(foundation=platform["T"])
    board.ground = platform_interior(platform["T"])
    reindex, mapping, targets = {}, {}, defaultdict(set)
    discarded = set(endpoints)
    for index in endpoints:
        source = wiring._direct_sources(index, 0)
        if len(source) != 1:
            continue
        config, _ = source[0]
        node = wiring._find(wiring.pins[index][1][0])
        if sum(wiring._find(p) == node for _, inputs, _ in wiring.pins.values() for p in inputs) == 1:
            discarded.add(config)
    for index, (_, entry) in enumerate(wiring.entries):
        if index in discarded:
            continue
        kind = _kind(entry)
        x, y, z, turn = _slot(entry)
        if kind in _FLAT_WIRES:
            site = x - board.origin_x, y - board.origin_y, z
            for (side, _, _, _), node in zip(PORTS[kind][2], wiring.pins[index][2], strict=True):
                net = wiring._find(node)
                board.traces[site].setdefault(net, set()).add((side + turn) % 4)
            if len(board.traces[site]) == 1:
                targets[next(iter(board.traces[site]))].add(site)
        else:
            body = _building_cells(entry, kind)
            if body is None:
                raise ValueError(f"建筑 {kind} 缺少占地定义")
            board.occupied.update((a - board.origin_x, b - board.origin_y, level) for a, b, level in body)
            reindex[index] = len(board.entries)
            board.entries.append(entry)
    pending = []
    for index, (sends, slot) in endpoints.items():
        x, y, z, turn = slot
        net = wiring._find(wiring.pins[index][1][1] if sends else wiring.pins[index][0][0])
        kind = "WireTransmitterSender" if sends else "WireTransmitterReceiver"
        mapping[index] = (1,) if sends else ()
        reindex[index] = len(board.entries)
        board.entries.append({"T": kind + "InternalVariant", "X": x, "Y": y, "L": z, "R": turn})
        x, y = x - board.origin_x, y - board.origin_y
        board.occupied.add((x, y, z))
        side = (turn + 2 * sends) % 4
        dx, dy = DIRECTIONS[side]
        board.pin(net, x, y, z, side)
        pending.append((net, (x + dx, y + dy, z)))
    for net, site in pending:
        if not targets[net] or not _route_to(board, net, site, targets[net], direct=True):
            raise ValueError("原板的信号母线无法接到飞线端口")
    new = board.finish()["Entries"][0]
    _verify(wiring, new, reindex, {}, keep_ports=True, input_ports=mapping)
    return new


def _convert(netlist, endpoints):
    mapping = {}
    wiring, parts, used, replaced = netlist
    updated, slots = [], []
    for part in parts:
        if part.index in endpoints:
            outgoing, slot = endpoints[part.index]
            kind = "WireTransmitterSender" if outgoing else "WireTransmitterReceiver"
            outputs, inputs = part.ports
            if outgoing:
                net, _ = inputs[1]
                if net is None:
                    raise ValueError("飞线发送端没有可接线的信号来源")
            mapping[part.index] = (1,) if outgoing else ()
            ports = ((), (inputs[1],)) if outgoing else (outputs, ())
            part = replace(part, entry={"T": kind + "InternalVariant"}, ports=ports)
            slots.append(slot)
        elif _kind(part.entry) in _SHORT:
            slots.append(_slot(part.entry))
        updated.append(part)
    return (wiring, updated, used, replaced), slots, mapping


def wire_unicast(platforms, channels):
    """按调用方确认过时序的频道列表排板并重布线，保留原有飞线配对。"""
    if not channels or len(channels) != len(set(channels)):
        raise ValueError("请选择至少一个频道，且频道不能重复")
    before = audit(platforms)
    links = before["one_to_one_global_links"]
    eligible = {row["channel"]: (row["sender_board"] - 1, row["receiver_board"] - 1)
                for row in (*links["adjacent_boards"], *links["separated_boards"])}
    if missing := sorted(set(channels) - eligible.keys()):
        raise ValueError(f"这些频道并非跨板同岛层的一发一收：{missing}")
    platforms = list(platforms)
    expected = _pairs(platforms)
    groups = dict.fromkeys(tuple(sorted(eligible[ch])) for ch in channels)
    moved = _join(platforms, groups, expected)
    boards = sorted({i for group in groups for i in group})
    netlists, endpoints, radios, occupied = {}, defaultdict(dict), {}, {}
    for i in boards:
        platform = platforms[i]
        netlist = _netlist([platform], keep_ports=True, merge_receivers=False)
        if netlist is None:
            raise ValueError(f"第 {i + 1} 块平台含无法重布线的建筑")
        netlists[i] = netlist
        radios[i] = {(sends, channel): index for index, sends, channel, _ in _radio_ports(netlist[0], by_entry=True)}
        occupied[i] = {p.origin for p in netlist[1] if _kind(p.entry) in _SHORT}
    added = []
    for ch in channels:
        a, b = eligible[ch]
        tx, rx = radios[a][True, ch], radios[b][False, ch]
        origins = tuple(netlists[i][0].sites[index][1:] for i, index in ((a, tx), (b, rx)))
        first, second = _edge(platforms[a], platforms[b], occupied[a], occupied[b], origins)
        for i, index, sends, slot in ((a, tx, True, first), (b, rx, False, second)):
            endpoints[i][index] = sends, slot
            occupied[i].add(slot[:3])
        expected.add(((b, *second), (a, *first)))
        added.append({"channel": ch, "sender_board": a + 1, "sender_slot": first,
                      "receiver_board": b + 1, "receiver_slot": second})
    result = list(platforms)
    for i in boards:
        base = platforms[i]
        choices, failures = [], []
        try:
            choices.append(_graft(base, netlists[i][0], endpoints[i]))
        except ValueError as error:
            failures.append(str(error))
        netlist, slots, mapping = _convert(netlists[i], endpoints[i])
        layouts = () if choices and moved else ((4, True, True), (4, False, True), (5, False, False))
        for pitch, stagger, prefer_short in layouts:
            try:
                choices.append(_place_on(netlist, base["T"], pitch, edge_slots=slots, stagger=stagger,
                                         prefer_short=prefer_short, input_ports=mapping))
            except ValueError as error:
                failures.append(str(error))
                if choices:
                    break
            else:
                break
        if not choices:
            raise ValueError(f"第 {i + 1} 块平台重新布线失败：{' / '.join(failures)}")
        best = min(choices, key=lambda board: len(board["B"]["Entries"]))
        result[i] = {**base, "B": best["B"]}
    if _pairs(result) != expected:
        raise ValueError("重新解码后，短距端口的实际配对与预期不符")
    after = audit(result)
    if (after["global_radio_count"] != before["global_radio_count"] - 2 * len(channels)
            or after["same_island_layer_one_to_one"] != before["same_island_layer_one_to_one"] - len(channels)):
        raise ValueError("重新解码后，无线端口的数量与预期不符")
    return result, {"moved_boards": moved, "flywires": added, "audit": after,
                    "buildings_before": sum(len(p["B"]["Entries"]) for p in platforms),
                    "buildings_after": sum(len(p["B"]["Entries"]) for p in result)}


def main() -> int:
    parser = argparse.ArgumentParser(description="把已核对时序的跨板同岛层单播排成相邻板并接飞线")
    parser.add_argument("source", type=Path, help="原生 .spz2bp 蓝图")
    parser.add_argument("--channel", type=int, nargs="+", required=True, help="已核对改接时序的频道")
    parser.add_argument("--output", type=Path, required=True, help="候选蓝图输出路径")
    args = parser.parse_args()
    try:
        if args.source.resolve() == args.output.resolve():
            raise ValueError("候选蓝图须使用独立输出路径")
        island = _native_island(args.source)
        platforms, report = wire_unicast(island["Entries"], args.channel)
        island["Entries"] = platforms
        _write_blueprint({"V": island["BinaryVersion"], "BP": island}, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
