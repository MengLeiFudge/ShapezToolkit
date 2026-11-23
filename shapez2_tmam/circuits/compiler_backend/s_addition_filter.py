"""复用同一层电路检查 S 前态的非晶追加支撑。"""

import argparse
from inspect import getsource
from pathlib import Path

from ...synthesis.physics import Shape
from ...synthesis.row_support import _unsupported, addition_needs_lower
from ...synthesis.shape_methods import analyze_part, rotate_ccw, shape_literal
from ..circuit_packing import stack_platforms
from ..compiler_frontend import FrontendError, compile_field_methods, compile_method
from ..local_module import Module
from . import _write_blueprint
from .fields import compile_fields
from .method_sequence import _radio_channels
from .module_caller import _RADIO_TICKS, _compare, _gate, _local_wiring, _wait_timer
from .prefix_scan_wiring import _append


_START, _DONE, _ACCEPTED = range(1704700, 1704703)
_TARGET = tuple(range(1704710, 1704715))
_SOURCE = tuple(range(1703513, 1703518))
_LEVEL, _ROW, _LOWER, _CANDIDATE, _GROUND, _ROW_OK = range(1704720, 1704726)
_STATES = tuple(range(1704730, 1704734))
_TIMERS = tuple(range(1704740, 1704745))
_PASS, _FAIL = 5, 6


def _addition(row: Shape | None, candidate: Shape | None, below: Shape | None, ground: bool) -> int:
    part = analyze_part(row)
    if (part is None) | (analyze_part(candidate) is not None):
        return 0
    if part == shape_literal("cu------"):
        return 5
    supported = ground | (analyze_part(below) is not None)
    if part == shape_literal("P-------"):
        if supported:
            return 4
        return 3
    if supported:
        return 2
    return 1


def addition_q0(row: Shape | None, candidate: Shape | None, below: Shape | None, ground: bool) -> int:
    return _addition(row, candidate, below, ground)


def addition_q1(row: Shape | None, candidate: Shape | None, below: Shape | None, ground: bool) -> int:
    return _addition(rotate_ccw(row), rotate_ccw(candidate), rotate_ccw(below), ground)


def addition_q2(row: Shape | None, candidate: Shape | None, below: Shape | None, ground: bool) -> int:
    return addition_q1(rotate_ccw(row), rotate_ccw(candidate), rotate_ccw(below), ground)


def addition_q3(row: Shape | None, candidate: Shape | None, below: Shape | None, ground: bool) -> int:
    return addition_q2(rotate_ccw(row), rotate_ccw(candidate), rotate_ccw(below), ground)


def addition_row_allowed(q0: int, q1: int, q2: int, q3: int) -> bool:
    return ((q0 != 5) & (q1 != 5) & (q2 != 5) & (q3 != 5)
            & (not addition_needs_lower(q0, q3, q1, q2))
            & (not addition_needs_lower(q1, q0, q2, q3))
            & (not addition_needs_lower(q2, q1, q3, q0))
            & (not addition_needs_lower(q3, q2, q0, q1)))


def _rows(rows: tuple[int, ...], output: int, *, first: int = 0) -> Module:
    board = Module({"level": _LEVEL, **{f"row{i}": channel for i, channel in enumerate(rows, first)}})
    for i in range(first, first + len(rows)):
        active = _compare(board, f"level{i}", "level", i)
        _gate(board, "If", "row", f"row{i}", active)
    board.outputs = {"row": output}
    if output == _ROW:
        board.outputs[_compare(board, "ground", "level", 0)] = _GROUND
    return board


def _advance(ready: int) -> Module:
    board = Module({"start": _START, "level": _LEVEL, "ready": ready, "row_ok": _ROW_OK})
    enabled = _compare(board, "enabled", "start", 1)
    board.lookup("level", "increment", ((level, level + 1) for level in range(5)))
    idle = _compare(board, "idle", "level", -1)
    at_row = _compare(board, "at_row", "increment", None, "Bg==")
    sampled = _gate(board, "And", "sampled", at_row, _compare(board, "stable", "ready", "level"))
    accepted = _compare(board, "row_accepted", "row_ok", 1)
    rejected = _compare(board, "row_rejected", "row_ok", 0)
    _gate(board, "If", "next", 0, idle)
    _gate(board, "If", "next", "increment", _gate(board, "And", "next_row", sampled, accepted))
    _gate(board, "If", "next", _FAIL, _gate(board, "And", "reject", sampled, rejected))
    unchanged = _compare(board, "unchanged", "next", None)
    _gate(board, "If", "state", "next", enabled)
    _gate(board, "If", "state", "level", _gate(board, "And", "continue_waiting", enabled, unchanged))
    _gate(board, "If", "state", -1, _gate(board, "Not", "reset", enabled))
    board.outputs = {"state": _LEVEL}
    return board


