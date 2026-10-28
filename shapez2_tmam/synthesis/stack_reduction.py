"""条件堆叠约化：K_add下料的基础块域，以及直接判据确认的单次N/P上料。"""

from collections.abc import Iterable, Iterator

from .physics import EMPTY, PIN, Position, Rules, Shape
from .recipe import Builder, Recipe
from .support import in_addition_class


def stack_successors(rules: Rules, lower: Shape, known: Iterable[Shape]) -> Iterator[tuple[Shape, Shape]]:
    """给出(上料,结果)；调用方提供同一规则下、普通格统一为Cu的结构目录快照。

    K_add下料使用基础块；一次结算后进入K_add的下料先给出纯C触发料。
    两种替换均保持最终闭包，不要求在原轮数取得同一结果。其余保留真实上料。
    """
    if not in_addition_class(rules, lower):
        settled = rules.collapse(rules.cells(lower))
        if settled is not None and settled != lower and in_addition_class(rules, settled):
            # 纯C单层属于显式可制造种子；在高处全部碎裂，只触发下料的一次结算。
            yield Shape((("cr",) * rules.quadrants,)), settled
            return
        for upper in known:
            result = rules.stack(lower, upper)
            if result is not None and result != lower:
                yield upper, result
        return
    cells = rules.cells(lower)
    n = rules.quadrants
    tops = rules.column_tops(cells)

    def place(columns: tuple[int, ...], cell: str) -> tuple[Shape, Shape] | None:
        """K_add原格不动，单个基础块停在所占列最高阻挡上方。"""
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


def _minimum_levels(limits: list[int], edges: list[tuple[int, int, int]]) -> list[int] | None:
    """求非负差分下界的逐分量最小解；超出逐变量上限或有正环时返回None。"""
    levels = [0] * len(limits)
    for _ in limits:
        changed = False
        for before, after, distance in edges:
            candidate = levels[before] + distance
            if candidate > levels[after]:
                if candidate > limits[after]:
                    return None
                levels[after] = candidate
                changed = True
        if not changed:
            return levels
    return None


def _packed_upper(builder: Builder, delta: dict[Position, str]) -> Recipe | None:
    """列内N/P压紧，差分约束确定最短C前缀；仅接受能全体释放的最小解。"""
    rules = builder.rules
    n = rules.quadrants
    height = max(z for z, _ in delta) + 1
    words: list[list[str]] = [[] for _ in range(n)]
    ranks = {}
    for z in range(height):
        for q in range(n):
            if (cell := delta.get((z, q))) is not None:
                ranks[z, q] = len(words[q])
                words[q].append(cell)
    edges = []
    for q in range(n):
        r = (q + 1) % n
        previous = None
        for z in range(height):
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
    starts = _minimum_levels([rules.height - len(word) for word in words], edges)
    if starts is None:
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


def _layered_upper(builder: Builder, delta: dict[Position, str], blocks: list[set[Position]],
                   *, ground_prefix: bool) -> Recipe | None:
    """按块来源层保留晶体间隙；可将初始针固定为触地前缀以放宽后缀约束。"""
    rules = builder.rules
    height = max(z for z, _ in delta) + 1
    owner = {pos: index for index, block in enumerate(blocks) for pos in block}
    edges = []
    limits = [rules.height - 1] * len(blocks)
    for q in range(rules.quadrants):
        previous = None
        pinned = False
        normal_seen = False
        prefix_length = 0
        for z in range(height):
            pos = z, q
            if pos not in delta:
                continue
            current = owner[pos]
            if previous is not None:
                edges.append((previous, current, 1))
                if pinned:
                    edges.append((current, previous, -1))
            if delta[pos] != PIN:
                normal_seen = True
            elif ground_prefix and not normal_seen:
                limits[current] = prefix_length
                prefix_length += 1
            else:
                pinned = True
            previous = current
        previous = None
        r = (q + 1) % rules.quadrants
        for z in range(height):
            pos = next(((z, column) for column in (q, r)
                        if (z, column) in delta and delta[z, column] != PIN), None)
            if pos is not None:
                current = owner[pos]
                if previous is not None:
                    edges.append((previous, current, 1))
                previous = current
    levels = _minimum_levels(limits, edges)
    if levels is None:
        return None
    placed = {(levels[owner[pos]], pos[1]): cell for pos, cell in delta.items()}
    cells = {(z, q): placed.get((z, q), "cr")
             for q, top in enumerate(rules.column_tops(placed)) for z in range(top + 1)}
    if rules.stationary(cells, grounded=False):
        return None
    source = rules.fold(cells)
    assert source is not None
    upper = builder.independent_columns(source)
    if upper is None:
        raise RuntimeError("针下晶体与连续针后缀未生成独立柱制造证书")
    return upper


def _single_stack(builder: Builder, lower: Recipe, target: Shape, *, pins: bool) -> Recipe | None:
    """共用下料一次结算判据；依次尝试无C、原位补C、列压紧和针下间隙。"""
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
            for ground_prefix in (False, True):
                upper = _layered_upper(builder, delta, blocks, ground_prefix=ground_prefix)
                if upper is not None:
                    break
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
    """新增N/P的单次构造；依次检查无C、原位补C、列压紧和针下间隙载体。

    下料允许非K或不稳定。每个补C候选均须全体释放并取得独立列制造凭据。
    返回None仅表示必要条件或四种候选未通过，不能判目标全局不可制作。
    """
    return _single_stack(builder, lower, target, pins=True)
