"""合装可暂停的四列顶针候选枚举。"""

import argparse
from pathlib import Path

from ..compiler_backend import _write_blueprint
from ..compiler_backend.fields import compile_fields
from ..compiler_backend.module_caller import _RADIO_TICKS, _any, _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from . import compile_field_methods
from .pin_column_cursor import compile_pin_column_cursor


_RESET, _RUN, _CALCULATE, _SAVE, _DISPATCH = range(1, 6)
_READY, _EXHAUSTED, _RESUME, _ADVANCE, _REARM = range(6, 11)
_SYNC_CAPTURE, _SYNC_STORE = 11, 12
_WAIT_PHASES = (_RESET, _RUN, _CALCULATE, _RESUME, _REARM, _READY, _EXHAUSTED)
_FIELDS = ("slot", "next_slot", *(f"material_{i}" for i in range(4)))


def _waiting(phase, reset_tap, result_tap, done, advance, output):
    board = Module({"phase": phase, "reset_tap": reset_tap, "result_tap": result_tap,
                    "done": done, "advance": advance})
    reset_wait = _gate(board, "Or", "reset_wait", _compare(board, "reset_pending", "reset_tap", _RESET, "Bg=="),
                       _compare(board, "cursor_busy", "done", 0, "Bg=="))
    waits = []
    for state, condition in (
        (_RESET, reset_wait), (_RUN, _compare(board, "result_pending", "done", 1, "Bg==")),
        (_CALCULATE, _compare(board, "calculate_pending", "result_tap", _CALCULATE, "Bg==")),
        (_RESUME, _compare(board, "resume_pending", "result_tap", _RESUME, "Bg==")),
        (_REARM, _compare(board, "advance_still_on", "advance", 0, "Bg==")),
        (_READY, _compare(board, "no_advance", "advance", 1, "Bg==")), (_EXHAUSTED, 1),
    ):
        waits.append(_gate(board, "And", f"wait_{state}", _compare(board, f"in_{state}", "phase", state), condition))
    pending = _any(board, "waiting", tuple(waits))
    _gate(board, "If", "ready_stamp", "phase", _gate(board, "Not", "can_step", pending))
    board.outputs = {"ready_stamp": output}
    return board


def _phase(enable, phase, column, waiting):
    board = Module({"enable": enable, "phase": phase, "column": column, "waiting": waiting})
    board.lookup("phase", "next", ((0, _RESET), (None, _RESET), (_RESET, _RUN), (_RUN, _CALCULATE),
                                    (_CALCULATE, _SAVE), (_SAVE, _SYNC_CAPTURE), (_SYNC_CAPTURE, _SYNC_STORE),
                                    (_SYNC_STORE, _DISPATCH), (_REARM, _READY),
                                    (_READY, _RESUME), (_RESUME, _ADVANCE), (_ADVANCE, _RESET)))
    _gate(board, "If", "state", "next", "advance")
    enabled = _compare(board, "enabled", "enable", 1)
    dispatch = _compare(board, "dispatch", "phase", _DISPATCH)
    waits = tuple(_compare(board, f"waits_{state}", "phase", state) for state in _WAIT_PHASES)
    blocked = _gate(board, "And", "blocked", _any(board, "waits", waits),
                    _compare(board, "stale_stamp", "waiting", "phase", "Bg=="))
    _gate(board, "And", "advance", enabled,
          _gate(board, "Not", "no_advance", _gate(board, "Or", "pending", blocked, dispatch)))
    _gate(board, "If", "state", "phase", _gate(board, "And", "keep", enabled, blocked))
    route = _gate(board, "And", "route", enabled, dispatch)
    for label, value, condition in (("query", _RESET, _compare(board, "query_column", "column", 0, "Ag==")),
                                    ("ready", _REARM, _compare(board, "combination", "column", 4)),
                                    ("end", _EXHAUSTED, _compare(board, "end_column", "column", -1))):
        if label == "query":
            condition = _gate(board, "And", "querying", condition, _compare(board, "query_range", "column", 4, "BA=="))
        _gate(board, "If", "state", value, _gate(board, "And", label, route, condition))
    _gate(board, "If", "state", 0, _gate(board, "Not", "disabled", enabled))
    board.outputs = {"state": phase}
    return board


