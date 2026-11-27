"""共用顶针行读取器预取低四层，并按请求封存顶盖。"""

import argparse
from pathlib import Path

from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _any, _compare, _control, _gate, _local_wiring, _results, _wait_timer
from ..local_module import Module
from .pin_candidate_row import _in_phases, _RADIO, _read_report
from .pin_source_rows import _parameters, _publish, _reply, _sealed, _verify_channels


_BASE = 1702280
_WINDOW = 60
_CALLS = ((1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12), (14, 15, 16))
_LOWER_DONE, _DONE = 13, 17
_PREFETCH = (1704300, 1704301, 1704302, 1704303)
_PREFETCH_READY = 1704309


def _permission(phase, reply, elapsed, output):
    board = Module({"phase": phase, "reply": reply, "elapsed": elapsed})
    preparing = _in_phases(board, "prepare", tuple(reset for reset, _, _ in _CALLS))
    reading = _in_phases(board, "read", tuple(run for _, run, _ in _CALLS))
    reset_time = _compare(board, "reset_time", "elapsed", "phase")
    cleared = _compare(board, "cleared", "reply", 0)
    reset_done = _gate(board, "And", "reset_done", reset_time, cleared)
    wait_reset = _gate(board, "And", "wait_reset", preparing, _gate(board, "Not", "reset_needed", reset_done))
    wait_read = _gate(board, "And", "wait_read", reading, _compare(board, "read_pending", "reply", 1, "Bg=="))
    pending = _gate(board, "Or", "pending", wait_reset, wait_read)
    board.outputs[_gate(board, "If", "permission", "phase", _gate(board, "Not", "cleared_phase", pending))] = output
    return board


def _phase(frozen, enable, phase, permission, top_active):
    board = Module({"frozen": frozen, "enable": enable, "phase": phase, "permission": permission})
    board.lookup("phase", "following", ((i, i + 1) for i in range(_DONE)))
    live = _compare(board, "live", "frozen", 1)
    request = _compare(board, "request", "enable", 1)
    active = _gate(board, "And", "top_active", live, request)
    no_top = _gate(board, "Not", "no_top", request)
    top = _compare(board, "top", "phase", _LOWER_DONE + 1, "Ag==")
    rewind = _gate(board, "And", "rewind", top, no_top)
    hold_for_top = _gate(board, "And", "hold_for_top", no_top, _compare(board, "lower_done", "phase", _LOWER_DONE))
    done = _compare(board, "done", "phase", _DONE)
    waiting = _compare(board, "waiting", "phase", "permission", "Bg==")
    blocked = _any(board, "blocked", (waiting, hold_for_top, done))
    forward = _gate(board, "And", "forward", live, _gate(board, "Not", "hold", rewind))
    moving = _gate(board, "And", "moving", forward, _gate(board, "Not", "step", blocked))
    _gate(board, "If", "next", "phase", _gate(board, "And", "pausing", forward, blocked))
    _gate(board, "If", "next", _LOWER_DONE, _gate(board, "And", "reset_top", live, rewind))
    _gate(board, "If", "next", 0, _gate(board, "Not", "reset", live))
    _gate(board, "If", "next", "following", moving)
    board.outputs = {"next": phase, active: top_active}
    return board


def _level(phase, channel):
    board = Module({"phase": phase})
    board.lookup("phase", "level", ((state, z) for z, states in enumerate(_CALLS) for state in states))
    board.outputs = {"level": channel}
    return board


def _lower_ready(frozen, phase, statuses, output):
    board = Module({"frozen": frozen, "phase": phase, **{f"valid{z}": ch for z, ch in enumerate(statuses)}})
    valid = _gate(board, "And", "valid_lower", _compare(board, "valid_phase", "phase", _LOWER_DONE, "Ag=="),
                  _compare(board, "enabled", "frozen", 1))
    for z in range(4):
        valid = _gate(board, "And", f"checked{z}", valid, f"valid{z}")
    board.outputs = {valid: output}
    return board


def _prefetch(frozen, valid, pairs, *, ready=None):
    board = Module({"frozen": frozen, "valid": valid})
    live = _gate(board, "And", "live", "valid", _compare(board, "frozen_now", "frozen", 1))
    if ready is not None:
        board.outputs[live] = ready
    for i, (storage, channel) in enumerate(pairs):
        board.inputs[f"stored{i}"] = storage
        board.outputs[_gate(board, "If", f"row{i}", f"stored{i}", live)] = channel
    return board


