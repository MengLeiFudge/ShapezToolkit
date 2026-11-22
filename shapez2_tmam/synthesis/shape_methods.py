"""读取原生四象限五层目标的层高、层和材料。"""

from .physics import EMPTY, PIN, Rules, Shape


_RULES = Rules(4, 5)
Color = str


def shape_literal(code: str) -> Shape:
    return _RULES.parse(code)


def crystal(target: Shape | None, color: Color) -> Shape | None:
    return _RULES.crystal(target, color) if target is not None else None


def unstack_lower(target: Shape | None) -> Shape | None:
    if target is None:
        return None
    top = len(target.layers) - 1
    return _RULES.fold({pos: cell for pos, cell in _RULES.cells(target).items() if pos[0] < top})


def unstack_upper(target: Shape | None) -> Shape | None:
    return Shape((target.layers[-1],)) if target is not None else None


def analyze_part(target: Shape | None) -> Shape | None:
    if target is None or target.layers[0][0] == EMPTY:
        return None
    cell = target.layers[0][0]
    part = PIN if cell == PIN else cell[0] + "u"
    return Shape(((part, EMPTY, EMPTY, EMPTY),))


def analyze_color(target: Shape | None) -> Color | None:
    if target is None or target.layers[0][0] in (EMPTY, PIN):
        return None
    return target.layers[0][0][1]


def target_height(target: Shape | None) -> int:
    """测量原高度，计入空底层和空中间层。"""
    dense = crystal(target, "r")
    for height in (0, 1, 2, 3, 4):
        if dense is None:
            return height
        dense = unstack_lower(dense)
    return 5


def read_top_row_at(target: Shape | None, height: int) -> Shape | None:
    """高度从 1 开始；当前顶层位于指定层时返回原材料单层。"""
    if target_height(target) == height:
        return unstack_upper(target)
    return None


def bottom_material(target: Shape | None) -> int:
    """底层 q0 按空、普通格、针、晶体分别返回 0、1、2、3。"""
    part = analyze_part(target)
    if part is None:
        return 0
    if part == shape_literal("P-------"):
        return 2
    if part == shape_literal("cu------"):
        return 3
    return 1
