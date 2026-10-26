"""结构目录的条件堆叠约化：K下料仅用基础块，非K下料保留完整上料域。"""

from collections.abc import Iterable, Iterator

from .physics import EMPTY, PIN, Rules, Shape
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
