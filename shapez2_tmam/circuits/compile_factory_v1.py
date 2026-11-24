"""生成首版四象限五层整厂的共用求解电路。"""

import argparse
import json
from collections import Counter, defaultdict
from math import isqrt
from pathlib import Path

from ..mari.blueprint import Wiring, _kind
from .circuit import constant, encode_document
from .compile_root_search import build_direct
from .compiler_backend.module_caller import _compare, _gate, _local_wiring
from .compiler_backend.prefix_scan_wiring import _native_wiring
from .factory_assembly.interface import FIELDS, LOADED, OPERATOR_INPUTS, ORDER_INPUTS, PACKET_TAG, WRITE_RESET, WRITE_STATUS
from .export_wiring_review import _building_cells
from .factory_circuit_packing import _SHORT, compact_platforms, shrink_short_groups
from .foundations import TILE_SIZE, foundation_origin, foundation_tiles, platform_ground, platform_interior
from .compiler_frontend.pin_candidate_closure import _radio_ports
from .local_module import Module


_CIRCUITS = Path(__file__).resolve().parent
_BOOK = _CIRCUITS.parent / "blueprints/验收/电路"
_TAIL_CLOSURE = 1705370
_TAIL_COUNT = 1705371
_REMAINING = 1703740
_TAIL_RELAYS = {1704800: 1705331, 1704801: 1705332,
                **dict(zip(range(1704304, 1704309), range(1703513, 1703518), strict=True))}


def _rewrite(wiring, receivers, transmitters, aliases=None):
    found = (set(), set())
    counts = (Counter(), Counter())
    configs = {}
    maps = (receivers, transmitters)
    for _, sends, channel, config in _radio_ports(wiring):
        output = maps[sends].get(channel, channel)
        if not sends and aliases is not None:
            output = aliases.get(output, output)
        if configs.setdefault(id(config), (config, output))[1] != output:
            raise ValueError(f"共用频道常量 {channel} 对应不同接点")
        found[sends].add(channel)
        counts[sends][output] += 1
    absent = tuple(mapping.keys() - seen for mapping, seen in zip(maps, found, strict=True))
    if any(absent):
        raise ValueError(f"合装需要重接的端口未找到 {absent}")
    for config, output in configs.values():
        config["C"] = constant(output)
    return counts


def _root_closure():
    board = Module({"direct": 1704676, "tail": 1704678, "tail_run": _TAIL_CLOSURE})
    searching = _gate(board, "And", "searching", "tail", "tail_run")
    running = _gate(board, "Or", "running", "direct", searching)
    for name, channel in (("mode", 1703001), ("top", 1703002)):
        _gate(board, "If", name, 0, "direct")
        _gate(board, "If", name, 1, searching)
        board.outputs[name] = channel
    board.outputs[running] = 1703000
    return board


def _successful_path(retain_leaf):
    board = Module({"direct_capture": 1704677, "tail_capture": 1705336,
                    "direct_replay": 1704687, "tail_replay": 1705341, "frame_count": _TAIL_COUNT})
    capture = _gate(board, "Or", "capture", "direct_capture", "tail_capture")
    replay = _gate(board, "Or", "replay", "direct_replay", "tail_replay")
    _gate(board, "If", "count", 0, "direct_replay")
    _gate(board, "If", "count", "frame_count", "tail_replay")
    board.outputs = {replay: 1702850, "count": 1704000}
    if retain_leaf:
        board.inputs["chosen"] = 1703004
        board.outputs[_gate(board, "And", "ready", capture, "chosen")] = 1704602
    else:
        board.outputs[capture] = 1704601
    return board


