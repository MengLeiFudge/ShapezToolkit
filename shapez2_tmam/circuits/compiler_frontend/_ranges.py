"""按基本块访问上界检查整数运算并推导返回范围。"""

from collections.abc import Mapping
from dataclasses import dataclass

from ..compiler_contract import INT, Apply, Bind, Block, Branch, Call, Constant, Function, Jump, Operand, Reference, Return


_INT_MIN = -(1 << 31)
_INT_MAX = (1 << 31) - 1
_INT_BOUNDS = (_INT_MIN, _INT_MAX)
_ANALYSIS_BLOCK_LIMIT = 16_384

_Bounds = tuple[int, int]
_Ranges = dict[str, _Bounds]


@dataclass(frozen=True)
class _RangeAnalysis:
    result: _Bounds | None = None
    failure: tuple[str, _Bounds | None] | None = None


def _add_bounds(left: _Bounds, right: _Bounds) -> _Bounds:
    return left[0] + right[0], left[1] + right[1]


def _within(bounds: _Bounds, allowed: _Bounds) -> bool:
    return allowed[0] <= bounds[0] <= bounds[1] <= allowed[1]


def _fits_int(bounds: _Bounds) -> bool:
    return _within(bounds, _INT_BOUNDS)


def _bounds(operand: Operand, ranges: _Ranges) -> _Bounds:
    if isinstance(operand, Reference):
        return ranges.get(operand.name, _INT_BOUNDS)
    assert operand.type is INT and type(operand.value) is int
    return operand.value, operand.value


def _join_ranges(left: _Ranges, right: _Ranges) -> _Ranges:
    return {name: (min(left[name][0], right[name][0]), max(left[name][1], right[name][1]))
            for name in left.keys() & right.keys()}


def _exclude_endpoint(bounds: _Bounds, value: int) -> _Bounds:
    lo, hi = bounds
    return lo + (lo == value), hi - (hi == value)


def _restrict(operation: str, left: Operand, right: Operand, ranges: _Ranges) -> _Ranges | None:
    lo, hi = _bounds(left, ranges)
    other_lo, other_hi = _bounds(right, ranges)
    if operation in ("lt", "le"):
        gap = int(operation == "lt")
        a = (lo, min(hi, other_hi - gap))
        b = (max(other_lo, lo + gap), other_hi)
    elif operation == "eq":
        a = b = (max(lo, other_lo), min(hi, other_hi))
    else:
        a = _exclude_endpoint((lo, hi), other_lo) if other_lo == other_hi else (lo, hi)
        b = _exclude_endpoint((other_lo, other_hi), lo) if lo == hi else (other_lo, other_hi)
    if a[0] > a[1] or b[0] > b[1]:
        return None
    narrowed = ranges.copy()
    for operand, bounds in ((left, a), (right, b)):
        if isinstance(operand, Reference):
            prev = _bounds(operand, narrowed)
            narrowed[operand.name] = (max(prev[0], bounds[0]), min(prev[1], bounds[1]))
            if narrowed[operand.name][0] > narrowed[operand.name][1]:
                return None
    return narrowed


def _branch_ranges(block: Block, end: Branch, ranges: _Ranges,
                   integers: set[str]) -> tuple[_Ranges | None, _Ranges | None]:
    condition = end.condition
    if isinstance(condition, Constant):
        return (ranges, None) if condition.value else (None, ranges)
    last = block.instructions[-1] if block.instructions else None
    if (not isinstance(last, Apply) or last.target != condition.name
            or last.operation not in ("lt", "le", "eq", "ne")):
        return ranges, ranges
    left, right = last.args
    if any((operand.name not in integers if isinstance(operand, Reference) else operand.type is not INT)
           for operand in (left, right)):
        return ranges, ranges
    operation = last.operation
    yes = _restrict(operation, left, right, ranges)
    if operation in ("lt", "le"):
        no = _restrict("le" if operation == "lt" else "lt", right, left, ranges)
    else:
        no = _restrict("ne" if operation == "eq" else "eq", left, right, ranges)
    return yes, no


def _analyze_ranges(function: Function, required: Mapping[str, _Bounds], call_bounds: Mapping[str, _Bounds],
                    table_edges: dict[str, set[str]]) -> _RangeAnalysis | None:
    blocks = {block.name: block for block in function.blocks}
    integers = {var.name for var in (*function.inputs, *function.locals) if var.type is INT}
    current: dict[str, _Ranges] = {function.blocks[0].name: {}}
    budget = _ANALYSIS_BLOCK_LIMIT
    result = None
    # 每一层的状态来自恰好访问了同样多块的路径。循环次数上界独立于区间分析。
    for _ in range(function.max_block_visits):
        if not current:
            break
        following: dict[str, _Ranges] = {}
        for name, incoming in current.items():
            if budget == 0:
                return _RangeAnalysis(failure=(next(iter(required)), None)) if required else None
            budget -= 1
            block = blocks[name]
            ranges = incoming.copy()
            for instruction in block.instructions:
                target = instruction.target
                if target not in integers:
                    continue
                if isinstance(instruction, Bind):
                    bounds = _bounds(instruction.value, ranges)
                elif isinstance(instruction, Apply) and instruction.operation == "add":
                    left, right = instruction.args
                    bounds = _add_bounds(_bounds(left, ranges), _bounds(right, ranges))
                elif isinstance(instruction, Call):
                    bounds = call_bounds.get(instruction.function, _INT_BOUNDS)
                else:
                    bounds = _INT_BOUNDS
                allowed = required.get(target)
                if allowed is not None and not _within(bounds, allowed):
                    return _RangeAnalysis(failure=(target, bounds))
                if _fits_int(bounds):
                    ranges[target] = bounds
                else:
                    # 快速检查已证明此加法安全，丢掉不够精确的区间。
                    ranges.pop(target, None)
            end = block.end
            if isinstance(end, Jump):
                edges = ((end.target, ranges),)
            elif isinstance(end, Branch):
                yes, no = _branch_ranges(block, end, ranges, integers)
                edges = ((end.if_true, yes), (end.if_false, no))
            else:
                assert isinstance(end, Return)
                if function.result is INT:
                    lo, hi = _bounds(end.value, ranges)
                    result = (lo, hi) if result is None else (min(lo, result[0]), max(hi, result[1]))
                continue
            for successor, state in edges:
                if state is not None:
                    if name in table_edges:
                        table_edges[name].add(successor)
                    previous = following.get(successor)
                    following[successor] = state if previous is None else _join_ranges(previous, state)
        current = following
    return _RangeAnalysis(result)
