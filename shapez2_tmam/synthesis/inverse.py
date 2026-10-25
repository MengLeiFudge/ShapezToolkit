"""四象限切割/顶针逆像的惰性候选族；不把物理逆像当作可制作性证明。"""

from dataclasses import dataclass
from itertools import combinations, product
from typing import Iterator

from .corners import CornerBuilder
from .physics import EMPTY, PIN, Position, Rules, Shape


@dataclass(frozen=True)
class PinFamily:
    """前四层和顶层晶体掩码相同的一组前态，族内一次顶针的输出相同。"""

    lower: tuple[tuple[str, ...], ...]
    top_crystals: int

    def members(self, rules: Rules) -> Iterator[Shape]:
        """恢复顶层非晶体的空/N/P 选择；可制作性仍须分别由真实配方确认。"""
        free = [q for q in range(rules.quadrants) if not self.top_crystals & (1 << q)]
        for choices in product((EMPTY, "Cu", PIN), repeat=len(free)):
            top = ["cr" if self.top_crystals & (1 << q) else EMPTY for q in range(rules.quadrants)]
            for q, cell in zip(free, choices):
                top[q] = cell
            rows = (*self.lower, tuple(top))
            if any(not CornerBuilder.admissible(tuple(row[q] for row in rows)) for q in range(rules.quadrants)):
                continue
            cells = {(z, q): cell for z, row in enumerate(rows)
                     for q, cell in enumerate(row) if cell != EMPTY}
            result = rules.fold(cells)
            if result is not None:
                yield result


def pin_families(rules: Rules, target: Shape, *, check_output: bool = True) -> Iterator[PinFamily]:
    """生成覆盖全部可制作顶针前态结构的候选族，默认每族先检查一次正向 Π。

    目标保留格的标签逐格恢复；最终消失的辅助晶体用红色，顶层删除的
    普通块用 Cu。它们的具体标签不影响可制作性的结构判定。
    返回成员未必可制作；族耗尽只表示不存在可制作的顶针前态。
    族内空/N/P 顶盖不能相互替代来证明可制作性；每个成员须另找配方。
    check_output=False 仅生成结构候选；调用者须在取得真实制造证书后再核对输出。
    不保存整个候选集，不调用全图可制作判定，也不隐式接受递归环。
    """
    if rules.quadrants != 4:
        raise ValueError("此逆像生成器当前限定四象限五层")
    if any(cell[0] == "c" for cell in target.layers[0]):
        return
    height = rules.height - 1
    columns: list[list[tuple[str, ...]]] = []
    for q in range(rules.quadrants):
        new_pin = target.layers[0][q] == PIN
        forced = {z - 1: row[q] for z, row in enumerate(target.layers) if row[q][0] == "c"}
        retained = [(z, row[q]) for z, row in enumerate(target.layers)
                    if row[q] != EMPTY and row[q][0] != "c" and not (z == 0 and new_pin)]
        candidates = []
        for sources in combinations(range(height), len(retained)):
            if any(r in forced or z > r + 1 for r, (z, _) in zip(sources, retained)):
                continue
            cells = dict(forced)
            cells.update({r: cell for r, (_, cell) in zip(sources, retained)})
            free = [r for r in range(height) if r not in cells]
            for filling in product((EMPTY, "cr"), repeat=len(free)):
                column = [cells.get(r, EMPTY) for r in range(height)]
                for r, cell in zip(free, filling):
                    column[r] = cell
                if (column[0] != EMPTY) == new_pin and CornerBuilder.admissible(tuple(column)):
                    candidates.append(tuple(column))
        if not candidates:
            return
        columns.append(candidates)
    for selected in product(*columns):
        lower = tuple(tuple(selected[q][z] for q in range(rules.quadrants)) for z in range(height))
        fixed = {(z, q): cell for z, row in enumerate(lower) for q, cell in enumerate(row) if cell != EMPTY}
        capped = [CornerBuilder.admissible((*column, "cr")) for column in selected]
        for mask in range(1 << rules.quadrants):
            if any(mask & (1 << q) and not capped[q] for q in range(rules.quadrants)):
                continue
            cells = dict(fixed)
            cells.update({(height, q): "cr" for q in range(rules.quadrants) if mask & (1 << q)})
            representative = rules.fold(cells)
            if representative is not None and (not check_output or rules.pin(representative) == target):
                yield PinFamily(lower, mask)


