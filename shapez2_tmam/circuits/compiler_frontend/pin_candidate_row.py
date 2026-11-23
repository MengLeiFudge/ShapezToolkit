"""从冻结的顶针候选读取一层原色来源行。"""

import argparse
import base64
import gzip
import json
from pathlib import Path

from ...mari.blueprint import _kind
from ...mari.signals import decode_constant
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _results, _wait_timer
from ..local_module import Module
from .pin_column_loop import _place
from .pin_column_select import build as build_selector


_PREPARE = (1, 4, 7, 10)
_SCAN = (2, 5, 8, 11)
_CAPTURE = (3, 6, 9, 12)
_SETTLE, _DONE = 13, 14
_RADIO = 12
_RESET_TICKS = 96
_COLUMN_BASE = 1701904


def _in_phases(board, name, phases):
    matches = tuple(_compare(board, f"{name}_{phase}", "phase", phase) for phase in phases)
    return _any(board, name, matches)


def _active(enable, ready, level, output):
    board = Module({"enable": enable, "ready": ready, "level": level})
    _gate(board, "And", "requested", _compare(board, "enabled", "enable", 1),
          _compare(board, "frozen", "ready", 1))
    board.lookup("level", "valid_level", tuple((level, 1) for level in range(4)))
    _gate(board, "And", "active", "requested", "valid_level")
    board.outputs = {"active": output}
    return board


def _stamp(phase, reset_tap, sample_tap, scan_done, selected, output):
    board = Module({"phase": phase, "reset_tap": reset_tap, "sample_tap": sample_tap,
                    "done": scan_done, "selected": selected})
    prepared = _gate(board, "And", "prepared", _compare(board, "reset_elapsed", "phase", "reset_tap"),
                     _compare(board, "reset_done", "done", 0))
    prepared = _gate(board, "And", "selected_ready", prepared, "selected")
    sampled = _compare(board, "sample_elapsed", "phase", "sample_tap")
    labels = _gate(board, "And", "labels_ready", sampled, _compare(board, "done_high", "done", 1))
    tests = (("prepare", _PREPARE, prepared), ("scan", _SCAN, labels),
             ("row", (_SETTLE,), sampled))
    for name, phases, condition in tests:
        go = _gate(board, "And", name, _in_phases(board, name, phases), condition)
        _gate(board, "If", "stamp", "phase", go)
    board.outputs = {"stamp": output}
    return board


def _phase(active, phase, stamp):
    board = Module({"active": active, "phase": phase, "stamp": stamp})
    board.lookup("phase", "next", ((None, 1), *((i, i + 1) for i in range(_DONE))))
    waiting = _in_phases(board, "wait", (*_PREPARE, *_SCAN, _SETTLE))
    blocked = _gate(board, "And", "blocked", waiting, _compare(board, "stale", "phase", "stamp", "Bg=="))
    hold = _gate(board, "Or", "hold", blocked, _compare(board, "done", "phase", _DONE))
    running = _compare(board, "running", "active", 1)
    _gate(board, "If", "state", "next", _gate(board, "And", "step", running, _gate(board, "Not", "advance", hold)))
    _gate(board, "If", "state", "phase", _gate(board, "And", "keep", running, hold))
    _gate(board, "If", "state", 0, _gate(board, "Not", "reset", running))
    board.outputs = {"state": phase}
    return board


