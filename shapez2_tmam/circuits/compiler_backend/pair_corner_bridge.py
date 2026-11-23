"""让制角子步骤和双半形主控共用配方写入桥。"""

import argparse
from pathlib import Path

from ..local_module import Module
from . import _write_blueprint
from .method_sequence import _DEFAULT_METHODS, _ENABLE, _KIND, _method
from .module_caller import _RADIO_TICKS, _WAIT_RADIX, _compare, _gate, _wait_timer
from .pair_sequence_bridge import _SELECTOR, _SHARED_DONE, _WRITE_RUN, _build, _completion, _select
from .prefix_scan_wiring import _report


_CORNER_SELECTOR, _CORNER_RUN, _CORNER_DONE = 1701636, 1701637, 1701638
_DENSE_RUN, _DENSE_DONE, _DENSE_PHASE, _DENSE_LEVEL = 1701461, 1701464, 1701400, 1701465
_NORMAL_SOURCE, _NORMAL_RUN, _ARMED, _ATTEMPT, _STARTED, _ACTIVE, _ACK, _DENSE_STATUS, _READY = range(1702140, 1702149)
_TIMERS = 1702149
_LOW_TICKS = 8 * _RADIO_TICKS


def _request() -> Module:
    board = Module({"kind": _KIND, "enable": _ENABLE, "corner": _DEFAULT_METHODS[0][1],
                    "run": _CORNER_RUN, "source": _CORNER_SELECTOR, "armed": _ARMED})
    owned = _gate(board, "And", "owned", _compare(board, "corner_kind", "kind", 1), "corner")
    active = _gate(board, "And", "active", "enable", owned)
    low = _compare(board, "low", "run", 0)
    high = _compare(board, "high", "run", 1)
    armed = _gate(board, "Or", "remember", low, "armed")
    source = _gate(board, "Or", "valid_source", _compare(board, "dense", "source", 1),
                   _compare(board, "release", "source", 2))
    request = _gate(board, "And", "request", high, _gate(board, "And", "valid", source, "armed"))
    board.outputs = {_gate(board, "And", "armed_out", active, armed): _ARMED,
                     _gate(board, "If", "attempt", "source", _gate(board, "And", "issue", active, request)): _ATTEMPT}
    return board


def _readiness() -> Module:
    board = Module({"dense": _DENSE_STATUS, "packet": _SHARED_DONE, "source": _STARTED})
    clear = _gate(board, "And", "clear", _compare(board, "dense_clear", "dense", 0),
                  _compare(board, "packet_clear", "packet", 0))
    _gate(board, "If", "status", 0, clear)
    for source, name in ((1, "dense"), (2, "packet")):
        selected = _compare(board, name + "_selected", "source", source)
        done = _compare(board, name + "_done", name, 1)
        _gate(board, "If", "status", 1, _gate(board, "And", name + "_accepted", selected, done))
    board.outputs = {"status": _READY}
    return board


def _reply() -> Module:
    board = Module({"attempt": _ATTEMPT, "ack": _ACK})
    present = _compare(board, "present", "attempt", None, "Bg==")
    matching = _compare(board, "matching", "ack", "attempt")
    board.outputs = {_gate(board, "And", "done", present, matching): _CORNER_DONE}
    return board


def _route() -> Module:
    board = Module({"kind": _KIND, "enable": _ENABLE, "corner_source": _STARTED, "corner_run": _ACTIVE,
                    "method_source": _NORMAL_SOURCE, "method_run": _NORMAL_RUN})
    corner = _compare(board, "corner", "kind", 1)
    corner_owned = _gate(board, "And", "corner_owned", "enable", corner)
    method_owned = _gate(board, "And", "method_owned", "enable", _gate(board, "Not", "method", corner))
    _gate(board, "If", "source", "corner_source", corner_owned)
    _gate(board, "If", "source", "method_source", method_owned)
    corner_run = _gate(board, "And", "call_corner", corner_owned, "corner_run")
    method_run = _gate(board, "And", "call_method", method_owned, "method_run")
    board.outputs = {"source": _SELECTOR, _gate(board, "Or", "run", corner_run, method_run): _WRITE_RUN}
    return board


def _dispatch(runs: dict[int, int], reset_steps: int, sample_steps: int):
    reset_width = 4 if reset_steps <= _WAIT_RADIX else 5
    reset_boards, reset, _ = _wait_timer(_ATTEMPT, tuple(range(_TIMERS, _TIMERS + reset_width)), reset_steps, 1)
    sample_base = _TIMERS + reset_width
    sample_boards, sampled, _ = _wait_timer(_STARTED, tuple(range(sample_base, sample_base + 4)), sample_steps, 1)
    return (_select(runs, _NORMAL_SOURCE, _NORMAL_RUN), _request(),
            _completion(_DENSE_RUN, _DENSE_DONE, _DENSE_PHASE, _DENSE_LEVEL, _DENSE_STATUS), _readiness(),
            *reset_boards, *sample_boards, _method(_ATTEMPT, _STARTED, reset, sampled, _ACTIVE, _READY, _ACK),
            _reply(), _route())


def build(writer: Path, dense: Path) -> tuple[dict, dict]:
    interface = _report(writer)
    dense_clock = _report(dense)
    if (dense_clock["inputs"]["enable"], dense_clock["inputs"]["done"],
            dense_clock["states"]["phase"]["current"], dense_clock["states"]["level"]["current"]) != (
            _DENSE_RUN, _DENSE_DONE, _DENSE_PHASE, _DENSE_LEVEL):
        raise ValueError("紧柱时钟的复位频道不匹配")
    if (interface["selector_values"]["dense"], interface["selector_values"]["release"]) != (1, 2):
        raise ValueError("pair-writer 的紧柱和释放来源编号不匹配")
    reset_ticks = max(256, dense_clock["timing"]["reset_hold_signal_ticks"] + 4 * _RADIO_TICKS,
                      interface["clock"]["timing"]["reset_hold_signal_ticks"] + 4 * _RADIO_TICKS)
    reset_steps = (reset_ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 2
    sample_steps = 16
    if reset_steps > _WAIT_RADIX ** 2:
        raise ValueError("制角子步骤的复位等待超出计数器范围")
    document, report = _build(writer, lambda runs: _dispatch(runs, reset_steps, sample_steps),
                              (_DENSE_RUN, _DENSE_DONE, _DENSE_PHASE, _DENSE_LEVEL))
    report["corner"] = {
        "inputs": {"selector": _CORNER_SELECTOR, "run": _CORNER_RUN}, "outputs": {"done": _CORNER_DONE},
        "selector_values": {"dense": 1, "release": 2}, "run_low_signal_ticks": _LOW_TICKS,
        "reset_timer_signal_ticks": reset_steps * _RADIO_TICKS,
        "sample_timer_signal_ticks": sample_steps * _RADIO_TICKS,
        "reserved_channels": list(range(_NORMAL_SOURCE, _TIMERS + (4 if reset_steps <= _WAIT_RADIX else 5) + 4)),
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出制角与双半形共用配方写入确认器")
    parser.add_argument("--writer", required=True, type=Path, help="pair-writer 原生蓝图及同名接口表")
    parser.add_argument("--dense-clock", required=True, type=Path, help="pair-writer 内紧柱时钟的接口表")
    parser.add_argument("--output", required=True, type=Path, help="确认器原生蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.writer, args.dense_clock)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