@dataclass(frozen=True)
class CutFamily:
    """保留侧固定、晶体融合删除效果固定的一族完整切割输入。"""

    retained: Shape
    deleted: tuple[frozenset[Position], ...]

    def members(self, rules: Rules) -> Iterator[Shape]:
        """生成满足各融合组删除/保护约束的另一半；不替代前态可制作判定。"""
        fixed = rules.cells(self.retained)
        groups = rules.groups(fixed, fused=True)
        dropped = [(z, q) for z in range(rules.height)
                   for q in range(rules.quadrants // 2, rules.quadrants)]
        for values in product((EMPTY, "Cu", PIN, "cr"), repeat=len(dropped)):
            outside = dict(zip(dropped, values))
            valid = True
            for group in groups:
                touched = any(outside.get((z, (q + direction) % rules.quadrants), EMPTY)[0] == "c"
                              for z, q in group for direction in (-1, 1))
                if touched != (frozenset(group) in self.deleted):
                    valid = False
                    break
            if valid:
                cells = dict(fixed)
                cells.update({pos: cell for pos, cell in outside.items() if cell != EMPTY})
                result = rules.fold(cells)
                assert result is not None
                yield result


def cut_families(rules: Rules, target: Shape) -> Iterator[CutFamily]:
    """反推标准前半输出，按保留侧融合分量的删除效果合并候选输入。

    保留晶体不移动；N/P 按列保序，原位高度至少等于目标高度；剩余
    保留侧源格为空或消失的晶体。被切掉半面只通过晶体跨界融合影响
    输出，因此每个可触边晶体分量只需枚举删除/保留两种物理效果。
    返回的族覆盖全部真实可制作前态结构，但族成员本身未获制造证明。
    """
    if rules.quadrants != 4:
        raise ValueError("此逆像生成器当前限定四象限五层")
    half = rules.quadrants // 2
    if any(cell != EMPTY for row in target.layers for cell in row[half:]):
        raise ValueError("切割逆像目标必须只占索引前半；其他方向先旋转到标准方向")
    columns: list[list[tuple[str, ...]]] = []
    for q in range(half):
        forced = {z: row[q] for z, row in enumerate(target.layers) if row[q][0] == "c"}
        retained = [(z, row[q]) for z, row in enumerate(target.layers)
                    if row[q] != EMPTY and row[q][0] != "c"]
        candidates = []
        for sources in combinations(range(rules.height), len(retained)):
            if any(r in forced or z > r for r, (z, _) in zip(sources, retained)):
                continue
            cells = dict(forced)
            cells.update({r: cell for r, (_, cell) in zip(sources, retained)})
            free = [r for r in range(rules.height) if r not in cells]
            for values in product((EMPTY, "cr"), repeat=len(free)):
                column = [cells.get(r, EMPTY) for r in range(rules.height)]
                for r, cell in zip(free, values):
                    column[r] = cell
                candidates.append(tuple(column))
        if not candidates:
            return
        columns.append(candidates)
    target_cells = rules.cells(target)
    for selected in product(*columns):
        cells = {(z, q): selected[q][z] for z in range(rules.height) for q in range(half)
                 if selected[q][z] != EMPTY}
        source = rules.fold(cells)
        if source is None:
            continue
        groups = rules.groups(cells, fused=True)
        # 含目标晶体的分量不能删除；其余分量均有保留侧外边界可触及。
        removable = [group for group in groups
                     if not any(target_cells.get(pos, EMPTY)[0] == "c" for pos in group)]
        for flags in product((False, True), repeat=len(removable)):
            deleted = tuple(frozenset(group) for group, remove in zip(removable, flags) if remove)
            vanished = set().union(*deleted)
            live = {pos: cell for pos, cell in cells.items() if pos not in vanished}
            if rules.collapse(live) == target:
                yield CutFamily(source, deleted)
