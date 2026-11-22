"""按组件真实占地装箱；组件之间保留一格，旋转不改变端口对应关系。"""

import math
from itertools import islice

# Foundation_3x3 的九区块为 (-1..1, -1..1)；外缘退让三格。
_SIZE = 54
_ORIGIN = -17


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
        if width > _SIZE or height > _SIZE:
            raise ValueError("组件旋转后的占地超出3×3平台的54×54内部范围")
        mask = sum(1 << ((y - bottom) * _SIZE + x - left) for x, y in tiles)
        if mask in seen:
            continue
        seen.add(mask)
        result.append(([{**entry, "X": entry["X"] - left, "Y": entry["Y"] - bottom} for entry in rotated],
                       mask, width, height))
    return result


def pack_components(platforms: list[dict]) -> tuple[list[dict], dict[int, tuple[int, int]]]:
    """在3×3大平台装箱；位集并行筛除碰撞的原点，不枚举全部平移掩码。"""
    components = [_orientations(platform["B"]["Entries"]) for platform in platforms]
    order = sorted(range(len(components)), key=lambda i: (-components[i][0][1].bit_count(), i))
    packed: list[dict] = []
    blocked: list[int] = []
    spaces: dict[int, dict[int, None]] = {}
    mapping = {}
    placements: dict[tuple[int, int, int], tuple[int, tuple[int, ...]]] = {}
    area = _SIZE * _SIZE
    full = (1 << area) - 1
    left_edge = sum(1 << (_SIZE * y) for y in range(_SIZE))
    right_edge = left_edge << (_SIZE - 1)
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
                    origins = sum(((1 << (_SIZE - width + 1)) - 1) << (_SIZE * y)
                                  for y in range(_SIZE - height + 1))
                    offsets = []
                    remaining = mask
                    while remaining:
                        bit = remaining & -remaining
                        offsets.append(bit.bit_length() - 1)
                        remaining ^= bit
                    placements[key] = origins, tuple(offsets)
                available, offsets = placements[key]
                # 原点p可用，当且仅当每个占地偏移d处的p+d均未被禁止。
                for offset in offsets:
                    available &= ~(occupied >> offset)
                    if not available:
                        break
                if available:
                    shift = (available & -available).bit_length() - 1
                    y, x = divmod(shift, _SIZE)
                    chosen = platform, entries, mask << shift, x, y
                if chosen is not None:
                    break
            if chosen is not None:
                break
        if chosen is None:
            raise ValueError("组件不能放入空平台")
        platform, entries, mask, x, y = chosen
        if platform == len(packed):
            packed.append({"T": "Foundation_3x3", "B": {
                "$type": "Building", "BinaryVersion": 1137, "Entries": []}})
            blocked.append(0)
        else:
            old_space = area - blocked[platform].bit_count()
            del spaces[old_space][platform]
            if not spaces[old_space]:
                del spaces[old_space]
        target = packed[platform]["B"]["Entries"]
        mapping[index] = platform, len(target)
        target.extend({**entry, "X": entry["X"] + x + _ORIGIN, "Y": entry["Y"] + y + _ORIGIN}
                      for entry in entries)
        # 相邻格不能再放另一组件，阻断所有相对端口可能形成的额外连接。
        blocked[platform] |= (mask | ((mask & ~left_edge) >> 1) | ((mask & ~right_edge) << 1)
                              | (mask >> _SIZE) | ((mask << _SIZE) & full))
        free = area - blocked[platform].bit_count()
        spaces.setdefault(free, {})[platform] = None
    stack_platforms(packed)
    return packed, mapping


def stack_platforms(platforms: list[dict]) -> None:
    """3×3平台上下成对，保持岛内布局、平台次序和独立网络。"""
    columns = (len(platforms) + 1) // 2
    width = math.isqrt(max(0, columns - 1)) + 1
    for index, platform in enumerate(platforms):
        if platform["T"] != "Foundation_3x3":
            raise ValueError("双层装箱需要3×3平台")
        column, level = divmod(index, 2)
        platform.update(X=3 * (column % width) + 1, Y=3 * (column // width) + 1, Z=level)
