"""依次读回并封存顶针前态的五层原色行。"""

import argparse
from pathlib import Path

from ...mari.blueprint import _kind
from ...mari.signals import decode_constant
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _advance, _compare, _control, _gate, _local_wiring, _results, _wait_timer
from ..local_module import Module
from .pin_candidate_row import _RADIO, _RESET_TICKS, _read_report


_BASE = 1702280
_WINDOW = 60
_CALLS = tuple((phase, phase + 1, phase + 2) for phase in range(2, 17, 3))
_PARAMS = ("mode", "crystal_mask", "q0", "q1", "q2", "q3")


def _ready_to_read(board):
    return _gate(board, "And", "requested", _compare(board, "enabled", "enable", 1),
                 _compare(board, "frozen", "candidate_ready", 1))


def _session(enable, candidate, state, active):
    board = Module({"enable": enable, "candidate_ready": candidate, "state": state})
    requested = _ready_to_read(board)
    live = _gate(board, "And", "live", requested, _compare(board, "usable", "state", 2, "Bg=="))
    was_started = _compare(board, "was_started", "state", 0, "Bg==")
    dropped = _gate(board, "And", "dropped", was_started, _gate(board, "Not", "not_live", live))
    blocked = _gate(board, "And", "blocked", "enabled", dropped)
    _gate(board, "If", "next", 2, blocked)
    _gate(board, "If", "next", 1, live)
    idle = _gate(board, "Not", "idle", _gate(board, "Or", "occupied", live, blocked))
    _gate(board, "If", "next", 0, idle)
    board.outputs = {"next": state, live: active}
    return board


def _parameters(active, capture, ports):
    board = Module({"active": active, "capture": capture})
    load = _gate(board, "And", "load", "active", "capture")
    keep = _gate(board, "And", "keep", "active", _gate(board, "Not", "outside_capture", "capture"))
    for name, source, saved in ports:
        old = f"saved_{name}"
        board.inputs.update({name: source, old: saved})
        result = f"latched_{name}"
        _gate(board, "If", result, name, load)
        _gate(board, "If", result, old, keep)
        board.outputs[result] = saved
    return board


def _reply(phase, done, mode, mask, output):
    board = Module({"phase": phase, "done": done, "mode": mode, "mask": mask})
    board.lookup("mask", "valid_mask", ((mask, 1) for mask in range(16)))
    modes = _gate(board, "Or", "valid_mode", _compare(board, "member", "mode", 0),
                  _compare(board, "template", "mode", 1))
    legal = _gate(board, "And", "legal", modes, "valid_mask")
    # 无效顶盖参数不会使读取器启动。结束这一层时仍保留整组的非法状态。
    reject = _gate(board, "And", "reject", _compare(board, "top_run", "phase", _CALLS[-1][1]),
                   _gate(board, "Not", "invalid", legal))
    _gate(board, "Or", "reply", _compare(board, "responded", "done", 1), reject)
    board.outputs = {"reply": output}
    return board


def _level(phase, output):
    board = Module({"phase": phase})
    board.lookup("phase", "level", ((step, z) for z, stages in enumerate(_CALLS) for step in stages))
    board.outputs = {"level": output}
    return board


def _sealed(active, done, statuses, ready, valid):
    board = Module({"active": active, "done": done, **{f"z{i}": ch for i, ch in enumerate(statuses)}})
    ready_gate = _gate(board, "And", "ready", "active", "done")
    valid_gate = ready_gate
    for i in range(len(statuses)):
        valid_gate = _gate(board, "And", f"checked_{i}", valid_gate, f"z{i}")
    board.outputs = {ready_gate: ready, valid_gate: valid}
    return board


def _publish(enable, candidate, active, ready, valid, *, flags=None, rows=()):
    board = Module({"enable": enable, "candidate_ready": candidate, "active": active, "valid": valid})
    permit = _gate(board, "And", "permit", _ready_to_read(board), "active")
    valid_now = _gate(board, "And", "valid_now", permit, "valid")
    if flags is not None:
        board.inputs["ready"] = ready
        _gate(board, "And", "ready_now", permit, "ready")
        board.outputs = dict(zip(("ready_now", valid_now), flags, strict=True))
    for i, (stored, output) in enumerate(rows):
        board.inputs[f"z{i}"] = stored
        _gate(board, "If", f"row{i}", f"z{i}", valid_now)
        board.outputs[f"row{i}"] = output
    return board


def _verify_channels(wiring, supplied, public, reader_inputs, window):
    receivers, senders = set(), set()
    for i, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind not in ("ControlledSignalReceiver", "ControlledSignalTransmitter"):
            continue
        (source, _), = wiring.sources(i, 0)
        channel = decode_constant(wiring.entries[source][1]["C"])
        if kind == "ControlledSignalTransmitter":
            if channel in senders:
                raise ValueError(f"五层封存发射频道重复 {channel}")
            senders.add(channel)
        else:
            receivers.add(channel)
    if (receivers - senders != supplied or not public <= senders
            or senders - set(window) != reader_inputs or senders & supplied):
        raise ValueError("五层封存的原生频道与接口表不符")


