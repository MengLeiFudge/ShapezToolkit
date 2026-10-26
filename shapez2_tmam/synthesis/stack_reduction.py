"""条件堆叠约化：K下料的基础块域，以及直接判据确认的单次N/P上料。"""

from collections.abc import Iterable, Iterator

from .physics import EMPTY, PIN, Position, Rules, Shape
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
    tops = rules.column_tops(cells)

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


def _packed_upper(builder: Builder, delta: dict[Position, str]) -> Recipe | None:
    """列内N/P压紧，差分约束确定最短C前缀；仅接受能全体释放的最小解。"""
    rules = builder.rules
    n = rules.quadrants
    words: list[list[str]] = [[] for _ in range(n)]
    ranks = {}
    for z in range(rules.height):
        for q in range(n):
            if (cell := delta.get((z, q))) is not None:
                ranks[z, q] = len(words[q])
                words[q].append(cell)
    edges = []
    for q in range(n):
        r = (q + 1) % n
        previous = None
        for z in range(rules.height):
            row = [(column, ranks[z, column]) for column in (q, r)
                   if (z, column) in delta and delta[z, column] != PIN]
            if not row:
                continue
            column, index = row[0]
            if len(row) == 2:
                other, other_index = row[1]
                edges.extend(((column, other, index - other_index),
                              (other, column, other_index - index)))
            if previous is not None:
                before, before_index = previous
                edges.append((before, column, before_index - index + 1))
            previous = column, index
    starts = [0] * n
    for _ in range(n):
        changed = False
        for before, after, distance in edges:
            candidate = starts[before] + distance
            if candidate > starts[after]:
                if candidate + len(words[after]) > rules.height:
                    return None
                starts[after] = candidate
                changed = True
        if not changed:
            break
    else:
        return None
    cells = {(z, q): cell for q, word in enumerate(words) if word
             for z, cell in enumerate(["cr"] * starts[q] + word)}
    if rules.stationary(cells, grounded=False):
        return None
    source = rules.fold(cells)
    assert source is not None
    upper = builder.independent_columns(source)
    if upper is None:
        raise RuntimeError("列底晶体与连续N/P后缀未生成独立柱制造证书")
    return upper


def _single_stack(builder: Builder, lower: Recipe, target: Shape, *, pins: bool) -> Recipe | None:
    """共用下料一次结算判据；保留旧候选，失败后尝试列内压紧上料。"""
    rules = builder.rules
    collapsed = rules.collapse(rules.cells(lower.result))
    original = rules.cells(collapsed) if collapsed is not None else {}
    desired = rules.cells(target)
    if any(desired.get(pos) != cell for pos, cell in original.items()):
        return None
    delta = {pos: cell for pos, cell in desired.items() if pos not in original}
    if any(cell[0] == "c" or (cell == PIN and not pins) for cell in delta.values()):
        return None
    tops = rules.column_tops(original)
    if any(z <= tops[q] for z, q in delta):
        return None
    blocks = rules.groups(delta)
    if any(not any(z == 0 or (z - 1, q) in desired for z, q in block) for block in blocks):
        return None
    bottom = min((z for z, _ in delta), default=0)
    shifted = {(z - bottom, q): cell for (z, q), cell in delta.items()}
    plain = rules.collapse(shifted)
    if plain is None:
        upper = builder.apply("crystal", builder.base((PIN,) * rules.quadrants), parameter="r")
    elif len(rules.groups(rules.cells(plain))) == len(blocks):
        upper = builder.noncrystal(plain)
    else:
        filled = {}
        for q, top in enumerate(rules.column_tops(shifted)):
            for z in range(top + 1):
                filled[z, q] = shifted.get((z, q), "cr")
        upper = None
        if not rules.stationary(filled, grounded=False):
            source = rules.fold(filled)
            assert source is not None
            upper = builder.independent_columns(source)
        if upper is None:
            upper = _packed_upper(builder, delta)
        if upper is None:
            return None
    if upper is None:
        raise RuntimeError("无晶体下落结果未生成制造证书")
    result = builder.apply("stack", lower, upper)
    if result.result != target:
        raise RuntimeError("单次追加上料与已确认的目标不一致")
    return result


def ordinary_stack(builder: Builder, lower: Recipe, target: Shape) -> Recipe | None:
    """保留不新增针的接口；只虚拟结算下料，实际仍使用原物品执行一次Stack。"""
    return _single_stack(builder, lower, target, pins=False)


def single_stack(builder: Builder, lower: Recipe, target: Shape) -> Recipe | None:
    """新增N/P的单次构造；依次检查无C、原位补C及列内压紧载体。

    下料允许非K或不稳定。每个补C候选均须全体释放并取得独立列制造凭据。
    返回None仅表示必要条件或三种候选未通过，不能判目标全局不可制作。
    """
    return _single_stack(builder, lower, target, pins=True)
