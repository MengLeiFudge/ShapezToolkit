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
    """两象限完整判定；其他参数由角、脚手架及同一个双半形入口构造。"""

    def __init__(self, rules: Rules):
        """固定物理规则；缓存只存当前目标分解用到的半形结果。"""
        self.rules = rules
        self.builder = Builder(rules)
        self.halves: dict[Shape, Recipe | None] = {}

    def half(self, target: Shape) -> Recipe | None:
        """四象限五层完整半形；其他参数仅覆盖直接释放或脚手架，失败不判不可解。"""
        n = self.rules.quadrants
        if n < 4:
            raise ValueError("半形构造需要至少四象限")
        if any(cell != EMPTY for row in target.layers for cell in row[n // 2:]):
            raise ValueError("半形构造只接受索引前半；其他方向先旋转")
        if target in self.halves:
            return self.halves[target]
        if n == 4:
            result = CornerBuilder(self.builder).pair(target)
        else:
            result = self._adjacent_pair(target)
            if result is None:
                result = CornerBuilder(self.builder).supported_half(target)
        self.halves[target] = result
        return result

    def paired_halves(self, target: Shape, start: int) -> Recipe | None:
        """按指定切向统一制造两个半形；空侧跳过，不另选独立柱或无C配方。"""
        half = self.rules.quadrants // 2
        if not 0 <= start < half:
            raise ValueError("双半形切向必须位于标准前半面")
        aligned = self.rules.rotate(target, -start)
        recipes = []
        for side in (0, 1):
            cells = {pos: cell for pos, cell in self.rules.cells(aligned).items() if pos[1] // half == side}
            part = self.rules.fold(cells)
            if part is None:
                recipes.append(None)
                continue
            found = self.half(self.rules.rotate(part, half * side))
            if found is None:
                return None
            recipes.append(self.builder.apply("rotate", found, parameter=half * side))
        first, second = recipes
        if first is None:
            recipe = second
        elif second is None:
            recipe = first
        else:
            recipe = self.builder.join(first, second, 0)
        if recipe is None:
            return None
        recipe = self.builder.apply("rotate", recipe, parameter=start)
        if recipe.result != target:
            raise RuntimeError("两半构造证书与目标不一致")
        return recipe

    def _adjacent_pair(self, target: Shape) -> Recipe | None:
        """把至多两根相邻目标列转到标准方向，按同一通用角程序制造。"""
        n = self.rules.quadrants
        columns = {q for row in target.layers for q, cell in enumerate(row) if cell != EMPTY}
        if len(columns) > 2:
            return None
        start = next(q for q in columns if (q - 1) % n not in columns)
        if any(q not in (start, (start + 1) % n) for q in columns):
            return None
        normalized = self.rules.rotate(target, -start)
        recipe = CornerBuilder(self.builder).pair(normalized)
        return self.builder.apply("rotate", recipe, parameter=start) if recipe is not None else None

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

    def check_target(self, target: Shape) -> Result | None:
        """共用供料范围与已证必要条件；通过不代表可制作，也不准备配方。"""
        if any(cell == "cu" for row in target.layers for cell in row):
            return Result("unknown", None, "未确认未着色晶体对应的实体流体供料")
        four_five = self.rules.height == 5 and self.rules.quadrants == 4
        if any(not CornerBuilder.admissible(tuple(row[q] for row in target.layers))
               for q in range(self.rules.quadrants)):
            return Result("unsolvable", None, "目标违反列内针支撑、针前缀或晶体间隙必要条件")
        if four_five and not in_support_class(self.rules, target):
            return Result("unsolvable", None, "四象限五层可制作状态必须通向地面或含针支撑环，目标不属于K")
        return None

    def construct(self, target: Shape) -> Result:
        """返回真实制造树、必要条件的否定，或未覆盖的含晶体目标。"""
        self.halves.clear()
        rejected = self.check_target(target)
        if rejected is not None:
            return rejected
        if not any(cell[0] == "c" for row in target.layers for cell in row):
            recipe = self.builder.noncrystal(target)
            return Result("solved" if recipe else "unsolvable", recipe,
                          "无晶体按层构造" if recipe else "无晶体目标不满足逐层支撑条件")
        if self.rules.quadrants == 2:
            return self._two_quadrant(target)
        if self.rules.quadrants >= 6:
            for start in range(self.rules.quadrants // 2):
                recipe = self.paired_halves(target, start)
                if recipe is not None:
                    return Result("solved", recipe, "通用角及外侧脚手架制造半形，统一拼接完整目标")
        recipe = self.builder.crystal_prefixes(target)
        if recipe is not None:
            return Result("solved", recipe, "独立柱前缀制造后逐层追加")
        if self.rules.quadrants == 4:
            for start in range(2):
                recipe = self.paired_halves(target, start)
                if recipe is not None:
                    return Result("solved", recipe, "逐列角构造的半形拼接")
        recipe = self._replicated(target)
        if recipe is not None:
            return Result("solved", recipe, "相邻象限等宽复制的制造证书")
        return Result("unknown", None, "含晶体目标未被当前局部构造覆盖；尚无完整实用求解器")
