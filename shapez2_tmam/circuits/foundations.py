"""原生基础平台的岛格范围和常规可建边界。"""

from itertools import product

TILE_SIZE = 20
EDGE_MARGIN = 3

# X、Y 方向岛格数。Foundation_2x3 的本地方向为 X 向三格、Y 向两格。
FOUNDATION_CHUNKS = {
    "Foundation_1x1": (1, 1),
    "Foundation_2x2": (2, 2),
    "Foundation_2x3": (3, 2),
    "Foundation_3x3": (3, 3),
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
