"""合并自动前缀闭包的行编码参数板，以短距口接入原双板编码器。"""

import argparse
from collections import Counter
from pathlib import Path

from ...mari.blueprint import _kind
from ...mari.ports import PORTS
from ..circuit import Circuit, Literal
from . import _write_blueprint
from ._layout import _EdgeLinks, _layout_platform
from .module_caller import _local_wiring
from .prefix_row_flywire import _port, _radio, _wire_path
from .prefix_scan_wiring import _native_wiring, _report


_ARGUMENTS = {"row": 1701240, "below": 1701241, "ground": 1701242}
_PHASE = 1701251
_ROWS = tuple(range(1701204, 1701199, -1))
_EDGE_ROWS = (-12, -11, 8)
_RECEIVER_ROWS = (-12, -7, -2)
_ROW_CLUSTER = (10, 4, 0)


def _parameters():
    circuit = Circuit()
    phase = circuit.add("ControlledSignalReceiver", Literal(_PHASE))
    rows = tuple(circuit.add("ControlledSignalReceiver", Literal(ch)) for ch in _ROWS)
    arguments = [[] for _ in _ARGUMENTS]
    for i, row in enumerate(rows):
        start = circuit.add("LogicGateCompare", phase, Literal(3 * i + 1), config="Ag==")
        end = circuit.add("LogicGateCompare", phase, Literal(3 * i + 3), config="BQ==")
        active = circuit.add("LogicGateAnd", start, end)
        below = rows[i + 1] if i < len(rows) - 1 else Literal(None)
        for net, source in zip(arguments, (row, below, Literal(int(i == len(rows) - 1))), strict=True):
            net.append(circuit.add("LogicGateIf", source, active))
    circuit.aliases = [tuple(net) for net in arguments]
    channels = circuit.channel_map()
    outgoing = {channels[group[0]]: (y + 17, 0) for group, y in zip(arguments, _EDGE_ROWS, strict=True)}
    return _layout_platform(circuit, channels, set(range(len(circuit.gates))), {}, _EdgeLinks({}, outgoing))


def _parts(before):
    ports = {name: _radio(before, channel) for name, channel in _ARGUMENTS.items()}
    rx_sites = [before.sites[ports[name][0][0]] for name in _ARGUMENTS]
    west = rx_sites[0][0]
    if rx_sites != [(west, -15, y, 0) for y in _RECEIVER_ROWS]:
        raise ValueError("基线的行编码接收器与飞线位置不匹配")
    removed_platforms = {before.entries[tx][0] for _, (tx, _) in ports.values()}
    if len(removed_platforms) != len(ports):
        raise ValueError("基线须包含三个独立参数板")
    radios = Counter(i for i, entry in before.entries if _kind(entry) == "ControlledSignalTransmitter")
    if any(radios[i] != 1 for i in removed_platforms):
        raise ValueError("参数板还向其他模块发射信号")
    partners = {before.entries[r][0] for r, s in before.short_ports.items() if before.entries[s][0] == west}
    if len(partners) != 1 or west in removed_platforms or partners & removed_platforms:
        raise ValueError("行编码器须由一对相邻平台组成")
    east, = partners
    return ports, removed_platforms, west, east


def _check_sources(before, after, translated, removed, receivers, replacement):
    expected_pairs = {translated[r]: translated[s] for r, s in before.short_ports.items()}
    expected_pairs.update(replacement)
    if after.short_ports != expected_pairs:
        raise ValueError("原生飞线配对与计划不符")
    sources = {old: after.sources(sender, 0) for old, sender in receivers.items()}
    for i, (_, entry) in enumerate(before.entries):
        if i in removed:
            continue
        for port in range(len(PORTS[_kind(entry)][1])):
            expected = set()
            for source, pin in before.sources(i, port):
                expected.update(sources[source] if source in sources else ((translated[source], pin),))
            if after.sources(translated[i], port) != tuple(sorted(expected)):
                raise ValueError(f"保留建筑 {before.sites[i]} 的输入 {port} 来源不匹配")