def _retain_tail_leaf(wiring):
    channels = set(range(1705330, 1705335))
    outputs = defaultdict(set)
    for platform, sends, channel, _ in _radio_ports(wiring):
        if sends:
            outputs[platform].add(channel)
    matches = [platform for platform, ports in outputs.items() if ports == channels]
    if len(matches) != 1:
        raise ValueError("尾部调度缺少独立的候选启停板")
    index, = matches
    board = Module({"phase": 1705301, "enable": 1705300})
    solved = _compare(board, "solved", "phase", 14)
    through = _compare(board, "before_pop", "phase", 10, "BQ==")
    for name, lower, channel in (("stack", 2, 1705331), ("pin", 5, 1705333)):
        reached = _compare(board, f"{name}_entered", "phase", lower, "Ag==")
        searching = _gate(board, "And", f"{name}_searching", reached, through)
        active = _gate(board, "Or", f"{name}_active", searching, solved)
        board.outputs[_gate(board, "And", name, active, "enable")] = channel
    for name, phase, channel in (("preflight", 1, 1705330), ("stack_reject", 3, 1705332)):
        active = _compare(board, f"is_{name}", "phase", phase)
        board.outputs[_gate(board, "And", name, active, "enable")] = channel
    missed = _gate(board, "Or", "missed", _compare(board, "skip", "phase", 6),
                   _compare(board, "resume", "phase", 7))
    board.outputs[_gate(board, "And", "proof_missed", missed, "enable")] = 1705334
    new, = board.layout()["BP"]["Entries"]
    old = wiring.platforms[index]
    platforms = [*wiring.platforms]
    platforms[index] = {**old, "B": new["B"]}
    return _local_wiring({"Entries": platforms})


def _leaf_and_reject():
    board = Module({"missed": 1705334, "order": 1704673})
    board.outputs = {"missed": 1703304, _gate(board, "If", "without_proof", 0, "missed"): 1703305,
                     "order": 1705358}
    return board


def _remaining():
    board = Module({"budget": 1704672, "depth": 1705344})
    for depth in range(3):
        here = _compare(board, f"depth{depth}", "depth", depth)
        for budget in range(depth + 1, 4):
            amount = _compare(board, f"budget{depth}_{budget}", "budget", budget)
            selected = _gate(board, "And", f"use{depth}_{budget}", here, amount)
            _gate(board, "If", "remaining", budget - depth - 1, selected)
    board.outputs = {"remaining": _REMAINING}
    return board


def _ports(pairs):
    board = Module({f"input{i}": source for i, (source, _) in enumerate(pairs)})
    board.outputs = {f"input{i}": destination for i, (_, destination) in enumerate(pairs)}
    return board


def _status():
    board = Module({"ready": 1702854, "exhausted": 1705342, "unknown": 1704679, "invalid": 1704680,
                    "root_fault": 1704681, "tail_fault": 1705343, "replay_fault": 1702853,
                    "support_fault": 1705230, "enable": 1704673})
    fault = _gate(board, "Or", "root_or_tail", "root_fault", "tail_fault")
    fault = _gate(board, "Or", "faults", fault, _gate(board, "Or", "hardware", "replay_fault", "support_fault"))
    terminal = _gate(board, "Or", "done", "ready", "exhausted")
    terminal = _gate(board, "Or", "terminal", terminal, _gate(board, "Or", "invalid_order", "unknown", "invalid"))
    running = _gate(board, "And", "running", "enable", _gate(board, "Not", "searching", terminal))
    _gate(board, "If", "state", 0, running)
    for code, pin in enumerate(("ready", "exhausted", "unknown", "invalid"), 1):
        _gate(board, "If", "state", code, pin)
    _gate(board, "If", "status", "state", _gate(board, "Not", "healthy", fault))
    _gate(board, "If", "status", 5, fault)
    board.outputs = {"status": 1705399}
    return board


def _footprint(platform):
    if platform.get("R", 0):
        raise ValueError("整厂合装需要未旋转的平台部件")
    dx, dy = foundation_origin(platform["T"])
    x = platform.get("X", 0) + dx
    y = platform.get("Y", 0) + dy
    z = platform.get("Z", 0)
    return {(x + dx, y + dy, z) for dx, dy in foundation_tiles(platform["T"])}


