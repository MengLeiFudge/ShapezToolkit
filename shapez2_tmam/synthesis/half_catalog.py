"""按切后半形合并交换候选；凭据保留原输入，避免额外执行一次重力。"""

from .physics import Shape
from .recipe import Builder, Recipe


class HalfCatalog:
    """增量登记已知配方；缺少目标半形凭据只表示尚未覆盖。"""

    def __init__(self, builder: Builder):
        self.builder = builder
        self.fronts: dict[Shape | None, Recipe] = {}
        self.backs: dict[Shape | None, Recipe] = {}

    def add(self, recipe: Recipe) -> None:
        """双出口各保留最低成本原输入；后半只旋转索引键，不旋转使用凭据。"""
        rules = self.builder.rules
        half = rules.quadrants // 2
        for start in range(rules.quadrants):
            source = self.builder.apply("rotate", recipe, parameter=-start)
            front, back = rules.cut(source.result)
            back = rules.rotate(back, half) if back is not None else None
            for table, key in ((self.fronts, front), (self.backs, back)):
                previous = table.get(key)
                if previous is None or source.step_count < previous.step_count:
                    table[key] = source

    def join(self, target: Shape) -> Recipe | None:
        """投影目标的n个有向半面，选两表中总成本最低的真实交换配方。"""
        rules = self.builder.rules
        half = rules.quadrants // 2
        best: tuple[Recipe, Recipe, int] | None = None
        best_cost = None
        for start in range(rules.quadrants):
            aligned = rules.rotate(target, -start)
            cells = rules.cells(aligned)
            front = rules.fold({pos: cell for pos, cell in cells.items() if pos[1] < half})
            back = rules.fold({(z, q - half): cell for (z, q), cell in cells.items() if q >= half})
            first, second = self.fronts.get(front), self.backs.get(back)
            if first is None or second is None:
                continue
            cost = first.step_count + second.step_count + 1 + (aligned != target)
            if best_cost is None or cost < best_cost:
                best, best_cost = (first, second, start), cost
        if best is None:
            return None
        first, second, start = best
        result = self.builder.apply("swap", first, second, parameter=0)
        result = self.builder.apply("rotate", result, parameter=start)
        if result.result != target:
            raise RuntimeError("半形凭据的交换结果与目标投影不一致")
        return result
