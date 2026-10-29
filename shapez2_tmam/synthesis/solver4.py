"""四象限五层的完整目标逆推；用局部半形构造替代全量半形目录。"""

from itertools import product
from typing import Iterator

from .construct import Constructor, Result
from .inverse import PinFamily, pin_families
from .physics import Rules, Shape
from .pin_constraints import pin_base_possible
from .prefix_closure import minimal_start
from .recipe import Recipe
from .support import in_support_class


class Solver4:
    """穷尽有限 S/顶针尾部，不设置会将未完成搜索误报为不可解的预算。"""

    def __init__(self, rules: Rules | None = None, *, certificate_first: bool = False):
        """共用四象限规则；可选以静止组及块支撑判据代替族的正向Pin检查。"""
        self.rules = rules or Rules(4)
        if self.rules.quadrants != 4 or self.rules.height != 5:
            raise ValueError("完整尾部求解目前限定四象限五层")
        self.constructor = Constructor(self.rules)
        self.builder = self.constructor.builder
        self.certificate_first = certificate_first

    def predecessors(self, target: Shape, *, grounded: bool = False) -> Iterator[Shape]:
        """按非空格前缀生成K中的S前态，保留原层号与全部晶体。"""
        desired = self.rules.cells(target)
        columns = [sorted((z, cell) for (z, column), cell in desired.items() if column == q)
                   for q in range(4)]
        ranges = []
        for column in columns:
            required = max((i + 1 for i, (_, cell) in enumerate(column) if cell[0] == "c"), default=0)
            ranges.append(range(required, len(column) + 1))
        for counts in product(*ranges):
            original = {(z, q): cell for q, count in enumerate(counts) for z, cell in columns[q][:count]}
            source = self.rules.fold(original)
            if source is None or not in_support_class(self.rules, source, grounded=grounded):
                continue
            delta = {pos: cell for pos, cell in desired.items() if pos not in original}
            # 分组只读取新增格；与下料的新接触不能把独立上料块合并。
            if all(any(z == 0 or (z - 1, q) in desired for z, q in block)
                   for block in self.rules.groups(delta)):
                yield source

    def _finish(self, source: Recipe, target: Shape) -> Recipe:
        """把已证明可制作的 S 前态按层追加；失配表示内部证明实现不一致。"""
        result = self.builder.append_noncrystal(source, target)
        if result is None:
            raise RuntimeError("已接受 S 判据及可制作前态，但逐层追加未生成目标")
        return result

    def solve(self, target: Shape) -> Result:
        """返回合法制造树或穷尽后的不可制作；未界定供料颜色仍为 unknown。"""
        self.constructor.halves.clear()
        rejected = self.constructor.check_target(target)
        if rejected is not None:
            return rejected
        highest = max((z for z, row in enumerate(target.layers) if any(cell[0] == "c" for cell in row)), default=-1)
        recipe = self._tail(target, remaining_pins=max(0, highest - 1))
        if recipe is not None:
            return Result("solved", recipe, "统一双半形起点及有界顶针/逐层追加循环")
        return Result("unsolvable", None, "已穷尽局部半形起点及最高晶体推导界内的全部顶针/堆叠尾部")

    def _tail(self, target: Shape, *, skip_start: bool = False, remaining_pins: int = 3) -> Recipe | None:
        """三次尾部Pin界保持覆盖；余量为零仍先完成尚未排除的A→S。"""
        if not skip_start:
            for start in range(2):
                source = minimal_start(self.rules, target, start)
                if source is None:
                    continue
                found = self.constructor.paired_halves(source, start)
                if found is None:
                    raise RuntimeError("强制前缀闭包已证明A起点，但角构造未生成证书")
                return self._finish(found, target)
        if remaining_pins == 0:
            return None
        lowest = min(z for z, row in enumerate(target.layers) if any(cell[0] == "c" for cell in row))
        if not pin_base_possible(target) or not in_support_class(self.rules, target, grounded=True):
            return None
        for pushed in self.predecessors(target, grounded=True):
            # 逐列前缀保持A，grounded筛选已强于K；制造凭据仍由下面的逆推取得。
            for family in pin_families(self.rules, pushed, check_output=not self.certificate_first):
                previous = self._family_recipe(family, lowest, remaining_pins - 1)
                if previous is None:
                    continue
                result = self.builder.apply("pin", previous)
                if result.result != pushed:
                    raise RuntimeError("顶针逆像族成员的制造证书未产生指定中间输出")
                return self._finish(result, target)
        return None

    def _family_recipe(self, family: PinFamily, lowest: int, remaining_pins: int) -> Recipe | None:
        """每族共用两次A→S闭包，失败后只恢复成员的Pin尾部。"""
        template = Shape((*family.lower, tuple("cr" if family.top_crystals & (1 << q) else "Cu"
                                              for q in range(4))))
        desired = self.rules.cells(template)
        for start in range(2):
            initial = minimal_start(self.rules, template, start, optional_top=True)
            if initial is None:
                continue
            direct = self.constructor.paired_halves(initial, start)
            if direct is None:
                raise RuntimeError("可选顶格闭包已证明A起点，但角构造未生成证书")
            selected = self.rules.cells(initial)
            completed = self.rules.fold({pos: cell for pos, cell in desired.items()
                                         if pos[0] < 4 or cell[0] == "c" or pos in selected})
            assert completed is not None
            return self._finish(direct, completed)
        if (remaining_pins == 0 or not pin_base_possible(template)
                or not in_support_class(self.rules, template, grounded=True, optional_top=True)):
            return None
        source_lowest = min(z for z, row in enumerate(template.layers) if any(cell[0] == "c" for cell in row))
        if source_lowest >= lowest:
            raise RuntimeError("顶针逆像没有使最低保留晶体严格降低")
        for source in family.members(self.rules):
            previous = self._tail(source, skip_start=True, remaining_pins=remaining_pins)
            if previous is not None:
                return previous
        return None
