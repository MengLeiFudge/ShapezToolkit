"""任意Stack的下料结算摘要、上料块序列及保留原输入的制造凭据。"""

from dataclasses import dataclass

from .physics import EMPTY, PIN, Rules, Shape
from .recipe import Builder, Recipe


@dataclass(frozen=True)
class StackPlan:
    """上料可能保留的有序N/P块；此序列不是一份可直接送入机器的物品。"""

    quadrants: int
    pieces: tuple[tuple[tuple[int, str], ...], ...]

    def apply(self, rules: Rules, settled: Shape | None) -> Shape | None:
        """从下料的一次结算结果更新列顶；超高块仍阻挡后续块。"""
        if rules.quadrants != self.quadrants:
            raise ValueError("上料摘要与当前象限数不一致")
        cells = rules.cells(settled) if settled is not None else {}
        tops = [max((z for z, column in cells if column == q), default=-1) for q in range(self.quadrants)]
        for piece in self.pieces:
            level = 1 + max(tops[q] for q, _ in piece)
            for q, cell in piece:
                tops[q] = level
                if level < rules.height:
                    cells[level, q] = cell
        return rules.fold(cells)


def stack_plan(rules: Rules, upper: Shape) -> StackPlan:
    """空地面种子求上料静止组，再剔除必超高块，规范化独立块的顺序。"""
    cells = rules.cells(upper)
    groups = rules.groups(cells)
    owner = {pos: index for index, group in enumerate(groups) for pos in group}
    edges: list[set[int]] = [set() for _ in groups]
    for (z, q), index in owner.items():
        below = owner.get((z - 1, q))
        if below is not None and below != index:
            edges[index].add(below)
    fixed = set(range(len(groups)))
    while True:
        following = {index for index in fixed if edges[index] & fixed}
        if following == fixed:
            break
        fixed = following
    blocked = [min((z for (z, column), index in owner.items() if column == q and index in fixed), default=rules.height)
               for q in range(rules.quadrants)]
    moving = {pos: cell for pos, cell in cells.items() if owner[pos] not in fixed and cell[0] != "c"}
    ranks = [0] * rules.quadrants
    pieces = []
    for block in sorted(rules.groups(moving), key=min):
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
        """保留原下料；空或单块上料摘要改用已证明等价的基础配方。"""
        rules = self.builder.rules
        if recipe.height != rules.height or len(recipe.result.layers[0]) != rules.quadrants:
            raise ValueError("堆叠凭据必须与目录的物理配置一致")
        settled = rules.collapse(rules.cells(recipe.result))
        self.lowers.setdefault(settled, recipe)
        plan = stack_plan(rules, recipe.result)
        upper = recipe
        if not plan.pieces:
            upper = self.builder.apply("crystal", self.builder.base((PIN,) * rules.quadrants), parameter="r")
        elif len(plan.pieces) == 1:
            values = dict(plan.pieces[0])
            upper = self.builder.base(tuple(values.get(q, EMPTY) for q in range(rules.quadrants)))
        self.uppers.setdefault(plan, upper)

    def construct(self, target: Shape) -> Recipe | None:
        """求值已知摘要对；命中后用原输入凭据实际生成制造树，缺失仅返回None。"""
        desired = self.builder.rules.cells(target)
        for settled, lower in self.lowers.items():
            original = self.builder.rules.cells(settled) if settled is not None else {}
            if (any(desired.get(pos) != cell for pos, cell in original.items())
                    or any(cell[0] == "c" and original.get(pos) != cell for pos, cell in desired.items())):
                continue
            for plan, upper in self.uppers.items():
                if plan.apply(self.builder.rules, settled) != target:
                    continue
                result = self.builder.apply("stack", lower, upper)
                if result.result != target:
                    raise RuntimeError("堆叠摘要与原输入的加工结果不一致")
                return result
        return None
