"""四象限五层的逐列角构造：目标列旁保留一根不含晶体的辅助柱。"""

from .physics import EMPTY, PIN, Shape
from .recipe import Builder, Recipe


class CornerBuilder:
    """以普通辅助材料、融合删除和一次顶破处理列内间隙。"""

    def __init__(self, builder: Builder):
        """共用已有制造树与物理配置，角构造仅启用四象限五层。"""
        if builder.rules.quadrants != 4 or builder.rules.height != 5:
            raise ValueError("此角构造限定四象限五层")
        self.builder = builder
        self.rules = builder.rules

    @staticmethod
    def admissible(cells: tuple[str, ...]) -> bool:
        """检查针前缀、晶体间隙及独立针的直接支撑这些列内必要条件。"""
        prefix = 0
        while prefix < len(cells) and cells[prefix] == PIN:
            prefix += 1
        crystals = [z for z, cell in enumerate(cells) if cell[0] == "c"]
        for z, cell in enumerate(cells):
            if cell == PIN and z and cells[z - 1] == EMPTY:
                return False
        for z in crystals:
            if any(cells[r] == PIN for r in range(prefix, z)):
                return False
            if z and cells[z - 1] == EMPTY:
                below = next((cells[r] for r in range(z - 1, -1, -1) if cells[r] != EMPTY), EMPTY)
                if below == EMPTY or below == PIN or below[0] == "c":
                    return False
        for lower, upper in zip(crystals, crystals[1:]):
            between = cells[lower + 1:upper]
            if EMPTY in between:
                ordinary = sum(cell != EMPTY and cell != PIN and cell[0] != "c" for cell in between)
                if ordinary < 2 or cells[lower + 1] == EMPTY:
                    return False
        return True

    def accepts_half(self, target: Shape) -> bool:
        """局部半形判据：逐列条件成立，每个新分组均触地或有外部直接阻挡。"""
        if any(cell != EMPTY for row in target.layers for cell in row[2:]):
            raise ValueError("半形判据只接受索引前半")
        if any(not self.admissible(tuple(row[q] for row in target.layers)) for q in (0, 1)):
            return False
        return self.stable_half(tuple(row[:2] for row in target.layers))

    @staticmethod
    def stable_half(rows: tuple[tuple[str, ...], ...]) -> bool:
        """两列每层至多一个非针组；沿晶体竖边扫描各组的外部支撑。"""
        if not rows or any(len(row) != 2 for row in rows):
            raise ValueError("半形稳定性需要非空的两列原层位网格")
        links = [False] + [any(rows[z][q][0] == "c" and rows[z - 1][q][0] == "c"
                               for q in (0, 1)) for z in range(1, len(rows))]
        supported = False
        for z, row in enumerate(rows):
            nonpins = [q for q in (0, 1) if row[q] not in (EMPTY, PIN)]
            if z and any(row[q] == PIN and rows[z - 1][q] == EMPTY for q in (0, 1)):
                return False
            if not links[z]:
                supported = z == 0 or any(rows[z - 1][q] != EMPTY for q in nonpins)
            else:
                supported |= any(rows[z - 1][q] == PIN for q in nonpins)
            if nonpins and not supported and (z + 1 == len(rows) or not links[z + 1]):
                return False
        return True

    @staticmethod
    def helper(cells: tuple[str, ...]) -> tuple[str, ...]:
        """返回角构造最终保留的五格助手；普通格固定为Cu，供精确半形匹配。"""
        word = "".join("-" if cell == EMPTY else "P" if cell == PIN else "C" if cell[0] == "c" else "N"
                       for cell in cells).ljust(5, "-")
        if word.startswith("-N-C"):
            return (PIN, "Cu", PIN, "Cu", "Cu")
        if word == "-N--C":
            return (PIN, "Cu", PIN, PIN, "Cu")
        if word in ("N-N-C", "P-N-C", "--N-C"):
            return (PIN, "Cu", "Cu", PIN, "Cu")
        helper = ["Cu"] * 5
        for z in range(1, len(cells)):
            if cells[z][0] == "c" and cells[z - 1] == EMPTY:
                helper[z - 1] = PIN
        return tuple(helper)

    def _shape(self, main: tuple[str, ...], helper: tuple[str, ...], near: int) -> Shape:
        """主列固定为 q0，辅助列为 q1 或 q3，保留空底层。"""
        cells = {(z, q): cell for q, column in ((0, main), (near, helper))
                 for z, cell in enumerate(column) if cell != EMPTY}
        shape = self.rules.fold(cells)
        assert shape is not None
        return shape

    def build(self, cells: tuple[str, ...], quadrant: int, direction: int) -> Recipe | None:
        """制造指定列及其顺/逆时针相邻 N/P 助手；不消耗外部晶体原料。"""
        if not 0 <= quadrant < 4 or direction not in (-1, 1) or len(cells) > 5:
            raise ValueError("角构造需要 q0～q3、相邻方向 ±1 和至多五格")
        cells = cells + (EMPTY,) * (5 - len(cells))
        if all(cell == EMPTY for cell in cells) or "cu" in cells or not self.admissible(cells):
            return None
        near = direction % 4
        word = "".join("-" if cell == EMPTY else "P" if cell == PIN else "C" if cell[0] == "c" else "N"
                       for cell in cells)
        if word.startswith("-N-C") or word in ("N-N-C", "P-N-C", "--N-C", "-N--C"):
            result = self._pin_corner(cells, word, near)
        else:
            result = self._simple_corner(cells, near)
        return self.builder.apply("rotate", result, parameter=quadrant) if result is not None else None

    def _simple_corner(self, cells: tuple[str, ...], near: int) -> Recipe | None:
        """在 N 隔断间填辅助晶体，必要时将一格 N 的来源提高到间隙顶端。"""
        top = max((z for z, cell in enumerate(cells) if cell[0] == "c"), default=-1)
        helper = self.helper(cells)
        if top < 0:
            return self.builder.noncrystal(self._shape(cells, helper, near))
        source = list(cells)
        for z in range(1, top + 1):
            if cells[z][0] != "c" or cells[z - 1] != EMPTY:
                continue
            lower = next((r for r in range(z - 1, -1, -1) if cells[r] != EMPTY), -1)
            if lower < 0 or (lower and cells[lower - 1] == EMPTY):
                return None
            source[z - 1], source[lower] = cells[lower], EMPTY
        deleted = {z for z in range(top + 1) if source[z] == EMPTY}
        for z in deleted:
            source[z] = "cr"
        retained = self._shape(tuple(source), helper, near)
        groups = self.rules.groups(self.rules.cells(retained), fused=True)
        if any(any(q == 0 and z in deleted for z, q in group)
               and any(q == 0 and cells[z][0] == "c" for z, q in group) for group in groups):
            return None
        prepared = self.builder.crystal_prefixes(retained)
        if prepared is None:
            return None
        start = 0 if near == 1 else 3
        if deleted:
            far = (4 - near) % 4
            support = self.builder.column(tuple("cr" if z in deleted else "Cu" for z in range(5)), far)
            assert support is not None
            prepared = self.builder.join(prepared, support, start)
            prepared = self.builder.window(prepared, start)
        expected = self._shape(cells, helper, near)
        return prepared if prepared.result == expected else None

    def _pin_corner(self, cells: tuple[str, ...], word: str, near: int) -> Recipe | None:
        """两次转交支撑后顶破远侧晶体脊，再为目标列补齐永久 N/P 助手。"""
        far = (4 - near) % 4
        start = 0 if near == 1 else 3
        opposite_start = 3 if near == 1 else 0
        extra = None
        if word.startswith("-N-C"):
            crystal_level = 4
            main = (EMPTY, cells[1], cells[3])
            if word[4] == "C":
                main += (cells[4],)
            elif word[4] in "NP":
                extra = cells[4]
            anchor = ("cr", "Cu")
            tail = (PIN, "Cu", "Cu")
        else:
            crystal_level = 5
            if word == "N-N-C":
                main = (EMPTY, cells[0], cells[2], cells[4])
            elif word == "P-N-C":
                main = ("cr", "cr", cells[2], cells[4])
            else:
                main = (EMPTY, EMPTY, cells[1] if word == "-N--C" else cells[2], cells[4])
            if word == "-N--C":
                anchor = ("cr", "cr", "Cu")
                tail = (PIN, PIN, "Cu")
            else:
                anchor = ("Cu", "cr", "Cu")
                tail = (PIN, "Cu")
        bottom = next(z for z, cell in enumerate(main) if cell != EMPTY)
        full = tuple("cr" if z < bottom else cell for z, cell in enumerate(main))
        initial = self.rules.cells(self._shape(full, ("Cu",) * 5, near))
        initial.update({(z, far): "cr" if z < bottom else "Cu" for z in range(5)})
        shape = self.rules.fold(initial)
        assert shape is not None
        source = self.builder.independent_columns(shape)
        assert source is not None
        source = self.builder.window(source, start)
        support = self.builder.column(("Cu",) * 5, far)
        fixed = self.builder.column(anchor, near)
        assert support is not None and fixed is not None
        source = self.builder.join(source, support, start)
        source = self.builder.window(source, opposite_start)
        source = self.builder.join(source, fixed, opposite_start)
        source = self.builder.window(source, start)
        complement = {(z, 2): "cr" for z in range(5)}
        complement.update({(z, far): cell for z, cell in enumerate((PIN,) * (crystal_level - 2) + ("Cu",))})
        shape = self.rules.fold(complement)
        assert shape is not None
        support = self.builder.independent_columns(shape)
        assert support is not None
        source = self.builder.join(source, support, start)
        source = self.builder.apply("pin", source)
        for cell in tail:
            row = tuple(cell if q == near else EMPTY for q in range(4))
            source = self.builder.apply("stack", source, self.builder.base(row))
        if extra is not None:
            source = self.builder.apply("stack", source, self.builder.base((extra, EMPTY, EMPTY, EMPTY)))
        source = self.builder.window(source, start)
        return source if source.result == self._shape(cells, self.helper(cells), near) else None
