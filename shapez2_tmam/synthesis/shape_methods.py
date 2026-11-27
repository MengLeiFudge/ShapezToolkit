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


def _label_single_row(row: Shape | None) -> Shape | None:
    uncolored_crystal = shape_literal("cu------")
    is_crystal = analyze_part(row) == uncolored_crystal
    color = analyze_color(row)
    if is_crystal:
        # 形状分析已读到晶体，该角一定带颜色。
        row = crystal(shape_literal("--CuCuCu"), color)  # pyright: ignore[reportArgumentType]
    if is_crystal & (color == "u"):
        return uncolored_crystal
    return _cut_ground_corner(row)


def read_labeled_corner(row: Shape | None) -> Shape | None:
    """读取原单层 q0 的一格，保留形状和颜色。"""
    if unstack_lower(row) is not None:
        return None
    return _label_single_row(row)


def read_labeled_corner_q1(row: Shape | None) -> Shape | None:
    if unstack_lower(row) is not None:
        return None
    return _label_single_row(rotate_ccw(row))


def read_labeled_corner_q2(row: Shape | None) -> Shape | None:
    if unstack_lower(row) is not None:
        return None
    return _label_single_row(rotate_ccw(rotate_ccw(row)))


def read_labeled_corner_q3(row: Shape | None) -> Shape | None:
    if unstack_lower(row) is not None:
        return None
    return _label_single_row(rotate_cw(row))


def read_prefix_corner(row: Shape | None, row_height: int, prefix_height: int) -> Shape | None:
    """保留前缀内的一格原料，层高从 1 起算。"""
    if (row_height < 1) | (row_height > prefix_height):
        return None
    return read_labeled_corner(row)


def target_present(target: Shape | None) -> bool:
    return target is not None


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
        present = _has_row_at_bound(target, height)
        rows.append(unstack_upper(target) if present else None)
        if present:
            target = unstack_lower(target)
    return tuple(reversed(rows))


def _has_row_at_bound(target: Shape | None, height: int) -> bool:
    # 前面的轮次已移除更高的原层，填满空位后剥去 height-1 层即可判断。
    if height == 1:
        return target is not None
    dense = unstack_lower(crystal(target, "r"))
    for level in (2, 3, 4):
        if level < height:
            dense = unstack_lower(dense)
    return dense is not None


def _read_original_row(target: Shape | None, wanted: int) -> Shape | None:
    for height in (5, 4, 3, 2, 1):
        present = _has_row_at_bound(target, height)
        if height == wanted:
            if present:
                return unstack_upper(target)
            return None
        if present:
            target = unstack_lower(target)
    return None


def original_row_0(target: Shape | None) -> Shape | None:
    return _read_original_row(target, 1)


def original_row_1(target: Shape | None) -> Shape | None:
    return _read_original_row(target, 2)


def original_row_2(target: Shape | None) -> Shape | None:
    return _read_original_row(target, 3)


def original_row_3(target: Shape | None) -> Shape | None:
    return _read_original_row(target, 4)


def original_row_4(target: Shape | None) -> Shape | None:
    return _read_original_row(target, 5)


def _row_at_bound(target: Shape | None, height: int) -> Shape | None:
    if _has_row_at_bound(target, height):
        return unstack_upper(target)
    return None


def _remaining_after_bound(target: Shape | None, height: int) -> Shape | None:
    if _has_row_at_bound(target, height):
        return unstack_lower(target)
    return target


def remaining_after_row4(target: Shape | None) -> Shape | None:
    return _remaining_after_bound(target, 5)


def read_bound_row3(target: Shape | None) -> Shape | None:
    return _row_at_bound(target, 4)


def remaining_after_row3(target: Shape | None) -> Shape | None:
    return _remaining_after_bound(target, 4)


def read_bound_row2(target: Shape | None) -> Shape | None:
    return _row_at_bound(target, 3)


def remaining_after_row2(target: Shape | None) -> Shape | None:
    return _remaining_after_bound(target, 3)


def read_bound_row1(target: Shape | None) -> Shape | None:
    return _row_at_bound(target, 2)


def remaining_after_row1(target: Shape | None) -> Shape | None:
    return _remaining_after_bound(target, 2)


def read_bound_row0(target: Shape | None) -> Shape | None:
    return unstack_upper(target)


def read_bound_row0_after_row1(target: Shape | None) -> Shape | None:
    return read_bound_row0(remaining_after_row1(target))


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


def _pack_support_corner(row: Shape | None, below: Shape | None, ground: bool,
                         keep_crystal: bool) -> Shape | None:
    part = analyze_part(row)
    if part is None:
        return None
    if part == shape_literal("cu------"):
        if keep_crystal:
            return shape_literal("P-------")
        return None
    supported = ground | (analyze_part(below) is not None)
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


def _pack_support_half(row: Shape | None, below: Shape | None, ground: bool,
                       keep_crystal: bool) -> Shape | None:
    left = _pack_support_corner(row, below, ground, keep_crystal)
    right = _pack_support_corner(rotate_ccw(row), rotate_ccw(below), ground, keep_crystal)
    return _merge_stack_corners(left, rotate_cw(right))


def pack_stack_half(row: Shape | None, below: Shape | None, ground: bool) -> Shape | None:
    """编码输入的 q0 和 q1，保留在这两个象限。"""
    return _pack_support_half(row, below, ground, False)


def _pack_support_row(row: Shape | None, below: Shape | None, ground: bool,
                      keep_crystal: bool) -> Shape | None:
    front = _pack_support_half(row, below, ground, keep_crystal)
    back = _pack_support_half(rotate_ccw(rotate_ccw(row)), rotate_ccw(rotate_ccw(below)), ground, keep_crystal)
    return _merge_stack_corners(front, rotate_ccw(rotate_ccw(back)))


def pack_stack_row(row: Shape | None, below: Shape | None, ground: bool) -> Shape | None:
    """一层原图及其直接下方的一层转为前缀扫描信号。"""
    return _pack_support_row(row, below, ground, False)


def pack_prefix_half(row: Shape | None, below: Shape | None, ground: bool) -> Shape | None:
    return _pack_support_half(row, below, ground, True)


def pack_prefix_row(row: Shape | None, below: Shape | None, ground: bool) -> Shape | None:
    """沿用堆叠支撑编码，另用单针记录前缀中已保留的晶体。"""
    return _pack_support_row(row, below, ground, True)


def _tail_stack_corner(row: Shape | None, level: int, prefix: int) -> Shape | None:
    part = analyze_part(row)
    if (level >= prefix) & (part is not None) & (part != shape_literal("cu------")):
        return _cut_ground_corner(row)
    return None


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
