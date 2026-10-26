"""直接构造制造证书：两象限完整判定，其他参数未覆盖的含晶体目标返回unknown。"""

from dataclasses import dataclass
from math import gcd

from .corners import CornerBuilder
from .physics import EMPTY, PIN, Rules, Shape
from .recipe import Builder, Recipe
from .support import in_support_class


@dataclass(frozen=True)
class Result:
    """三态结果；unsolvable 必须来自已证必要条件或完整搜索耗尽。"""

    status: str
    recipe: Recipe | None
    reason: str


class Constructor:
    """两象限用完整前缀判据，其余先走独立前缀，再准备四象限半形。"""

    def __init__(self, rules: Rules):
        """固定物理规则；缓存只存当前目标分解用到的半形结果。"""
        self.rules = rules
        self.builder = Builder(rules)
        self.halves: dict[Shape, Recipe | None] = {}

    def half(self, target: Shape) -> Recipe | None:
        """合法颜色范围内精确判半形并生成配方；cu 供料未界定时返回 None。"""
        if self.rules.quadrants != 4 or self.rules.height != 5:
            raise ValueError("逐列半形构造目前限定四象限五层")
        if any(cell != EMPTY for row in target.layers for cell in row[2:]):
            raise ValueError("半形构造只接受索引前半；其他方向先旋转")
        if target in self.halves:
            return self.halves[target]
        corners = CornerBuilder(self.builder)
        if any(cell == "cu" for row in target.layers for cell in row) or not corners.accepts_half(target):
            self.halves[target] = None
            return None
        result = None
        if not any(cell[0] == "c" for row in target.layers for cell in row):
            result = self.builder.noncrystal(target)
            if result is None:
                raise RuntimeError("稳定的无晶体半形未生成逐层制造证书")
        else:
            columns = [tuple(row[q] for row in target.layers) + (EMPTY,) * (5 - len(target.layers))
                       for q in (0, 1)]
            for q in (0, 1):
                if columns[1 - q] != corners.helper(columns[q]):
                    continue
                result = corners.build(columns[q], q, 1 if q == 0 else -1)
                if result is None:
                    raise RuntimeError("目标匹配角助手，但内向角构造未生成证书")
                break
        if result is None:
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
            raise RuntimeError("半形制造证书与通过判据的目标不一致")
        self.halves[target] = result
        return result

    def _replicated(self, target: Shape) -> Recipe | None:
        """按完全相同的相邻列压缩商图；只提升成功证书，不传播商图的否定。"""
        n = self.rules.quadrants
        columns = [tuple(row[q] for row in target.layers) for q in range(n)]
        start = next((q for q in range(n) if columns[q] != columns[(q - 1) % n]), 0)
        factor = n // 2
        length = 1
        for offset in range(1, n):
            if columns[(start + offset) % n] == columns[(start + offset - 1) % n]:
                length += 1
            else:
                factor = gcd(factor, length)
                length = 1
        factor = gcd(factor, length)
        if factor == 1:
            return None
        factors = [factor]
        if n > 4 and n % 4 == 0 and factor % (n // 4) == 0 and factor != n // 4:
            factors.append(n // 4)
        for factor in factors:
            small = Shape(tuple(tuple(row[(start + offset) % n] for offset in range(0, n, factor))
                                for row in target.layers))
            source = Constructor(Rules(n // factor, self.rules.height)).construct(small).recipe
            if source is None:
                continue
            result = self.builder.apply("rotate", self.builder.replicate(source), parameter=start)
            if result.result != target:
                raise RuntimeError("复制商图的制造证书未还原目标朝向与格位")
            return result
        return None

    def _two_quadrant(self, target: Shape) -> Result:
        """对含晶体两象限目标检查充要条件；完整前缀和无C上层直接制造。"""
        if not in_support_class(self.rules, target):
            return Result("unsolvable", None, "两象限可制作目标必须稳定，目标不满足支撑条件")
        highest = max(z for z, row in enumerate(target.layers) if any(cell[0] == "c" for cell in row))
        prefix = Shape(target.layers[:highest + 1])
        for q in range(2):
            column = tuple(row[q] for row in prefix.layers)
            top = max((z for z, cell in enumerate(column) if cell != EMPTY), default=-1)
            if EMPTY in column[:top + 1]:
                return Result("unsolvable", None, "两象限目标在最高晶体以下存在不连续的列前缀")
            crystal = max((z for z, cell in enumerate(column) if cell[0] == "c"), default=-1)
            if crystal >= 0:
                first = next(z for z, cell in enumerate(column) if cell != PIN)
                if PIN in column[first:crystal]:
                    return Result("unsolvable", None, "晶体下方的针不属于触地连续针前缀")
        source = self.builder.independent_columns(prefix)
        if source is None:
            raise RuntimeError("两象限目标通过前缀判据，却未生成独立柱制造证书")
        recipe = self.builder.append_noncrystal(source, target)
        if recipe is None:
            raise RuntimeError("两象限目标通过稳定性判据，却未生成上层追加证书")
        return Result("solved", recipe, "两象限连续前缀制造后逐层追加")

    def construct(self, target: Shape) -> Result:
        """返回真实制造树、必要条件的否定，或未覆盖的含晶体目标。"""
        self.halves.clear()
        if any(cell == "cu" for row in target.layers for cell in row):
            return Result("unknown", None, "未确认未着色晶体对应的实体流体供料")
        fixed_five = self.rules.height == 5 and self.rules.quadrants in (4, 6)
        four_five = self.rules.height == 5 and self.rules.quadrants == 4
        if fixed_five and any(not CornerBuilder.admissible(tuple(row[q] for row in target.layers))
                              for q in range(self.rules.quadrants)):
            return Result("unsolvable", None, "目标违反列内针支撑、针前缀或晶体间隙必要条件")
        if four_five and not in_support_class(self.rules, target):
            return Result("unsolvable", None, "四象限五层可制作状态必须通向地面或含针支撑环，目标不属于K")
        if not any(cell[0] == "c" for row in target.layers for cell in row):
            recipe = self.builder.noncrystal(target)
            return Result("solved" if recipe else "unsolvable", recipe,
                          "无晶体按层构造" if recipe else "无晶体目标不满足逐层支撑条件")
        if self.rules.quadrants == 2:
            return self._two_quadrant(target)
        recipe = self.builder.crystal_prefixes(target)
        if recipe is not None:
            return Result("solved", recipe, "独立柱前缀制造后逐层追加")
        if four_five:
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
        recipe = self._replicated(target)
        if recipe is not None:
            return Result("solved", recipe, "相邻象限等宽复制的制造证书")
        return Result("unknown", None, "含晶体目标未被当前局部构造覆盖；尚无完整实用求解器")
