"""Mari 四象限五层电路使用的图形运算，对应游戏 ShapeLogic/ShapeOperation*。

层和象限均从零开始，层从底向上，象限依次为右上、右下、左下、左上。
一次下落只拆组，不合并新接触的组；截高后不再结算重力。
"""

from dataclasses import dataclass

MAX_LAYERS = 5
COLORS = "urgbcmyw"
EMPTY = "--"
PIN = "P-"


@dataclass(frozen=True)
class Shape:
    """保留空底层和空中间层的不可变四象限图形。"""

    layers: tuple[tuple[str, ...], ...]

    @classmethod
    def from_key(cls, key: str) -> "Shape":
        """读取四象限五层短代码；语法检查不判断可制作性或稳定性。"""
        rows = key.split(":")
        if not 1 <= len(rows) <= MAX_LAYERS or any(len(row) != 8 for row in rows):
            raise ValueError(f"需要四象限、1～5 层图形：{key}")
        layers = tuple(tuple(row[q:q + 2] for q in range(0, 8, 2)) for row in rows)
        for layer in layers:
            for cell in layer:
                if cell not in (EMPTY, PIN) and not (cell[0] in "CRSWc" and cell[1] in COLORS):
                    raise ValueError(f"未知部件或颜色 {cell!r}：{key}")
        if all(cell == EMPTY for cell in layers[-1]):
            raise ValueError(f"最高层必须非空；全空结果用 None 表示：{key}")
        return cls(layers)

    def to_key(self) -> str:
        """输出逐层短代码，不删除底部或中间的空层。"""
        return ":".join("".join(layer) for layer in self.layers)


@dataclass(eq=False)
class _Part:
    """一次加工内的可移动部件；对象身份保留切割前的晶体融合关系。"""

    z: int
    q: int
    cell: str


def _unfold(shape: Shape) -> list[_Part]:
    """按游戏的层优先、象限次序展开非空部件。"""
    return [_Part(z, q, cell) for z, layer in enumerate(shape.layers)
            for q, cell in enumerate(layer) if cell != EMPTY]


def _fold(parts: list[_Part]) -> Shape | None:
    """恢复原层号；没有保留部件时返回空图形。"""
    if not parts:
        return None
    layers = [[EMPTY] * 4 for _ in range(1 + max(p.z for p in parts))]
    for part in parts:
        layers[part.z][part.q] = part.cell
    return Shape(tuple(tuple(layer) for layer in layers))


def _connected(a: _Part, b: _Part) -> bool:
    """普通块与晶体水平粘连；垂直只连接相邻晶体；针从不粘连。"""
    if a.z == b.z and (a.q - b.q) % 4 in (1, 3):
        return a.cell != PIN and b.cell != PIN
    return a.cell[0] == b.cell[0] == "c" and a.q == b.q and abs(a.z - b.z) == 1


def _groups(parts: list[_Part]) -> list[list[_Part]]:
    """保留 ShapeLogic.BuildGroups 的分组和组内遍历次序。"""
    pending = parts.copy()
    groups = []
    while pending:
        group = [pending[0]]
        while True:
            added = False
            for part in pending:
                if part not in group and any(_connected(other, part) for other in group):
                    group.append(part)
                    added = True
            if not added:
                break
        pending = [part for part in pending if part not in group]
        groups.append(group)
    return groups


def _fused(parts: list[_Part]) -> list[set[_Part]]:
    """保存仅由相邻晶体组成的融合组；颜色不参与融合。"""
    return [set(group) for group in _groups([p for p in parts if p.cell[0] == "c"])]


def _collapse(parts: list[_Part], fused: tuple | list[set[_Part]] = ()) -> Shape | None:
    """融合删除 → 按组逐格下落及碎晶 → 截高，保持源码的结算顺序。

    已消失的组不阻挡其他组，其后续运动只影响动画，可从结果计算中移除。
    每次有效下落降低保留部件的层号和，或删除部件，因此循环必定终止。
    """
    groups = _groups(parts)
    retained = set(parts)
    shattered = set().union(*(group for group in fused if not group <= retained))
    if shattered:
        split = []
        for group in groups:
            keep = [part for part in group if part not in shattered]
            split.extend(_groups(keep) if len(keep) != len(group) else [group])
        groups = split
    while True:
        for index, group in enumerate(groups):
            occupied = {(p.z, p.q) for other in groups if other is not group for p in other}
            if any(p.z == 0 or (p.z - 1, p.q) in occupied for p in group):
                continue
            for part in group:
                part.z -= 1
            keep = [part for part in group if part.cell[0] != "c"]
            groups.pop(index)
            # 整组下降后才删掉易碎部件并重新拆分该组；不与其他组重新合并。
            groups.extend(_groups(keep) if len(keep) != len(group) else [group])
            break
        else:
            break
    return _fold([p for group in groups for p in group if p.z < MAX_LAYERS])


