"""四象限五层的完整目标逆推；用局部半形构造替代全量半形目录。"""

from itertools import product
from typing import Iterator

from .construct import Constructor, Result
from .inverse import pin_families
from .physics import Rules, Shape
from .recipe import Recipe


class Solver4:
    """穷尽有限 S/顶针尾部，不设置会将未完成搜索误报为不可解的预算。"""

    def __init__(self, rules: Rules | None = None, *, certificate_first: bool = False):
        """共用四象限规则；可选择先制造候选，再在其真实产物上核对顶针。"""
        self.rules = rules or Rules(4)
        if self.rules.quadrants != 4:
            raise ValueError("完整尾部求解目前限定四象限五层")
        self.constructor = Constructor(self.rules)
        self.builder = self.constructor.builder
        self.certificate_first = certificate_first

    def predecessors(self, target: Shape) -> Iterator[Shape]:
        """按非空格前缀惰性生成全部 S 前态，保留原层号与全部晶体。"""
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
            if source is None:
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
        direct = self.constructor.construct(target)
        if direct.status != "unknown" or any(cell == "cu" for row in target.layers for cell in row):
            return direct
        recipe = self._tail(target)
        if recipe is not None:
            return Result("solved", recipe, "局部半形起点及完整有界顶针/逐层堆叠尾部")
        return Result("unsolvable", None, "已穷尽局部半形起点及最低晶体限制内的全部顶针/堆叠尾部")

    def _tail(self, target: Shape) -> Recipe | None:
        """先尝试零顶针尾部，再深度优先恢复最后一次顶针的真实输入。"""
        for source in self.predecessors(target):
            found = self.constructor.construct(source)
            if found.recipe is not None:
                return self._finish(found.recipe, target)
        lowest = min(z for z, row in enumerate(target.layers) if any(cell[0] == "c" for cell in row))
        if lowest == 0:
            return None
        for pushed in self.predecessors(target):
            # 不可制作的中间输出不能成为尾部节点；unknown 则继续完整逆推。
            if self.constructor.construct(pushed).status == "unsolvable":
                continue
            for family in pin_families(self.rules, pushed, check_output=not self.certificate_first):
                for source in family.members(self.rules):
                    direct = self.constructor.construct(source)
                    if direct.status == "unsolvable":
                        continue
                    source_lowest = min(z for z, row in enumerate(source.layers)
                                        if any(cell[0] == "c" for cell in row))
                    if source_lowest >= lowest:
                        raise RuntimeError("顶针逆像没有使最低保留晶体严格降低")
                    previous = direct.recipe if direct.recipe is not None else self._tail(source)
                    if previous is None:
                        continue
                    if self.certificate_first and self.rules.pin(previous.result) != pushed:
                        continue
                    result = self.builder.apply("pin", previous)
                    if result.result != pushed:
                        raise RuntimeError("顶针逆像族成员的制造证书未产生指定中间输出")
                    return self._finish(result, target)
        return None
