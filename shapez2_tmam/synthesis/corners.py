"""角与脚手架半形：任意层释放及四象限五层顶破，共用稳定半形拼装。"""

from .physics import EMPTY, PIN, Shape
from .recipe import Builder, Recipe


class CornerBuilder:
    """制造主列及相邻N/P助手，再以外向两角制造指定的稳定两列目标。"""

    def __init__(self, builder: Builder):
        """共用制造树；四象限任意层仅接受直接释放，悬空落点顶破仍限定五层。"""
        rules = builder.rules
        if rules.quadrants < 4:
            raise ValueError("角构造需要至少四象限")
        self.builder = builder
        self.rules = builder.rules

    @staticmethod
    def admissible(cells: tuple[str, ...]) -> bool:
        """检查针前缀、晶体间隙及独立针的直接支撑这些列内必要条件。"""
        prefix = True
        outside_pin = False
        below = EMPTY
        lower = -1
        ordinary = 0
        gap = False
        for z, cell in enumerate(cells):
            if cell == PIN:
                if z and cells[z - 1] == EMPTY:
                    return False
                outside_pin |= not prefix
            else:
                prefix = False
            if cell[0] == "c":
                if outside_pin:
                    return False
                if z and cells[z - 1] == EMPTY and (below in (EMPTY, PIN) or below[0] == "c"):
                    return False
                if lower >= 0 and gap and (ordinary < 2 or cells[lower + 1] == EMPTY):
                    return False
                lower, ordinary, gap = z, 0, False
            elif cell == EMPTY:
                gap = True
            elif cell != PIN:
                ordinary += 1
            if cell != EMPTY:
                below = cell
        return True

    def accepts_half(self, target: Shape) -> bool:
        """检查q0/q1两列的A条件与稳定性；循环支撑也算直接阻挡。"""
        if any(cell != EMPTY for row in target.layers for cell in row[2:]):
            raise ValueError("两列判据只接受q0/q1；其他方向先旋转")
        if any(not self.admissible(tuple(row[q] for row in target.layers)) for q in (0, 1)):
            return False
        return self.stable_half(tuple(row[:2] for row in target.layers))

    @staticmethod
    def stable_half(rows: tuple[tuple[str, ...], ...], *, supported_column: int | None = None) -> bool:
        """扫描两列的组支撑；可指定某列外侧另有一根等高的完整N柱。"""
        if not rows or any(len(row) != 2 for row in rows):
            raise ValueError("半形稳定性需要非空的两列原层位网格")
        if supported_column not in (None, 0, 1):
            raise ValueError("外侧N柱只能支撑两列中的0或1")
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
            supported |= supported_column in nonpins
            if nonpins and not supported and (z + 1 == len(rows) or not links[z + 1]):
                return False
        return True

    @staticmethod
    def _gaps(cells: tuple[str, ...]) -> list[tuple[int, int]]:
        """对已通过A的列返回(C层号, 最近下方N层号)，从低到高扫描。"""
        gaps = []
        below = -1
        for r, cell in enumerate(cells):
            if cell[0] == "c" and r and cells[r - 1] == EMPTY:
                gaps.append((r, below))
            if cell != EMPTY:
                below = r
        return gaps

    @staticmethod
    def helper(cells: tuple[str, ...]) -> tuple[str, ...]:
        """直接释放助手与目标列等高；悬空落点的助手只采用五层已证公式。"""
        helper = ["Cu"] * len(cells)
        for r, m in CornerBuilder._gaps(cells):
            if m and cells[m - 1] == EMPTY:
                if len(cells) != 5:
                    raise ValueError("四象限悬空落点的助手公式仅在五层证明")
                return (PIN,) + ("Cu",) * m + (PIN,) * (r - m - 1) + ("Cu",) * (5 - r)
            helper[r - 1] = PIN
        return tuple(helper)

    def _shape(self, main: tuple[str, ...], helper: tuple[str, ...], near: int) -> Shape:
        """主列固定为q0，助手放在指定相邻列，保留空底层。"""
        cells = {(z, q): cell for q, column in ((0, main), (near, helper))
                 for z, cell in enumerate(column) if cell != EMPTY}
        shape = self.rules.fold(cells)
        assert shape is not None
        return shape

    def build(self, cells: tuple[str, ...], quadrant: int, direction: int) -> Recipe | None:
        """制造指定列及N/P助手；4q5l和n≥6的A完整，其他四象限仅覆盖直接释放。"""
        n, height = self.rules.quadrants, self.rules.height
        if not 0 <= quadrant < n or direction not in (-1, 1) or len(cells) > height:
            raise ValueError("角构造需要合法象限、相邻方向±1和不超过高度上限的列")
        cells = cells + (EMPTY,) * (height - len(cells))
        if all(cell == EMPTY for cell in cells) or "cu" in cells or not self.admissible(cells):
            return None
        if n >= 6:
            result = self._release_corner(cells, direction % n)
            return self.builder.apply("rotate", result, parameter=quadrant)
        near = direction % 4
        if any(m and cells[m - 1] == EMPTY for _, m in self._gaps(cells)):
            if height != 5:
                return None
            result = self._pin_corner(cells, near)
        else:
            result = self._simple_corner(cells, near)
        return self.builder.apply("rotate", result, parameter=quadrant) if result is not None else None

    def pair(self, target: Shape) -> Recipe | None:
        """制造只占q0/q1的稳定目标，允许目标助手含C及含针支撑环。"""
        if not self.accepts_half(target) or any(cell == "cu" for row in target.layers for cell in row):
            return None
        if self.rules.quadrants == 4 and self.rules.height != 5:
            for q in (0, 1):
                column = tuple(row[q] for row in target.layers)
                if any(m and column[m - 1] == EMPTY for _, m in self._gaps(column)):
                    return None
        prepared = []
        for q in (0, 1):
            column = tuple(row[q] for row in target.layers)
            if all(cell == EMPTY for cell in column):
                continue
            recipe = self.build(column, q, -1 if q == 0 else 1)
            if recipe is None:
                raise RuntimeError("两列目标满足判据，但未生成角制造证书")
            prepared.append(recipe)
        half = self.rules.quadrants // 2
        source = prepared[0] if len(prepared) == 1 else self.builder.join(prepared[0], prepared[1], 1 - half)
        result = self.builder.window(source, 0)
        if half > 2:
            result = self.builder.window(result, 2 - half)
        if result.result != target:
            raise RuntimeError("两列角制造证书与通过判据的目标不一致")
        return result

    def supported_half(self, target: Shape) -> Recipe | None:
        """逐列转交给外侧N脚手架，反向复用角程序；中间半形不稳定则未覆盖。"""
        n, height = self.rules.quadrants, self.rules.height
        half = n // 2
        if n < 6 or any(cell != EMPTY for row in target.layers for cell in row[half:]):
            raise ValueError("脚手架半形需要至少六象限，且仅占标准前半面")
        if any(cell == "cu" for row in target.layers for cell in row):
            return None
        if any(not self.admissible(tuple(row[q] for row in target.layers)) for q in range(half)):
            return None
        cells = self.rules.cells(target)
        if self.rules.stationary(cells) != cells.keys():
            return None
        for edge, direction, outside, start in ((0, -1, half, 1 - half), (half - 1, 1, n - 1, half - 1)):
            goal = target
            stages = []
            support = None
            # 固定方向每次去掉一根原目标列，并在另一端补N柱；至多half次后不再含C。
            for _ in range(half + 1):
                cells = self.rules.cells(goal)
                if stages:
                    if n == 6:
                        rows = tuple(row[:2] if direction == -1 else row[1:3] for row in goal.layers)
                        stable = self.stable_half(rows, supported_column=1 if direction == -1 else 0)
                    else:
                        stable = self.rules.stationary(cells) == cells.keys()
                    if not stable:
                        break
                if not any(cell[0] == "c" for cell in cells.values()):
                    support = self.builder.noncrystal(goal)
                    if support is None:
                        raise RuntimeError("静止的无晶体脚手架未生成逐层制造证书")
                    break
                stages.append(goal)
                scaffold = self.rules.fold({**{pos: cell for pos, cell in cells.items() if pos[1] != edge},
                                            **{(z, outside): "Cu" for z in range(height)}})
                assert scaffold is not None
                goal = self.rules.rotate(scaffold, direction)
            if support is None:
                continue
            for original in reversed(stages):
                support = self.builder.apply("rotate", support, parameter=-direction)
                column = tuple(row[edge] for row in original.layers)
                if any(cell != EMPTY for cell in column):
                    main = self.build(column, edge, direction)
                    if main is None:
                        raise RuntimeError("通过列A的脚手架边列未生成通用角证书")
                    support = self.builder.join(main, support, start)
                support = self.builder.window(support, 0)
                if support.result != original:
                    raise RuntimeError("半形及脚手架通过支撑条件，但去助手后没有得到目标")
            return support
        return None

    def _release_corner(self, cells: tuple[str, ...], helper: int) -> Recipe:
        """三列保留、外列触发删除；近支撑的高度同时决定所有N的落点。"""
        n, height = self.rules.quadrants, self.rules.height
        top = max((z for z, cell in enumerate(cells) if cell[0] == "c"), default=-1)
        source = list(cells)
        fixed = ["Cu"] * height
        moves = {}
        for r, m in self._gaps(cells):
            source[r - 1], source[m] = cells[m], EMPTY
            moves[r - 1] = m
            fixed[r - 1] = PIN

        # 每个牺牲C区间只生成删除掩码；移动N的近柱保留到目标落点下方。
        anchor = ["Cu"] * height
        z = 0
        while z <= top:
            if source[z] != EMPTY:
                z += 1
                continue
            start = z
            while z <= top and source[z] == EMPTY:
                source[z] = "cr"
                z += 1
            bottom = moves.get(z, z - 1)
            assert start <= bottom < z
            anchor[bottom:z] = ["cr"] * (z - bottom)

        prepared = self.builder.crystal_prefixes(self._shape(tuple(source), tuple(fixed), helper))
        temporary, trigger = (-helper) % n, (-2 * helper) % n
        shape = self.rules.fold({(z, q): cell for q in (temporary, trigger) for z, cell in enumerate(anchor)})
        assert shape is not None
        support = self.builder.independent_columns(shape)
        if prepared is None or support is None:
            raise RuntimeError("通过列条件A的角未生成连续前缀及支撑柱")
        half = n // 2
        start = 0 if helper == 1 else 1 - half
        release_start = -1 if helper == 1 else 2 - half
        result = self.builder.join(prepared, support, start)
        result = self.builder.window(result, release_start)
        result = self.builder.window(result, start)
        if result.result != self._shape(cells, tuple(fixed), helper):
            raise RuntimeError("三列释放的角产物与目标列及N/P助手不一致")
        return result

    def _simple_corner(self, cells: tuple[str, ...], near: int) -> Recipe | None:
        """在 N 隔断间填辅助晶体，必要时将一格 N 的来源提高到间隙顶端。"""
        top = max((z for z, cell in enumerate(cells) if cell[0] == "c"), default=-1)
        helper = self.helper(cells)
        if top < 0:
            return self.builder.noncrystal(self._shape(cells, helper, near))
        source = list(cells)
        for z, lower in self._gaps(cells):
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
            support = self.builder.column(tuple("cr" if z in deleted else "Cu" for z in range(self.rules.height)), far)
            assert support is not None
            prepared = self.builder.join(prepared, support, start)
            prepared = self.builder.window(prepared, start)
        expected = self._shape(cells, helper, near)
        return prepared if prepared.result == expected else None

    def _pin_corner(self, cells: tuple[str, ...], near: int) -> Recipe | None:
        """四象限五层以间隙上端r和落点m生成同一顶破程序的全部原料。"""
        far = (4 - near) % 4
        start = 0 if near == 1 else 3
        opposite_start = 3 if near == 1 else 0
        r, m = next((r, m) for r, m in self._gaps(cells) if m and cells[m - 1] == EMPTY)
        top = max(z for z, cell in enumerate(cells) if cell[0] == "c")
        main = [EMPTY] * top
        for z, cell in enumerate(cells):
            if cell[0] == "c":
                main[z - 1] = cell
        main[r - 2] = cells[m]
        # 五层A条件下，更低的目标格至多是地面N/P；只决定原料，不改变工序。
        if cells[0] == PIN:
            main[:r - 2] = ["cr"] * (r - 2)
        elif cells[0] != EMPTY:
            main[r - 3] = cells[0]
        anchor = ("Cu",) * (m - 1) + ("cr",) * (r - m - 1) + ("Cu",)
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
        complement.update({(z, far): cell for z, cell in enumerate((PIN,) * (r - 1) + ("Cu",))})
        shape = self.rules.fold(complement)
        assert shape is not None
        support = self.builder.independent_columns(shape)
        assert support is not None
        source = self.builder.join(source, support, start)
        source = self.builder.apply("pin", source)
        for z in range(m + 1, 5):
            row = [EMPTY] * 4
            row[near] = PIN if z < r else "Cu"
            if z > top:
                row[0] = cells[z]
            source = self.builder.apply("stack", source, self.builder.base(tuple(row)))
        source = self.builder.window(source, start)
        return source if source.result == self._shape(cells, self.helper(cells), near) else None