def rotate(shape: Shape, turns: int = 1) -> Shape | None:
    """旋转只改变象限，不结算重力；负数表示逆时针。"""
    parts = _unfold(shape)
    for part in parts:
        part.q = (part.q + turns) % 4
    return _fold(parts)


def cut(shape: Shape) -> tuple[Shape | None, Shape | None]:
    """依次返回左半与右半；切断任一晶体会删除原融合组并结算下落。"""
    parts = _unfold(shape)
    fused = _fused(parts)
    # 两侧各用独立部件，避免第一侧下落改变第二侧的坐标和融合信息。
    left = _collapse([p for p in parts if p.q >= 2], fused)
    parts = _unfold(shape)
    right = _collapse([p for p in parts if p.q < 2], _fused(parts))
    return left, right


def stack(lower: Shape, upper: Shape) -> Shape | None:
    """上料整体提高六层后结算，不预删晶体，不按下料实际高度放置。"""
    parts = _unfold(lower)
    above = _unfold(upper)
    for part in above:
        part.z += MAX_LAYERS + 1
    return _collapse(parts + above)


def push_pin(shape: Shape) -> Shape | None:
    """先截去原第五层，其余上移并补底针，再按原融合组处理顶破。"""
    parts = _unfold(shape)
    fused = _fused(parts)
    keep = [p for p in parts if p.z < MAX_LAYERS - 1]
    for part in keep:
        part.z += 1
    pins = [_Part(0, p.q, PIN) for p in keep if p.z == 1]
    return _collapse(keep + pins, fused)


def swap_halves(lower: Shape, upper: Shape) -> tuple[Shape | None, Shape | None]:
    """先分别切割结算，再交叉拼接；合并两半之后没有第二次重力结算。"""
    left_a, right_a = cut(lower)
    left_b, right_b = cut(upper)
    results = []
    for first, second in ((left_b, right_a), (right_b, left_a)):
        parts = ([] if first is None else _unfold(first))
        parts += [] if second is None else _unfold(second)
        results.append(_fold(parts))
    return results[0], results[1]


def unstack(shape: Shape) -> tuple[Shape | None, Shape | None]:
    """信号拆层：最高层移至底层，其余保持层号，不碎晶、不结算重力。"""
    top = len(shape.layers) - 1
    parts = _unfold(shape)
    lower = _fold([p for p in parts if p.z < top])
    upper = [p for p in parts if p.z == top]
    for part in upper:
        part.z = 0
    return lower, _fold(upper)


def crystallize(shape: Shape, color: str) -> Shape:
    """将当前高度以内的空位和针填为指定颜色晶体，保留已有晶体颜色。"""
    return Shape(tuple(tuple("c" + color if cell in (EMPTY, PIN) else cell for cell in layer)
                       for layer in shape.layers))


def paint_top(shape: Shape, color: str) -> Shape | None:
    """虚拟染色器仅改变最上层普通块；晶体不可改色，针不带颜色。"""
    parts = _unfold(shape)
    for part in parts:
        if part.z == len(shape.layers) - 1 and part.cell[0] in "CRSW":
            part.cell = part.cell[0] + color
    return _fold(parts)


def analyze(shape: Shape) -> tuple[Shape | None, str | None]:
    """读取底层右上角；形状输出是单角无色块，另一路为原颜色。"""
    cell = shape.layers[0][0]
    if cell == EMPTY:
        return None, None
    normalized = PIN if cell == PIN else cell[0] + "u"
    return Shape(((normalized, EMPTY, EMPTY, EMPTY),)), None if cell == PIN else cell[1]
