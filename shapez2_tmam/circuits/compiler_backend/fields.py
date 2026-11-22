"""把多个同签名的组合方法布置到一个共享输入的平台。"""

from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from ..circuit import Literal, constant
from ..compiler_contract import Program
from . import _write_blueprint
from ._layout import LayoutCapacityError, layout, logic_gates
from ._lower import Lowering, _Value
from ._optimize import compact


def compile_fields(programs: Mapping[str, Program], *, input_channels: Mapping[str, int],
                   output_channels: Mapping[str, int]) -> tuple[dict, dict]:
    """各入口读取相同的命名输入，返回映射键对应的字段。"""
    if not programs or any(not isinstance(name, str) or not name.isidentifier() for name in programs):
        raise ValueError("至少需要一个有效标识符作为输出字段名")
    if set(output_channels) != set(programs):
        raise ValueError("输出频道须与方法字段逐一对应")
    if any((program.quadrants, program.height) != (4, 5) for program in programs.values()):
        raise ValueError("原生后端需要四象限五层 Program")

    lowerings = {field: Lowering(program) for field, program in programs.items()}
    methods = {field: lowerings[field].functions[program.entry] for field, program in programs.items()}
    entry = next(iter(methods.values()))
    if len({arg.name for arg in entry.inputs}) != len(entry.inputs):
        raise ValueError("输入参数名须唯一")
    if any(method.inputs != entry.inputs for method in methods.values()):
        raise ValueError("各字段方法须按相同顺序声明同名、同类型的输入")
    if set(input_channels) != {arg.name for arg in entry.inputs}:
        raise ValueError("输入频道须与方法参数逐一对应")
    channels = [*input_channels.values(), *output_channels.values()]
    if any(type(channel) is not int or not 1 <= channel < 1 << 24 for channel in channels):
        raise ValueError("所有公开频道都必须在 1～16777215 内")
    if len(set(channels)) != len(channels):
        raise ValueError("输入和输出频道均须独占且互不重复")

    circuit = next(iter(lowerings.values())).circuit
    args = tuple(_Value(arg.type, circuit.add("ControlledSignalReceiver", Literal(input_channels[arg.name])))
                 for arg in entry.inputs)
    outputs = {}
    for field, method in methods.items():
        lowering = lowerings[field]
        lowering.circuit = circuit
        value = lowering.invoke(method.name, args).signal
        outputs[output_channels[field]] = (circuit.add("ConstantSignal", config=constant(value.value))
                                           if isinstance(value, Literal) else value)
    reduced, refs = compact(circuit, outputs)
    try:
        document, depth = layout(reduced, refs)
    except LayoutCapacityError:
        if reduced is circuit:
            raise
        document, depth = layout(circuit, outputs)
        reduced, refs = circuit, outputs

    entries = document["BP"]["Entries"][0]["B"]["Entries"]
    counts = Counter(e["T"].removesuffix("InternalVariant") for e in entries)
    hold_ticks = 64 * (depth + 2)
    report = {
        "methods": {field: method.name for field, method in methods.items()},
        "quadrants": 4,
        "height": 5,
        "inputs": {arg.name: {"channel": input_channels[arg.name], "type": arg.type.value} for arg in entry.inputs},
        "outputs": {field: {"channel": output_channels[field], "type": method.result.value}
                    for field, method in methods.items()},
        "reserved_channels": sorted(channels),
        "schedule": "combination",
        "expanded_blocks": {field: dict(lowering.expanded_blocks) for field, lowering in lowerings.items()},
        "settling": {
            "max_gate_depth": depth,
            "hold_signal_ticks": hold_ticks,
            "hold_simulation_seconds": hold_ticks / 12,
            "conditions": "整件批量导入或完整重载，固定接线与配置，公开频道独占。采用 Hybrid 或 AlwaysHighUPS 常速推进，每批最多 4 信号 tick。调用方保持整组输入满采样时间后读取各字段。",
        },
        "platform_type": "Foundation_3x3",
        "platforms": 1,
        "island_footprint_chunks": [3, 3],
        "buildings_by_layer": [sum(e["L"] == z for e in entries) for z in range(3)],
        "logic_gates": logic_gates(reduced, refs),
        "logic_gates_before_reuse": logic_gates(circuit, outputs),
        "building_entries": len(entries),
        "global_receivers": counts["ControlledSignalReceiver"],
        "global_transmitters": counts["ControlledSignalTransmitter"],
        "internal_global_devices": 0,
    }
    return document, report


def export_fields(programs: Mapping[str, Program], output: Path, *, input_channels: Mapping[str, int],
                  output_channels: Mapping[str, int]) -> dict:
    """写入共享输入的 .spz2bp 和同名 .json 接口表。"""
    return _write_blueprint(*compile_fields(programs, input_channels=input_channels, output_channels=output_channels),
                            output)
