"""任意Stack的下料结算摘要、上料块序列及保留原输入的制造凭据。"""

from dataclasses import dataclass
from typing import Iterator

from .physics import EMPTY, PIN, Position, Rules, Shape
from .recipe import Builder, Recipe
from .stack_reduction import ordered_carriers

Piece = tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class StackPlan:
    """上料可能保留的有序N/P块；此序列不是一份可直接送入机器的物品。"""

    quadrants: int
    pieces: tuple[Piece, ...]

    def apply(self, rules: Rules, settled: Shape | None) -> Shape | None:
        """从下料的一次结算结果更新列顶；超高块仍阻挡后续块。"""
        if rules.quadrants != self.quadrants:
            raise ValueError("上料摘要与当前象限数不一致")
        cells = rules.cells(settled) if settled is not None else {}
        tops = rules.column_tops(cells)
        for level, piece in self._landings(tops):
            if level < rules.height:
                for q, cell in piece:
                    cells[level, q] = cell
        return rules.fold(cells)

    def noncrystal_carrier(self, rules: Rules) -> Shape | None:
        """同摘要无C实体的唯一候选；空摘要或落地后块合并时返回None。"""
        source = self.apply(rules, None)
        if source is None or len(rules.groups(rules.cells(source))) != len(self.pieces):
            return None
        return source

    def carrier_orders(self) -> Iterator[tuple[Piece, ...]]:
        """原规范序及同秩三着色序；只重排互不占同列的块。"""
        yield self.pieces
        ranks = [0] * self.quadrants
        colors: dict[tuple[int, int], int] = {}
        buckets: list[list[list[Piece]]] = []
        for piece in self.pieces:
            rank = 1 + max(ranks[q] for q, _ in piece)
            for q, _ in piece:
                ranks[q] = rank
            color = 0
            if piece[0][1] != PIN:
                adjacent = {colors.get((rank, (q + direction) % self.quadrants))
                            for q, _ in piece for direction in (-1, 1)}
                # 普通块是环上区间，同秩时至多接触两个其他普通块。
                color = next(value for value in range(3) if value not in adjacent)
                for q, _ in piece:
                    colors[rank, q] = color
            while len(buckets) < rank:
                buckets.append([[], [], []])
            buckets[rank - 1][color].append(piece)
        colored = tuple(piece for rank in buckets for color in rank for piece in color)
        if colored != self.pieces:
            yield colored

    def _landings(self, tops: list[int]) -> Iterator[tuple[int, Piece]]:
        """复制起始列顶，逐块更新；来源序列已经排除固定的高处障碍。"""
        tops = tops.copy()
        for piece in self.pieces:
            level = 1 + max(tops[q] for q, _ in piece)
            for q, _ in piece:
                tops[q] = level
            yield level, piece

    def _matches(self, height: int, tops: list[int], delta: dict[Position, str]) -> bool:
        """目录已确认下料格保留且不新增C；按不可撤销的新增格拒绝不符前缀。"""
        added = 0
        for level, piece in self._landings(tops):
            if level >= height:
                continue
            if any(delta.get((level, q)) != cell for q, cell in piece):
                return False
            added += len(piece)
        return added == len(delta)


def stack_plan(rules: Rules, upper: Shape) -> StackPlan:
    """空地面种子求上料静止组，再剔除必超高块，规范化独立块的顺序。"""
    cells = rules.cells(upper)
    fixed = rules.stationary(cells, grounded=False)
    blocked = [rules.height] * rules.quadrants
    for z, q in fixed:
        blocked[q] = min(blocked[q], z)
    moving = {pos: cell for pos, cell in cells.items() if pos not in fixed and cell[0] != "c"}
    ranks = [0] * rules.quadrants
    pieces = []
    for block in rules.groups(moving):
        source = min(block)[0]
        columns = tuple(sorted(q for _, q in block))
        if any(blocked[q] < source for q in columns):
            for q in columns:
                blocked[q] = min(blocked[q], source)
            continue
        rank = 1 + max(ranks[q] for q in columns)
        for q in columns:
            ranks[q] = rank
        pieces.append((rank, tuple((q, moving[source, q]) for q in columns)))
    return StackPlan(rules.quadrants, tuple(piece for _, piece in sorted(pieces)))


class StackCatalog:
    """按两类摘要合并已知配方；只在已有凭据范围内查找目标的最后一次Stack。"""

    def __init__(self, builder: Builder):
        self.builder = builder
        self.lowers: dict[Shape | None, Recipe] = {}
        self.uppers: dict[StackPlan, Recipe] = {}

    def add(self, recipe: Recipe) -> None:
        """每个摘要按步数、槽数取优；首次登记尝试同摘要的简化上料。"""
        rules = self.builder.rules
        if recipe.height != rules.height or len(recipe.result.layers[0]) != rules.quadrants:
            raise ValueError("堆叠凭据必须与目录的物理配置一致")
        settled = rules.collapse(rules.cells(recipe.result))
        previous = self.lowers.get(settled)
        if previous is None or (recipe.step_count, recipe.register_count) < (previous.step_count, previous.register_count):
            self.lowers[settled] = recipe
        plan = stack_plan(rules, recipe.result)
        previous = self.uppers.get(plan)
        upper = recipe
        if previous is None:
            if not plan.pieces:
                upper = self.builder.apply("crystal", self.builder.base((PIN,) * rules.quadrants), parameter="r")
            elif len(plan.pieces) == 1:
                values = dict(plan.pieces[0])
                upper = self.builder.base(tuple(values.get(q, EMPTY) for q in range(rules.quadrants)))
            elif (source := plan.noncrystal_carrier(rules)) is not None:
                compact = self.builder.noncrystal(source)
                if compact is None:
                    raise RuntimeError("上料摘要的无合并落点未生成无晶体制造证书")
                if (compact.step_count, compact.register_count) < (upper.step_count, upper.register_count):
                    upper = compact
            else:
                for pieces in plan.carrier_orders():
                    for compact in ordered_carriers(self.builder, pieces):
                        if (compact.step_count, compact.register_count) < (upper.step_count, upper.register_count):
                            upper = compact
        if previous is None or (upper.step_count, upper.register_count) < (previous.step_count, previous.register_count):
            self.uppers[plan] = upper

    def construct(self, target: Shape) -> Recipe | None:
        """选总步数最少、同长槽数最少的精确命中，缺失仅返回None。"""
        rules = self.builder.rules
        desired = rules.cells(target)
        best: tuple[Recipe, Recipe] | None = None
        best_cost = None
        for settled, lower in self.lowers.items():
            original = rules.cells(settled) if settled is not None else {}
            if (any(desired.get(pos) != cell for pos, cell in original.items())
                    or any(cell[0] == "c" and original.get(pos) != cell for pos, cell in desired.items())):
                continue
            delta = {pos: cell for pos, cell in desired.items() if pos not in original}
            tops = rules.column_tops(original)
            if any(z <= tops[q] for z, q in delta):
                continue
            for plan, upper in self.uppers.items():
                slots = max(lower.register_count, upper.register_count) + (lower.register_count == upper.register_count)
                cost = (lower.step_count + upper.step_count + 1, slots)
                if best_cost is not None and cost >= best_cost:
                    continue
                if plan._matches(rules.height, tops, delta):
                    best, best_cost = (lower, upper), cost
        if best is None:
            return None
        result = self.builder.apply("stack", *best)
        if result.result != target:
            raise RuntimeError("堆叠摘要与原输入的加工结果不一致")
        return result
