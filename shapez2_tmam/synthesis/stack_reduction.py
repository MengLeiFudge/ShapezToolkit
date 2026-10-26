"""条件堆叠约化：K下料的基础块域，以及普通格/针尾的单次上料构造。"""

from collections.abc import Iterable, Iterator

from .physics import EMPTY, PIN, Rules, Shape
from .recipe import Builder, Recipe
from .support import in_support_class


def stack_successors(rules: Rules, lower: Shape, known: Iterable[Shape]) -> Iterator[tuple[Shape, Shape]]:
    """给出(上料,结果)；调用方提供同一规则下、普通格统一为Cu的结构目录快照。

    K分支使用初始种子中的连续普通块或单针；完整性针对最终闭包，
    不要求与原双输入规则在同一轮产生相同结果。非K分支原样保留真实堆叠。
    """
    if not in_support_class(rules, lower):
        for upper in known:
            result = rules.stack(lower, upper)
            if result is not None and result != lower:
                yield upper, result
        return
    cells = rules.cells(lower)
    n = rules.quadrants
    tops = [max((z for z, q in cells if q == column), default=-1) for column in range(n)]

    def place(columns: tuple[int, ...], cell: str) -> tuple[Shape, Shape] | None:
        """K原格不动，单个基础块停在所占列最高阻挡上方。"""
        level = 1 + max(tops[q] for q in columns)
        if level >= rules.height:
            return None
        upper = Shape((tuple(cell if q in columns else EMPTY for q in range(n)),))
        result = rules.fold({**cells, **{(level, q): cell for q in columns}})
        assert result is not None
        return upper, result

    for length in range(1, n + 1):
        for start in range(n if length < n else 1):
            extension = place(tuple((start + offset) % n for offset in range(length)), "Cu")
            if extension is not None:
                yield extension
    for q in range(n):
        extension = place((q,), PIN)
        if extension is not None:
            yield extension


def _single_stack(builder: Builder, lower: Recipe, target: Shape, *, pins: bool) -> Recipe | None:
    """共用下料一次结算判据；优先直接上料，再用无环列前缀补辅助C。"""
    rules = builder.rules
    collapsed = rules.collapse(rules.cells(lower.result))
    original = rules.cells(collapsed) if collapsed is not None else {}
    desired = rules.cells(target)
    if any(desired.get(pos) != cell for pos, cell in original.items()):
        return None
    delta = {pos: cell for pos, cell in desired.items() if pos not in original}
    if any(cell[0] == "c" or (cell == PIN and not pins) for cell in delta.values()):
        return None
    tops = [max((z for z, column in original if column == q), default=-1) for q in range(rules.quadrants)]
    if any(z <= tops[q] for z, q in delta):
        return None
    if any(not any(z == 0 or (z - 1, q) in desired for z, q in block) for block in rules.groups(delta)):
        return None
    bottom = min((z for z, _ in delta), default=0)
    shifted = {(z - bottom, q): cell for (z, q), cell in delta.items()}
    plain = rules.fold(shifted)
    if plain is None:
        upper = builder.apply("crystal", builder.base((PIN,) * rules.quadrants), parameter="r")
    else:
        upper = builder.noncrystal(plain)
        if upper is None:
            filled = {}
            for q in range(rules.quadrants):
                top = max((z for z, column in shifted if column == q), default=-1)
                pin_tail = False
                for z in range(top + 1):
                    cell = shifted.get((z, q), "cr")
                    if pin_tail and cell != PIN:
                        return None
                    pin_tail |= cell == PIN
                    filled[z, q] = cell
            source = rules.fold(filled)
            assert source is not None
            upper = builder.independent_columns(source)
    if upper is None:
        raise RuntimeError("列前缀上料未生成制造证书")
    result = builder.apply("stack", lower, upper)
    if result.result != target:
        raise RuntimeError("单次追加的列前缀上料与目标不一致")
    return result


def ordinary_stack(builder: Builder, lower: Recipe, target: Shape) -> Recipe | None:
    """保留不新增针的接口；只虚拟结算下料，实际仍使用原物品执行一次Stack。"""
    return _single_stack(builder, lower, target, pins=False)


def single_stack(builder: Builder, lower: Recipe, target: Shape) -> Recipe | None:
    """新增N/P的单次构造；覆盖直接无晶体上料及各列N在下/P尾在上的范围。

    下料允许非K或不稳定。返回None还可能是针普通格交错时尚未覆盖，
    不能作为固定下料之外、更不能作为目标全局不可制作的结论。
    """
    return _single_stack(builder, lower, target, pins=True)
