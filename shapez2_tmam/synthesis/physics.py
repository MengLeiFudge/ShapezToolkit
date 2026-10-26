"""合成器使用的精确局部物理；保留加工前分组，输出后不再稳定化。

规则实例支持偶数象限及至少两层的参数化模型，独立于 Mari 的固定四象限电路。
"""

from collections import deque
from dataclasses import dataclass


EMPTY = "--"
PIN = "P-"
COLORS = "urgbcmyw"
Position = tuple[int, int]


@dataclass(frozen=True)
class Shape:
    """带完整标签及原层号的非空图形；用 Rules.parse 建立外部输入。"""

    layers: tuple[tuple[str, ...], ...]

    def to_key(self) -> str:
        """按底层到顶层输出，不删除底部或中间空层。"""
        return ":".join("".join(row) for row in self.layers)


@dataclass(frozen=True)
class Rules:
    """一个偶数象限、固定高度上限的局部加工实例；实例之间不混用物品。"""

    quadrants: int = 4
    height: int = 5

    def __post_init__(self):
        """等分半切要求偶数象限；一层顶针语义不在当前证明范围。"""
        if (not isinstance(self.quadrants, int) or self.quadrants < 2 or self.quadrants % 2
                or not isinstance(self.height, int) or self.height < 2):
            raise ValueError("局部物理需要偶数象限n≥2、层数上限H≥2")

    def parse(self, key: str) -> Shape:
        """校验图形编码；语法合法不等于可制作或稳定。"""
        rows = key.split(":")
        if not 1 <= len(rows) <= self.height or any(len(row) != 2 * self.quadrants for row in rows):
            raise ValueError(f"需要 {self.quadrants} 象限、1～{self.height} 层图形：{key}")
        layers = tuple(tuple(row[q:q + 2] for q in range(0, len(row), 2)) for row in rows)
        for row in layers:
            for cell in row:
                if cell in (EMPTY, PIN):
                    continue
                if cell[0] not in "CRSWc" or cell[1] not in COLORS:
                    raise ValueError(f"未知部件或颜色 {cell!r}：{key}")
        if all(cell == EMPTY for cell in layers[-1]):
            raise ValueError("最高层必须非空；加工无产物用 None 表示")
        return Shape(layers)

    def cells(self, shape: Shape) -> dict[Position, str]:
        """取得非空格；内部调用方保证物品来自同一规则实例。"""
        return {(z, q): cell for z, row in enumerate(shape.layers)
                for q, cell in enumerate(row) if cell != EMPTY}

    def fold(self, cells: dict[Position, str]) -> Shape | None:
        """按当前高度上限折叠，保留空底层和空中间层。"""
        cells = {pos: cell for pos, cell in cells.items() if pos[0] < self.height}
        if not cells:
            return None
        rows = [[EMPTY] * self.quadrants for _ in range(1 + max(z for z, _ in cells))]
        for (z, q), cell in cells.items():
            rows[z][q] = cell
        return Shape(tuple(tuple(row) for row in rows))

    def groups(self, cells: dict[Position, str], *, fused: bool = False) -> list[set[Position]]:
        """划分粘连组或晶体融合组，按最小格位排序；颜色不影响连接。"""
        pending = {pos for pos, cell in cells.items() if not fused or cell[0] == "c"}
        groups = []
        for first in sorted(pending):
            if first not in pending:
                continue
            pending.remove(first)
            group = {first}
            queue = [first]
            while queue:
                z, q = queue.pop()
                cell = cells[z, q]
                if cell == PIN:
                    continue
                neighbors = [(z, (q - 1) % self.quadrants), (z, (q + 1) % self.quadrants)]
                if cell[0] == "c":
                    neighbors.extend((r, q) for r in (z - 1, z + 1)
                                     if cells.get((r, q), EMPTY)[0] == "c")
                for pos in neighbors:
                    if pos in pending and cells[pos] != PIN:
                        pending.remove(pos)
                        group.add(pos)
                        queue.append(pos)
            groups.append(group)
        return groups

    def stationary(self, cells: dict[Position, str], *, grounded: bool = True) -> set[Position]:
        """反向支撑队列求最大静止格集合；抬高的上料使用空地面种子。"""
        groups = self.groups(cells)
        owner = {pos: index for index, group in enumerate(groups) for pos in group}
        ground = {owner[pos] for pos in cells if grounded and pos[0] == 0}
        supports: list[set[int]] = [set() for _ in groups]
        for (z, q), index in owner.items():
            below = owner.get((z - 1, q))
            if below is not None and below != index:
                supports[index].add(below)
        dependents: list[set[int]] = [set() for _ in groups]
        for index, edges in enumerate(supports):
            for below in edges:
                dependents[below].add(index)
        counts = [len(edges) for edges in supports]
        queue = deque(index for index, count in enumerate(counts) if not count and index not in ground)
        removed = set()
        while queue:
            index = queue.popleft()
            removed.add(index)
            for above in dependents[index]:
                counts[above] -= 1
                if not counts[above] and above not in ground:
                    queue.append(above)
        return {pos for pos, index in owner.items() if index not in removed}

    def collapse(self, cells: dict[Position, str], fused: tuple | list[set[Position]] = ()) -> Shape | None:
        """用静止组及落点公式计算一次重力，最后截高，不合并下落中的新接触。"""
        vanished = set().union(*(group for group in fused if not group <= cells.keys()))
        live = {pos: cell for pos, cell in cells.items() if pos not in vanished}
        fixed = self.stationary(live)
        result = {pos: live[pos] for pos in fixed}
        moving = {pos: cell for pos, cell in live.items() if pos not in fixed and cell[0] != "c"}
        barriers = iter(sorted(fixed))
        barrier = next(barriers, None)
        tops = [-1] * self.quadrants
        for block in self.groups(moving):
            source = next(iter(block))[0]
            while barrier is not None and barrier[0] < source:
                z, q = barrier
                tops[q] = max(tops[q], z)
                barrier = next(barriers, None)
            columns = {q for _, q in block}
            z = 1 + max(tops[q] for q in columns)
            for q in columns:
                tops[q] = z
                result[z, q] = moving[source, q]
        return self.fold(result)

    def rotate(self, shape: Shape, turns: int) -> Shape:
        """旋转整个物品，不执行重力。"""
        cells = {(z, (q + turns) % self.quadrants): cell for (z, q), cell in self.cells(shape).items()}
        result = self.fold(cells)
        assert result is not None
        return result

    def cut(self, shape: Shape) -> tuple[Shape | None, Shape | None]:
        """分别返回索引前半和后半，两个出口独立处理原晶体融合与重力。"""
        cells = self.cells(shape)
        fused = self.groups(cells, fused=True)
        middle = self.quadrants // 2
        return (self.collapse({pos: cell for pos, cell in cells.items() if pos[1] < middle}, fused),
                self.collapse({pos: cell for pos, cell in cells.items() if pos[1] >= middle}, fused))

    def stack(self, lower: Shape, upper: Shape) -> Shape | None:
        """将上料提高高度上限加一层，统一结算并截高；不预删上料晶体。"""
        cells = self.cells(lower)
        cells.update({(z + self.height + 1, q): cell for (z, q), cell in self.cells(upper).items()})
        return self.collapse(cells)

    def pin(self, shape: Shape) -> Shape | None:
        """按删前底层掩码补针，删除顶层及相连融合组，再上移、结算。"""
        original = self.cells(shape)
        fused = self.groups(original, fused=True)
        vanished = set().union(*(group for group in fused if any(z == self.height - 1 for z, _ in group)))
        cells = {(z + 1, q): cell for (z, q), cell in original.items()
                 if z < self.height - 1 and (z, q) not in vanished}
        cells.update({(0, q): PIN for z, q in original if z == 0})
        return self.collapse(cells)

    def crystal(self, shape: Shape, color: str) -> Shape:
        """填满当前高度内的空格与针，保留已有普通块和晶体标签。"""
        if color not in COLORS or len(color) != 1:
            raise ValueError(f"未知结晶颜色：{color!r}")
        return Shape(tuple(tuple("c" + color if cell in (EMPTY, PIN) else cell for cell in row)
                           for row in shape.layers))

    def swap(self, first: Shape, second: Shape) -> tuple[Shape | None, Shape | None]:
        """先分别半切，再交叉合并；不在拼接后额外结算重力。"""
        front_a, back_a = self.cut(first)
        front_b, back_b = self.cut(second)
        results = []
        for front, back in ((front_a, back_b), (front_b, back_a)):
            cells = self.cells(front) if front is not None else {}
            if back is not None:
                cells.update(self.cells(back))
            results.append(self.fold(cells))
        return results[0], results[1]
