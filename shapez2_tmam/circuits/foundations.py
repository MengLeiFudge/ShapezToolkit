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
    "Foundation_2x2": (2, 2),
    "Foundation_2x3": (3, 2),
    "Foundation_3x3": (3, 3),
    "Foundation_L3": (2, 2),
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


def foundation_tiles(kind):
    if kind == "Foundation_L3":
        return ((0, 0), (1, 0), (0, 1))
    width, height = FOUNDATION_CHUNKS[kind]
    return tuple(product(range(width), range(height)))


@cache
def platform_ground(kind):
    if kind != "Foundation_L3":
        return frozenset(foundation_ground(*FOUNDATION_CHUNKS[kind]))
    tiles = set(foundation_tiles(kind))
    ground = set()
    for cx, cy in tiles:
        for x, y in product(range(TILE_SIZE), repeat=2):
            dx = (x >= TILE_SIZE - EDGE_MARGIN) - (x < EDGE_MARGIN)
            dy = (y >= TILE_SIZE - EDGE_MARGIN) - (y < EDGE_MARGIN)
            # 凹角的对角岛格也要存在，两个相邻边才都能铺到角上。
            if {(cx + dx, cy), (cx, cy + dy), (cx + dx, cy + dy)} <= tiles:
                ground.add((cx * TILE_SIZE + x, cy * TILE_SIZE + y))
        for (dx, dy), notch in (
            ((1, 0), product((17,), range(8, 12))),
            ((-1, 0), product((2,), range(8, 12))),
            ((0, 1), product(range(8, 12), (17,))),
            ((0, -1), product(range(8, 12), (2,))),
        ):
            if (cx + dx, cy + dy) not in tiles:
                ground.update((cx * TILE_SIZE + x, cy * TILE_SIZE + y) for x, y in notch)
    return frozenset(ground)
