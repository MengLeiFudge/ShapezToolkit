"""四象限切割/顶针逆像的惰性候选族；不把物理逆像当作可制作性证明。"""

from dataclasses import dataclass
from itertools import combinations, product
from typing import Iterator

from .corners import CornerBuilder
from .physics import EMPTY, PIN, Position, Rules, Shape
from .pin_constraints import pin_base_possible, pin_image_matches
from .pin_patterns import SOURCE_PATTERNS


@dataclass(frozen=True)
class PinFamily:
    """前四层和顶层晶体掩码相同的一组前态，族内一次顶针的输出相同。"""

    lower: tuple[tuple[str, ...], ...]
    top_crystals: int

    def members(self, rules: Rules) -> Iterator[Shape]:
        """恢复顶层非晶体的空/N/P 选择；可制作性仍须分别由真实配方确认。"""
        free = [q for q in range(rules.quadrants) if not self.top_crystals & (1 << q)]
        domains = [(EMPTY, "Cu", PIN) if self.lower[-1][q] != EMPTY else (EMPTY, "Cu") for q in free]
        for choices in product(*domains):
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


def _sources_fit(sources: tuple[int, ...] | list[int], retained: list[tuple[int, str]],
                 forced: dict[int, str]) -> bool:
    """抬升后只能向下落，且保留N/P不能穿过同列保留晶体。"""
    return all(z <= r + 1 and not any(z <= crystal <= r for crystal in forced)
               for r, (z, _) in zip(sources, retained))


def pin_column(target: tuple[str, ...], keep_mask: int, crystal_mask: int) -> tuple[str, ...] | None:
    """由两个四位掩码恢复一列前四层；只判结构约束，不计算Pin物理。"""
    if len(target) != 5 or not 0 <= keep_mask < 16 or not 0 <= crystal_mask < 16:
        raise ValueError("顶针单列候选需要五格目标和两个0～15掩码")
    if target[0][0] == "c":
        return None
    new_pin = target[0] == PIN
    retained = [(z, cell) for z, cell in enumerate(target)
                if cell != EMPTY and cell[0] != "c" and not (z == 0 and new_pin)]
    sources = [r for r in range(4) if keep_mask & (1 << r)]
    if len(sources) != len(retained):
        return None
    forced = {z - 1: cell for z, cell in enumerate(target) if cell[0] == "c"}
    forced_mask = sum(1 << r for r in forced)
    if keep_mask & forced_mask or crystal_mask & (keep_mask | forced_mask):
        return None
    if not _sources_fit(sources, retained, forced):
        return None
    column = [forced.get(r, "cr" if crystal_mask & (1 << r) else EMPTY) for r in range(4)]
    for r, (_, cell) in zip(sources, retained):
        column[r] = cell
    result = tuple(column)
    if (result[0] != EMPTY) != new_pin or not CornerBuilder.admissible(result):
        return None
    return result


def _source_patterns(target: tuple[str, ...]) -> tuple[tuple[int, int], ...]:
    """按地面新针及保留NPC数量选固定模式桶；不生成目标图形。"""
    new_pin = target[0] == PIN
    count = sum(cell != EMPTY and cell[0] != "c" and not (z == 0 and new_pin)
                for z, cell in enumerate(target))
    return SOURCE_PATTERNS[int(new_pin)][count] if count <= 4 else ()


def pin_column_at(target: tuple[str, ...], slot: int) -> tuple[str, ...] | None:
    """二十槽直接选址，与电路共用来源模式；空余槽和不合结构的模式返回None。"""
    if len(target) != 5 or not 0 <= slot < 20:
        raise ValueError("顶针单列选址需要五格目标及0～19槽号")
    patterns = _source_patterns(target)
    if slot >= len(patterns):
        return None
    keep, crystals = patterns[slot]
    forced = sum(1 << (z - 1) for z, cell in enumerate(target) if z and cell[0] == "c")
    if forced & ~crystals:
        return None
    extra = crystals & ~forced
    if extra & ((forced << 1) | (forced >> 1)):
        return None
    return pin_column(target, keep, extra)


def pin_families(rules: Rules, target: Shape, *, check_output: bool = True) -> Iterator[PinFamily]:
    """生成覆盖全部可制作顶针前态结构的候选族，默认每族先检查一次正向 Π。

    目标保留格的标签逐格恢复；最终消失的辅助晶体用红色，顶层删除的
    普通块用 Cu。它们的具体标签不影响可制作性的结构判定。
    返回成员未必可制作；族耗尽只表示不存在可制作的顶针前态。
    族内空/N/P 顶盖不能相互替代来证明可制作性；每个成员须另找配方。
    check_output=False 用静止集合及块支撑精确匹配物理输出；调用者仍须取得前态制造证书。
    不保存整个候选集，不调用全图可制作判定，也不隐式接受递归环。
    """
    if rules.quadrants != 4:
        raise ValueError("此逆像生成器当前限定四象限五层")
    if not pin_base_possible(target):
        return
    height = rules.height - 1
    columns: list[list[tuple[str, ...]]] = []
    for q in range(rules.quadrants):
        # Shape省略空顶层；选址仍按五个原层位工作。
        target_column = tuple(target.layers[z][q] if z < len(target.layers) else EMPTY for z in range(5))
        candidates = [column for slot in range(len(_source_patterns(target_column)))
                      if (column := pin_column_at(target_column, slot)) is not None]
        if not candidates:
            return
        columns.append(candidates)
    forced_masks = tuple(sum(1 << r for r, row in enumerate(target.layers[1:]) if row[q][0] == "c")
                         for q in range(4))
    for selected in product(*columns):
        crystal_masks = tuple(sum(1 << r for r, cell in enumerate(column) if cell[0] == "c") for column in selected)
        if any(crystal_masks[q] & crystal_masks[(q + 1) % 4] & (forced_masks[q] ^ forced_masks[(q + 1) % 4])
               for q in range(4)):
            continue
        lower = tuple(tuple(selected[q][z] for q in range(rules.quadrants)) for z in range(height))
        fixed = {(z, q): cell for z, row in enumerate(lower) for q, cell in enumerate(row) if cell != EMPTY}
        capped = [not (forced_masks[q] & 8) and CornerBuilder.admissible((*column, "cr"))
                  for q, column in enumerate(selected)]
        for mask in range(1 << rules.quadrants):
            if any(mask & (1 << q) and not capped[q] for q in range(rules.quadrants)):
                continue
            cells = dict(fixed)
            cells.update({(height, q): "cr" for q in range(rules.quadrants) if mask & (1 << q)})
            representative = rules.fold(cells)
            if representative is None:
                continue
            possible = (rules.pin(representative) == target if check_output
                        else pin_image_matches(rules, lower, mask, target))
            if possible:
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
