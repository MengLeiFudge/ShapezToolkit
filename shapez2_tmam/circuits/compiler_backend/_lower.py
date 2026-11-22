"""将共享中间表示的块访问转换成有向无环的本地门网。"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from operator import eq, le, lt, ne

from ...synthesis.physics import COLORS, Rules
from ..circuit import Circuit, Literal, Ref
from ..compiler_contract import (
    BOOL, BUILTINS, COLOR, INT, SHAPE, Apply, Bind, Block, Branch, Call, Constant,
    Function, Jump, Operand, Program, Reference, Return, ValueType,
)


Signal = Ref | Literal
_FALSE = Literal(0)
_TRUE = Literal(1)
_MAX_EXPANDED_BLOCKS = 4096
_COMPARE = {"eq": ("AQ==", eq), "ne": ("Bg==", ne), "lt": ("BA==", lt), "le": ("BQ==", le)}
_NATIVE = {
    "not": "LogicGateNot", "and": "LogicGateAnd", "or": "LogicGateOr",
    "rotate_cw": "VirtualRotator", "rotate_ccw": "VirtualRotatorCCW",
    "cut_front": "VirtualHalfCutter", "pin": "VirtualPinPusher", "stack": "VirtualStacker",
    "swap_front_a": "VirtualHalvesSwapper", "swap_front_b": "VirtualHalvesSwapper",
    "crystal": "VirtualCrystalGenerator",
}


@dataclass(frozen=True)
class _Value:
    type: ValueType
    signal: Signal


@dataclass(frozen=True)
class _Arrival:
    active: Signal
    values: dict[str, _Value]


@dataclass(frozen=True)
class _Frame:
    function: Function
    blocks: dict[str, Block]
    types: dict[str, ValueType]

    @classmethod
    def from_function(cls, function: Function):
        variables = (*function.inputs, *function.locals)
        types = {v.name: v.type for v in variables}
        blocks = {b.name: b for b in function.blocks}
        if not blocks or len(blocks) != len(function.blocks):
            raise ValueError(f"{function.name}：需要入口块，且块名必须唯一")
        if len(types) != len(variables) or any(not isinstance(t, ValueType) for t in types.values()):
            raise ValueError(f"{function.name}：变量需要唯一名称和已声明的类型")
        if not isinstance(function.result, ValueType):
            raise ValueError(f"{function.name}：需要已声明的返回类型")
        if type(function.max_block_visits) is not int or function.max_block_visits < 1:
            raise ValueError(f"{function.name}：max_block_visits 必须为正整数")
        return cls(function, blocks, types)


class Lowering:
    def __init__(self, program: Program):
        self.circuit = Circuit()
        self.rules = Rules(program.quadrants, program.height)
        self.functions = {fn.name: fn for fn in program.functions}
        if len(self.functions) != len(program.functions) or program.entry not in self.functions:
            raise ValueError("Program 需要唯一的函数名和已声明的入口函数")
        self.stack: list[str] = []
        self.expanded_blocks: Counter[str] = Counter()

    def _read(self, source: Operand, values: dict[str, _Value]) -> _Value:
        if isinstance(source, Reference):
            if source.name not in values:
                raise ValueError(f"读取未赋值或未声明的变量 {source.name!r}")
            return values[source.name]
        if not isinstance(source, Constant):
            raise ValueError(f"未知操作数 {source!r}")
        value = source.value
        if source.type is BOOL and type(value) is bool:
            return _Value(BOOL, Literal(int(value)))
        if source.type is INT and type(value) is int and -(1 << 31) <= value < (1 << 31):
            return _Value(INT, Literal(value))
        if source.type is SHAPE and (value is None or isinstance(value, str)):
            return _Value(SHAPE, Literal(None if value is None else self.rules.parse(value)))
        if source.type is COLOR and (value is None or isinstance(value, str) and len(value) == 1 and value in COLORS):
            return _Value(COLOR, Literal(None if value is None else "color:" + value))
        raise ValueError(f"常量的类型或取值不合法 {source!r}")

    def _not(self, value: Signal) -> Signal:
        if isinstance(value, Literal):
            return _FALSE if value == _TRUE else _TRUE
        return self.circuit.add("LogicGateNot", value)

    def _bool_pair(self, kind: str, a: Signal, b: Signal) -> Signal:
        identity, absorbing = (_TRUE, _FALSE) if kind == "LogicGateAnd" else (_FALSE, _TRUE)
        if a == absorbing or b == absorbing:
            return absorbing
        if a == identity:
            return b
        if b == identity or a == b:
            return a
        return self.circuit.add(kind, a, b)

    def _merge(self, selected: list[tuple[Signal, Signal]]) -> Signal:
        if len({value for _, value in selected}) == 1:
            return selected[0][1]
        driven = [self.circuit.add("LogicGateIf", value, active) for active, value in selected
                  if value != Literal(None)]
        if len(driven) > 1:
            self.circuit.aliases.append(tuple(driven))
        return driven[0] if driven else Literal(None)

    def _join(self, arrivals: list[_Arrival]) -> _Arrival:
        if len(arrivals) == 1:
            return arrivals[0]
        active: Signal = _FALSE
        values = {}
        for arrival in arrivals:
            active = self._bool_pair("LogicGateOr", active, arrival.active)
        for name, value in arrivals[0].values.items():
            if all(name in arrival.values for arrival in arrivals):
                values[name] = _Value(value.type, self._merge([
                    (arrival.active, arrival.values[name].signal) for arrival in arrivals
                ]))
        return _Arrival(active, values)

    def _apply(self, operation: str, args: tuple[_Value, ...]) -> _Value:
        types = tuple(arg.type for arg in args)
        if operation in ("eq", "ne"):
            if len(types) != 2 or types[0] is not types[1]:
                raise ValueError(f"{operation} 需要两个同类型的操作数")
            result_type = BOOL
        else:
            signature = BUILTINS.get(operation)
            if signature is None or types != signature[0]:
                raise ValueError(f"未知内建操作或实参类型不符 {operation}{types}")
            result_type = signature[1]
        signals = tuple(arg.signal for arg in args)
        if operation in _COMPARE:
            config, compare = _COMPARE[operation]
            a, b = signals
            if isinstance(a, Literal) and isinstance(b, Literal):
                result = Literal(int(compare(a.value, b.value)))
            else:
                result = self.circuit.add("LogicGateCompare", a, b, config=config)
        elif operation == "add":
            a, b = signals
            if isinstance(a, Literal) and isinstance(b, Literal):
                assert isinstance(a.value, int) and isinstance(b.value, int)
                total = a.value + b.value
                result = self._read(Constant(INT, total), {}).signal
            elif Literal(0) in signals:
                result = b if a == Literal(0) else a
            else:
                raise ValueError("add 需要编译时已知的整数，或一个操作数恒为 0")
        elif operation == "not":
            result = self._not(signals[0])
        elif operation in ("and", "or"):
            a, b = signals
            result = self._bool_pair(_NATIVE[operation], a, b)
        elif Literal(None) in signals:
            result = Literal(None)
        elif operation == "cut_back":
            result = signals[0]
            for kind in ("VirtualRotator", "VirtualRotator", "VirtualHalfCutter", "VirtualRotator", "VirtualRotator"):
                result = self.circuit.add(kind, result)
        else:
            result = self.circuit.add(_NATIVE[operation], *signals)
            if operation == "swap_front_b":
                result = Ref(result.node, 1)
        return _Value(result_type, result)

    def invoke(self, name: str, args: tuple[_Value, ...]) -> _Value:
        if name not in self.functions:
            raise ValueError(f"调用未声明的函数 {name!r}")
        if name in self.stack:
            raise ValueError(f"不支持递归调用 {' → '.join((*self.stack, name))}")
        if len(self.stack) >= 64:
            raise ValueError("方法调用嵌套超过 64 层")
        frame = _Frame.from_function(self.functions[name])
        function = frame.function
        if tuple(arg.type for arg in args) != tuple(v.type for v in function.inputs):
            raise ValueError(f"{name} 的实参与形参类型不符")
        self.stack.append(name)
        try:
            return self._expand(frame, {v.name: arg for v, arg in zip(function.inputs, args)})
        finally:
            self.stack.pop()

    def _expand(self, frame: _Frame, inputs: dict[str, _Value]) -> _Value:
        function = frame.function
        pending = {function.blocks[0].name: [_Arrival(_TRUE, inputs)]}
        returned = []
        for _ in range(function.max_block_visits):
            # 同一步到达同一块时合并互斥状态，避免按路径复制共同后续代码。
            following = defaultdict(list)
            for name, arrivals in pending.items():
                if sum(self.expanded_blocks.values()) >= _MAX_EXPANDED_BLOCKS:
                    raise ValueError(f"{function.name}：展开块数超过 {_MAX_EXPANDED_BLOCKS}")
                self.expanded_blocks[function.name] += 1
                try:
                    self._visit(frame, name, self._join(arrivals), following, returned)
                except ValueError as error:
                    raise ValueError(f"{function.name}/{name}：{error}") from error
            if not following:
                break
            pending = following
        else:
            if any(arrival.active == _TRUE for arrivals in pending.values() for arrival in arrivals):
                raise ValueError(f"{function.name}：访问次数超过 max_block_visits")
        if not returned:
            raise ValueError(f"{function.name}：给定访问上界内没有可返回的路径")
        # 有未静态排除的超界路径时，只有已返回路径可以驱动结果。
        if following:
            result = self._merge([*returned, (_FALSE, Literal(None))])
        else:
            result = self._merge(returned)
        return _Value(function.result, result)

    def _visit(self, frame: _Frame, name: str, arrival: _Arrival,
               following: dict[str, list[_Arrival]], returned: list[tuple[Signal, Signal]]) -> None:
        block = frame.blocks.get(name)
        if block is None:
            raise ValueError(f"跳转到未声明的块 {name!r}")
        active = arrival.active
        values = arrival.values.copy()
        for instruction in block.instructions:
            if isinstance(instruction, Bind):
                value = self._read(instruction.value, values)
            elif isinstance(instruction, (Apply, Call)):
                args = tuple(self._read(source, values) for source in instruction.args)
                value = (self._apply(instruction.operation, args) if isinstance(instruction, Apply)
                         else self.invoke(instruction.function, args))
            else:
                raise ValueError(f"未知指令 {instruction!r}")
            if frame.types.get(instruction.target) is not value.type:
                raise ValueError(f"写入未声明或类型不符的变量 {instruction.target!r}")
            values[instruction.target] = value
        end = block.end
        if isinstance(end, Return):
            value = self._read(end.value, values)
            if value.type is not frame.function.result:
                raise ValueError("返回值的类型与声明不符")
            returned.append((active, value.signal))
        elif isinstance(end, Branch):
            condition = self._read(end.condition, values)
            if condition.type is not BOOL:
                raise ValueError("条件跳转需要 bool")
            if end.if_true == end.if_false:
                following[end.if_true].append(_Arrival(active, values))
            else:
                for dest, guard in ((end.if_true, condition.signal), (end.if_false, self._not(condition.signal))):
                    selected = self._bool_pair("LogicGateAnd", active, guard)
                    if selected != _FALSE:
                        following[dest].append(_Arrival(selected, values))
        elif isinstance(end, Jump):
            following[end.target].append(_Arrival(active, values))
        else:
            raise ValueError(f"未知块结束指令 {end!r}")
