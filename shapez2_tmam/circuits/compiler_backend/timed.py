"""在公开状态和单步方法之间复用有限次折叠。"""

from collections.abc import Mapping
from dataclasses import dataclass

from ...mari.blueprint import Wiring
from ...mari.signals import decode_constant
from ..circuit import Circuit, Literal, Ref
from ..circuit_packing import stack_platforms
from ..compiler_contract import BOOL, INT, Function, Program, ValueType
from ..sequential_circuit import select
from ._layout import _RADIO_ROWS, LayoutCapacityError, layout, logic_gates, used_input_channels
from ._lower import Lowering, _Value
from ._optimize import compact


_CHANNEL_TICKS = 12
_RESET_TICKS = 256
_IO_MARGIN_TICKS = 64
_MAX_STATE_STEPS = 32


def _verify_radios(document: dict, ports: tuple[tuple[set[int], set[int]], ...]) -> None:
    wiring = Wiring(document["BP"])
    by_platform: list[tuple[set[int], set[int]]] = [(set(), set()) for _ in ports]
    radio_kinds = ("ControlledSignalReceiverInternalVariant", "ControlledSignalTransmitterInternalVariant")
    for index, (platform, entry) in enumerate(wiring.entries):
        if entry["T"] not in radio_kinds:
            continue
        (source, _), = wiring.sources(index, 0)
        channel = decode_constant(wiring.entries[source][1]["C"])
        side = by_platform[platform][radio_kinds.index(entry["T"])]
        if not isinstance(channel, int) or channel in side:
            raise ValueError(f"模块 {platform} 的频道 {channel} 非整数或重复")
        side.add(channel)
    if tuple(by_platform) != ports:
        raise ValueError("状态与计算模块的实际收发频道和接口表不一致")


@dataclass(frozen=True)
class _Ports:
    run: int
    initial: dict[str, int]
    done: int
    result: dict[str, int]
    items: dict[str, int]
    index: int
    value: dict[str, int]
    next_index: int
    next_value: dict[str, int]


def _state(ports: _Ports, steps: int) -> dict:
    circuit = Circuit()
    sources = (ports.run, *ports.initial.values(), ports.next_index, *ports.next_value.values())
    signals = {channel: circuit.add("ControlledSignalReceiver", Literal(channel)) for channel in sources}
    run = signals[ports.run]
    index = select(circuit, run, signals[ports.next_index], Literal(0))
    values = tuple(select(circuit, run, signals[nxt], signals[initial])
                   for initial, nxt in zip(ports.initial.values(), ports.next_value.values()))
    terminal = circuit.add("LogicGateCompare", index, Literal(steps), config="AQ==")
    done = circuit.add("LogicGateAnd", run, terminal)
    results = (circuit.add("LogicGateIf", value, done) for value in values)
    document, _ = layout(circuit, {ports.index: index, **dict(zip(ports.value.values(), values)),
                                   ports.done: done, **dict(zip(ports.result.values(), results))})
    return document["BP"]["Entries"][0]


def _worker(lowerings: tuple[Lowering, ...], methods: tuple[Function, ...], ports: _Ports,
            signature: tuple[ValueType, ...], steps: int,
            round_values: tuple[int, ...] | None) -> tuple[Circuit, dict[int, Ref]]:
    circuit = lowerings[0].circuit
    index, *signals = (circuit.add("ControlledSignalReceiver", Literal(channel)) for channel in
                       (ports.index, *ports.value.values(), *ports.items.values()))
    count = len(ports.value)
    values, items = signals[:count], signals[count:]
    active = [circuit.add("LogicGateCompare", index, Literal(i), config="AQ==") for i in range(steps + 1)]
    old = tuple(_Value(type_, signal) for type_, signal in zip(signature[:count], values, strict=True))
    if items:
        item = lowerings[0]._merge(list(zip(active, items)))
        old += (_Value(signature[count], item),)
    if round_values is not None:
        value = lowerings[0]._merge([(guard, Literal(number)) for guard, number in zip(active, round_values)])
        old += (_Value(INT, value),)
    # 各更新方法只接收这同一份旧状态。下一值只送到状态模块。
    computed = (lowering.invoke(method.name, old) for lowering, method in zip(lowerings, methods))
    next_values = tuple(old_value if update.signal == old_value else select(circuit, active[-1], old_value, update.signal)
                        for old_value, update in zip(values, computed))
    next_index = lowerings[0]._merge([(guard, Literal(min(i + 1, steps))) for i, guard in enumerate(active)])
    if isinstance(next_index, Literal):
        next_index = circuit.add("LogicGateIf", next_index, Literal(1))
    return circuit, {ports.next_index: next_index, **dict(zip(ports.next_value.values(), next_values))}


