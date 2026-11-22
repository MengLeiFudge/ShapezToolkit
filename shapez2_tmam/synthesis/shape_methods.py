"""读取原生四象限五层目标的层高、层和材料。"""

from .layer_methods import stack
from .physics import EMPTY, PIN, Rules, Shape


_RULES = Rules(4, 5)
Color = str


def shape_literal(code: str) -> Shape:
    return _RULES.parse(code)


def crystal(target: Shape | None, color: Color) -> Shape | None:
    return _RULES.crystal(target, color) if target is not None else None


def rotate_cw(target: Shape | None) -> Shape | None:
    return _RULES.rotate(target, 1) if target is not None else None


def rotate_ccw(target: Shape | None) -> Shape | None:
    return _RULES.rotate(target, -1) if target is not None else None


def cut_front(target: Shape | None) -> Shape | None:
    return _RULES.cut(target)[0] if target is not None else None


def swap_front_a(front: Shape | None, back: Shape | None) -> Shape | None:
    if front is None or back is None:
        return None
    return _RULES.swap(front, back)[0]


def pin(target: Shape | None) -> Shape | None:
    return _RULES.pin(target) if target is not None else None


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


def _cut_ground_corner(row: Shape | None) -> Shape | None:
    return rotate_ccw(cut_front(rotate_cw(cut_front(row))))


def read_labeled_corner(row: Shape | None) -> Shape | None:
    """读取原单层 q0 的一格，保留形状和颜色。"""
    if unstack_lower(row) is not None:
        return None
    if analyze_part(row) == shape_literal("cu------"):
        color = analyze_color(row)
        if color is None or color == "u":
            return shape_literal("cu------")
        row = crystal(shape_literal("--CuCuCu"), color)
    return _cut_ground_corner(row)


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


def advance_target_rows(target: Shape | None, height: int) -> Shape | None:
    """扫描到当前顶层时移除它，跨过空层时保留剩余图形。"""
    if target_height(target) == height:
        return unstack_lower(target)
    return target


def row_scan_remaining(remaining: Shape | None, top: Shape | None, below: Shape | None,
                       select: int, height: int) -> Shape | None:
    return advance_target_rows(remaining, height)


def row_scan_top(remaining: Shape | None, top: Shape | None, below: Shape | None,
                 select: int, height: int) -> Shape | None:
    if select == 1:
        return read_top_row_at(remaining, height)
    return top


def row_scan_below(remaining: Shape | None, top: Shape | None, below: Shape | None,
                   select: int, height: int) -> Shape | None:
    if select == 2:
        return read_top_row_at(remaining, height)
    return below


def record_crystal_height(previous: int, row: Shape | None, height: int) -> int:
    """自顶向下扫描时，只记录 q0 中遇到的第一颗晶体。"""
    if previous == 0 and analyze_part(row) == shape_literal("cu------"):
        return height
    return previous


def original_rows(target: Shape | None) -> tuple[Shape | None, ...]:
    """按原层号从底到顶返回五层，空层保留为 None。"""
    rows = []
    for height in (5, 4, 3, 2, 1):
        rows.append(read_top_row_at(target, height))
        target = advance_target_rows(target, height)
    return tuple(reversed(rows))


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


def _pack_stack_corner(row: Shape | None, below: Shape | None, ground: bool) -> Shape | None:
    part = analyze_part(row)
    if part is None or part == shape_literal("cu------"):
        return None
    supported = ground or analyze_part(below) is not None
    if part == shape_literal("P-------"):
        if supported:
            return shape_literal("Wu------")
        return shape_literal("Su------")
    if supported:
        return shape_literal("Ru------")
    return shape_literal("Cu------")


def _merge_stack_corners(a: Shape | None, b: Shape | None) -> Shape | None:
    if a is None:
        return b
    if b is None:
        return a
    return stack(a, b)


def pack_stack_half(row: Shape | None, below: Shape | None, ground: bool) -> Shape | None:
    """编码输入的 q0 和 q1，保留在这两个象限。"""
    left = _pack_stack_corner(row, below, ground)
    right = _pack_stack_corner(rotate_ccw(row), rotate_ccw(below), ground)
    return _merge_stack_corners(left, rotate_cw(right))


def pack_stack_row(row: Shape | None, below: Shape | None, ground: bool) -> Shape | None:
    """一层原图及其直接下方的一层转为前缀扫描信号。"""
    front = pack_stack_half(row, below, ground)
    back = pack_stack_half(rotate_ccw(rotate_ccw(row)), rotate_ccw(rotate_ccw(below)), ground)
    return _merge_stack_corners(front, rotate_ccw(rotate_ccw(back)))


def _tail_stack_corner(row: Shape | None, level: int, prefix: int) -> Shape | None:
    if level < prefix:
        return None
    part = analyze_part(row)
    if part is None or part == shape_literal("cu------"):
        return None
    return _cut_ground_corner(row)


def tail_stack_half(row: Shape | None, level: int, left_prefix: int, right_prefix: int) -> Shape | None:
    """读取 q0/q1 未纳入前态的 N/P 原料，level 从 0 开始。"""
    left = _tail_stack_corner(row, level, left_prefix)
    right = _tail_stack_corner(rotate_ccw(row), level, right_prefix)
    return _merge_stack_corners(left, rotate_cw(right))


def tail_stack_row(row: Shape | None, level: int, h0: int, h1: int, h2: int, h3: int) -> Shape | None:
    """按已闭合前缀，从原单层选择本轮实际堆叠的原料。"""
    front = tail_stack_half(row, level, h0, h1)
    back = tail_stack_half(rotate_ccw(rotate_ccw(row)), level, h2, h3)
    return _merge_stack_corners(front, rotate_cw(rotate_cw(back)))
