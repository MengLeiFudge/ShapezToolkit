"""无需完整可制作状态库的局部构造；未覆盖的含晶体目标明确返回 unknown。"""

from dataclasses import dataclass

from .corners import CornerBuilder
from .physics import EMPTY, Rules, Shape
from .recipe import Builder, Recipe


@dataclass(frozen=True)
class Result:
    """三态结果；unsolvable 必须来自已证必要条件或完整搜索耗尽。"""

    status: str
    recipe: Recipe | None
    reason: str


class Constructor:
    """先走独立前缀构造，再通过逐列角构造准备四象限半形。"""

    def __init__(self, rules: Rules):
        """固定物理规则；缓存只存当前目标分解用到的半形结果。"""
        self.rules = rules
        self.builder = Builder(rules)
        self.halves: dict[Shape, Recipe | None] = {}

    def half(self, target: Shape) -> Recipe | None:
        """合法颜色范围内精确判半形并生成配方；cu 供料未界定时返回 None。"""
        if self.rules.quadrants != 4:
            raise ValueError("逐列半形构造目前限定四象限")
        if any(cell != EMPTY for row in target.layers for cell in row[2:]):
            raise ValueError("半形构造只接受索引前半；其他方向先旋转")
        if target in self.halves:
            return self.halves[target]
        corners = CornerBuilder(self.builder)
        if any(cell == "cu" for row in target.layers for cell in row) or not corners.accepts_half(target):
            self.halves[target] = None
            return None
        prepared = []
        for q in (0, 1):
            column = tuple(row[q] for row in target.layers)
            if all(cell == EMPTY for cell in column):
                continue
            recipe = corners.build(column, q, -1 if q == 0 else 1)
            if recipe is None:
                raise RuntimeError("目标已满足半形判据，但角构造未生成证书")
            prepared.append(recipe)
        source = prepared[0] if len(prepared) == 1 else self.builder.join(prepared[0], prepared[1], 3)
        result = self.builder.window(source, 0)
        if result.result != target:
            raise RuntimeError("两角拼接结果与通过判据的目标半形不一致")
        self.halves[target] = result
        return result

    def construct(self, target: Shape) -> Result:
        """返回真实制造树、必要条件的否定，或未覆盖的含晶体目标。"""
        self.halves.clear()
        if any(cell == "cu" for row in target.layers for cell in row):
            return Result("unknown", None, "未确认未着色晶体对应的实体流体供料")
        if any(not CornerBuilder.admissible(tuple(row[q] for row in target.layers))
               for q in range(self.rules.quadrants)):
            return Result("unsolvable", None, "目标违反列内针支撑、针前缀或晶体间隙必要条件")
        if self.rules.quadrants == 4 and self.rules.collapse(self.rules.cells(target)) != target:
            return Result("unsolvable", None, "四象限五层可制作状态必须稳定，目标重新分组后会下落")
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
                return Result("solved", recipe, "逐列角构造的半形拼接")
        return Result("unknown", None, "含晶体目标未被当前局部构造覆盖；尚无完整实用求解器")
