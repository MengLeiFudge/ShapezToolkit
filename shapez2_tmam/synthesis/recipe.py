"""制造树及无需搜索的种子构造；所有多层晶体原料均展开为真实加工。"""

from dataclasses import dataclass, field
from typing import Iterator

from .physics import EMPTY, PIN, Rules, Shape


@dataclass(frozen=True, eq=False)
class Recipe:
    """一次实体加工及其物品输入；相同子树引用表示需要另生产一份。"""

    operation: str
    result: Shape
    inputs: tuple["Recipe", ...] = ()
    parameter: int | str | None = None
    height: int = 5
    step_count: int = field(init=False)

    def __post_init__(self):
        """保存制造上限，防止不同Pin截高语义的配方或指令相互混用。"""
        if self.height < 2 or len(self.result.layers) > self.height or any(
                node.height != self.height or len(node.result.layers[0]) != len(self.result.layers[0]) for node in self.inputs):
            raise ValueError("制造树的层数上限、象限数或输入配方配置不一致")
        object.__setattr__(self, "step_count", 1 + sum(node.step_count for node in self.inputs))

    def steps(self) -> Iterator[dict]:
        """按依赖顺序流式展开，每份实体物品有独立编号，不隐式复制实物。"""
        pending: list[tuple[Recipe, bool]] = [(self, False)]
        outputs = []
        index = 0
        while pending:
            node, ready = pending.pop()
            if not ready:
                pending.append((node, True))
                pending.extend((child, False) for child in reversed(node.inputs))
                continue
            count = len(node.inputs)
            inputs = outputs[-count:] if count else []
            if count:
                del outputs[-count:]
            yield {"id": index, "operation": node.operation, "inputs": inputs,
                   "parameter": node.parameter, "result": node.result.to_key()}
            outputs.append(index)
            index += 1

    def instructions(self, registers: int = 6) -> Iterator[dict]:
        """把四象限制造树流式编为消费输入的寄存器指令，不复制实体。"""
        if len(self.result.layers[0]) != 4 or self.height != 5 or registers < 1:
            raise ValueError("寄存器指令当前需要四象限五层配置和至少一个寄存器")
        live: dict[int, int] = {}
        occupied: set[int] = set()
        for step in self.steps():
            operation = step["operation"]
            parameter = step["parameter"]
            if operation == "base":
                opcode = 14
            elif operation == "rotate" and isinstance(parameter, int) and parameter % 4:
                opcode = {1: 1, 2: 3, 3: 2}[parameter % 4]
            elif operation in ("cut", "swap") and parameter in (0, 1):
                opcode = (4 if operation == "cut" else 8) + parameter
            elif operation in ("pin", "stack", "crystal"):
                opcode = {"pin": 6, "stack": 7, "crystal": 10}[operation]
            else:
                raise ValueError(f"制造步骤无法编码为寄存器指令：{operation!r}, {parameter!r}")
            operands = [live[index] for index in step["inputs"]]
            destination = operands[0] if operands else next((i for i in range(registers) if i not in occupied), None)
            if destination is None:
                raise ValueError(f"制造树需要超过{registers}个同时存活的物品寄存器")
            for index in step["inputs"]:
                del live[index]
            occupied.difference_update(operands)
            occupied.add(destination)
            live[step["id"]] = destination
            yield {"id": step["id"], "opcode": opcode, "destination": destination,
                   "a": operands[0] if operands else 0, "b": operands[1] if len(operands) == 2 else 0,
                   "base": step["result"] if operation == "base" else None,
                   "color": f"color:{parameter}" if operation == "crystal" else None,
                   "request": (step["id"] + 1) % 2, "result": step["result"]}