def _events(enable, phase, outputs):
    board = Module({"enable": enable, "phase": phase})
    enabled = _compare(board, "enabled", "enable", 1)
    _gate(board, "Not", "reset", enabled)
    for name, states in (("query", (_RUN, _CALCULATE, _SAVE)), ("result_ready", (_CALCULATE, _SAVE)),
                         ("consume", (_RESUME, _ADVANCE)), ("commit", (_SAVE, _ADVANCE)),
                         ("capture", (_SAVE,)), ("ready", (_REARM, _READY)), ("exhausted", (_EXHAUSTED,))):
        matches = tuple(_compare(board, f"{name}_{state}", "phase", state) for state in states)
        _gate(board, "And", name, enabled, _any(board, name, matches))
    board.outputs = outputs
    return board


def _controls(reset, commit, selectors):
    board = Module({"reset": reset, "commit": commit})
    active = _compare(board, "active", "reset", 0)
    _gate(board, "And", "load", active, "commit")
    _gate(board, "And", "keep", active, _gate(board, "Not", "idle", "commit"))
    _compare(board, "clear", "reset", 1)
    board.outputs = selectors
    return board


def _lane_controls(lane, column, capture, valid, reset, selectors):
    board = Module({"column": column, "capture": capture, "valid": valid, "reset": reset})
    active = _compare(board, "active", "reset", 0)
    capture_enabled = _gate(board, "And", "capture_enabled", active, "capture")
    hit = _gate(board, "And", "hit", _compare(board, "selected", "column", lane), "valid")
    _gate(board, "And", "load", capture_enabled, hit)
    changed = _gate(board, "And", "changed", "capture", _compare(board, "affected", "column", lane, "BQ=="))
    _gate(board, "And", "keep", active, _gate(board, "Not", "unchanged", changed))
    _gate(board, "Or", "clear", "reset", _gate(board, "And", "drop", changed, _gate(board, "Not", "miss", hit)))
    board.outputs = selectors
    return board


def _store(selectors, inputs, outputs, defaults):
    board = Module({**selectors, **{f"new_{name}": channel for name, channel in inputs.items()},
                    **{f"old_{name}": channel for name, channel in outputs.items()}})
    for name, value in defaults.items():
        _gate(board, "If", name, f"new_{name}", "load")
        _gate(board, "If", name, f"old_{name}", "keep")
        _gate(board, "If", name, value, "clear")
    board.outputs = outputs
    return board


def _place(entries, document):
    boards = document["BP"]["Entries"]
    offset = max((p.get("X", 0) for p in entries), default=-3) + 3 - min(p.get("X", 0) for p in boards)
    entries.extend({**p, "X": p.get("X", 0) + offset} for p in boards)


