"""从原生整厂蓝图核对无线单播和跨板飞线。"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from ..mari.blueprint import DIRECTIONS, Wiring
from .compile_factory_dense import _short_wiring
from .compile_factory_v1 import _footprint, _groups
from .compiler_backend.prefix_scan_wiring import _native_island
from .compiler_frontend.pin_candidate_closure import _radio_ports


_RADIO_LIMIT = 555


def audit(platforms: list[dict]) -> dict:
    footprints = [_footprint(board) for board in platforms]
    owners = {tile: index for index, footprint in enumerate(footprints, 1) for tile in footprint}
    if len(owners) != sum(map(len, footprints)):
        raise ValueError("平台占地重叠，无法核对板间接线")
    adjacent = set()
    for (x, y, z), a in owners.items():
        for dx, dy in DIRECTIONS[:2]:
            b = owners.get((x + dx, y + dy, z))
            if b is not None and a != b:
                adjacent.add(tuple(sorted((a, b))))
    short = _short_wiring(platforms)
    flywire = [(short.entries[rx][0], short.entries[tx][0]) for rx, tx in short.short_ports.items()
               if short.entries[rx][0] != short.entries[tx][0]]
    groups = Counter(map(len, _groups(len(platforms), flywire)))
    senders, receivers = defaultdict(list), defaultdict(list)
    for index, board in enumerate(platforms, 1):
        wiring = Wiring({"Entries": [board]})
        for _, sends, channel, _ in _radio_ports(wiring):
            (senders if sends else receivers)[channel].append(index)
    layers = [p.get("Z", 0) for p in platforms]
    same_board, adjacent_boards, separated_boards, cross_layer = [], [], [], []
    for channel, (a, *other_senders) in sorted(senders.items()):
        ports = receivers.get(channel, ())
        if other_senders or len(ports) != 1:
            continue
        b, = ports
        row = {"channel": channel, "sender_board": a, "receiver_board": b}
        if a == b:
            same_board.append(row)
        elif layers[a - 1] != layers[b - 1]:
            cross_layer.append(row)
        elif tuple(sorted((a, b))) in adjacent:
            adjacent_boards.append(row)
        else:
            separated_boards.append(row)
    radio_count = sum(map(len, senders.values())) + sum(map(len, receivers.values()))
    single_links = {"same_board": same_board, "adjacent_boards": adjacent_boards,
                    "separated_boards": separated_boards, "cross_layer": cross_layer}
    return {"global_radio_count": radio_count, "global_radio_limit": _RADIO_LIMIT,
            "over_limit_by": max(0, radio_count - _RADIO_LIMIT),
            "same_island_layer_one_to_one": len(same_board) + len(adjacent_boards) + len(separated_boards),
            "one_to_one_global_links": single_links, "adjacent_board_pairs": len(adjacent),
            "cross_board_flywires": len(flywire),
            "flywire_connected_board_pairs": len({tuple(sorted(pair)) for pair in flywire}),
            "flywire_groups_by_size": dict(sorted(groups.items())), "isolated_boards": groups[1]}


def main() -> int:
    parser = argparse.ArgumentParser(description="核对整厂蓝图的无线单播、跨板飞线和全局收发数量")
    parser.add_argument("source", type=Path, help="整厂原生 .spz2bp 蓝图")
    parser.add_argument("--check", action="store_true", help="有同岛层单播或全局收发超额时返回 1")
    args = parser.parse_args()
    try:
        result = audit(_native_island(args.source)["Entries"])
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(args.check and (result["over_limit_by"] > 0 or result["same_island_layer_one_to_one"] > 0))


if __name__ == "__main__":
    raise SystemExit(main())
