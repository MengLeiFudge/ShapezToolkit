"""按组件真实占地装箱；组件之间保留一格，旋转不改变端口对应关系。"""

import math
from itertools import islice


def _rotate(x: int, y: int, turns: int) -> tuple[int, int]:
    return ((x, y), (-y, x), (-x, -y), (y, -x))[turns]


def _tiles(entry: dict) -> list[tuple[int, int]]:
    kind = entry["T"]
    if kind.startswith(("ControlledSignalReceiver", "ControlledSignalTransmitter")):
        offsets = [(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1)]
    elif kind.startswith("VirtualHalvesSwapper"):
        offsets = [(0, 0), (0, -1)]
    else:
        offsets = [(0, 0)]
    return [(entry["X"] + x, entry["Y"] + y)
            for dx, dy in offsets for x, y in [_rotate(dx, dy, entry["R"])]]


def _orientations(entries: list[dict]) -> list[tuple[list[dict], int, int, int]]:
    result = []
    seen = set()
    for turns in range(4):
        rotated = [{**entry, "X": _rotate(entry["X"], entry["Y"], turns)[0],
                    "Y": _rotate(entry["X"], entry["Y"], turns)[1], "R": (entry["R"] + turns) % 4}
                   for entry in entries]
        tiles = {tile for entry in rotated for tile in _tiles(entry)}
        left, bottom = min(x for x, _ in tiles), min(y for _, y in tiles)
        width, height = max(x for x, _ in tiles) - left + 1, max(y for _, y in tiles) - bottom + 1
        if width > 16 or height > 16:
            raise ValueError("组件旋转后的占地超出16×16内部范围")
        mask = sum(1 << ((y - bottom) * 16 + x - left) for x, y in tiles)
        if mask in seen:
            continue
        seen.add(mask)
        result.append(([{**entry, "X": entry["X"] - left, "Y": entry["Y"] - bottom} for entry in rotated],
                       mask, width, height))
    return result


def pack_components(platforms: list[dict]) -> tuple[list[dict], dict[int, tuple[int, int]]]:
    """有界候选箱选择与256位占地交集；不运行信号或目标图形。"""
    components = [_orientations(platform["B"]["Entries"]) for platform in platforms]
    order = sorted(range(len(components)), key=lambda i: (-components[i][0][1].bit_count(), i))
    packed: list[dict] = []
    blocked: list[int] = []
    spaces: dict[int, dict[int, None]] = {}
    mapping = {}
    placements: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    full = (1 << 256) - 1
    left_edge = sum(1 << (16 * y) for y in range(16))
    right_edge = left_edge << 15
    for index in order:
        variants = components[index]
        size = variants[0][1].bit_count()
        candidates = []
        for space in sorted(spaces):
            if space >= size:
                candidates.extend(islice(spaces[space], 8 - len(candidates)))
                if len(candidates) == 8:
                    break
        candidates = list(dict.fromkeys((*candidates, *range(max(0, len(packed) - 8), len(packed)))))
        chosen = None
        for platform in (*candidates, len(packed)):
            occupied = blocked[platform] if platform < len(packed) else 0
            for entries, mask, width, height in variants:
                key = mask, width, height
                if key not in placements:
                    placements[key] = [(mask << (16 * y + x), x, y)
                                       for y in range(17 - height) for x in range(17 - width)]
                for shifted, x, y in placements[key]:
                    if not shifted & occupied:
                        chosen = platform, entries, shifted, x, y
                        break
                if chosen is not None:
                    break
            if chosen is not None:
                break
        if chosen is None:
            raise ValueError("组件不能放入空平台")
        platform, entries, mask, x, y = chosen
        if platform == len(packed):
            packed.append({"T": "Foundation_1x1", "B": {
                "$type": "Building", "BinaryVersion": 1137, "Entries": []}})
            blocked.append(0)
        else:
            old_space = 256 - blocked[platform].bit_count()
            del spaces[old_space][platform]
            if not spaces[old_space]:
                del spaces[old_space]
        target = packed[platform]["B"]["Entries"]
        mapping[index] = platform, len(target)
        target.extend({**entry, "X": entry["X"] + x + 2, "Y": entry["Y"] + y + 2} for entry in entries)
        # 相邻格不能再放另一组件，阻断所有相对端口可能形成的额外连接。
        blocked[platform] |= (mask | ((mask & ~left_edge) >> 1) | ((mask & ~right_edge) << 1)
                              | (mask >> 16) | ((mask << 16) & full))
        free = 256 - blocked[platform].bit_count()
        spaces.setdefault(free, {})[platform] = None
    width = max(1, math.isqrt(max(0, len(packed) - 1)) + 1)
    for index, platform in enumerate(packed):
        platform.update(X=index % width, Y=index // width)
    return packed, mapping
