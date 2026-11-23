"""顺序回放已冻结的叶端和最多三层正向顶针帧。"""

import argparse
from pathlib import Path

from ...mari.signals import decode_constant
from ..circuit import constant
from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .auto_prefix_scan import _radio_ports
from .method_sequence import _DONE, _ENABLE, _radio_channels
from .module_caller import _RADIO_TICKS, _compare, _gate, _local_wiring, _wait_timer
from .prefix_scan_wiring import _append, _native_wiring
from .two_pass_recipe import _METHOD_RUN, build as build_two_pass


_COUNT = 1704000
_PHASE, _LEAF_RUN, _LEAF_DONE, _LEAF_NEXT, _FRAME_NEXT = range(1704003, 1704008)
_MODE, _OFFSET, _SUCCESSOR, _CLEARED = range(1704008, 1704012)
_TIMERS = tuple(range(1704020, 1704025))
_TAIL_RUN, _TAIL_DONE = 1703900, 1703901
_TAIL_ROWS = range(1703902, 1703912)
_READ, _VALID = 1704201, 1704205
_ROWS = range(1704220, 1704230)
_MAX_FRAMES = 3
_CLEAR = (3, 6, 9, 12)
_READ_PHASE = (4, 7, 10)
_RUN_PHASE = (5, 8, 11)
_COMPLETE = 13
_RESET_TICKS = 96
_READ_TICKS = 1920


def _leaf(reset_at: int) -> Module:
    board = Module({"phase": _PHASE, "enable": _ENABLE, "count": _COUNT,
                    "reset_at": reset_at, "done": _LEAF_DONE})
    boot, reset, run = (_compare(board, f"phase{i}", "phase", i) for i in range(3))
    enabled = _compare(board, "enabled", "enable", 1)
    count_present = _compare(board, "count_present", "count", None, "Bg==")
    nonnegative = _compare(board, "nonnegative", "count", 0, "Ag==")
    bounded = _compare(board, "bounded", "count", _MAX_FRAMES, "BQ==")
    valid = _gate(board, "And", "count_valid", count_present, _gate(board, "And", "range_ok", nonnegative, bounded))
    quiet = _gate(board, "And", "quiet", _compare(board, "delay_met", "reset_at", 1),
                  _compare(board, "done_low", "done", 0))
    _gate(board, "If", "next", 1, _gate(board, "And", "arm", boot, valid))
    _gate(board, "If", "next", 2, _gate(board, "And", "start_leaf", reset, quiet))
    _gate(board, "If", "next", _CLEAR[0], _gate(board, "And", "end_leaf", run,
                                                 _compare(board, "leaf_done", "done", 1)))
    board.outputs = {"next": _LEAF_NEXT, _gate(board, "And", "leaf_run", enabled, run): _LEAF_RUN}
    return board


