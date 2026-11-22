"""从共享 Program 生成原生蓝图和采样接口表。"""

import json
from collections import Counter
from pathlib import Path

from ..circuit import Literal, constant, encode_document
from ..compiler_contract import INT, Program
from ._layout import LayoutCapacityError, layout, logic_gates
from ._lower import Lowering, _Value
from ._optimize import compact
from ._table import interval_table


__all__ = ["compile_program", "export_program"]


def compile_program(program: Program, channel_base: int) -> tuple[dict, dict]:
    """生成蓝图数据和公开频道表。channel_base 及后续频道由调用方独占。"""
    if (program.quadrants, program.height) != (4, 5):
        raise ValueError("原生后端需要四象限五层 Program")
    lowering = Lowering(program)
    entry = lowering.functions[program.entry]
    if type(channel_base) is not int or not 1 <= channel_base < (1 << 24) - len(entry.inputs):
        raise ValueError("所有公开频道都必须在 1～16777215 内")
    output_channel = channel_base + len(entry.inputs)
    circuit = lowering.circuit
    inputs = {arg.name: {"channel": channel_base + i, "type": arg.type.value}
              for i, arg in enumerate(entry.inputs)}
    args = tuple(_Value(arg.type, circuit.add("ControlledSignalReceiver", Literal(channel_base + i)))
                 for i, arg in enumerate(entry.inputs))
    value = lowering.invoke(entry.name, args).signal
    result = circuit.add("ConstantSignal", config=constant(value.value)) if isinstance(value, Literal) else value
    outputs = {output_channel: result}
    variants = [compact(circuit, outputs)]
    if variants[0][0] is not circuit:
        variants.append((circuit, outputs))
    failures = []
    for reduced, reduced_outputs in variants:
        try:
            document, depth = layout(reduced, reduced_outputs)
        except LayoutCapacityError as error:
            failures.append(error)
        else:
            break
    else:
        integer_table = len(entry.inputs) == 1 and entry.inputs[0].type is INT and entry.result is INT
        table = interval_table(circuit, result) if integer_table else None
        if table is not None:
            reduced, table_output = table
            reduced_outputs = {output_channel: table_output}
            document, depth = layout(reduced, reduced_outputs)
        elif len(failures) == 1:
            raise failures[0]
        else:
            first, last = failures
            raise LayoutCapacityError(f"复用后 {first}。未复用的网表也无法布置，{last}") from last
    entries = document["BP"]["Entries"][0]["B"]["Entries"]
    counts = Counter(e["T"].removesuffix("InternalVariant") for e in entries)
    hold_ticks = 64 * (depth + 2)
    report = {
        "method": entry.name,
        "quadrants": program.quadrants,
        "height": program.height,
        "inputs": inputs,
        "outputs": {"result": {"channel": output_channel, "type": entry.result.value}},
        "reserved_channels": [channel_base, output_channel],
        "schedule": "combination",
        "expanded_blocks": dict(lowering.expanded_blocks),
        "settling": {
            "max_gate_depth": depth,
            "hold_signal_ticks": hold_ticks,
            "hold_simulation_seconds": hold_ticks / 12,
            "conditions": "整件批量导入或完整重载，固定接线与配置，公开频道独占。采用 Hybrid 或 AlwaysHighUPS 常速推进，每批最多 4 信号 tick。调用方保持整组输入满采样时间后读取频道结果。",
        },
        "platform_type": "Foundation_3x3",
        "platforms": 1,
        "island_footprint_chunks": [3, 3],
        "buildings_by_layer": [sum(e["L"] == z for e in entries) for z in range(3)],
        "logic_gates": logic_gates(reduced, reduced_outputs),
        "logic_gates_before_reuse": logic_gates(circuit, outputs),
        "building_entries": len(entries),
        "global_receivers": counts["ControlledSignalReceiver"],
        "global_transmitters": counts["ControlledSignalTransmitter"],
        "internal_global_devices": 0,
    }
    return document, report


def export_program(program: Program, channel_base: int, output: Path) -> dict:
    """写入 .spz2bp 及同名 .json 接口表。"""
    return _write_blueprint(*compile_program(program, channel_base), output)


def _write_blueprint(document: dict, report: dict, output: Path) -> dict:
    if output.suffix != ".spz2bp":
        raise ValueError("蓝图输出路径须使用 .spz2bp 后缀")
    encoded = encode_document(document)
    report_text = json.dumps(report, ensure_ascii=False, indent=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded + "\n", encoding="utf-8")
    output.with_suffix(".json").write_text(report_text + "\n", encoding="utf-8")
    return report