@dataclass(frozen=True)
class _Worker:
    platform: dict
    inputs: set[int]
    outputs: set[int]
    gates: int


def _place_workers(circuit: Circuit, outputs: dict[int, Ref], failures: list[dict]) -> list[_Worker]:
    try:
        document, _ = layout(circuit, outputs, retain_inputs=False)
    except LayoutCapacityError as error:
        if len(outputs) == 1:
            channel, = outputs
            raise LayoutCapacityError(f"计算频道 {channel} 无法单独布置，{error}") from error
        failures.append({"outputs": list(outputs), "reason": str(error)})
        midpoint = (len(outputs) + 1) // 2
        entries = tuple(outputs.items())
        return (_place_workers(circuit, dict(entries[:midpoint]), failures)
                + _place_workers(circuit, dict(entries[midpoint:]), failures))
    return [_Worker(document["BP"]["Entries"][0], used_input_channels(circuit, outputs),
                    set(outputs), logic_gates(circuit, outputs))]


def compile_fold(program: Program, steps: int, channel_base: int) -> tuple[dict, dict]:
    """复用一个 (累积值, 本轮输入) → 累积值方法，依次折叠固定数量的公开输入。"""
    return _compile_fold({"": program}, steps, channel_base, None)


def compile_state_fold(programs: Mapping[str, Program], steps: int, channel_base: int, *,
                       round_values: tuple[int, ...] | None = None) -> tuple[dict, dict]:
    """更新方法接收旧字段、本轮输入及可选整数轮值，返回同名字段的下一值。"""
    _validate_field_names(programs)
    return _compile_fold(programs, steps, channel_base, round_values)


def compile_state_steps(programs: Mapping[str, Program], steps: int, channel_base: int) -> tuple[dict, dict]:
    """各更新方法接收同一份旧状态，执行固定轮数后统一发布结果。"""
    _validate_field_names(programs)
    return _compile_fold(programs, steps, channel_base, None, with_items=False)


def _validate_field_names(programs: Mapping[str, Program]) -> None:
    if any(not isinstance(name, str) or not name.isidentifier() for name in programs):
        raise ValueError("状态字段名须为有效标识符")