def _result() -> Module:
    board = Module({"start": _START, "level": _LEVEL})
    enabled = _compare(board, "enabled", "start", 1)
    passed = _compare(board, "passed", "level", _PASS)
    failed = _compare(board, "failed", "level", _FAIL)
    finished = _gate(board, "Or", "finished", passed, failed)
    board.outputs = {_gate(board, "And", "done", enabled, finished): _DONE,
                     _gate(board, "And", "accepted", enabled, passed): _ACCEPTED}
    return board


def _classifiers() -> tuple[tuple[dict, dict], ...]:
    inputs = {"row": _ROW, "candidate": _CANDIDATE, "below": _LOWER, "ground": _GROUND}
    result = []
    for start in (0, 2):
        names = {f"q{i}": f"addition_q{i}" for i in (start, start + 1)}
        programs, _ = compile_field_methods(Path(__file__), names)
        outputs = {f"q{i}": _STATES[i] for i in (start, start + 1)}
        result.append(compile_fields(programs, input_channels=inputs, output_channels=outputs))
    return tuple(result)


def _row_check() -> tuple[dict, dict]:
    source = "\n\n".join(getsource(function) for function in (_unsupported, addition_needs_lower, addition_row_allowed))
    program = compile_method(source, "addition_row_allowed")
    inputs = dict(zip(("q0", "q1", "q2", "q3"), _STATES, strict=True))
    return compile_fields({"allowed": program}, input_channels=inputs, output_channels={"allowed": _ROW_OK})


def build() -> tuple[dict, dict]:
    classifiers = _classifiers()
    row_check, row_report = _row_check()
    select_ticks = 2 * _RADIO_TICKS
    classify_ticks = max(report["settling"]["hold_signal_ticks"] for _, report in classifiers)
    check_ticks = row_report["settling"]["hold_signal_ticks"]
    row_steps = (select_ticks + classify_ticks + check_ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 2
    timers, ready, _ = _wait_timer(_LEVEL, _TIMERS, row_steps, row_steps)
    modules = [_rows(_TARGET, _ROW), _rows(_TARGET[:-1], _LOWER, first=1), _rows(_SOURCE, _CANDIDATE),
               _advance(ready), _result(), *timers]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    for part in (*[compiled for compiled, _ in classifiers], row_check):
        _append(document, part["BP"]["Entries"])
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    if (received.keys() - sent.keys() != {_START, *_TARGET, *_SOURCE}
            or any(count != 1 for count in sent.values())):
        raise ValueError("追加许可的原生收发不匹配")
    report = {"inputs": {"start": _START, "target_rows_bottom_to_top": _TARGET,
                         "candidate_rows_bottom_to_top": _SOURCE},
              "outputs": {"done": _DONE, "accepted": _ACCEPTED}, "reserved_channels": [1704700, 1704799],
              "timing": {"row_hold_signal_ticks": row_steps * _RADIO_TICKS,
                         "accepted_path_signal_ticks": 5 * (row_steps + 3) * _RADIO_TICKS + 5 * _RADIO_TICKS,
                         "reset_signal_ticks": 4 * _RADIO_TICKS},
              "row_logic_gates": sum(report["logic_gates"] for _, report in classifiers) + row_report["logic_gates"],
              "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
              "global_transmitters": len(sent)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 S 前态的逐层追加许可")
    parser.add_argument("--output", type=Path, required=True, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build()
        _write_blueprint(document, report, args.output)
    except FrontendError as error:
        parser.error(f"{error.filename}:{error.lineno}:{error.offset} {error.msg}")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
