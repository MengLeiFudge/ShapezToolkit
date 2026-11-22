"""将受支持的纯 Python 方法编译为蓝图后端共用的 Program。"""

import ast
from dataclasses import dataclass, field

from ...synthesis.physics import COLORS, Rules
from ..compiler_contract import (
    BOOL, BUILTINS, COLOR, INT, SHAPE, Apply, Bind, Block, Branch, Call,
    Constant, Function, Instruction, Jump, Operand, Program, Reference,
    Return, ValueType, Variable,
)
from ._ranges import _Bounds, _INT_BOUNDS, _add_bounds, _fits_int, _range_failure, _within


__all__ = ["FrontendError", "compile_method"]

_SHAPE_LITERAL = "shape_literal"
_RULES = Rules()
_TYPES = {"bool": BOOL, "int": INT, "Shape": SHAPE, "Color": COLOR}
_STATEMENTS = (ast.AnnAssign, ast.Assign, ast.Expr, ast.For, ast.If, ast.Pass, ast.Return)
_COMPARISONS = {ast.Eq: "eq", ast.NotEq: "ne", ast.Is: "eq", ast.IsNot: "ne",
                ast.Lt: "lt", ast.LtE: "le", ast.Gt: "lt", ast.GtE: "le"}

_Assigned = dict[str, _Bounds | None]


class FrontendError(SyntaxError):
    """带文件、行列和源码的前端诊断。"""


@dataclass(frozen=True)
class _Value:
    operand: Operand
    type: ValueType
    bounds: _Bounds | None = None


@dataclass
class _Block:
    name: str
    visits: int
    instructions: list[Instruction] = field(default_factory=list)
    end: Jump | Branch | Return | None = None


def compile_method(source: str, entry: str, *, filename: str = "<source>") -> Program:
    """读取同一文件中的入口与被调用方法，生成 IR，无需导入或执行源码。"""
    return _Module(source, filename).compile(entry)