def _compile_fold(programs: Mapping[str, Program], steps: int, channel_base: int,
                  round_values: tuple[int, ...] | None, *, with_items: bool = True) -> tuple[dict, dict]:
    count = len(programs)
    side = len(_RADIO_ROWS)
    fields_max = (side - 2) // 2
    if not 1 <= count <= fields_max:
        raise ValueError(f"时序折叠需要 1～{fields_max} 个状态字段")
    steps_max = side - count - 1 if with_items else _MAX_STATE_STEPS
    if type(steps) is not int or not 1 <= steps <= steps_max:
        raise ValueError(f"{count} 个状态字段可折叠 1～{steps_max} 轮")
    item_count = steps if with_items else 0
    width = item_count + 4 * count + 4
    if type(channel_base) is not int or not 1 <= channel_base <= (1 << 24) - width:
        raise ValueError("所有频道都必须在 1～16777215 内")
    if any((program.quadrants, program.height) != (4, 5) for program in programs.values()):
        raise ValueError("原生后端需要四象限五层 Program")
    lowerings = tuple(Lowering(program) for program in programs.values())
    methods = tuple(lowering.functions[program.entry] for lowering, program in zip(lowerings, programs.values()))
    field_types = tuple(method.result for method in methods)
    signature = tuple(arg.type for arg in methods[0].inputs)
    if round_values is not None and (len(round_values) != steps or any(
            type(value) is not int or not -(1 << 31) <= value < 1 << 31 for value in round_values)):
        raise ValueError("每轮需要一个有符号 32 位整数轮值")
    update_inputs = int(with_items) + int(round_values is not None)
    if (len(signature) != count + update_inputs or signature[:count] != field_types
            or round_values is not None and signature[-1] is not INT):
        message = "更新方法须按字段顺序接收同类型旧值"
        if with_items:
            tail = "本轮输入" if round_values is None else "本轮输入和整数轮值"
            message += f"，末尾接收{tail}"
        raise ValueError(message)
    for name, method, lowering in zip(programs, methods, lowerings):
        if tuple(arg.type for arg in method.inputs) != signature:
            raise ValueError(f"字段 {name!r} 的更新方法 {method.name} 参数类型与本轮参数不一致")
        lowering.circuit = lowerings[0].circuit

    channels = iter(range(channel_base, channel_base + width))

    def field_ports(prefix: str) -> dict[str, int]:
        return {f"{prefix}_{name}" if name else prefix: next(channels) for name in programs}

    ports = _Ports(next(channels), field_ports("initial"), next(channels), field_ports("result"),
                   {f"item{i}": next(channels) for i in range(item_count)}, next(channels), field_ports("value"),
                   next(channels), field_ports("next_value"))
    state = _state(ports, steps)
    circuit, updates = _worker(lowerings, methods, ports, signature, steps, round_values)
    failures: list[dict] = []
    reduced, reduced_outputs = compact(circuit, updates)
    try:
        workers = _place_workers(reduced, reduced_outputs, failures)
    except LayoutCapacityError as error:
        if reduced is circuit:
            raise
        failures.append({"reason": str(error), "unreduced_fallback": True})
        workers = _place_workers(circuit, updates, failures)
    platforms = [state, *(worker.platform for worker in workers)]
    if len(platforms) == 2:
        platforms[1]["X"] = 3
    else:
        stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    state_link = {ports.index, *ports.value.values()}
    worker_link = {ports.next_index, *ports.next_value.values()}
    worker_inputs = {*ports.items.values(), *state_link}
    _verify_radios(document, (({ports.run, *ports.initial.values(), *worker_link},
                              {ports.done, *ports.result.values(), *state_link}),
                              *((worker.inputs, worker.outputs) for worker in workers)))

    def typed(named: dict[str, int], types: tuple[ValueType, ...]) -> dict:
        return {name: {"channel": channel, "type": type_.value}
                for (name, channel), type_ in zip(named.items(), types, strict=True)}

    inputs = {"run": ports.run, **ports.initial, **ports.items}
    item_types = (signature[count],) * item_count if with_items else ()
    outputs = {"done": ports.done, **ports.result}
    initial_values = "本次所有初值和 item" if with_items else "本次所有初值"
    entries = [entry for platform in platforms for entry in platform["B"]["Entries"]]
    bounds = [3 + max(p.get(axis, 0) for p in platforms) - min(p.get(axis, 0) for p in platforms)
              for axis in ("X", "Y")]
    round_ticks = 2 * _CHANNEL_TICKS
    names = {"method": methods[0].name} if "" in programs else {
        "methods": {name: method.name for name, method in zip(programs, methods)}
    }
    report = {
        **names,
        "schedule": "bounded_fold",
        "quadrants": 4,
        "height": 5,
        "steps": steps,
        "inputs": typed(inputs, (BOOL, *field_types, *item_types)),
        "outputs": typed(outputs, (BOOL, *field_types)),
        "module_links": {
            "state_to_step": typed({"index": ports.index, **ports.value}, (INT, *field_types)),
            "step_to_state": typed({"next_index": ports.next_index, **ports.next_value}, (INT, *field_types)),
        },
        "reserved_channels": [channel_base, channel_base + width - 1],
        "timing": {
            "channel_signal_ticks": _CHANNEL_TICKS,
            "round_signal_ticks": round_ticks,
            "reset_hold_signal_ticks": _RESET_TICKS,
            "start_to_sample_signal_ticks": (steps - 1) * round_ticks + _IO_MARGIN_TICKS,
            "conditions": "整件批量导入或完整重载。常速 Hybrid 或 AlwaysHighUPS，固定接线与配置，每批最多 4 信号 tick，保留频道由本实例独占。",
            "protocol": f"从 run=0 复位开始，保持{initial_values}，达到复位时间才置 run=1。"
                        "保持所有输入，达到采样时间且 done=1 后读取结果。",
        },
        "platform_type": "Foundation_3x3",
        "platforms": len(platforms),
        "island_footprint_chunks": bounds,
        "buildings_by_layer": [sum(e["L"] == z for e in entries) for z in range(3)],
        "building_entries": len(entries),
        "global_receivers": sum(e["T"] == "ControlledSignalReceiverInternalVariant" for e in entries),
        "global_transmitters": sum(e["T"] == "ControlledSignalTransmitterInternalVariant" for e in entries),
        "internal_global_devices_per_module": 0,
    }
    if round_values is not None:
        report["round_values"] = list(round_values)
    if failures:
        report["worker_partitions"] = [sorted(worker.outputs) for worker in workers]
        report["worker_layout_failures"] = failures
    if len(workers) > 1 or any(worker.inputs != worker_inputs for worker in workers):
        report["worker_ports"] = [{"inputs": sorted(worker.inputs), "outputs": sorted(worker.outputs)}
                                  for worker in workers]
    report["worker_logic_gates"] = sum(worker.gates for worker in workers)
    report["worker_logic_gates_before_reuse"] = logic_gates(circuit, updates)
    report["worker_logic_gates_after_reuse"] = logic_gates(reduced, reduced_outputs)
    return document, report
