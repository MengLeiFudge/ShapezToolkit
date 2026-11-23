"""将五行编码样件的邻层输入改接同岛层飞线。"""

import argparse
from collections import Counter
from pathlib import Path

from ...mari.blueprint import DIRECTIONS, Wiring, _kind
from ...mari.ports import PORTS
from ...mari.signals import decode_constant
from . import _write_blueprint
from .module_caller import _local_wiring
from .prefix_scan_wiring import _native_wiring, _report


def _radio(wiring: Wiring, channel: int) -> tuple[tuple[int, int], ...]:
    ports = []
    for i, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind not in ("ControlledSignalReceiver", "ControlledSignalTransmitter"):
            continue
        (source, _), = wiring.sources(i, 0)
        if decode_constant(wiring.entries[source][1]["C"]) == channel:
            ports.append((kind, i, source))
    ports.sort()
    if [kind for kind, _, _ in ports] != ["ControlledSignalReceiver", "ControlledSignalTransmitter"]:
        raise ValueError(f"频道 {channel} 须恰有一发一收")
    return tuple((index, source) for _, index, source in ports)


def _wire_path(*points):
    tiles = [points[0]]
    for x, y in points[1:]:
        a, b = tiles[-1]
        dx, dy = (x > a) - (x < a), (y > b) - (y < b)
        if abs(dx) + abs(dy) != 1:
            raise ValueError("导线须沿水平或垂直线段")
        tiles.extend((a + i * dx, b + i * dy) for i in range(1, abs(x - a) + abs(y - b) + 1))
    for (a, b), (x, y), (c, d) in zip(tiles, tiles[1:], tiles[2:]):
        pins = {(a - x, b - y), (c - x, d - y)}
        for name, directions in (("Forward", (0, 2)), ("Left", (2, 3))):
            for rotation in range(4):
                if pins == {DIRECTIONS[(port + rotation) % 4] for port in directions}:
                    yield {"T": f"WireDefault{name}InternalVariant", "X": x, "Y": y, "R": rotation, "L": 0}
                    break
            else:
                continue
            break


def _port(role, x, y):
    return {"T": f"WireTransmitter{role}InternalVariant", "X": x, "Y": y, "R": 0, "L": 0}


def _verify(before: Wiring, after: Wiring, removed, rx, tx, receiver, sender):
    sites = before.sites
    expected_pairs = {after.lookup[sites[r]]: after.lookup[sites[s]] for r, s in before.short_ports.items()}
    expected_pairs[after.lookup[receiver]] = after.lookup[sender]
    if after.short_ports != expected_pairs:
        raise ValueError("合装后的飞线配对与原接线不符")
    upstream = before.sources(tx, 1)
    if not upstream or after.sources(after.lookup[sender], 0) != tuple(
            sorted((after.lookup[sites[source]], port) for source, port in upstream)):
        raise ValueError("新飞线未接到原发射端的数据源")
    for i, (_, entry) in enumerate(before.entries):
        if i in removed:
            continue
        for port in range(len(PORTS[_kind(entry)][1])):
            sources = set()
            for source, pin in before.sources(i, port):
                sources.update(upstream if source == rx else ((source, pin),))
            expected = tuple(sorted((after.lookup[sites[source]], pin) for source, pin in sources))
            if after.sources(after.lookup[sites[i]], port) != expected:
                raise ValueError(f"飞线改接导致 {sites[i]} 的端口 {port} 接入错误")


def build(path: Path) -> tuple[dict, dict]:
    report = _report(path)
    channel = report["channel_use"]["pack_inputs"]["below"]
    before = _native_wiring(path)
    if any(platform["T"] != "Foundation_3x3" or platform.get("R", 0) for platform in before.platforms):
        raise ValueError("样件须由未旋转的 3×3 平台组成")
    (rx, rx_config), (tx, tx_config) = _radio(before, channel)
    load, producer = before.entries[rx][0], before.entries[tx][0]
    if (before.sites[rx][1:] != (-15, -7, 0) or before.sites[tx][1:] != (34, 10, 0)
            or any(before.entries[i][1].get("R", 0) for i in (rx, tx))):
        raise ValueError("邻层无线口位置与样件走线不符")
    paired = {before.entries[r][0] for r, s in before.short_ports.items() if before.entries[s][0] == load}
    if len(paired) != 1:
        raise ValueError("行编码板须接一块相邻计算平台")
    second, = paired
    removed = {rx, tx, rx_config, tx_config}
    entries = [dict(platform, B={**platform["B"], "Entries": []}) for platform in before.platforms]
    for i, (pi, entry) in enumerate(before.entries):
        if i not in removed:
            entries[pi]["B"]["Entries"].append(entry)
    right = max(platform.get("X", 0) for platform in entries) + 3
    for i, pi in enumerate((producer, load, second)):
        entries[pi].update(X=right + 3 * i, Y=0, Z=0)
    entries[producer]["B"]["Entries"].extend((*_wire_path((32, 10), (35, 10), (35, 9), (37, 9)),
                                               _port("Sender", 37, 9)))
    entries[load]["B"]["Entries"].extend((*_wire_path((-18, 9), (-17, 9), (-17, -7), (-13, -7)),
                                          _port("Receiver", -18, 9)))
    blueprint = {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}
    after = _local_wiring(blueprint)
    _verify(before, after, removed, rx, tx, (load, -18, 9, 0), (producer, 37, 9, 0))
    counts = Counter(_kind(entry) for _, entry in after.entries)
    report["channel_use"]["pack_inputs"].pop("below")
    report["channel_use"]["transmitters"].remove(channel)
    report["flywire"] = {"argument": "below", "replaced_channel": channel,
                        "sender": [right, 0, 0, 37, 9, 0], "receiver": [right + 3, 0, 0, -18, 9, 0]}
    report["building_entries"] = len(after.entries)
    report["short_range_links"] = len(after.short_ports)
    report["global_receivers"] = counts["ControlledSignalReceiver"]
    report["global_transmitters"] = counts["ControlledSignalTransmitter"]
    return {"V": 1137, "BP": blueprint}, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出五行编码邻层飞线对照")
    parser.add_argument("--baseline", required=True, type=Path, help="五行闭包接线的原生蓝图及同名接口表")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.baseline)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['short_range_links']} 对飞线。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