def _groups(board_count, short_pairs):
    parent = list(range(board_count))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for a, b in short_pairs:
        parent[root(b)] = root(a)
    groups = defaultdict(list)
    for i in range(board_count):
        groups[root(i)].append(i)
    return groups.values()


def _place_platforms(platforms, short_pairs, leaf):
    # 有飞线的板一起平移。叶端和批次门控保持已审阅的三岛层位置关系。
    pairs = list(short_pairs)
    pairs.extend(zip(leaf, leaf[1:]))
    groups = []
    footprints = tuple(map(_footprint, platforms))
    for indices in _groups(len(platforms), pairs):
        tiles = set.union(*(footprints[i] for i in indices))
        x0, y0, z0 = (min(tile[d] for tile in tiles) for d in range(3))
        width, height, levels = (max(tile[d] for tile in tiles) - base + 1
                                 for d, base in enumerate((x0, y0, z0)))
        if levels > 3 or sum(len(footprints[i]) for i in indices) != len(tiles):
            raise ValueError("同一飞线组的平台重叠或超过三个岛层")
        slots = {(x - x0, y - y0, z - z0) for x, y, z in tiles}
        groups.append((indices, (x0, y0, z0), slots, width, height, levels))
    groups.sort(key=lambda group: (-len(group[2]), group[0][0]))
    span = max(3 + isqrt(sum(len(group[2]) for group in groups) // 3),
               max(max(g[3], g[4]) for g in groups))
    occupied = [0, 0, 0]
    rows = 0
    for indices, (x0, y0, z0), slots, width, height, levels in groups:
        edge = (1 << (span - width + 1)) - 1
        origins = sum(edge << (row * span) for row in range(rows + 1))
        offsets = [(y * span + x, layer) for x, y, layer in slots]
        choices = []
        for z in range(4 - levels):
            available = origins
            for offset, layer in offsets:
                available &= ~(occupied[z + layer] >> offset)
            if available:
                choices.append(((available & -available).bit_length() - 1, z))
        origin, z = min(choices)
        y, x = divmod(origin, span)
        for offset, layer in offsets:
            occupied[z + layer] |= 1 << (origin + offset)
        rows = max(rows, y + height)
        for i in indices:
            p = platforms[i]
            p.update(X=p.get("X", 0) + x - x0, Y=p.get("Y", 0) + y - y0, Z=p.get("Z", 0) + z - 1 - z0)


def _check_short_pairs(platforms, expected):
    # 平移整板保留板内线路。只需从合装坐标重新推导板间配对。
    ports = []
    indices = []
    count = 0
    for platform in platforms:
        entries = platform["B"]["Entries"]
        short = []
        for entry in entries:
            if _kind(entry) in ("WireTransmitterSender", "WireTransmitterReceiver"):
                indices.append(id(entry))
                short.append(entry)
        ports.append({**platform, "B": {"Entries": short}})
        count += len(entries)
    actual = Wiring({"Entries": ports}).short_ports
    if {indices[rx]: indices[tx] for rx, tx in actual.items()} != expected:
        raise ValueError("整厂合装改变了原生飞线配对")
    return count


def _measure_placement(platforms, counts, xs, ys):
    left, top = min(xs) * TILE_SIZE, min(ys) * TILE_SIZE
    layout, used = defaultdict(int), defaultdict(int)
    records = []
    for i, (name, board) in enumerate(zip((p for p, n in counts.items() for _ in range(n)), platforms, strict=True), 1):
        foundation = board["T"]
        ground = platform_ground(foundation)
        interior = platform_interior(foundation)
        notches = ground - interior
        occupied = set()
        radio = 0
        for entry in board["B"]["Entries"]:
            kind = _kind(entry)
            body = _building_cells(entry, kind)
            if body is None:
                raise ValueError(f"平台 {i} 的建筑 {kind} 缺少占地定义")
            allowed = notches if kind in _SHORT else interior
            for x, y, z in body:
                pos = x, y, z
                if (x, y) not in allowed or not 0 <= z < 3 or pos in occupied:
                    raise ValueError(f"平台 {i} ({name}) 的 {kind} 在 {pos} 越界、占用缺口或重叠")
                occupied.add(pos)
                radio += kind in ("ControlledSignalReceiver", "ControlledSignalTransmitter", "WireGlobalTransmitterReceiver")
        dx, dy = board["X"] * TILE_SIZE - left, board["Y"] * TILE_SIZE - top
        for x, y in ground:
            layout[y + dy] |= 1 << (x + dx)
        projection = {(x, y) for x, y, _ in occupied}
        for x, y in projection:
            used[y + dy] |= 1 << (x + dx)
        capacity = 3 * len(ground)
        records.append({"platform": i, "part": name, "foundation": foundation,
                        "position": [board[k] for k in ("X", "Y", "Z")],
                        "occupied_cells": len(occupied), "buildable_cells": capacity,
                        "percent": round(100 * len(occupied) / capacity, 2),
                        "projected_cells": len(projection), "radio_cells": radio,
                        "radio_percent": round(100 * radio / capacity, 2),
                        "radio_percent_of_occupied": round(100 * radio / len(occupied), 2) if occupied else 0})
    projected, available = (sum(map(int.bit_count, rows.values())) for rows in (used, layout))
    capacity = sum(r["buildable_cells"] for r in records)
    area = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1) * TILE_SIZE ** 2
    radio = sum(r["radio_cells"] for r in records)
    occupied = sum(r["occupied_cells"] for r in records)
    radio_order = sorted(records, key=lambda r: -r["radio_cells"] / r["buildable_cells"])
    radio_over_limit = [r for r in radio_order if 10 * r["radio_cells"] >= r["buildable_cells"]]
    return {"top_projected_cells": projected, "top_buildable_cells": available,
            "top_percent": round(100 * projected / available, 2),
            "top_outline_percent": round(100 * projected / area, 2),
            "platform_top_percent": round(300 * sum(r["projected_cells"] for r in records) / capacity, 2),
            "radio_cells": radio, "radio_percent": round(100 * radio / capacity, 2),
            "radio_percent_of_occupied": round(100 * radio / occupied, 2),
            "platforms_at_or_above_10_percent_radio": len(radio_over_limit),
            "sparsest_platforms": sorted(records, key=lambda r: r["occupied_cells"] / r["buildable_cells"])[:20],
            "highest_radio_platforms": radio_order[:20], "radio_over_limit": radio_over_limit}


