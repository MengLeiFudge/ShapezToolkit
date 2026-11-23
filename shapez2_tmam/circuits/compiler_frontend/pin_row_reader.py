"""按同一冻结候选逐层读取顶针前态。"""

import argparse
from pathlib import Path

from ...mari.blueprint import _kind
from ...mari.signals import decode_constant
from ..circuit import constant
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _compare, _gate, _local_wiring, _results, _wait_timer
from ..local_module import Module
from .pin_candidate_row import (
    _CAPTURE, _PREPARE, _RADIO, _RESET_TICKS, _SCAN, _SETTLE,
    _channel, _choose_level, _in_phases, _phase, _read_blueprint, _read_report, _rotate_row, _routing,
)
from .pin_cap_row import _cell, _mask, _publish
from .pin_column_loop import _place
from .pin_column_select import _select_field, build as build_selector


_BASE = 1702200
_CONTROL_CHANNELS = 40
_WINDOW = 80
_PARTS = ("pin-source-rank", "pin-retained-label", "pin-source-label", "pin-cap-column", "pin-source-row")
_RADIO_KINDS = ("ControlledSignalReceiver", "ControlledSignalTransmitter")


def _request(enable, frozen, level, lower, cap_request, rank_level):
    board = Module({"enable": enable, "frozen": frozen, "level": level})
    requested = _gate(board, "And", "requested", _compare(board, "enabled", "enable", 1),
                      _compare(board, "frozen_ready", "frozen", 1))
    board.lookup("level", "lower_level", ((z, 1) for z in range(4)))
    _gate(board, "And", "lower", requested, "lower_level")
    _gate(board, "And", "cap", requested, _compare(board, "top_level", "level", 4))
    _gate(board, "If", "rank_level", "level", "lower")
    board.outputs = {"lower": lower, "cap": cap_request, "rank_level": rank_level}
    return board


def _active(lower, cap, output):
    board = Module({"lower": lower, "cap": cap})
    _gate(board, "Or", "active", "lower", "cap")
    board.outputs = {"active": output}
    return board


def _stamp(phase, prepare_tap, sample_tap, scan_done, selected, cap, output):
    board = Module({"phase": phase, "prepare_tap": prepare_tap, "sample_tap": sample_tap,
                    "done": scan_done, "selected": selected, "cap": cap})
    reset = _gate(board, "And", "reset", "selected", _compare(board, "reset_done", "done", 0))
    prepared = _gate(board, "And", "prepared", reset, _compare(board, "prepared_at", "phase", "prepare_tap"))
    elapsed = _compare(board, "sampled_at", "phase", "sample_tap")
    labels = _gate(board, "And", "labels", elapsed, _compare(board, "labels_done", "done", 1))
    sampled = _gate(board, "Or", "sampled", labels, "cap")
    for name, phases, condition in (("prepare", _PREPARE, prepared), ("scan", _SCAN, sampled),
                                    ("row", (_SETTLE,), elapsed)):
        stamped = _gate(board, "And", name, _in_phases(board, name, phases), condition)
        _gate(board, "If", "stamp", "phase", stamped)
    board.outputs = {"stamp": output}
    return board


def _route(active, lower, phase, column, run, captures):
    board = _routing(active, phase, column, run, captures)
    board.inputs["lower"] = lower
    _gate(board, "And", "run_labels", "run", "lower")
    del board.outputs["run"]
    board.outputs["run_labels"] = run
    return board


def _select_cell(lower, cap, lower_cell, cap_cell, cap_valid, cell, valid):
    board = Module({"lower": lower, "cap": cap, "lower_cell": lower_cell,
                    "cap_cell": cap_cell, "cap_valid": cap_valid})
    _gate(board, "If", "cell", "lower_cell", "lower")
    _gate(board, "If", "cell", "cap_cell", "cap")
    _gate(board, "Or", "valid", "lower", _gate(board, "And", "valid_cap", "cap", "cap_valid"))
    board.outputs = {"cell": cell, "valid": valid}
    return board


