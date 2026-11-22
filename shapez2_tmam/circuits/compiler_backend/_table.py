"""把单整数输入的常量选择网表压缩为区间译码。"""

from collections import defaultdict

from ..circuit import Circuit, Gate, Literal, Ref, constant
from ._lower import _COMPARE


_MIN = -(1 << 31)
_END = 1 << 31
_MAX_INTERVALS = 128
_VALUES_PER_GROUP = 5
_COMPARE_BY_CONFIG = {config: compare for config, compare in _COMPARE.values()}
_BOOL_GATES = {"LogicGateAnd", "LogicGateOr", "LogicGateNot"}


def _interval_masks(circuit: Circuit, slot: Ref, guards: list[Ref | Literal]
                    ) -> tuple[list[int], dict[Ref | Literal, int]] | None:
    edges = {_MIN, _END}
    predicates: dict[Ref, Gate] = {}
    pending = guards.copy()
    while pending:
        signal = pending.pop()
        if signal in predicates:
            continue
        if isinstance(signal, Literal):
            if type(signal.value) is not int or signal.value not in (0, 1):
                return None
            continue
        gate = circuit.gates[signal.node]
        if signal.port != 0:
            return None
        if gate.kind == "LogicGateCompare" and gate.config in _COMPARE_BY_CONFIG:
            left, right = gate.inputs
            bound = right if left == slot else left if right == slot else None
            if not isinstance(bound, Literal) or type(bound.value) is not int or not _MIN <= bound.value < _END:
                return None
            edges.update((bound.value, bound.value + 1))
            if len(edges) > _MAX_INTERVALS + 1:
                return None
        elif gate.kind in _BOOL_GATES:
            pending.extend(gate.inputs)
        else:
            return None
        predicates[signal] = gate

    edges = sorted(edges)
    full = (1 << (len(edges) - 1)) - 1
    masks: dict[Ref | Literal, int] = {Literal(0): 0, Literal(1): full}
    # 比较在相邻端点之间不变，每个区间只需检查左端点。
    for ref in sorted(predicates, key=lambda ref: ref.node):
        gate = predicates[ref]
        if gate.kind == "LogicGateCompare":
            left, right = gate.inputs
            assert gate.config is not None
            compare = _COMPARE_BY_CONFIG[gate.config]
            if isinstance(left, Literal):
                masks[ref] = sum(1 << i for i, edge in enumerate(edges[:-1]) if compare(left.value, edge))
            else:
                assert isinstance(right, Literal)
                masks[ref] = sum(1 << i for i, edge in enumerate(edges[:-1]) if compare(edge, right.value))
        elif gate.kind == "LogicGateNot":
            masks[ref] = full ^ masks[gate.inputs[0]]
        else:
            left, right = (masks[arg] for arg in gate.inputs)
            masks[ref] = left & right if gate.kind == "LogicGateAnd" else left | right
    return edges, masks


def _condition(circuit: Circuit, slot: Ref, lo: int, end: int) -> Ref:
    if end == lo + 1:
        return circuit.add("LogicGateCompare", slot, Literal(lo), config=_COMPARE["eq"][0])
    if lo == _MIN:
        return circuit.add("LogicGateCompare", slot, Literal(end), config=_COMPARE["lt"][0])
    lower = circuit.add("LogicGateCompare", Literal(lo), slot, config=_COMPARE["le"][0])
    if end == _END:
        return lower
    upper = circuit.add("LogicGateCompare", slot, Literal(end), config=_COMPARE["lt"][0])
    return circuit.add("LogicGateAnd", lower, upper)


def interval_table(circuit: Circuit, output: Ref) -> tuple[Circuit, Ref] | None:
    """重建只依赖单个有符号 32 位整数输入的互斥常量选择。"""
    receivers = [Ref(i) for i, gate in enumerate(circuit.gates) if gate.kind == "ControlledSignalReceiver"]
    if len(receivers) != 1:
        return None
    slot, = receivers
    drivers = next((group for group in circuit.aliases if output in group), (output,))
    values, guards = [], []
    for driver in drivers:
        gate = circuit.gates[driver.node]
        if driver.port != 0 or gate.kind != "LogicGateIf":
            return None
        value, guard = gate.inputs
        if not isinstance(value, Literal) or type(value.value) is not int:
            return None
        values.append(value)
        guards.append(guard)
    normalized = _interval_masks(circuit, slot, guards)
    if normalized is None:
        return None
    edges, masks = normalized
    selected = defaultdict(int)
    for value, guard in zip(values, guards):
        selected[value] |= masks[guard]
    covered = 0
    for mask in selected.values():
        if mask & covered:
            return None
        covered |= mask
    if not covered:
        return None

    cases = [(value, mask) for value, mask in selected.items() if mask]
    result = Circuit(circuit.channel_base)
    slot = result.add("ControlledSignalReceiver", *circuit.gates[slot.node].inputs)
    if len(cases) == 1 and covered == (1 << (len(edges) - 1)) - 1:
        return result, result.add("ConstantSignal", config=constant(cases[0][0].value))
    if len(cases) <= _VALUES_PER_GROUP:
        return result, _emit_cases(result, slot, edges, cases)
    # 各组独立布索引线。全局掩码互斥，所以稳定时至多一组驱动总线。
    drivers = []
    for i in range(0, len(cases), _VALUES_PER_GROUP):
        local_slot = result.add("LogicGateIf", slot, Literal(1))
        local_value = _emit_cases(result, local_slot, edges, cases[i:i + _VALUES_PER_GROUP])
        drivers.append(result.add("LogicGateIf", local_value, Literal(1)))
    result.aliases.append(tuple(drivers))
    return result, drivers[0]


def _emit_cases(circuit: Circuit, slot: Ref, edges: list[int], cases: list[tuple[Literal, int]]) -> Ref:
    drivers = []
    for value, mask in cases:
        guard = None
        i = 0
        while i < len(edges) - 1:
            if not mask & (1 << i):
                i += 1
                continue
            j = i + 1
            while j < len(edges) - 1 and mask & (1 << j):
                j += 1
            term = _condition(circuit, slot, edges[i], edges[j])
            guard = term if guard is None else circuit.add("LogicGateOr", guard, term)
            i = j
        assert guard is not None
        drivers.append(circuit.add("LogicGateIf", value, guard))
    if len(drivers) > 1:
        circuit.aliases.append(tuple(drivers))
    return drivers[0]
