"""按切后半形合并交换候选；凭据保留原输入，避免额外执行一次重力。"""

from .physics import Shape
from .recipe import Builder, Recipe


class HalfCatalog:
    """增量登记已知配方；缺少目标半形凭据只表示尚未覆盖。"""

    def __init__(self, builder: Builder):
        self.builder = builder
        self.sources: dict[Shape | None, Recipe] = {}

    def add(self, recipe: Recipe) -> None:
        """登记所有单象限旋转的前半结果，包括有非空来源凭据的空半形。"""
        for start in range(self.builder.rules.quadrants):
            source = self.builder.apply("rotate", recipe, parameter=-start)
            front, _ = self.builder.rules.cut(source.result)
            self.sources.setdefault(front, source)

    def join(self, target: Shape) -> Recipe | None:
        """直接投影目标并查询k条直径；实际交换使用原输入，不使用切后结果。"""
        rules = self.builder.rules
        half = rules.quadrants // 2
        for start in range(half):
            aligned = rules.rotate(target, -start)
            cells = rules.cells(aligned)
            front = rules.fold({pos: cell for pos, cell in cells.items() if pos[1] < half})
            back = rules.fold({(z, q - half): cell for (z, q), cell in cells.items() if q >= half})
            first, second = self.sources.get(front), self.sources.get(back)
            if first is None or second is None:
                continue
            second = self.builder.apply("rotate", second, parameter=half)
            result = self.builder.apply("swap", first, second, parameter=0)
            result = self.builder.apply("rotate", result, parameter=start)
            if result.result != target:
                raise RuntimeError("半形凭据的交换结果与目标投影不一致")
            return result
        return None