def _routing(active, phase, column, run, captures):
    board = Module({"active": active, "phase": phase})
    board.lookup("phase", "lane", ((i+1, i//3) for i in range(12)))
    _gate(board, "If", "column", "lane", "active")
    _gate(board, "And", "run", "active", _in_phases(board, "scan", (*_SCAN, *_CAPTURE)))
    board.outputs = {"column": column, "run": run}
    for i, (state, channel) in enumerate(zip(_CAPTURE, captures, strict=True)):
        capture = _gate(board, "And", f"capture_{i}", "active", _compare(board, f"saving_{i}", "phase", state))
        board.outputs[capture] = channel
    return board


def _rotate_row(row, column, output):
    board = Module({"row": row, "column": column})
    board.gate("VirtualRotatorCCW", ("row",), ("ccw",))
    board.gate("VirtualRotatorCCW", ("ccw",), ("opposite",))
    board.gate("VirtualRotator", ("row",), ("cw",))
    for i, rotated in enumerate(("row", "ccw", "opposite", "cw")):
        _gate(board, "If", "selected", rotated, _compare(board, f"lane_{i}", "column", i))
    board.outputs = {"selected": output}
    return board


def _choose_level(level, channels, output):
    board = Module({"level": level, **{f"z{i}": ch for i, ch in enumerate(channels)}})
    for i in range(4):
        _gate(board, "If", "selected", f"z{i}", _compare(board, f"layer_{i}", "level", i))
    board.outputs = {"selected": output}
    return board


def _publish(active, phase, row, output, ready):
    board = Module({"active": active, "phase": phase, "row": row})
    _gate(board, "And", "ready", "active", _compare(board, "complete", "phase", _DONE))
    _gate(board, "If", "result", "row", "ready")
    board.outputs = {"result": output, "ready": ready}
    return board


def _read_report(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_blueprint(path):
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text.startswith("SHAPEZ2-4-") or not text.endswith("$"):
        raise ValueError(f"需要 SHAPEZ2-4 格式的原生蓝图 {path}")
    return json.loads(gzip.decompress(base64.b64decode(text[10:-1], validate=True)))


def _channel(report, direction, name):
    return report[direction][name]["channel"]


def build(circuits: Path, target_rows: Path, channel_base: int) -> tuple[dict, dict]:
    def report(name):
        return _read_report(circuits / f"{name}.json")

    sample = report("pin-column-sample")
    selector, selected = build_selector(sample, report("pin-cap-column"), _COLUMN_BASE)
    rank = report("pin-source-rank")
    retained = report("pin-retained-label")
    cell = report("pin-source-label")
    row = report("pin-source-row")
    target = _read_report(target_rows)
    rows = tuple(_channel(target, "outputs", f"row{i}") for i in range(5))
    enable, active, phase, stamp, output, ready, *private = range(channel_base, channel_base + 15)
    captures, timer = tuple(private[:4]), tuple(private[4:])
    column = selected["inputs"]["column"]
    z = tuple(selected["outputs"][f"z{i}"] for i in range(4))
    items = tuple(_channel(retained, "inputs", f"item{i}") for i in range(5))
    level = _channel(rank, "inputs", "level")
    scan_done = _channel(retained, "outputs", "done")
    frozen = sample["outputs"]["ready"]
    labels = tuple(_channel(row, "inputs", f"q{i}") for i in range(4))
    initial_label = _channel(retained, "inputs", "initial_label")
    reset_ticks = selected["settling"]["hold_signal_ticks"] + rank["settling"]["hold_signal_ticks"]
    reset_ticks += retained["timing"]["reset_hold_signal_ticks"] + 6 * _RADIO
    read_ticks = max(retained["timing"]["start_to_sample_signal_ticks"] + cell["settling"]["hold_signal_ticks"],
                     row["settling"]["hold_signal_ticks"]) + 4 * _RADIO
    reset_steps, read_steps = ((n + _RADIO - 1) // _RADIO for n in (reset_ticks, read_ticks))
    timers, reset_tap, sample_tap = _wait_timer(phase, timer, reset_steps, read_steps)

    modules = [
        _active(enable, frozen, level, active),
        _stamp(phase, reset_tap, sample_tap, scan_done, selected["outputs"]["valid"], stamp),
        _phase(active, phase, stamp),
        _routing(active, phase, column, _channel(retained, "inputs", "run"), captures),
        _choose_level(level, z, _channel(cell, "inputs", "material")),
        _choose_level(level, items[1:], _channel(cell, "inputs", "forced_row")),
        _publish(active, phase, _channel(row, "outputs", "row"), output, ready),
        *timers,
        *(_rotate_row(source, column, item) for source, item in zip(rows, items, strict=True)),
    ]
    for i in range(0, 4, 2):
        registers = tuple(zip(captures[i:i + 2], labels[i:i + 2], strict=True))
        modules.append(_results(active, _channel(cell, "outputs", "cell"), registers))
    entries = []
    for i, module in enumerate(modules):
        entry, = module.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 6), "Y": 3 * (i // 6)})
    _place(entries, selector)
    for name in ("pin-source-rank", "pin-retained-label", "pin-source-label", "pin-source-row"):
        _place(entries, _read_blueprint(circuits / f"{name}.spz2bp"))
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    first, last = sample["reserved_channels"]
    sample_channels = range(first, last + 1)
    senders, receivers = set(), set()
    for i, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind not in ("ControlledSignalReceiver", "ControlledSignalTransmitter"):
            continue
        (source, _), = wiring.sources(i, 0)
        channel = decode_constant(wiring.entries[source][1]["C"])
        if kind == "ControlledSignalTransmitter":
            if channel in senders or channel in sample_channels:
                raise ValueError(f"原生发射频道重复 {channel}")
            senders.add(channel)
        else:
            receivers.add(channel)
    selector_inputs = {frozen, *selected["inputs"]["words"],
                       *(ch for lane in selected["inputs"]["columns"] for ch in lane.values())}
    external = selector_inputs | {enable, level, *rows}
    if initial_label in senders or receivers - senders != external | {initial_label} or senders & external:
        raise ValueError("候选行的原生收发频道与接口表不符")
    return document, {
        "inputs": {"enable": enable, "level": level, "target_rows_bottom_to_top": rows, "candidate_ready": frozen},
        "outputs": {"row": output, "ready": ready},
        "channels": {"private_range": [channel_base, channel_base + 14], "selector": selected["reserved_channels"],
                     "initial_label_empty": initial_label},
        "timing": {"channel_signal_ticks": _RADIO, "reset_hold_signal_ticks": _RESET_TICKS,
                   "column_prepare_signal_ticks": reset_steps * _RADIO, "column_read_signal_ticks": read_steps * _RADIO,
                   "start_to_ready_signal_ticks": (4 * (reset_steps + read_steps + 6) + read_steps + 8) * _RADIO},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出四列冻结候选的原色来源行读取器")
    parser.add_argument("circuits", type=Path, help="顶针逆推验收分册目录")
    parser.add_argument("target_rows", type=Path, help="五层原色读取 JSON 接口表")
    parser.add_argument("--channel-base", type=int, default=1701920, help="行读取器的首频道")
    parser.add_argument("--output", required=True, type=Path, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(args.circuits, args.target_rows, args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
