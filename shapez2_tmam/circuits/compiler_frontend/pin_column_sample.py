"""合装四列循环及其全部原生单列校验模块。"""

import argparse
from collections import Counter
from pathlib import Path

from ...mari.blueprint import _kind
from ...mari.signals import decode_constant
from ..compiler_backend import _write_blueprint
from ..compiler_backend.fields import compile_fields
from ..compiler_backend.module_caller import _local_wiring
from . import compile_method
from .pin_column_loop import _place, build as build_loop
from .pin_column_stages import generate_pin_column_stages, pin_column_stage_plan


COLUMN_BASE = 1701800
CURSOR_BASE = 1701823
LOOP_BASE = 1701840


def _check_channels(document, report, stages):
    wiring = _local_wiring(document["BP"])
    senders = Counter()
    receivers = Counter()
    for index, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind not in ("ControlledSignalReceiver", "ControlledSignalTransmitter"):
            continue
        (source, _), = wiring.sources(index, 0)
        channel = decode_constant(wiring.entries[source][1]["C"])
        (senders if kind == "ControlledSignalTransmitter" else receivers)[channel] += 1
    external = set(report["inputs"].values())
    ports = report["outputs"]
    published = {ports["ready"], ports["exhausted"], *(ch for lane in ports["columns"] for ch in lane.values())}
    if any(count != 1 for count in senders.values()) or set(receivers) - senders.keys() != external:
        raise ValueError("原生频道存在重复发射或未接通输入")
    for receiver in external:
        if receiver in senders:
            raise ValueError(f"外部输入频道 {receiver} 被样件占用")
    declared = set(range(COLUMN_BASE, LOOP_BASE + 64))
    if (set(senders) | set(receivers)) - declared or published - senders.keys():
        raise ValueError("样件频道与接口表不一致")
    for stage in stages:
        if set(stage["inputs"].values()) - receivers.keys() or set(stage["outputs"].values()) - senders.keys():
            raise ValueError(f"单列模块 {stage['name']} 未接通")
    return {"receivers": receivers.total(), "transmitters": senders.total()}


def build():
    document, report = build_loop(COLUMN_BASE, CURSOR_BASE, LOOP_BASE)
    entries = document["BP"]["Entries"]
    source = generate_pin_column_stages()
    stages = []
    for name, methods, inputs, outputs in pin_column_stage_plan(COLUMN_BASE):
        programs = {field: compile_method(source, method) for field, method in methods.items()}
        checker, interface = compile_fields(programs, input_channels=inputs, output_channels=outputs)
        _place(entries, checker)
        stages.append({"name": name, "inputs": inputs, "outputs": outputs, "platforms": interface["platforms"],
                       "buildings": interface["building_entries"],
                       "hold_signal_ticks": interface["settling"]["hold_signal_ticks"]})
    report["radios"] = _check_channels(document, report, stages)
    report["column_modules"] = stages
    report["platforms"] = len(entries)
    report["building_entries"] = sum(len(p["B"]["Entries"]) for p in entries)
    report["reserved_channels"] = [COLUMN_BASE, LOOP_BASE + 63]
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出四列组合枚举及完整原生校验样件")
    parser.add_argument("--output", required=True, type=Path, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(), args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