def build(pieces: Path | None = None, *, direct_root: Path | None = None, density_threshold: int = 60,
          retain_leaf: bool = False) -> tuple[dict, dict]:
    if retain_leaf and (pieces is not None or direct_root is not None):
        raise ValueError("保留闭包结果时需要从项目分册重建根订单和尾部调度")
    parts = (
        ("direct-root", {1704676: 1703000}, {1704601: 1705375, 1702850: 1705376,
                                             1703001: 1705377, 1703002: 1705378, 1704000: 1705379,
                                             1704201: 1705355}),
        ("tail-search", {1705300: 1704678, 1705307: 1705001, 1705311: 1704602}, {}),
        ("tail-frames-control", {1705300: 1704678, 1705357: 1702288}, {1704000: _TAIL_COUNT}),
        ("search-checkpoint", {}, {}),
        ("tail-search-workers", {}, {}),
        ("tail-node-inputs", {}, {}),
        ("pin-column-sample", {}, {}),
        ("pin-row-reader", dict(zip(range(1701200, 1701205), range(1703513, 1703518), strict=True)), {}),
        ("pin-rows-prefetch", {}, {}),
        ("pin-layer-search", {1703300: 1705333}, {1703000: _TAIL_CLOSURE, 1703001: 1705380, 1703002: 1705381}),
        ("pin-cap-plan", {1703300: 1705333}, {}),
        ("pin-cap-crystals", {}, {}),
        ("pin-landings", {}, {}),
    )
    folder = pieces or _BOOK / "顶针逆推"
    locations = {"tail-search-workers": _CIRCUITS / "compiler_backend", "tail-node-inputs": _CIRCUITS / "compiler_frontend"}
    if direct_root is None and pieces is None:
        direct_root = folder / "direct-root-stacked.spz2bp"
    counts, platforms, pairs = {}, [], {}
    received, sent = Counter(), Counter()
    leaf = []
    board_links = []
    before, after = [], []
    for name, receivers, transmitters in parts:
        source = folder if pieces else locations.get(name, folder)
        if retain_leaf and name == "direct-root":
            document, _ = build_direct(_BOOK / "原层读取/read-five-rows.spz2bp", folder / "dual-source-closure.spz2bp",
                                       _BOOK / "配方回放/success-path.spz2bp", 4096, retain_leaf=True)
            wiring = _local_wiring(document["BP"])
            transmitters = {**transmitters, 1704602: transmitters[1704601]}
            del transmitters[1704601]
        else:
            path = direct_root if name == "direct-root" and direct_root is not None else source / f"{name}.spz2bp"
            wiring = _native_wiring(path)
            if retain_leaf and name == "tail-search":
                wiring = _retain_tail_leaf(wiring)
        base = len(platforms)
        rx, tx = _rewrite(wiring, receivers, transmitters, _TAIL_RELAYS if retain_leaf else None)
        received.update(rx)
        sent.update(tx)
        boards = wiring.platforms
        leaf_boards = [p for p in boards if name == "direct-root" and p["T"] in ("Foundation_1x1", "Foundation_1x2")]
        links = [(wiring.entries[rx][0], wiring.entries[tx][0]) for rx, tx in wiring.short_ports.items()]
        groups = _groups(len(boards), links)
        shrunk = shrink_short_groups(boards, groups, density_threshold)
        packed, old_usage, new_usage = compact_platforms(shrunk, density_threshold, baseline=boards)
        before.extend(old_usage)
        after.extend(new_usage)
        index = {id(board): base + i for i, board in enumerate(packed)}
        leaf.extend(index[id(board)] for board in leaf_boards)
        moved = {}
        for a in {i for pair in links for i in pair}:
            if shrunk[a] is not boards[a]:
                old, new = ([e for e in board["B"]["Entries"] if _kind(e).startswith("WireTransmitter")]
                            for board in (boards[a], shrunk[a]))
                moved.update((id(p), id(q)) for p, q in zip(old, new, strict=True))
        for input_port, output_port in wiring.short_ports.items():
            a, port_a = wiring.entries[input_port]
            b, port_b = wiring.entries[output_port]
            pairs[moved.get(id(port_a), id(port_a))] = moved.get(id(port_b), id(port_b))
            board_links.append((index[id(shrunk[a])], index[id(shrunk[b])]))
        counts[name] = len(packed)
        platforms.extend(packed)
    controls = (_root_closure(), _successful_path(retain_leaf), _leaf_and_reject(), _remaining())
    if retain_leaf:
        controls += (_status(),)
    else:
        controls += (_ports(tuple(zip(range(1703513, 1703518), range(1704304, 1704309), strict=True))),
                     _status(), _ports(((1705331, 1704800), (1705332, 1704801))))
    control_boards = []
    for board in controls:
        wiring = _local_wiring(board.layout()["BP"])
        rx, tx = _rewrite(wiring, {}, {})
        received.update(rx)
        sent.update(tx)
        control_boards.extend(wiring.platforms)
    packed, old_usage, new_usage = compact_platforms(control_boards, density_threshold)
    before.extend(old_usage)
    after.extend(new_usage)
    counts["controls"] = len(packed)
    platforms.extend(packed)
    _place_platforms(platforms, board_links, leaf)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    buildings = _check_short_pairs(platforms, pairs)
    duplicates = sorted(channel for channel, count in sent.items() if count != 1)
    if duplicates:
        raise ValueError(f"整厂电路重复发射频道 {duplicates}")
    # 支撑扫描空地址运行。单层候选的独立回放口留空，由主控二次回放全路径。
    order = {"target": ORDER_INPUTS["target"], "enable": 1704673, "feed_request": 1702851}
    shop_replies = {name: WRITE_STATUS[name] for name in ("address", "request", "ack")}
    shop_replies.update(reset=WRITE_RESET, loaded=LOADED, clean=OPERATOR_INPUTS["clean_confirmed"])
    shop_commands = {"run": OPERATOR_INPUTS["run"], "feed": OPERATOR_INPUTS["enable_feed"],
                     **{name: channel for name, channel in ORDER_INPUTS.items() if name != "target"},
                     "tag": PACKET_TAG, **FIELDS}
    inputs = {*order.values(), *shop_replies.values()}
    open_ports = {1702250, 1703306, 1703307, 1704430, 1704431, 1704432}
    external = received.keys() - sent.keys()
    if external != inputs | open_ports:
        raise ValueError(f"整厂收发接口不符，缺少 {sorted((inputs | open_ports) - external)}，额外 {sorted(external - inputs - open_ports)}")
    outputs = {"status": 1705399, "root_phase": 1704674, "tail_phase": 1705301, "tail_depth": 1705344,
               "recipe_length": shop_commands["length"], "feed": shop_commands["feed"]}
    missing = set(outputs.values()) | set(shop_commands.values())
    if missing := missing - sent.keys():
        raise ValueError(f"整厂缺少配方或状态输出 {sorted(missing)}")
    footprints = list(map(_footprint, platforms))
    tiles = set.union(*footprints)
    if len(tiles) != sum(map(len, footprints)):
        raise ValueError("整厂电路平台占地重叠")
    xs, ys, zs = (set(coords) for coords in zip(*tiles, strict=True))
    usage = {}
    for label, rows in (("before", before), ("after", after)):
        used, capacity = map(sum, zip(*rows, strict=True))
        usage[label] = {"occupied_cells": used, "buildable_cells": capacity, "percent": round(100 * used / capacity, 2),
                        "below_5_percent": sum(20 * a < b for a, b in rows),
                        "below_10_percent": sum(10 * a < b for a, b in rows)}
    usage.update(_measure_placement(platforms, counts, xs, ys))
    return document, {"inputs": order, "outputs": outputs, "occupancy": usage,
                      "factory": {"receives": shop_commands, "sends": shop_replies},
                      "status": {0: "计算中", 1: "配方已写入", 2: "不可制作", 3: "未着色晶体供料未定",
                                 4: "空目标", 5: "内部核对失败"},
                      "parts": counts, "external_inputs": sorted(external), "unused_inputs": sorted(open_ports),
                      "platforms": len(platforms), "island_cells": len(tiles),
                      "platform_sizes": dict(Counter(board["T"] for board in platforms)),
                      "footprint_chunks": [max(xs) - min(xs) + 1, max(ys) - min(ys) + 1],
                      "island_levels": sorted(zs), "short_range_links": len(pairs),
                      "building_entries": buildings, "global_transmitters": len(sent),
                      "global_receivers": sum(received.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description="从分册原生部件导出首版整厂电路")
    parser.add_argument("pieces", nargs="?", type=Path, help="覆盖项目分册，使用指定目录中的部件")
    parser.add_argument("--direct-root", type=Path, help="替换目录内的直接路线蓝图，例如三岛层叶端版")
    parser.add_argument("--density-threshold", type=int, default=60, choices=range(0, 101), metavar="0–100",
                        help="参与压缩的最大空间利用率，默认 60%%")
    parser.add_argument("--retain-leaf", action="store_true", help="复用闭包已选字段，省去叶端锁存板，供原生验收")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图路径")
    args = parser.parse_args()
    try:
        if args.output.suffix != ".spz2bp":
            raise ValueError("蓝图输出路径须使用 .spz2bp 后缀")
        document, report = build(args.pieces, direct_root=args.direct_root, density_threshold=args.density_threshold,
                                 retain_leaf=args.retain_leaf)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document, format_version=5), encoding="utf-8")
        args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