def build(column_base: int, cursor_base: int, channel_base: int) -> tuple[dict, dict]:
    if type(channel_base) is not int or not 1 <= channel_base < 1 << 24:
        raise ValueError("循环首频道须在 1～16777215 内")
    names = ("enable", "advance", "q0", "q1", "q2", "q3", "start", "column", "phase", "reentry", "next_column",
             "next_start", "waiting", "reset", "result_ready", "consume", "commit", "capture", "ready", "exhausted")
    ch = dict(zip(names, range(channel_base, channel_base + len(names))))
    numbers = iter(range(channel_base + len(names), channel_base + 64))
    timer = tuple(next(numbers) for _ in range(5))
    lanes = [{name: next(numbers) for name in _FIELDS} for _ in range(4)]
    selectors = [{mode: next(numbers) for mode in ("load", "keep", "clear")} for _ in range(5)]
    end = max(max(c.values()) for c in selectors)
    if end >= 1 << 24 or set(range(channel_base, end + 1)) & (
        set(range(column_base, column_base + 23)) | set(range(cursor_base, cursor_base + 17))
    ):
        raise ValueError("循环频道须合法，并和单列校验、游标互不重叠")
    cursor, interface = compile_pin_column_cursor(column_base, cursor_base, start_slot_channel=ch["start"])
    raw = interface["outputs"]
    cursor_run = interface["inputs"]["enable"]
    source = Path(__file__).with_name("pin_column_combinations.py")
    base_inputs = {key: ch[key] for key in ("column", "start", "reset", "result_ready", "consume")}
    groups = [
        ({"word": "select_word"}, {k: ch[k] for k in ("column", "q0", "q1", "q2", "q3")},
         {"word": interface["inputs"]["word"]}),
        ({"restart": "retained_start"}, {"column": ch["column"], **{f"q{i}_next": lane["next_slot"] for i, lane in enumerate(lanes)}},
         {"restart": ch["reentry"]}),
        ({name: name for name in ("next_column", "next_start")},
         {**base_inputs, "restart": ch["reentry"], "result_valid": raw["valid"]},
         {name: ch[name] for name in ("next_column", "next_start")}),
    ]
    entries = []
    reports = []
    for fields, inputs, outputs in groups:
        programs, _ = compile_field_methods(source, fields)
        document, report = compile_fields(programs, input_channels=inputs, output_channels=outputs)
        _place(entries, document)
        reports.append(report)
    mux, restart, transition = (report["settling"]["hold_signal_ticks"] for report in reports)
    reset_steps = (max(mux, interface["reset_signal_ticks"], interface["start_slot_hold_signal_ticks"])
                   + _RADIO_TICKS - 1) // _RADIO_TICKS + 3
    sample_steps = (restart + transition + _RADIO_TICKS - 1) // _RADIO_TICKS + 4
    timers, reset_tap, result_tap = _wait_timer(ch["phase"], timer, reset_steps, sample_steps)
    event_outputs = {k: ch[k] for k in ("reset", "result_ready", "consume", "commit", "capture", "ready", "exhausted")}
    event_outputs["query"] = cursor_run
    modules = [
        _waiting(ch["phase"], reset_tap, result_tap, raw["done"], ch["advance"], ch["waiting"]),
        _phase(ch["enable"], ch["phase"], ch["column"], ch["waiting"]),
        _events(ch["enable"], ch["phase"], event_outputs),
        _controls(ch["reset"], ch["commit"], selectors[4]),
        _store(selectors[4], {field: ch[f"next_{field}"] for field in ("column", "start")},
               {field: ch[field] for field in ("column", "start")}, {"column": 0, "start": 0}),
        *timers,
    ]
    for i, lane in enumerate(lanes):
        modules.append(_lane_controls(i, ch["column"], ch["capture"], raw["valid"], ch["reset"], selectors[i]))
        for pair in (_FIELDS[:2], _FIELDS[2:4], _FIELDS[4:]):
            modules.append(_store(selectors[i], {k: raw[k] for k in pair}, {k: lane[k] for k in pair},
                                  {k: 20 if k in _FIELDS[:2] else -1 for k in pair}))
    offset = 3 + max(board["X"] for board in entries)
    entries.extend({**module.layout()["BP"]["Entries"][0], "X": offset + 3 * (i % 6), "Y": 3 * (i // 6)}
                   for i, module in enumerate(modules))
    _place(entries, cursor)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    _local_wiring(document["BP"])
    report = {
        "inputs": {name: ch[name] for name in ("enable", "advance", "q0", "q1", "q2", "q3")},
        "outputs": {"ready": ch["ready"], "exhausted": ch["exhausted"], "columns": lanes},
        "column_base": column_base, "cursor": interface,
        "reserved_channels": [channel_base, end],
        "timing": {"channel_signal_ticks": _RADIO_TICKS, "reset_signal_ticks": 96,
                   "query_reset_wait_signal_ticks": reset_steps * _RADIO_TICKS,
                   "transition_wait_signal_ticks": sample_steps * _RADIO_TICKS},
        "platforms": len(entries), "building_entries": sum(len(p["B"]["Entries"]) for p in entries),
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="合装可暂停的四列顶针候选枚举")
    parser.add_argument("--column-base", required=True, type=int, help="单列校验首频道")
    parser.add_argument("--cursor-base", required=True, type=int, help="单列游标首频道")
    parser.add_argument("--channel-base", required=True, type=int, help="四列循环首频道")
    parser.add_argument("--output", required=True, type=Path, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(args.column_base, args.cursor_base, args.channel_base), args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
