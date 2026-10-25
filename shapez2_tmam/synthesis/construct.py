"""无需完整可制作状态库的局部构造；未覆盖的含晶体目标明确返回 unknown。"""

from dataclasses import dataclass
from itertools import product

from .inverse import CutFamily, cut_families
from .physics import EMPTY, PIN, Rules, Shape
from .recipe import Builder, Recipe


@dataclass(frozen=True)
class Result:
    """三态结果；只有已证明无晶体判据失败时才给出 unsolvable。"""

    status: str
    recipe: Recipe | None
    reason: str


class Constructor:
    """先走无搜索构造，再尝试四象限直接半切及辅助支撑转交。"""

    def __init__(self, rules: Rules):
        """固定物理规则；缓存只存当前目标分解用到的半形结果。"""
        self.rules = rules
        self.builder = Builder(rules)
        self.halves: dict[Shape, Recipe | None] = {}
        self.direct_halves: dict[Shape, Recipe | None] = {}

    def _cut_witness(self, family: CutFamily) -> Recipe | None:
        """给每个删除分量安排一个外侧晶体，其余外侧格用普通辅助材料。"""
        cells = self.rules.cells(family.retained)
        for q in (2, 3):
            cells.update({(z, q): "Cu" for z in range(self.rules.height)})
        for group in family.deleted:
            z, q = min(group)
            cells[z, 3 if q == 0 else 2] = "cr"
        halves = []
        for main, auxiliary in ((0, 3), (1, 2)):
            half = self.rules.fold({pos: cell for pos, cell in cells.items()
                                    if pos[1] in (main, auxiliary)})
            assert half is not None
            if any(row[main][0] == "c" for row in half.layers):
                recipe = self.builder.crystal_prefixes(half)
            else:
                recipe = self.builder.noncrystal(half)
            if recipe is None:
                return None
            halves.append(recipe)
        source = self.builder.join(halves[0], halves[1], 3)
        return self.builder.window(source, 0)

    def _direct_half(self, target: Shape) -> Recipe | None:
        """只尝试独立柱及一次半切，辅助转交调用此入口以避免递归。"""
        if self.rules.quadrants != 4:
            raise ValueError("单次删除的半形构造目前限定四象限")
        if any(cell != EMPTY for row in target.layers for cell in row[2:]):
            raise ValueError("半形构造只接受索引前半；其他方向先旋转")
        if target in self.direct_halves:
            return self.direct_halves[target]
        if not any(cell[0] == "c" for row in target.layers for cell in row):
            result = self.builder.noncrystal(target)
            self.direct_halves[target] = result
            return result
        result = self.builder.crystal_prefixes(target)
        if result is None:
            for family in cut_families(self.rules, target):
                result = self._cut_witness(family)
                if result is not None:
                    if result.result != target:
                        raise RuntimeError("半形构造证书与目标不一致")
                    break
        self.direct_halves[target] = result
        return result

    def half(self, target: Shape) -> Recipe | None:
        """尝试直接构造和一次辅助转交；失败仍表示 unknown。"""
        if target in self.halves:
            return self.halves[target]
        result = self._direct_half(target)
        if result is None:
            result = self._relay_half(target)
        self.halves[target] = result
        return result

    def _relay_half(self, target: Shape) -> Recipe | None:
        """先分别用外侧 N/P 柱准备两列，再拼接、移走临时支撑。"""
        for anchor in (0, 1):
            fixed_auxiliary = 3 if anchor == 0 else 2
            fixed_cells = {pos: cell for pos, cell in self.rules.cells(target).items() if pos[1] == anchor}
            fixed_cells.update({(z, fixed_auxiliary): "Cu" for z in range(self.rules.height)})
            fixed_shape = self.rules.fold(fixed_cells)
            assert fixed_shape is not None
            fixed = self.builder.crystal_prefixes(fixed_shape)
            if fixed is None:
                continue
            main = 1 - anchor
            auxiliary = 3 if main == 0 else 2
            start = 3 if main == 0 else 1
            main_cells = {pos: cell for pos, cell in self.rules.cells(target).items() if pos[1] == main}
            if not main_cells:
                continue
            for support in product(("Cu", PIN), repeat=self.rules.height):
                cells = dict(main_cells)
                cells.update({(z, auxiliary): cell for z, cell in enumerate(support)})
                corner = self.rules.fold(cells)
                assert corner is not None
                normalized = self.rules.rotate(corner, -start)
                prepared = self._direct_half(normalized)
                if prepared is None:
                    continue
                prepared = self.builder.apply("rotate", prepared, parameter=start)
                source = self.builder.join(prepared, fixed, start)
                if self.rules.cut(source.result)[0] == target:
                    return self.builder.window(source, 0)
        return None

    def construct(self, target: Shape) -> Result:
        """返回真实制造树，或精确否定无晶体目标，或承认局部构造尚未覆盖。"""
        self.halves.clear()
        self.direct_halves.clear()
        if any(cell == "cu" for row in target.layers for cell in row):
            return Result("unknown", None, "未确认未着色晶体对应的实体流体供料")
        if not any(cell[0] == "c" for row in target.layers for cell in row):
            recipe = self.builder.noncrystal(target)
            return Result("solved" if recipe else "unsolvable", recipe,
                          "无晶体按层构造" if recipe else "无晶体目标不满足逐层支撑条件")
        recipe = self.builder.crystal_prefixes(target)
        if recipe is not None:
            return Result("solved", recipe, "独立柱前缀制造后逐层追加")
        if self.rules.quadrants == 4:
            for start in range(2):
                aligned = self.rules.rotate(target, -start)
                recipes = []
                for side in (0, 1):
                    cells = {pos: cell for pos, cell in self.rules.cells(aligned).items()
                             if pos[1] // 2 == side}
                    part = self.rules.fold(cells)
                    if part is None:
                        recipes.append(None)
                        continue
                    normalized = self.rules.rotate(part, 2 * side)
                    found = self.half(normalized)
                    if found is None:
                        break
                    recipes.append(self.builder.apply("rotate", found, parameter=2 * side))
                if len(recipes) != 2:
                    continue
                first, second = recipes
                if first is None:
                    recipe = second
                elif second is None:
                    recipe = first
                else:
                    recipe = self.builder.join(first, second, 0)
                assert recipe is not None
                recipe = self.builder.apply("rotate", recipe, parameter=start)
                if recipe.result != target:
                    raise RuntimeError("两半构造证书与目标不一致")
                return Result("solved", recipe, "直接或辅助转交的半形构造后拼接")
        return Result("unknown", None, "含晶体目标未被当前局部构造覆盖；尚无完整实用求解器")
