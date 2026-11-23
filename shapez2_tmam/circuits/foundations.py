"""原生基础平台的岛格范围和常规可建边界。"""

TILE_SIZE = 20
EDGE_MARGIN = 3

# X、Y 方向岛格数。Foundation_2x3 的本地方向为 X 向三格、Y 向两格。
FOUNDATION_CHUNKS = {
    "Foundation_1x1": (1, 1),
    "Foundation_2x2": (2, 2),
    "Foundation_2x3": (3, 2),
    "Foundation_3x3": (3, 3),
}