class Builder:
    """以精确物理计算每个节点，提供基础层、紧柱和半形拼接构造。"""

    def __init__(self, rules: Rules):
        """保存此制造树唯一的物理配置。"""
        self.rules = rules

    def base(self, cells: tuple[str, ...]) -> Recipe:
        """取一份无晶体单层原料，拒绝把多层或晶体常量当作实体原料。"""
        shape = self.rules.parse("".join(cells))
        if any(cell[0] == "c" for cell in cells):
            raise ValueError("基础原料不能包含晶体")
        return Recipe("base", shape, height=self.rules.height)

    def apply(self, operation: str, *inputs: Recipe, parameter: int | str | None = None) -> Recipe:
        """计算一个实体操作；空产物不接入后续制造树。"""
        if any(node.height != self.rules.height or len(node.result.layers[0]) != self.rules.quadrants for node in inputs):
            raise ValueError("输入制造树必须与当前物理配置一致")
        shapes = tuple(node.result for node in inputs)
        arity = {"rotate": 1, "cut": 1, "pin": 1, "crystal": 1, "stack": 2, "swap": 2}
        if operation not in arity or len(inputs) != arity[operation]:
            raise ValueError(f"加工 {operation!r} 的物品输入数量不正确")
        if operation == "rotate":
            if not isinstance(parameter, int):
                raise ValueError("旋转参数需要整数象限数")
            source = inputs[0]
            while source.operation == "rotate":
                assert isinstance(source.parameter, int)
                parameter += source.parameter
                source = source.inputs[0]
            parameter %= self.rules.quadrants
            if not parameter:
                return source
            result = self.rules.rotate(source.result, parameter)
            inputs = (source,)
        elif operation == "cut":
            if parameter not in (0, 1):
                raise ValueError("切割出口需要 0（索引前半）或 1（索引后半）")
            result = self.rules.cut(shapes[0])[parameter]
        elif operation == "swap":
            if parameter not in (0, 1):
                raise ValueError("交换出口需要 0 或 1")
            result = self.rules.swap(shapes[0], shapes[1])[parameter]
        elif operation == "stack":
            result = self.rules.stack(shapes[0], shapes[1])
        elif operation == "pin":
            result = self.rules.pin(shapes[0])
        else:
            if not isinstance(parameter, str) or len(parameter) != 1 or parameter not in "rgbcmyw":
                raise ValueError("实体结晶配方需要 r/g/b/c/m/y/w；未着色晶体的实体供料尚未界定")
            result = self.rules.crystal(shapes[0], parameter)
        if result is None:
            raise ValueError(f"加工 {operation} 无产物，不能作为制造树输入")
        if len(inputs) == 1 and result == inputs[0].result:
            return inputs[0]
        return Recipe(operation, result, inputs, parameter, self.rules.height)

    def window(self, source: Recipe, start: int) -> Recipe:
        """旋转到原生方向、保留连续半面，再恢复世界方向。"""
        aligned = self.apply("rotate", source, parameter=-start)
        kept = self.apply("cut", aligned, parameter=0)
        return self.apply("rotate", kept, parameter=start)

    def join(self, front: Recipe, back: Recipe, start: int) -> Recipe:
        """在 start 开始的半面取 front，其互补半面取 back，再恢复世界方向。"""
        first = self.apply("rotate", front, parameter=-start)
        second = self.apply("rotate", back, parameter=-start)
        merged = self.apply("swap", first, second, parameter=0)
        return self.apply("rotate", merged, parameter=start)

    def dense_column(self, cells: tuple[str, ...], quadrant: int) -> Recipe:
        """制造一根连续触地 N/C 柱；其他列全用普通辅助格，最后用两刀切出。"""
        if not cells or len(cells) > self.rules.height or any(cell == EMPTY or cell == PIN for cell in cells):
            raise ValueError(f"紧柱需要连续1～{self.rules.height}个普通块或晶体")
        source = None
        for cell in cells:
            row = ["Cu"] * self.rules.quadrants
            row[quadrant] = PIN if cell[0] == "c" else cell
            layer = self.base(tuple(row))
            source = layer if source is None else self.apply("stack", source, layer)
            if cell[0] == "c":
                source = self.apply("crystal", source, parameter=cell[1])
        assert source is not None
        source = self.window(source, quadrant - self.rules.quadrants // 2 + 1)
        return self.window(source, quadrant)

    def column(self, cells: tuple[str, ...], quadrant: int) -> Recipe | None:
        """制造独立列精确分类内的柱；不满足连续性或针前缀条件时返回 None。"""
        while cells and cells[-1] == EMPTY:
            cells = cells[:-1]
        if not cells or EMPTY in cells:
            return None
        crystals = [i for i, cell in enumerate(cells) if cell[0] == "c"]
        if not crystals:
            rows = tuple(tuple(cell if q == quadrant else EMPTY for q in range(self.rules.quadrants)) for cell in cells)
            return self.noncrystal(Shape(rows))
        top = crystals[-1]
        prefix = next((i for i, cell in enumerate(cells) if cell != PIN), len(cells))
        if any(cell == PIN for cell in cells[prefix:top]):
            return None
        result = self.dense_column(cells[prefix:top + 1], quadrant)
        for _ in range(prefix):
            result = self.apply("pin", result)
        rows = tuple(tuple(cell if q == quadrant else EMPTY for q in range(self.rules.quadrants)) for cell in cells[top + 1:])
        for segment in self._noncrystal_segments(rows):
            result = self.apply("stack", result, segment)
        return result

    def independent_columns(self, target: Shape) -> Recipe | None:
        """分别造出可独立保留的各列，再依次拼接；有间隙的列不作为成功原料。"""
        half = self.rules.quadrants // 2
        halves = []
        for start in (0, half):
            result = None
            for q in range(start, start + half):
                cells = tuple(row[q] for row in target.layers)
                if all(cell == EMPTY for cell in cells):
                    continue
                column = self.column(cells, q)
                if column is None:
                    return None
                # 长度至多 half 的已有连续区间完整落在保留侧，新列在另一侧。
                result = column if result is None else self.join(result, column, q - half)
            halves.append(result)
        if halves[0] is None:
            result = halves[1]
        elif halves[1] is None:
            result = halves[0]
        else:
            result = self.join(halves[0], halves[1], 0)
        assert result is not None
        if result.result != target:
            raise RuntimeError("独立柱拼接结果与目标不一致")
        return result

    def append_noncrystal(self, lower: Recipe, target: Shape) -> Recipe | None:
        """保留下料，按目标层添加 N/P；失败只表示本次逐层追加不成立。"""
        original = self.rules.cells(lower.result)
        desired = self.rules.cells(target)
        if any(desired.get(pos) != cell for pos, cell in original.items()):
            return None
        delta = {pos: cell for pos, cell in desired.items() if pos not in original}
        if any(cell[0] == "c" for cell in delta.values()):
            return None
        tops = self.rules.column_tops(original)
        if any(z <= tops[q] for z, q in delta):
            return None
        source = lower
        expected = dict(original)
        for z in range(len(target.layers)):
            row = tuple(delta.get((z, q), EMPTY) for q in range(self.rules.quadrants))
            if all(cell == EMPTY for cell in row):
                continue
            source = self.apply("stack", source, self.base(row))
            expected.update({(z, q): cell for q, cell in enumerate(row) if cell != EMPTY})
            if source.result != self.rules.fold(expected):
                return None
        return source if source.result == target else None

    def crystal_prefixes(self, target: Shape) -> Recipe | None:
        """先造各列最高晶体以下的独立前缀，再追加目标 N/P 后缀。"""
        independent = self.independent_columns(target)
        if independent is not None:
            return independent
        tops = [max((z for z, row in enumerate(target.layers) if row[q][0] == "c"), default=-1)
                for q in range(self.rules.quadrants)]
        prefix = self.rules.fold({pos: cell for pos, cell in self.rules.cells(target).items()
                                  if pos[0] <= tops[pos[1]]})
        if prefix is None:
            return self.noncrystal(target)
        source = self.independent_columns(prefix)
        return self.append_noncrystal(source, target) if source is not None else None

    def _noncrystal_segments(self, rows: tuple[tuple[str, ...], ...]) -> Iterator[Recipe]:
        """把非空无C行分成纯针前缀段；每段只需一个活动物品槽。"""
        bottom = 0
        while bottom < len(rows):
            top = bottom
            while top + 1 < len(rows) and rows[top] == tuple(
                    PIN if cell != EMPTY else EMPTY for cell in rows[top + 1]):
                top += 1
            segment = self.base(rows[top])
            for _ in range(top - bottom):
                segment = self.apply("pin", segment)
            yield segment
            bottom = top + 1

    def noncrystal(self, target: Shape) -> Recipe | None:
        """按纯针行段制造无C目标；失败精确表示此类目标不可制作。"""
        if any(cell[0] == "c" for row in target.layers for cell in row):
            raise ValueError("无晶体构造不接受含晶体目标")
        if any(all(cell == EMPTY for cell in row) for row in target.layers):
            return None
        source = None
        for segment in self._noncrystal_segments(target.layers):
            source = segment if source is None else self.apply("stack", source, segment)
        return source if source is not None and source.result == target else None
