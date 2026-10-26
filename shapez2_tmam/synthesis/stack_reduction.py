"""条件堆叠约化：K下料的基础块域，以及任意下料不新增针时的直接上料构造。"""

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


def ordinary_stack(builder: Builder, lower: Recipe, target: Shape) -> Recipe | None:
    """构造一份普通或紧密N/C上料；只覆盖相对下料结算结果不新增针的单次Stack。

    下料仍使用原物品，只虚拟计算一次结算结果作判据，不能额外加工它。
    返回None只是否定这个固定下料的子问题，不代表目标全局不可制作。
    """
    rules = builder.rules
    collapsed = rules.collapse(rules.cells(lower.result))
    original = rules.cells(collapsed) if collapsed is not None else {}
    desired = rules.cells(target)
    if any(desired.get(pos) != cell for pos, cell in original.items()):
        return None
    delta = {pos: cell for pos, cell in desired.items() if pos not in original}
    if any(cell == PIN or cell[0] == "c" for cell in delta.values()):
        return None
    tops = [max((z for z, column in original if column == q), default=-1) for q in range(rules.quadrants)]
    if any(z <= tops[q] for z, q in delta):
        return None
    if any(not any(z == 0 or (z - 1, q) in desired for z, q in block) for block in rules.groups(delta)):
        return None
    bottom = min((z for z, _ in delta), default=0)
    shifted = {(z - bottom, q): cell for (z, q), cell in delta.items()}
    plain = rules.fold(shifted)
    upper = builder.noncrystal(plain) if plain is not None else None
    if upper is None:
        height = 1 + max((z for z, _ in shifted), default=0)
        source = Shape(tuple(tuple(shifted.get((z, q), "cr") for q in range(rules.quadrants)) for z in range(height)))
        upper = builder.independent_columns(source)
    if upper is None:
        raise RuntimeError("紧密N/C上料未生成制造证书")
    result = builder.apply("stack", lower, upper)
    if result.result != target:
        raise RuntimeError("单次普通追加的紧密上料与目标不一致")
    return result