def _frame_tables() -> tuple[Module, ...]:
    modes = (*((i, 1) for i in _CLEAR), *((i, 2) for i in _READ_PHASE), *((i, 3) for i in _RUN_PHASE))
    stages = range(_CLEAR[0], _COMPLETE)
    outputs = ((_MODE, modes), (_OFFSET, ((i, (i - _CLEAR[0]) // 3) for i in stages)),
               (_SUCCESSOR, ((i, i + 1) for i in stages)))
    boards = []
    for channel, pairs in outputs:
        board = Module({"phase": _PHASE})
        board.lookup("phase", "value", pairs)
        board.outputs = {"value": channel}
        boards.append(board)
    return tuple(boards)


def _clear(reset_at: int) -> Module:
    board = Module({"phase": _PHASE, "mode": _MODE, "reset_at": reset_at,
                    "leaf_done": _LEAF_DONE, "tail_done": _TAIL_DONE})
    clearing = _compare(board, "clearing", "mode", 1)
    quiet = _gate(board, "And", "quiet", _compare(board, "leaf_low", "leaf_done", 0),
                  _compare(board, "tail_low", "tail_done", 0))
    delay_met = _compare(board, "delay_met", "reset_at", "phase")
    cleared = _gate(board, "And", "cleared", clearing, _gate(board, "And", "reset_met", quiet, delay_met))
    board.outputs = {cleared: _CLEARED}
    return board


def _frame(read_at: int) -> Module:
    board = Module({"phase": _PHASE, "mode": _MODE, "offset": _OFFSET, "successor": _SUCCESSOR,
                    "count": _COUNT, "cleared": _CLEARED, "read_at": read_at,
                    "valid": _VALID, "tail_done": _TAIL_DONE})
    reading, running = (_compare(board, f"mode{i}", "mode", i) for i in (2, 3))
    has_next = _compare(board, "has_next", "offset", "count", "BA==")
    valid = _compare(board, "valid_on", "valid", 1)
    next_frame = _gate(board, "And", "next_frame", "cleared", _gate(board, "And", "read_cleared", has_next,
                       _gate(board, "Not", "no_data", valid)))
    read_ready = _gate(board, "And", "read_ready", valid, _compare(board, "read_met", "read_at", "phase"))
    start_tail = _gate(board, "And", "start_tail", reading, read_ready)
    tail_complete = _gate(board, "And", "tail_complete", running, _compare(board, "tail_high", "tail_done", 1))
    advance = _gate(board, "Or", "advance", next_frame, _gate(board, "Or", "tail_advance", start_tail, tail_complete))
    _gate(board, "If", "next", "successor", advance)
    _gate(board, "If", "next", _COMPLETE, _gate(board, "And", "complete", "cleared",
                                               _gate(board, "Not", "last_frame", has_next)))
    board.outputs = {"next": _FRAME_NEXT}
    return board


def _state() -> Module:
    board = Module({"enable": _ENABLE, "phase": _PHASE, "leaf": _LEAF_NEXT, "frame": _FRAME_NEXT})
    enabled = _compare(board, "enabled", "enable", 1)
    _gate(board, "If", "transition", "leaf", 1)
    _gate(board, "If", "transition", "frame", 1)
    hold = _compare(board, "hold", "transition", None)
    _gate(board, "If", "state", "transition", enabled)
    _gate(board, "If", "state", "phase", _gate(board, "And", "keep", enabled, hold))
    _gate(board, "If", "state", 0, _gate(board, "Not", "reset", enabled))
    done = _gate(board, "And", "done", enabled, _compare(board, "complete", "phase", _COMPLETE))
    board.outputs = {"state": _PHASE, done: _DONE}
    return board


def _readout() -> Module:
    board = Module({"enable": _ENABLE, "mode": _MODE, "offset": _OFFSET, "count": _COUNT})
    enabled = _compare(board, "enabled", "enable", 1)
    reading = _compare(board, "reading", "mode", 2)
    running = _compare(board, "running", "mode", 3)
    request = _gate(board, "And", "request", enabled, _gate(board, "Or", "reading_frame", reading, running))
    for count in range(1, _MAX_FRAMES + 1):
        chosen = _compare(board, f"count{count}", "count", count)
        for offset in range(count):
            name = f"frame{count}_{offset}"
            position = _compare(board, name + "_at", "offset", offset)
            use = _gate(board, "And", name, chosen, position)
            _gate(board, "If", "index", count - offset - 1, use)
    board.outputs = {_gate(board, "If", "read", "index", request): _READ,
                     _gate(board, "And", "tail_run", enabled, running): _TAIL_RUN}
    return board


def _control() -> tuple[list[dict], dict]:
    reset_steps = _RESET_TICKS // _RADIO_TICKS + 2
    read_steps = _READ_TICKS // _RADIO_TICKS + 2
    timers, reset_at, read_at = _wait_timer(_PHASE, _TIMERS, reset_steps, read_steps)
    modules = [_leaf(reset_at), *_frame_tables(), _clear(reset_at), _frame(read_at), _state(), _readout(), *timers]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    return platforms, {"reset_signal_ticks": reset_steps * _RADIO_TICKS,
                       "frame_read_signal_ticks": read_steps * _RADIO_TICKS}


def _bind_leaf(platforms: list[dict], enable: int) -> None:
    wiring = _local_wiring({"Entries": platforms})
    received, sent = _radio_channels(wiring)
    if (enable not in received or sent[_DONE] != 1 or sent[_TAIL_DONE] != 1
            or _TAIL_RUN not in received or not set(_TAIL_ROWS) <= received.keys()):
        raise ValueError("叶端、确认器或尾帧蓝图缺少运行、完工和逐行接点")
    assignments = {enable: _LEAF_RUN, _DONE: _LEAF_DONE, **dict(zip(_TAIL_ROWS, _ROWS, strict=True))}
    for _, entry in _radio_ports(wiring):
        channel = decode_constant(entry["C"])
        if channel in assignments:
            entry["C"] = constant(assignments[channel])


def build(writer: Path, caller: Path, corner_jobs: Path, *, two_pass: bool = False,
          frame_store: Path | None = None) -> tuple[dict, dict]:
    control, timing = _control()
    parts = [_native_wiring(path).platforms for path in (writer, caller, corner_jobs)]
    if two_pass:
        document, outer_report = build_two_pass(writer=writer, caller=caller, corner_jobs=corner_jobs)
        outer = {name: outer_report[name] for name in ("inputs", "outputs", "factory", "timing")}
        count = sum(map(len, parts))
        _bind_leaf(document["BP"]["Entries"][-count:], _METHOD_RUN)
        control_wiring = _local_wiring({"Entries": control})
        for _, entry in _radio_ports(control_wiring):
            if decode_constant(entry["C"]) == _ENABLE:
                entry["C"] = constant(_METHOD_RUN)
        _append(document, control)
    else:
        first_leaf = len(control)
        document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": control}}
        for part in parts:
            _append(document, part)
        _bind_leaf(document["BP"]["Entries"][first_leaf:], _ENABLE)
        outer = None
    if frame_store is not None:
        native = _native_wiring(frame_store)
        received, sent = _radio_channels(native)
        if _READ not in received or any(sent[ch] != 1 for ch in (_VALID, *_ROWS)):
            raise ValueError("父帧存储的读取、有效和逐行频道不匹配")
        _append(document, native.platforms)
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    duplicates = sorted(ch for ch, count in sent.items() if count != 1)
    store_outputs = {_VALID, *_ROWS}
    needed = {_COUNT, *store_outputs} if frame_store is None else {_COUNT}
    external = received.keys() - sent.keys()
    ports = {_READ, _DONE, _TAIL_RUN, _LEAF_RUN, _LEAF_DONE}
    if frame_store is not None:
        ports.update(store_outputs)
    if duplicates or not needed <= external or not ports <= sent.keys():
        raise ValueError(f"成功路径的原生收发不匹配，重复发射 {duplicates}，缺少输入 {sorted(needed - external)}")
    report = {"inputs": {"enable": _METHOD_RUN if two_pass else _ENABLE, "frame_count": _COUNT, "frame_valid": _VALID,
                         "target_rows": tuple(_ROWS)[:5], "pushed_rows": tuple(_ROWS)[5:]},
              "outputs": {"done": _DONE, "read_frame": _READ, "phase": _PHASE}, "max_frames": _MAX_FRAMES,
              "reserved_channels": [1704000, 1704059], "timing": timing, "external_inputs": sorted(external),
              "two_pass": outer, "includes_frame_store": frame_store is not None,
              "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
              "global_transmitters": len(sent)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出从叶端到根的串行配方回放")
    parser.add_argument("--writer", required=True, type=Path, help="已含尾帧的共用 writer 蓝图")
    parser.add_argument("--caller", required=True, type=Path, help="叶端方法确认器蓝图")
    parser.add_argument("--corner-jobs", required=True, type=Path, help="叶端制角排程蓝图")
    parser.add_argument("--two-pass", action="store_true", help="合装虚拟回放与实体写入控制")
    parser.add_argument("--frame-store", type=Path, help="同件导入三层父帧存储蓝图")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.writer, args.caller, args.corner_jobs, two_pass=args.two_pass,
                                 frame_store=args.frame_store)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