def build(reader: dict, channel_base: int = _BASE) -> tuple[dict, dict]:
    request, reply, timing = (reader[key] for key in ("inputs", "outputs", "timing"))
    candidate = request["candidate_ready"]
    arguments = (request["mode"], request["crystal_mask"], *request["members"])
    sends = {request["enable"], request["level"], *arguments}
    receives = {candidate, reply["ready"], reply["valid"], reply["row"]}
    old_base, old_end = reader["channels"]["private_range"]
    public_targets = set(request["target_rows_bottom_to_top"])
    window = range(channel_base, channel_base + _WINDOW)
    if (not 1 <= window[0] <= window[-1] < 1 << 24 or timing["channel_signal_ticks"] != _RADIO
            or len(sends) != 8 or len(receives) != 4 or sends & (receives | public_targets)
            or set(window).intersection((*range(old_base, old_end + 1), *sends, *receives, *public_targets))):
        raise ValueError("五层封存频道须合法且与原色发布及读取器接口分开")

    channels = iter(window)
    enable = next(channels)
    params = tuple(next(channels) for _ in _PARAMS)
    ready, valid = next(channels), next(channels)
    rows = tuple(next(channels) for _ in range(5))
    (session, active, phase, param_capture, done, reply_ready, sealed_ready,
     sealed_valid) = (next(channels) for _ in range(8))
    capture = tuple(next(channels) for _ in _CALLS)
    stored = tuple(next(channels) for _ in _CALLS)
    statuses = tuple(next(channels) for _ in _CALLS)
    timer = tuple(next(channels) for _ in range(5))
    # 读取器的低使能需穿过发送端和接收端，再开始计算复位保持期。
    reset_steps = (timing["reset_hold_signal_ticks"] + _RADIO - 1) // _RADIO + 2
    timers, reset_tap, sample_tap = _wait_timer(phase, timer, reset_steps, 1)
    routing = _control(phase, request["enable"], done, _CALLS, (), capture)
    control = routing[0]
    _compare(control, "capture_parameters", "phase", 1)
    control.outputs["capture_parameters"] = param_capture
    parameter_ports = tuple(zip(_PARAMS, params, arguments, strict=True))
    modules = [
        _session(enable, candidate, session, active),
        _advance(active, phase, reply_ready, reset_tap, sample_tap, _CALLS),
        *routing,
        _reply(phase, reply["ready"], *arguments[:2], reply_ready),
        _level(phase, request["level"]),
        _sealed(active, done, statuses, sealed_ready, sealed_valid),
        _publish(enable, candidate, active, sealed_ready, sealed_valid, flags=(ready, valid)),
        *timers,
    ]
    modules.extend(_parameters(active, param_capture, parameter_ports[i:i + 2]) for i in range(0, 6, 2))
    for i in range(0, 5, 2):
        for output, memory in ((reply["row"], stored), (reply["valid"], statuses)):
            pairs = tuple(zip(capture[i:i + 2], memory[i:i + 2], strict=True))
            modules.append(_results(active, output, pairs))
    rows_by_level = tuple(zip(stored, rows, strict=True))
    for group in (rows_by_level[:3], rows_by_level[3:]):
        modules.append(_publish(enable, candidate, active, sealed_ready, sealed_valid, rows=group))

    entries = []
    for i, module in enumerate(modules):
        entry, = module.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 6), "Y": 3 * (i // 6)})
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    _verify_channels(wiring, receives | {enable, *params}, {ready, valid, *rows}, sends, window)
    return document, {
        "inputs": {"enable": enable, "candidate_ready": candidate, "mode": params[0],
                   "crystal_mask": params[1], "members": params[2:]},
        "outputs": {"ready": ready, "valid": valid, "rows_bottom_to_top": rows},
        "reader": {"inputs": {key: request[key] for key in ("enable", "level", "mode", "crystal_mask", "members")},
                   "outputs": reply},
        "channels": {"private_range": [window[0], window[-1]]},
        "timing": {"channel_signal_ticks": _RADIO, "reset_hold_signal_ticks": _RESET_TICKS,
                   "per_layer_reset_signal_ticks": reset_steps * _RADIO,
                   "start_to_ready_signal_ticks": 4 * timing["lower_start_to_ready_signal_ticks"]
                   + timing["top_start_to_ready_signal_ticks"] + (5 * (reset_steps + 8) + 8) * _RADIO},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出顶针前态五层原色行的封存控制")
    parser.add_argument("reader", type=Path, help="五层行读取器的 JSON 接口表")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="五层封存控制的首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(_read_report(args.reader), args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
