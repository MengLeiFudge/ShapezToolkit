"""在公开状态和单步方法之间复用有限次折叠。"""

from ...mari.blueprint import Wiring
from ...mari.signals import decode_constant
from ..circuit import Circuit, Literal, Ref
from ..compiler_contract import BOOL, INT, Function, Program
from ..sequential_circuit import select
from ._layout import layout
from ._lower import Lowering, _Value


_CHANNEL_TICKS = 12
_RESET_TICKS = 256
_IO_MARGIN_TICKS = 64


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

def _state(inputs: dict[str, int], channels: dict[str, int], outputs: dict[str, int], steps: int) -> dict:
    circuit = Circuit()
    run, initial, next_index, next_value = (circuit.add("ControlledSignalReceiver", Literal(channel)) for channel in
                                            (inputs["run"], inputs["initial"],
                                             channels["next_index"], channels["next_value"]))
    index = select(circuit, run, next_index, Literal(0))
    value = select(circuit, run, next_value, initial)
    terminal = circuit.add("LogicGateCompare", index, Literal(steps), config="AQ==")
    done = circuit.add("LogicGateAnd", run, terminal)
    result = circuit.add("LogicGateIf", value, done)
    document, _ = layout(circuit, {channels["index"]: index, channels["value"]: value,
                                   outputs["done"]: done, outputs["result"]: result})
    return document["BP"]["Entries"][0]


def _worker(lowering: Lowering, step: Function, channels: dict[str, int], item_channels: tuple[int, ...]) -> dict:
    circuit = lowering.circuit
    index, value, *items = (circuit.add("ControlledSignalReceiver", Literal(channel)) for channel in
                            (channels["index"], channels["value"], *item_channels))
    limit = len(items)
    active = [circuit.add("LogicGateCompare", index, Literal(i), config="AQ==") for i in range(limit + 1)]
    item = lowering._merge(list(zip(active, items)))
    computed = lowering.invoke(step.name, (_Value(step.inputs[0].type, value), _Value(step.inputs[1].type, item)))
    next_value = select(circuit, active[-1], value, computed.signal)
    next_index = lowering._merge([(guard, Literal(min(i + 1, limit))) for i, guard in enumerate(active)])
    assert isinstance(next_index, Ref)
    document, _ = layout(circuit, {channels["next_index"]: next_index, channels["next_value"]: next_value})
    return document["BP"]["Entries"][0]


def compile_fold(program: Program, steps: int, channel_base: int) -> tuple[dict, dict]:
    """复用一个 (累积值, 本轮输入) → 累积值方法，依次折叠固定数量的公开输入。"""
    if (program.quadrants, program.height) != (4, 5):
        raise ValueError("原生后端需要四象限五层 Program")
    if type(steps) is not int or not 1 <= steps <= 8:
        raise ValueError("折叠需要 1～8 轮，计算模块还占用两个状态输入口")
    if type(channel_base) is not int or not 1 <= channel_base <= (1 << 24) - (8 + steps):
        raise ValueError("所有频道都必须在 1～16777215 内")
    lowering = Lowering(program)
    step = lowering.functions[program.entry]
    if len(step.inputs) != 2 or step.inputs[0].type is not step.result:
        raise ValueError(f"{step.name} 需要两个参数，且第一个参数必须与返回值同类型")
    run, initial, done, result = range(channel_base, channel_base + 4)
    item_channels = tuple(range(channel_base + 4, channel_base + 4 + steps))
    inputs = {"run": run, "initial": initial, **{f"item{i}": ch for i, ch in enumerate(item_channels)}}
    outputs = {"done": done, "result": result}
    channels = dict(zip(("index", "value", "next_index", "next_value"),
                        range(channel_base + 4 + steps, channel_base + 8 + steps)))
    state = _state(inputs, channels, outputs, steps)
    worker = _worker(lowering, step, channels, item_channels)
    worker["X"] = 3
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": [state, worker]}}
    state_link = {channels["index"], channels["value"]}
    worker_link = {channels["next_index"], channels["next_value"]}
    _verify_radios(document, (({run, initial, *worker_link}, {done, result, *state_link}),
                              ({*item_channels, *state_link}, worker_link)))
    input_types = {"run": BOOL, "initial": step.result,
                   **{f"item{i}": step.inputs[1].type for i in range(steps)}}
    entries = [entry for platform in (state, worker) for entry in platform["B"]["Entries"]]
    round_ticks = 2 * _CHANNEL_TICKS
    report = {
        "method": step.name,
        "schedule": "bounded_fold",
        "quadrants": program.quadrants,
        "height": program.height,
        "steps": steps,
        "inputs": {name: {"channel": ch, "type": input_types[name].value} for name, ch in inputs.items()},
        "outputs": {"done": {"channel": done, "type": BOOL.value},
                    "result": {"channel": result, "type": step.result.value}},
        "module_links": {
            "state_to_step": {"index": {"channel": channels["index"], "type": INT.value},
                              "value": {"channel": channels["value"], "type": step.result.value}},
            "step_to_state": {"next_index": {"channel": channels["next_index"], "type": INT.value},
                              "next_value": {"channel": channels["next_value"], "type": step.result.value}},
        },
        "reserved_channels": [channel_base, channel_base + 7 + steps],
        "timing": {
            "channel_signal_ticks": _CHANNEL_TICKS,
            "round_signal_ticks": round_ticks,
            "reset_hold_signal_ticks": _RESET_TICKS,
            "start_to_sample_signal_ticks": (steps - 1) * round_ticks + _IO_MARGIN_TICKS,
            "conditions": "整件批量导入或完整重载。常速 Hybrid 或 AlwaysHighUPS，固定接线与配置，每批最多 4 信号 tick，保留频道由本实例独占。",
            "protocol": "保持本次 initial 和所有 item，从 run=0 复位开始，达到复位时间才置 run=1。保持所有输入，达到采样时间且 done=1 后读取结果。",
        },
        "platform_type": "Foundation_3x3",
        "platforms": 2,
        "island_footprint_chunks": [6, 3],
        "buildings_by_layer": [sum(e["L"] == z for e in entries) for z in range(3)],
        "building_entries": len(entries),
        "global_receivers": sum(e["T"] == "ControlledSignalReceiverInternalVariant" for e in entries),
        "global_transmitters": sum(e["T"] == "ControlledSignalTransmitterInternalVariant" for e in entries),
        "internal_global_devices_per_module": 0,
    }
    return document, report