def _is_empty(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _integer(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        arg = node.operand
        if isinstance(arg, ast.Constant) and type(arg.value) is int:
            return -arg.value if isinstance(node.op, ast.USub) else arg.value
    return None


def _join(left: _Assigned, right: _Assigned) -> _Assigned:
    joined: _Assigned = {}
    for name in left.keys() & right.keys():
        a, b = left[name], right[name]
        joined[name] = (min(a[0], b[0]), max(a[1], b[1])) if a is not None and b is not None else None
    return joined


class _Module:
    def __init__(self, source: str, filename: str):
        self.filename = filename
        self.lines = source.splitlines()
        try:
            tree = ast.parse(source, filename)
        except SyntaxError as error:
            raise FrontendError(error.msg, (filename, error.lineno, error.offset, error.text)) from error
        self.methods: dict[str, list[ast.FunctionDef]] = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                self.methods.setdefault(node.name, []).append(node)
        self.functions: dict[str, Function] = {}
        self.active: list[str] = []

    def error(self, node: ast.AST | None, message: str) -> FrontendError:
        line = getattr(node, "lineno", 1)
        text = self.lines[line - 1] if line <= len(self.lines) else ""
        offset = len(text.encode()[:getattr(node, "col_offset", 0)].decode()) + 1
        return FrontendError(message, (self.filename, line, offset, text))

    def annotation(self, node: ast.expr | None, location: ast.AST) -> ValueType:
        if isinstance(node, ast.Name) and node.id in _TYPES:
            return _TYPES[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            other = node.right if _is_empty(node.left) else node.left if _is_empty(node.right) else None
            if isinstance(other, ast.Name) and other.id in ("Shape", "Color"):
                return _TYPES[other.id]
        raise self.error(node or location, "请用 bool、int、Shape 或 Color 标注类型，图形和颜色可联合 None")

    def compile(self, entry: str) -> Program:
        if entry in BUILTINS or entry == _SHAPE_LITERAL:
            raise self.error(None, f"“{entry}”是保留名称，请选择一个 Python 方法作为入口")
        function = self.method(entry, None)
        return Program(entry, (function, *(f for name, f in self.functions.items() if name != entry)))

    def method(self, name: str, location: ast.AST | None) -> Function:
        if name in self.active:
            cycle = " → ".join((*self.active, name))
            raise self.error(location, f"不支持递归调用（{cycle}），请改为固定次数的循环")
        if name not in self.functions:
            definitions = self.methods.get(name, [])
            if not definitions:
                raise self.error(location, f"找不到方法“{name}”，请在同一文件内定义它")
            if len(definitions) > 1:
                raise self.error(definitions[1], f"方法“{name}”有多个顶层定义，请保留一个")
            self.active.append(name)
            self.functions[name] = _Lowering(self, definitions[0]).lower()
            self.active.pop()
        return self.functions[name]


class _Lowering:
    def __init__(self, module: _Module, method: ast.FunctionDef):
        self.module = module
        self.method = method
        args = method.args
        if (method.decorator_list or args.defaults or args.kwonlyargs or args.vararg or args.kwarg
                or getattr(method, "type_params", ())):
            raise module.error(method, "请使用无装饰器、类型参数或默认值的固定位置参数")
        self.inputs = tuple(Variable(arg.arg, module.annotation(arg.annotation, arg))
                            for arg in (*args.posonlyargs, *args.args))
        if len({arg.name for arg in self.inputs}) != len(self.inputs):
            raise module.error(method, "方法参数名不能重复")
        self.result = module.annotation(method.returns, method)
        nodes = [node for statement in method.body for node in ast.walk(statement)]
        for node in nodes:
            if isinstance(node, ast.stmt) and not isinstance(node, _STATEMENTS):
                raise module.error(node, f"不支持语句 {type(node).__name__}，请使用赋值、if、定长 for 或 return")
        written = {node.id for node in nodes if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
        self.names = written | {arg.name for arg in self.inputs}
        self.types = {arg.name: arg.type for arg in self.inputs}
        self.slots = {arg.name: arg.name for arg in self.inputs}
        self.assigned: _Assigned = {arg.name: None for arg in self.inputs}
        self.locals: list[Variable] = []
        self.tables: dict[str, list[_Value]] = {}
        self.blocks: list[_Block] = []
        self.range_checks: dict[str, tuple[ast.AST, _Bounds]] = {}
        self.table_edges: dict[str, set[str]] = {}
        self.loop_visits = 1
        self.temp_number = 0
        self.current: _Block | None = self.block()
        for arg in self.inputs:
            if arg.name in written:
                slot = self.temp(arg.type)
                self.slots[arg.name] = slot
                self.emit(Bind(slot, Reference(arg.name)))

    def lower(self) -> Function:
        body = self.method.body[1:] if ast.get_docstring(self.method) is not None else self.method.body
        self.statements(body)
        if self.current is not None:
            raise self.module.error(self.method, "方法存在未返回值的路径，请在每条路径返回标注的类型")
        function = self.function()
        if self.range_checks:
            required = {slot: allowed for slot, (_, allowed) in self.range_checks.items()}
            failure = _range_failure(function, required, self.table_edges)
            if failure is not None:
                slot, bounds = failure
                node, allowed = self.range_checks[slot]
                subject = "加法" if allowed == _INT_BOUNDS else "索引"
                if bounds is None:
                    message = f"{subject}的范围分析超过块状态预算，请缩小循环范围或拆分方法"
                elif allowed == _INT_BOUNDS:
                    lo, hi = bounds
                    message = (f"无法证明加法结果在有符号 32 位范围内（推导范围 {lo}～{hi}），"
                               "请限定操作数的范围")
                else:
                    message = self.index_message(allowed, bounds)
                raise self.module.error(node, message)
            if self.prune_table_branches():
                return self.function()
        return function

    def function(self) -> Function:
        blocks = []
        for block in self.blocks:
            assert block.end is not None
            blocks.append(Block(block.name, tuple(block.instructions), block.end))
        return Function(self.method.name, self.inputs, self.result, tuple(self.locals), tuple(blocks),
                        sum(block.visits for block in self.blocks))

    def prune_table_branches(self) -> bool:
        forced = {name: next(iter(edges)) for name, edges in self.table_edges.items() if len(edges) == 1}
        if not forced:
            return False
        blocks = {block.name: block for block in self.blocks}
        for name, successor in forced.items():
            block = blocks[name]
            block.end = Jump(successor)
            block.instructions.pop()

        reachable = set()
        pending = [self.blocks[0].name]
        while pending:
            name = pending.pop()
            if name in reachable:
                continue
            reachable.add(name)
            end = blocks[name].end
            if isinstance(end, Jump):
                pending.append(end.target)
            elif isinstance(end, Branch):
                pending.extend((end.if_true, end.if_false))
        self.blocks = [block for block in self.blocks if block.name in reachable]
        return True

    def block(self, visits: int | None = None) -> _Block:
        block = _Block(f"b{len(self.blocks)}", self.loop_visits if visits is None else visits)
        self.blocks.append(block)
        return block

    def emit(self, instruction: Instruction) -> None:
        assert self.current is not None
        self.current.instructions.append(instruction)

    def temp(self, kind: ValueType) -> str:
        while True:
            name = f"_tmp{self.temp_number}"
            self.temp_number += 1
            if name not in self.names:
                self.locals.append(Variable(name, kind))
                return name

    def apply(self, operation: str, kind: ValueType, *args: Operand, bounds: _Bounds | None = None) -> _Value:
        slot = self.temp(kind)
        self.emit(Apply(slot, operation, args))
        return _Value(Reference(slot), kind, bounds)

    def require(self, node: ast.AST, actual: ValueType, expected: ValueType) -> None:
        if actual != expected:
            raise self.module.error(node, f"这里需要 {expected.value}，得到 {actual.value}")

    def declare(self, target: ast.Name, kind: ValueType) -> None:
        name = target.id
        if name in self.tables:
            raise self.module.error(target, f"只读表“{name}”只允许定义一次")
        if name in self.types:
            self.require(target, kind, self.types[name])
        else:
            self.types[name] = kind
            self.slots[name] = name
            self.locals.append(Variable(name, kind))

    def bind(self, target: ast.Name, value: _Value) -> None:
        self.declare(target, value.type)
        self.emit(Bind(self.slots[target.id], value.operand))
        self.assigned[target.id] = value.bounds

    def statements(self, body: list[ast.stmt]) -> None:
        for node in body:
            if self.current is None:
                break
            if isinstance(node, ast.Return):
                if node.value is None:
                    raise self.module.error(node, "return 后需要一个值，空图形或空颜色请写 return None")
                value = self.expression(node.value, self.result)
                assert self.current is not None
                self.current.end = Return(value.operand)
                self.current = None
            elif isinstance(node, ast.If):
                self.branch(node)
            elif isinstance(node, ast.For):
                self.loop(node)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                self.assignment(node)
            elif not isinstance(node, ast.Pass):
                raise self.module.error(node, "表达式的结果需要赋给局部变量或直接返回")

    def assignment(self, node: ast.Assign | ast.AnnAssign) -> None:
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if not isinstance(target, ast.Name) or not node.simple:
                raise self.module.error(target, "类型标注需要一个局部变量名")
            self.declare(target, self.module.annotation(node.annotation, node))
        else:
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise self.module.error(node, "每条赋值需要一个局部变量名")
            target = node.targets[0]
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
            name = target.id
            if name in self.types or name in self.tables:
                raise self.module.error(target, f"只读表“{name}”需要单独的变量名并且只定义一次")
            self.tables[name] = self.table_items(node.value, self.names)
            self.assigned[name] = None
        elif node.value is not None:
            self.bind(target, self.expression(node.value, self.types.get(target.id)))

    def condition(self, node: ast.expr, yes: _Block, no: _Block) -> None:
        if isinstance(node, ast.BoolOp):
            for value in node.values[:-1]:
                following = self.block()
                if isinstance(node.op, ast.And):
                    self.condition(value, following, no)
                else:
                    self.condition(value, yes, following)
                self.current = following
            self.condition(node.values[-1], yes, no)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            self.condition(node.operand, no, yes)
        else:
            value = self.expression(node, BOOL)
            assert self.current is not None
            self.current.end = Branch(value.operand, yes.name, no.name)

    def branch(self, node: ast.If) -> None:
        yes, no = self.block(), self.block()
        self.condition(node.test, yes, no)
        before = self.assigned.copy()
        self.current = yes
        self.statements(node.body)
        yes_end, yes_assigned = self.current, self.assigned
        self.current, self.assigned = no, before
        if not node.orelse:
            if yes_end is not None:
                yes_end.end = Jump(no.name)
                self.assigned = _join(yes_assigned, before)
            return
        self.statements(node.orelse)
        if yes_end is None:
            return
        if self.current is None:
            self.current, self.assigned = yes_end, yes_assigned
            return
        done = self.block()
        yes_end.end = self.current.end = Jump(done.name)
        self.current, self.assigned = done, _join(yes_assigned, self.assigned)

    def checked_int(self, node: ast.AST, value: int) -> _Value:
        bounds = (value, value)
        if not _fits_int(bounds):
            raise self.module.error(node, "整数字面值超出有符号 32 位范围")
        return _Value(Constant(INT, value), INT, bounds)

    def tuple_items(self, node: ast.Tuple, kind: ValueType | None, written: set[str]) -> list[_Value]:
        values: list[_Value | None] = []
        first_empty = None
        for item in node.elts:
            if _is_empty(item) and kind is None:
                if first_empty is None:
                    first_empty = item
                values.append(None)
                continue
            value = self.expression(item, kind)
            kind = value.type
            if isinstance(item, ast.Name) and item.id in written:
                slot = self.temp(kind)
                self.emit(Bind(slot, value.operand))
                value = _Value(Reference(slot), kind, value.bounds)
            values.append(value)
        if first_empty is not None and kind not in (SHAPE, COLOR):
            raise self.module.error(first_empty, "元组里的 None 需要 Shape 或 Color 类型，其他元素和循环变量也须同类型")
        if kind is None:
            return []
        empty = _Value(Constant(kind, None), kind)
        return [empty if value is None else value for value in values]

    def table_items(self, node: ast.Tuple, snapshots: set[str], expected: ValueType | None = None) -> list[_Value]:
        if not node.elts:
            raise self.module.error(node, "只读表需要至少一个元素")
        return self.tuple_items(node, expected, snapshots)

    @staticmethod
    def index_message(allowed: _Bounds, bounds: _Bounds) -> str:
        lo, hi = allowed
        low, high = bounds
        return f"无法证明索引在 {lo}～{hi} 内（推导范围 {low}～{high}），请限定索引范围"

    def subscript(self, node: ast.Subscript, expected: ValueType | None) -> _Value:
        table = node.value
        if isinstance(table, ast.Tuple):
            items = self.table_items(table, set(), expected)
        elif isinstance(table, ast.Name) and table.id in self.tables:
            if table.id not in self.assigned:
                raise self.module.error(table, f"只读表“{table.id}”可能未定义，请在每条读取路径先定义它")
            items = self.tables[table.id]
        else:
            raise self.module.error(table, "请索引固定元组或在方法内定义的只读表")
        index = self.expression(node.slice, INT)
        allowed = (-len(items), len(items) - 1)
        operand = index.operand
        if index.bounds is not None and _within(index.bounds, allowed):
            low, high = index.bounds
        elif isinstance(operand, Constant):
            assert index.bounds is not None
            raise self.module.error(node.slice, self.index_message(allowed, index.bounds))
        else:
            # 先在读取位置证明范围，选择树的叶块才可省略越界判断。
            slot = self.temp(INT)
            self.emit(Bind(slot, operand))
            self.range_checks[slot] = (node.slice, allowed)
            operand = Reference(slot)
            low, high = allowed
        if low == high:
            return items[low]

        candidates = [items[i] for i in range(low, high + 1)]
        runs = [(low, candidates[0].operand)]
        for i, candidate in enumerate(candidates[1:], low + 1):
            if candidate.operand != runs[-1][1]:
                runs.append((i, candidate.operand))
        kind = items[0].type
        bounds = [value.bounds for value in candidates if value.bounds is not None]
        result_bounds = ((min(lo for lo, _ in bounds), max(hi for _, hi in bounds))
                         if len(bounds) == len(candidates) else None)
        if len(runs) == 1:
            return _Value(runs[0][1], kind, result_bounds)

        result = self.temp(kind)
        done = self.block()
        self.table_selection(runs, operand, result, done)
        self.current = done
        return _Value(Reference(result), kind, result_bounds)

    def table_selection(self, runs: list[tuple[int, Operand]], index: Operand, result: str, done: _Block) -> None:
        leaves: dict[Operand, _Block] = {}

        def build(low: int, high: int, block: _Block | None = None) -> _Block:
            if high - low == 1:
                value = runs[low][1]
                if value not in leaves:
                    leaf = self.block()
                    leaf.instructions.append(Bind(result, value))
                    leaf.end = Jump(done.name)
                    leaves[value] = leaf
                return leaves[value]
            entry = block if block is not None else self.block()
            middle = (low + high) // 2
            before = build(low, middle)
            after = build(middle, high)
            self.current = entry
            condition = self.apply("lt", BOOL, index, Constant(INT, runs[middle][0]))
            entry.end = Branch(condition.operand, before.name, after.name)
            self.table_edges[entry.name] = set()
            return entry

        build(0, len(runs), self.current)

    def range_bounds(self, node: ast.expr) -> tuple[int, int]:
        if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name)
                or node.func.id != "range" or "range" in self.names or "range" in self.module.methods
                or node.keywords or len(node.args) not in (1, 2)):
            raise self.module.error(node, "循环需要固定元组、range(stop) 或 range(start, stop)")
        bounds = []
        for arg in node.args:
            value = _integer(arg)
            if value is None:
                raise self.module.error(arg, "range 边界需要有符号 32 位整数字面值")
            self.checked_int(arg, value)
            bounds.append(value)
        return (0, bounds[0]) if len(bounds) == 1 else (bounds[0], bounds[1])

    def loop(self, node: ast.For) -> None:
        target = node.target
        if not isinstance(target, ast.Name) or node.orelse:
            raise self.module.error(node, "定长 for 需要一个循环变量，循环后直接写后续语句")
        written = {child.id for statement in node.body for child in ast.walk(statement)
                   if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store)}
        items: list[_Value] | None = None
        if isinstance(node.iter, ast.Tuple):
            items = self.tuple_items(node.iter, self.types.get(target.id), written | {target.id})
            start, stop = 0, len(items)
        else:
            start, stop = self.range_bounds(node.iter)
        if start >= stop:
            return

        # 每个块的访问预算乘以上层循环次数，循环体始终只生成一份。
        outer_visits = self.loop_visits
        self.loop_visits *= stop - start
        assert self.current is not None
        index = self.temp(INT)
        self.emit(Bind(index, Constant(INT, start)))
        head = self.block()
        self.current.end = Jump(head.name)
        self.current = head
        for name in written & self.assigned.keys():
            self.assigned[name] = None
        if items is None:
            self.bind(target, _Value(Reference(index), INT, (start, stop - 1)))
        else:
            self.select_item(items, index, target, outer_visits)
        self.statements(node.body)
        self.loop_visits = outer_visits
        if self.current is not None:
            # index 最大为 stop - 1，末次递增到 stop 即退出。
            self.emit(Apply(index, "add", (Reference(index), Constant(INT, 1))))
            again = self.apply("lt", BOOL, Reference(index), Constant(INT, stop))
            done = self.block()
            self.current.end = Branch(again.operand, head.name, done.name)
            self.current = done

    def select_item(self, items: list[_Value], index: str, target: ast.Name, outer_visits: int) -> None:
        if len(items) == 1:
            self.bind(target, items[0])
            return
        done = self.block()
        for i, item in enumerate(items[:-1]):
            assert self.current is not None
            matches = self.apply("eq", BOOL, Reference(index), Constant(INT, i))
            pick = self.block(outer_visits)
            other = self.block(outer_visits * (len(items) - i - 1))
            self.current.end = Branch(matches.operand, pick.name, other.name)
            self.current = pick
            self.bind(target, item)
            pick.end = Jump(done.name)
            self.current = other
        assert self.current is not None
        self.bind(target, items[-1])
        self.current.end = Jump(done.name)
        self.current = done
        bounds = [item.bounds for item in items if item.bounds is not None]
        self.assigned[target.id] = ((min(a for a, _ in bounds), max(b for _, b in bounds))
                                    if len(bounds) == len(items) else None)

    def expression(self, node: ast.expr, expected: ValueType | None = None) -> _Value:
        value = self.value(node, expected)
        if expected is not None:
            self.require(node, value.type, expected)
        return value

    def value(self, node: ast.expr, expected: ValueType | None) -> _Value:
        if isinstance(node, ast.Name):
            if node.id not in self.names:
                raise self.module.error(node, f"未知变量“{node.id}”，请改用方法参数或局部变量")
            if node.id not in self.assigned:
                raise self.module.error(node, f"变量“{node.id}”可能未赋值，请在读取前为每条路径赋值")
            if node.id in self.tables:
                raise self.module.error(node, f"通过整数索引读取只读表“{node.id}”的元素")
            return _Value(Reference(self.slots[node.id]), self.types[node.id], self.assigned[node.id])
        if isinstance(node, ast.Subscript):
            return self.subscript(node, expected)
        if isinstance(node, ast.Constant):
            if type(node.value) is bool:
                return _Value(Constant(BOOL, node.value), BOOL)
            if isinstance(node.value, str):
                if expected is SHAPE:
                    raise self.module.error(node, f"图形短代码请写成 {_SHAPE_LITERAL}({node.value!r})")
                if len(node.value) != 1 or node.value not in COLORS:
                    raise self.module.error(node, f"颜色须使用单字符代码，可用字符为 {COLORS}")
                return _Value(Constant(COLOR, node.value), COLOR)
        if _is_empty(node):
            if expected != SHAPE and expected != COLOR:
                raise self.module.error(node, "None 需要明确的 Shape 或 Color 类型")
            return _Value(Constant(expected, None), expected)
        number = _integer(node)
        if number is not None:
            return self.checked_int(node, number)
        if isinstance(node, ast.Call):
            return self.call(node)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            inner = self.expression(node.operand, BOOL)
            return self.apply("not", BOOL, inner.operand)
        if isinstance(node, ast.BoolOp):
            return self.short_circuit(node)
        if isinstance(node, ast.Compare):
            return self.compare(node)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self.expression(node.left, INT), self.expression(node.right, INT)
            return self.add(node, left, right)
        raise self.module.error(node, f"不支持表达式 {type(node).__name__}，请使用标量、比较、加法或直接调用")

    def add(self, node: ast.expr, left: _Value, right: _Value) -> _Value:
        bounds = _add_bounds(left.bounds or _INT_BOUNDS, right.bounds or _INT_BOUNDS)
        slot = self.temp(INT)
        self.emit(Apply(slot, "add", (left.operand, right.operand)))
        if _fits_int(bounds):
            return _Value(Reference(slot), INT, bounds)
        self.range_checks[slot] = (node, _INT_BOUNDS)
        return _Value(Reference(slot), INT)

    def short_circuit(self, node: ast.BoolOp) -> _Value:
        slot = self.temp(BOOL)
        done = self.block()
        for child in node.values[:-1]:
            value = self.expression(child, BOOL)
            next_value = self.block()
            self.emit(Bind(slot, value.operand))
            assert self.current is not None
            yes, no = (next_value, done) if isinstance(node.op, ast.And) else (done, next_value)
            self.current.end = Branch(Reference(slot), yes.name, no.name)
            self.current = next_value
        last = self.expression(node.values[-1], BOOL)
        self.emit(Bind(slot, last.operand))
        assert self.current is not None
        self.current.end = Jump(done.name)
        self.current = done
        return _Value(Reference(slot), BOOL)

    def compare(self, node: ast.Compare) -> _Value:
        if len(node.ops) != 1 or type(node.ops[0]) not in _COMPARISONS:
            raise self.module.error(node, "请使用单个同类型比较，连续比较可用 and 连接")
        op = type(node.ops[0])
        left, right = node.left, node.comparators[0]
        if op in (ast.Is, ast.IsNot) and not (_is_empty(left) or _is_empty(right)):
            raise self.module.error(node, "is 和 is not 只用于检查空值，比较内容请用 == 或 !=")
        operation = _COMPARISONS[op]
        if operation in ("lt", "le"):
            a, b = self.expression(left, INT), self.expression(right, INT)
        elif _is_empty(left) and _is_empty(right):
            return _Value(Constant(BOOL, operation == "eq"), BOOL)
        elif _is_empty(left):
            b = self.expression(right)
            a = self.expression(left, b.type)
        else:
            a = self.expression(left)
            b = self.expression(right, a.type)
        if op in (ast.Gt, ast.GtE):
            a, b = b, a
        return self.apply(operation, BOOL, a.operand, b.operand)

    def call(self, node: ast.Call) -> _Value:
        if not isinstance(node.func, ast.Name) or node.keywords or any(isinstance(arg, ast.Starred) for arg in node.args):
            raise self.module.error(node, "请用方法名及固定位置参数调用")
        name = node.func.id
        if name in self.names:
            raise self.module.error(node.func, f"“{name}”是局部变量，不能作为方法调用")
        if name == _SHAPE_LITERAL:
            return self.shape_literal(node)
        if name in BUILTINS:
            types, result = BUILTINS[name]
        else:
            method = self.module.method(name, node.func)
            types, result = tuple(arg.type for arg in method.inputs), method.result
        if len(types) != len(node.args):
            raise self.module.error(node, f"“{name}”需要 {len(types)} 个参数，收到 {len(node.args)} 个")
        values = tuple(self.expression(arg, kind) for arg, kind in zip(node.args, types))
        if name == "add":
            return self.add(node, values[0], values[1])
        args = tuple(value.operand for value in values)
        if name in BUILTINS:
            return self.apply(name, result, *args)
        slot = self.temp(result)
        self.emit(Call(slot, name, args))
        return _Value(Reference(slot), result)

    def shape_literal(self, node: ast.Call) -> _Value:
        if len(node.args) != 1:
            raise self.module.error(node, f"{_SHAPE_LITERAL} 需要一个图形短代码")
        arg = node.args[0]
        if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
            raise self.module.error(arg, "请直接写图形短代码字符串")
        try:
            _RULES.parse(arg.value)
        except ValueError as error:
            raise self.module.error(arg, str(error)) from error
        return _Value(Constant(SHAPE, arg.value), SHAPE)