def _part_channels(name, report):
    reserved = report["reserved_channels"]
    return range(reserved[0], reserved[1] + 1) if name == "pin-retained-label" else reserved


def _move_channels(wiring, channel_map, external, outputs, initial_label, sample_channels, window):
    senders, receivers, replacements = set(), set(), {}
    channel_ports = set()
    for i, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind not in _RADIO_KINDS:
            continue
        (source, port), = wiring.sources(i, 0)
        driver = wiring.entries[source][1]
        if _kind(driver) != "ConstantSignal" or port != 0:
            raise ValueError("无线频道须由独立常量指定")
        old_channel = decode_constant(driver["C"])
        channel = channel_map.get(old_channel, old_channel)
        channel_ports.add((i, 0))
        if channel != old_channel:
            replacements[source] = channel
        if kind == _RADIO_KINDS[1]:
            if channel in senders or channel in sample_channels:
                raise ValueError(f"原生发射频道重复 {channel}")
            senders.add(channel)
        else:
            receivers.add(channel)
    if (receivers - senders != external | {initial_label} or senders & external
            or not outputs <= senders or not senders <= set(window)):
        raise ValueError("五层行读取器的原生频道与接口表不符")

    # 只迁移无线频道的常量，避免把同值的电路数据一并改动。
    for i, (_, inputs, _) in wiring.pins.items():
        for port in range(len(inputs)):
            if (i, port) not in channel_ports and any(source in replacements for source, _ in wiring.sources(i, port)):
                raise ValueError("无线频道常量同时驱动电路数据")
    for source, channel in replacements.items():
        wiring.entries[source][1]["C"] = constant(channel)


