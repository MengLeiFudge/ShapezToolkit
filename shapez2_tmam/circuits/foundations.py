"""原生基础平台的岛格范围和常规可建边界。"""

from functools import cache
from itertools import product

TILE_SIZE = 20
EDGE_MARGIN = 3

# 岛格尺寸按原生未旋转布局的 X、Y 方向记录。
FOUNDATION_CHUNKS = {
    "Foundation_1x1": (1, 1),
    "Foundation_1x2": (2, 1),
    "Foundation_1x3": (3, 1),
    "Foundation_1x4": (4, 1),
    "Foundation_2x2": (2, 2),
    "Foundation_2x3": (3, 2),
    "Foundation_2x4": (4, 2),
    "Foundation_3x3": (3, 3),
    "Foundation_L3": (2, 2),
}


# resources.assets 中的岛格偏移，以平台锚点为原点。
IRREGULAR_FOUNDATIONS = {
    "Foundation_L3": ((0, 0), (1, 0), (0, 1)),
}


def foundation_ground(width, height):
    x0 = -((width - 1) // 2) * TILE_SIZE
    y0 = -((height - 1) // 2) * TILE_SIZE
    x1, y1 = x0 + width * TILE_SIZE, y0 + height * TILE_SIZE
    ground = set(product(range(x0 + EDGE_MARGIN, x1 - EDGE_MARGIN),
                         range(y0 + EDGE_MARGIN, y1 - EDGE_MARGIN)))
    # 外缘每个岛格的四个凹口位置由 NotchDefinition 定义。
    for y in range(y0, y1, TILE_SIZE):
        ground.update(product((x0 + 2, x1 - 3), range(y + 8, y + 12)))
    for x in range(x0, x1, TILE_SIZE):
        ground.update(product(range(x + 8, x + 12), (y0 + 2, y1 - 3)))
    return ground


def _rotate(x, y, rotation):
    return ((x, y), (-y, x), (-x, -y), (y, -x))[rotation]


def rotate_cell(x, y, rotation):
    """围绕锚点岛格中心旋转建筑坐标。"""
    offset_x, offset_y = _rotate(TILE_SIZE - 1, TILE_SIZE - 1, rotation)
    x, y = _rotate(x, y, rotation)
    return x + (TILE_SIZE - 1 - offset_x) // 2, y + (TILE_SIZE - 1 - offset_y) // 2


@cache
def _island_offsets(kind, rotation):
    tiles = IRREGULAR_FOUNDATIONS.get(kind)
    if tiles is None:
        w, h = FOUNDATION_CHUNKS[kind]
        x, y = (w - 1) // 2, (h - 1) // 2
        tiles = tuple(product(range(-x, w - x), range(-y, h - y)))
    return tuple(_rotate(x, y, rotation) for x, y in tiles)


@cache
def foundation_origin(kind, rotation=0):
    return tuple(map(min, zip(*_island_offsets(kind, rotation), strict=True)))


@cache
def foundation_tiles(kind, rotation=0):
    x, y = foundation_origin(kind, rotation)
    return tuple((a - x, b - y) for a, b in _island_offsets(kind, rotation))


@cache
def platform_interior(kind, rotation=0):
    if rotation:
        return frozenset(rotate_cell(x, y, rotation) for x, y in platform_interior(kind))
    if kind not in IRREGULAR_FOUNDATIONS:
        width, height = FOUNDATION_CHUNKS[kind]
        x = EDGE_MARGIN - ((width - 1) // 2) * TILE_SIZE
        y = EDGE_MARGIN - ((height - 1) // 2) * TILE_SIZE
        return frozenset(product(range(x, x + width * TILE_SIZE - 2 * EDGE_MARGIN),
                                 range(y, y + height * TILE_SIZE - 2 * EDGE_MARGIN)))
    tiles = set(IRREGULAR_FOUNDATIONS[kind])
    return frozenset((cx * TILE_SIZE + x, cy * TILE_SIZE + y) for cx, cy in tiles
                     for x, y in product(range(TILE_SIZE), repeat=2)
                     if _inside_chunk_edges(tiles, cx, cy, x, y))


def _inside_chunk_edges(tiles, cx, cy, x, y):
    dx = (x >= TILE_SIZE - EDGE_MARGIN) - (x < EDGE_MARGIN)
    dy = (y >= TILE_SIZE - EDGE_MARGIN) - (y < EDGE_MARGIN)
    return {(cx + dx, cy), (cx, cy + dy), (cx + dx, cy + dy)} <= tiles


@cache
def platform_ground(kind, rotation=0):
    if rotation:
        return frozenset(rotate_cell(x, y, rotation) for x, y in platform_ground(kind))
    if kind not in IRREGULAR_FOUNDATIONS:
        return frozenset(foundation_ground(*FOUNDATION_CHUNKS[kind]))
    tiles = set(IRREGULAR_FOUNDATIONS[kind])
    ground = set(platform_interior(kind))
    for cx, cy in tiles:
        for (dx, dy), notch in (
            ((1, 0), product((17,), range(8, 12))),
            ((-1, 0), product((2,), range(8, 12))),
            ((0, 1), product(range(8, 12), (17,))),
            ((0, -1), product(range(8, 12), (2,))),
        ):
            if (cx + dx, cy + dy) not in tiles:
                ground.update((cx * TILE_SIZE + x, cy * TILE_SIZE + y) for x, y in notch)
    return frozenset(ground)