def build(reader: dict, previous: dict) -> tuple[dict, dict]:
    request, reply, timing = (reader[key] for key in ("inputs", "outputs", "timing"))
    inputs, outputs = previous["inputs"], previous["outputs"]
    frozen, enable = inputs["candidate_ready"], inputs["enable"]
    params = (inputs["mode"], inputs["crystal_mask"], *inputs["members"])
    arguments = (request["mode"], request["crystal_mask"], *request["members"])
    sends = {request["enable"], request["level"], *arguments}
    reads = {frozen, *reply.values(), enable, *params}
    used = {*outputs["rows_bottom_to_top"], outputs["ready"], outputs["valid"], *_PREFETCH, _PREFETCH_READY}
    window = range(_BASE, _BASE + _WINDOW)
    if (frozen != request["candidate_ready"] or timing["channel_signal_ticks"] != _RADIO
            or len(sends) != 8 or len(used) != 12 or len(reads) != 11 or reads & (used | sends)
            or sends & (used | set(window)) or previous["reader"]["outputs"] != reply):
        raise ValueError("四槽、五层封存与共用行读取器的接口不符")
    spare = iter(ch for ch in window if ch not in reads | used)

    def take(n):
        return tuple(next(spare) for _ in range(n))

    phase, permission, top_active, capture_params, done, reply_ready, sealed_ready, sealed_valid, lower_valid = take(9)
    captures, stored, statuses, timer = take(5), take(5), take(5), take(5)
    reset_steps = (timing["reset_hold_signal_ticks"] + _RADIO - 1) // _RADIO + 3
    timers, elapsed, _ = _wait_timer(phase, timer, reset_steps, 1)
    routing = _control(phase, request["enable"], done, _CALLS, (), captures)
    control = routing[0]
    _compare(control, "capture_parameters", "phase", _CALLS[-1][0])
    control.outputs["capture_parameters"] = capture_params
    parameter_ports = tuple(zip(("mode", "mask", "q0", "q1", "q2", "q3"), params, arguments, strict=True))
    modules = [_phase(frozen, enable, phase, permission, top_active),
               _permission(phase, reply_ready, elapsed, permission),
               *routing, _reply(phase, reply["ready"], *arguments[:2], reply_ready), _level(phase, request["level"]),
               _lower_ready(frozen, phase, statuses[:4], lower_valid), *timers,
               _sealed(top_active, done, statuses, sealed_ready, sealed_valid),
               _publish(enable, frozen, top_active, sealed_ready, sealed_valid, flags=(outputs["ready"], outputs["valid"]))]
    modules.extend(_parameters(top_active, capture_params, parameter_ports[i:i + 2]) for i in range(0, 6, 2))
    for i in range(0, 5, 2):
        active = frozen if i < 4 else top_active
        for value, memory in ((reply["row"], stored), (reply["valid"], statuses)):
            registers = tuple(zip(captures[i:i + 2], memory[i:i + 2], strict=True))
            modules.append(_results(active, value, registers))
        if i < 4:
            pairs = tuple(zip(stored[i:i + 2], _PREFETCH[i:i + 2], strict=True))
            modules.append(_prefetch(frozen, lower_valid, pairs, ready=_PREFETCH_READY if i == 0 else None))
    rows = tuple(zip(stored, outputs["rows_bottom_to_top"], strict=True))
    modules.extend(_publish(enable, frozen, top_active, sealed_ready, sealed_valid, rows=pair)
                   for pair in (rows[:3], rows[3:]))
    entries = []
    for i, board in enumerate(modules):
        entry, = board.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 6), "Y": 3 * (i // 6)})
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    _verify_channels(wiring, reads, used, sends | {*_PREFETCH, _PREFETCH_READY}, window)
    reset_ticks = (reset_steps + 8) * _RADIO
    return document, {
        "inputs": inputs,
        "outputs": {**outputs, "prefetched_rows": _PREFETCH, "prefetch_ready": _PREFETCH_READY},
        "reader": previous["reader"],
        "channels": {"private_range": [window[0], window[-1]], "phase": phase},
        "timing": {"channel_signal_ticks": _RADIO, "reset_hold_signal_ticks": timing["reset_hold_signal_ticks"],
                   "lower_start_to_ready_signal_ticks": 4 * (timing["lower_start_to_ready_signal_ticks"] + reset_ticks),
                   "top_start_to_ready_signal_ticks": timing["top_start_to_ready_signal_ticks"] + reset_ticks},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出共用低四行预取和第五层顶盖读取的封存控制")
    parser.add_argument("reader", type=Path, help="共用行读取器 JSON")
    parser.add_argument("previous", type=Path, help="旧五层封存 JSON")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(_read_report(args.reader), _read_report(args.previous)), args.output)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
