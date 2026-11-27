"""把尾部搜索的共用调度编成相位寄存器与方法调用口。"""

import argparse
from pathlib import Path

from ..synthesis import tail_search as search
from .compile_pair_writer import _compile, _one
from .compiler_backend import _write_blueprint
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _RADIO_TICKS, _compare, _gate, _local_wiring, _wait_timer
from .compiler_backend.prefix_scan_wiring import _append
from .compiler_frontend import FrontendError
from .local_module import Module


_ENABLE, _PHASE, _ELAPSED = range(1705300, 1705303)
_CHECKED, _LEGAL, _CAN_PIN, _RESUMING, _COUNT_MATCH, _CURSOR_MATCH = range(1705303, 1705309)
_HAS_PARENT, _PARENT_READY, _LEAF_READY, _MEMBER = range(1705309, 1705313)
_STACK_READY, _STACK_EXHAUSTED = 1704802, 1704803
_PIN_PROOF, _PIN_EXHAUSTED, _PIN_FAULT = 1703314, 1703317, 1703318
_TIMERS = tuple(range(1705315, 1705320))
_NEXT = tuple(range(1705320, 1705324))
_FLAGS = {name: 1705330 + i for i, name in enumerate((
    "preflight", "stack", "stack_reject", "pin", "proof_missed", "save", "capture_leaf",
    "down", "read_parent", "restore", "resumed", "solved", "exhausted", "fault",
))}
_INPUTS = {"enable": _ENABLE, "preflight_ready": _CHECKED, "preflight_ok": _LEGAL, "can_pin": _CAN_PIN,
           "resuming": _RESUMING, "s_matches": _COUNT_MATCH, "cursor_matches": _CURSOR_MATCH,
           "has_parent": _HAS_PARENT, "parent_ready": _PARENT_READY, "leaf_ready": _LEAF_READY,
           "member": _MEMBER, "s_ready": _STACK_READY, "s_exhausted": _STACK_EXHAUSTED,
           "pin_proof": _PIN_PROOF, "pin_exhausted": _PIN_EXHAUSTED, "pin_fault": _PIN_FAULT}
_STAGES = {
    "entry": {"elapsed": _ELAPSED, "checked": _CHECKED, "legal": _LEGAL, "can_pin": _CAN_PIN},
    "stack": {"ready": _STACK_READY, "exhausted": _STACK_EXHAUSTED, "resuming": _RESUMING,
              "count_match": _COUNT_MATCH},
    "pin": {"elapsed": _ELAPSED, "proof": _PIN_PROOF, "exhausted": _PIN_EXHAUSTED, "fault": _PIN_FAULT,
            "resuming": _RESUMING, "cursor_match": _CURSOR_MATCH, "member": _MEMBER},
    "frame": {"elapsed": _ELAPSED, "parent_ready": _PARENT_READY, "leaf_ready": _LEAF_READY,
              "has_parent": _HAS_PARENT},
}


def _state_select(sample):
    board = Module({"enable": _ENABLE, "phase": _PHASE, "sample": sample,
                    **{f"next{i}": channel for i, channel in enumerate(_NEXT)}})
    enabled = _compare(board, "enabled", "enable", 1)
    ready = _compare(board, "sampled", "phase", "sample")
    boundaries = (search.PREFLIGHT, search.S_SKIP, search.PIN_RESUME)
    lower = None
    for i, phase in enumerate(boundaries):
        upper = _compare(board, f"upper{i}", "phase", phase, "BQ==")
        selected = upper if lower is None else _gate(board, "And", f"selected{i}", lower, upper)
        _gate(board, "If", "proposed", f"next{i}", selected)
        lower = _gate(board, "Not", f"lower{i}", upper)
    _gate(board, "If", "proposed", "next3", lower)
    _gate(board, "If", "current", "proposed", _gate(board, "And", "change", enabled, ready))
    _gate(board, "If", "current", "phase", _gate(board, "And", "hold", enabled,
                                                 _gate(board, "Not", "unsampled", ready)))
    _gate(board, "If", "current", search.IDLE, _gate(board, "Not", "reset", enabled))
    board.outputs = {"current": _PHASE}
    return board


def build(hold: int = 4096):
    steps = (hold + _RADIO_TICKS - 1) // _RADIO_TICKS + 2
    timers, elapsed, sample = _wait_timer(_PHASE, _TIMERS, steps, 8)
    boards = tuple(_one("tail_search", f"tail_{name}_next", "next", {"phase": _PHASE, **inputs}, output)[0]
                   for (name, inputs), output in zip(_STAGES.items(), _NEXT, strict=True))
    document, *remaining = boards
    for part in remaining:
        _append(document, part["BP"]["Entries"])
    common = {"phase": _PHASE, "enable": _ENABLE}
    pairs = tuple(_FLAGS.items())
    for index in range(0, len(pairs), 5):
        fields = dict(pairs[index:index + 5])
        part, _ = _compile("tail_search", {field: f"tail_search_{field}" for field in fields}, common, fields)
        _append(document, part["BP"]["Entries"])
    stable = Module({"phase": _PHASE, "elapsed": elapsed})
    stable.outputs = {_compare(stable, "phase_settled", "phase", "elapsed"): _ELAPSED}
    for board in (*timers, stable, _state_select(sample)):
        _append(document, board.layout()["BP"]["Entries"])
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    if any(count != 1 for count in sent.values()) or set(_INPUTS.values()) != received.keys() - sent.keys():
        raise ValueError("尾部调度的原生收发与接口表不符")
    return document, {"inputs": _INPUTS, "outputs": _FLAGS, "phase": _PHASE,
                      "hold_signal_ticks": steps * _RADIO_TICKS, "phase_sample_signal_ticks": 96,
                      "platforms": len(wiring.platforms), "building_entries": len(wiring.entries)}


def main() -> int:
    parser = argparse.ArgumentParser(description="导出四帧尾部搜索的共享状态调度")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(), args.output)
    except FrontendError as error:
        parser.error(f"{error.filename}:{error.lineno}:{error.offset} {error.msg}")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