def build(path: Path) -> tuple[dict, dict]:
    report = _report(path)
    if report["platforms"] != 81 or report["part_platforms"]["prefix-scan-wiring"] != 20:
        raise ValueError("需使用 81 板自动前缀闭包及其接口表")
    before = _native_wiring(path)
    if len(before.platforms) != report["platforms"] or any(
            board["T"] != "Foundation_3x3" or board.get("R", 0) for board in before.platforms):
        raise ValueError("自动闭包原生平台与接口表不匹配")
    ports, removed_platforms, west, east = _parts(before)
    removed = {i for i, (pi, _) in enumerate(before.entries) if pi in removed_platforms}
    removed.update(i for (rx, cfg), _ in ports.values() for i in (rx, cfg))
    platform_map = {old: i for i, old in enumerate(p for p in range(len(before.platforms)) if p not in removed_platforms)}
    boards = [dict(before.platforms[i], B={**before.platforms[i]["B"], "Entries": []}) for i in platform_map]
    for i, (pi, entry) in enumerate(before.entries):
        if i not in removed:
            boards[platform_map[pi]]["B"]["Entries"].append(entry)
    left, y, level = _ROW_CLUSTER
    cluster = [(left + 3 * offset, y, level) for offset in range(3)]
    for p in set(platform_map) - {west, east}:
        x, other_y, z = (before.platforms[p].get(axis, 0) for axis in ("X", "Y", "Z"))
        if z == level and abs(other_y - y) < 3 and left - 2 <= x < left + 9:
            raise ValueError("三块相邻平台的预留岛格已占用")
    producer = _parameters()
    producer_index = len(boards)
    boards.append({**producer.entry, "X": left, "Y": y, "Z": level})
    for pi, (x, y, level) in zip((west, east), cluster[1:], strict=True):
        boards[platform_map[pi]].update(X=x, Y=y, Z=level)
    for edge, row in zip(_EDGE_ROWS, _RECEIVER_ROWS, strict=True):
        points = [(-18, edge), (-17, edge)]
        if edge != row:
            points.append((-17, row))
        points.append((-13, row))
        boards[platform_map[west]]["B"]["Entries"].extend((*_wire_path(*points), _port("Receiver", -18, edge)))
    bp = {"$type": "Island", "BinaryVersion": 1137, "Entries": boards}
    after = _local_wiring(bp)

    translated = {i: after.lookup[(platform_map[pi], *before.sites[i][1:])]
                  for i, (pi, _) in enumerate(before.entries) if i not in removed}
    producer_ids = tuple(i for i, (pi, _) in enumerate(after.entries) if pi == producer_index)
    for (i, port), expected in producer.expected.items():
        if tuple(sorted(after._direct_sources(producer_ids[i], port))) != tuple(
                sorted((producer_ids[source], pin) for source, pin in expected)):
            raise ValueError("合并参数板的原生输入来源不符")
    pairs, receivers = {}, {}
    for name, y in zip(_ARGUMENTS, _EDGE_ROWS, strict=True):
        sender = after.lookup[producer_index, 37, y, 0]
        pairs[after.lookup[platform_map[west], -18, y, 0]] = sender
        receivers[ports[name][0][0]] = sender
    _check_sources(before, after, translated, removed, receivers, pairs)
    counts = Counter(_kind(entry) for _, entry in after.entries)
    report["platforms"] = len(boards)
    report["part_platforms"]["prefix-scan-wiring"] -= len(removed_platforms) - 1
    report["building_entries"] = len(after.entries)
    report["global_receivers"] = counts["ControlledSignalReceiver"]
    report["global_transmitters"] = counts["ControlledSignalTransmitter"]
    report["short_range_links"] = len(after.short_ports)
    report["flywire"] = {"replaced_channels": _ARGUMENTS,
                        "platforms": cluster,
                        "port_rows": dict(zip(_ARGUMENTS, _EDGE_ROWS, strict=True))}
    return {"V": 1137, "BP": bp}, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出自动前缀闭包的三参数飞线合装")
    parser.add_argument("--baseline", required=True, type=Path, help="81 板原生蓝图及同名接口表")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.baseline)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