def build(circuits: Path, target_rows: Path, channel_base: int = _BASE) -> tuple[dict, dict]:
    sample = _read_report(circuits / "pin-column-sample.json")
    parts = {name: _read_report(circuits / f"{name}.json") for name in _PARTS}
    rank, retained, lower_label, cap, row = parts.values()
    target = _read_report(target_rows)
    rows = tuple(_channel(target, "outputs", f"row{i}") for i in range(5))
    first, last = sample["reserved_channels"]
    sample_channels = range(first, last + 1)
    old_channels = sorted({ch for name, report in parts.items() for ch in _part_channels(name, report)})
    window = range(channel_base, channel_base + _WINDOW)
    if (not 1 <= window[0] <= window[-1] < 1 << 24
            or set(window).intersection((*sample_channels, *old_channels, *rows))
            or len(old_channels) > _WINDOW - _CONTROL_CHANNELS):
        raise ValueError("五层读取频道须合法并避开候选、原色行和子模块的原频道")
    channel_map = dict(zip(old_channels, window[_CONTROL_CHANNELS:]))
    controls = iter(window[:_CONTROL_CHANNELS])
    inputs = {name: next(controls) for name in ("enable", "level", "mode", "crystal_mask")}
    members = tuple(next(controls) for _ in range(4))
    outputs = {name: next(controls) for name in ("ready", "valid", "row")}
    selector, selected = build_selector(sample, cap, next(controls))
    next(controls)
    next(controls)
    (lower, cap_request, top, active, phase, stamp, mask, mask_column, member, cap_cell,
     cap_valid, cell, cell_valid) = (next(controls) for _ in range(13))
    captures = tuple(next(controls) for _ in range(4))
    statuses = tuple(next(controls) for _ in range(4))
    timer = tuple(controls)

    frozen = sample["outputs"]["ready"]
    column = selected["inputs"]["column"]
    is_selected = selected["outputs"]["valid"]
    z = tuple(selected["outputs"][f"z{i}"] for i in range(4))
    items = tuple(_channel(retained, "inputs", f"item{i}") for i in range(5))
    labels = tuple(_channel(row, "inputs", f"q{i}") for i in range(4))
    level = _channel(rank, "inputs", "level")
    scan_done = _channel(retained, "outputs", "done")
    allowed = {name: _channel(cap, "outputs", name) for name in ("crystal_allowed", "pin_allowed")}

    lower_prepare = rank["settling"]["hold_signal_ticks"] + retained["timing"]["reset_hold_signal_ticks"]
    prepare = selected["settling"]["hold_signal_ticks"] + max(lower_prepare, cap["settling"]["hold_signal_ticks"])
    prepare += 6 * _RADIO
    read = retained["timing"]["start_to_sample_signal_ticks"] + lower_label["settling"]["hold_signal_ticks"]
    sample_ticks = max(read, row["settling"]["hold_signal_ticks"]) + 4 * _RADIO
    prepare_steps, sample_steps = ((n + _RADIO - 1) // _RADIO for n in (prepare, sample_ticks))
    timers, prepare_tap, sample_tap = _wait_timer(phase, timer, prepare_steps, sample_steps)
    modules = [
        _request(inputs["enable"], frozen, inputs["level"], lower, cap_request, level),
        _mask(cap_request, frozen, inputs["mode"], inputs["crystal_mask"], top, mask),
        _active(lower, top, active),
        _stamp(phase, prepare_tap, sample_tap, scan_done, is_selected, top, stamp),
        _phase(active, phase, stamp),
        _route(active, lower, phase, column, _channel(retained, "inputs", "run"), captures),
        _choose_level(level, z, _channel(lower_label, "inputs", "material")),
        _choose_level(level, items[1:], _channel(lower_label, "inputs", "forced_row")),
        _rotate_row(mask, column, mask_column),
        _select_field(column, top, members, "member", member),
        _cell(inputs["mode"], mask_column, member, allowed, cap_cell, cap_valid),
        _select_cell(lower, top, _channel(lower_label, "outputs", "cell"), cap_cell, cap_valid, cell, cell_valid),
        _publish(active, phase, _channel(row, "outputs", "row"), statuses, outputs),
        *timers,
        *(_rotate_row(source, column, item) for source, item in zip(rows, items, strict=True)),
    ]
    for i in range(0, 4, 2):
        for value, registers in ((cell, labels), (cell_valid, statuses)):
            pairs = tuple(zip(captures[i:i + 2], registers[i:i + 2], strict=True))
            modules.append(_results(active, value, pairs))

    entries = []
    for i, module in enumerate(modules):
        entry, = module.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 6), "Y": 3 * (i // 6)})
    _place(entries, selector)
    for name in parts:
        _place(entries, _read_blueprint(circuits / f"{name}.spz2bp"))
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    selector_inputs = {frozen, *selected["inputs"]["words"],
                       *(ch for lane in selected["inputs"]["columns"] for ch in lane.values())}
    external = selector_inputs | {*inputs.values(), *members, *rows}
    initial_label = channel_map[_channel(retained, "inputs", "initial_label")]
    _move_channels(wiring, channel_map, external, set(outputs.values()), initial_label, sample_channels, window)
    return document, {
        "inputs": {**inputs, "members": members, "target_rows_bottom_to_top": rows, "candidate_ready": frozen},
        "outputs": outputs,
        "channels": {"private_range": [window[0], window[-1]], "initial_label_empty": initial_label},
        "timing": {"channel_signal_ticks": _RADIO, "reset_hold_signal_ticks": _RESET_TICKS,
                   "column_prepare_signal_ticks": prepare_steps * _RADIO,
                   "lower_column_sample_signal_ticks": sample_steps * _RADIO,
                   "lower_start_to_ready_signal_ticks": (4 * (prepare_steps + sample_steps + 6)
                                                         + sample_steps + 8) * _RADIO,
                   "top_start_to_ready_signal_ticks": (4 * (prepare_steps + 6) + sample_steps + 8) * _RADIO},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出冻结顶针候选的五层原色行读取器")
    parser.add_argument("circuits", type=Path, help="顶针逆推验收分册目录")
    parser.add_argument("target_rows", type=Path, help="五层原色读取 JSON 接口表")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="五层行读取器的首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(args.circuits, args.target_rows, args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
