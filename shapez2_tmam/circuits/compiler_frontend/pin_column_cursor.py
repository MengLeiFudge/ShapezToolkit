"""生成复用顶针单列校验的槽推进器。"""

import argparse
from pathlib import Path

from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _RADIO_TICKS, _WAIT_RADIX, _wait_timer
from ..local_module import Module
from .pin_column_stages import pin_column_stage_plan


_SLOT_COUNT = 20
_HOLD_TICKS = 6960
_RESET_TICKS = 6 * _RADIO_TICKS
_CURSOR_WIDTH = 15
_ENUMERATION_WIDTH = 17


def _gate(board, kind, result, *inputs, config=None):
    board.gate(f"LogicGate{kind}", inputs, (result,), config)
    return result


def _compare(board, result, left, right, config="AQ=="):
    return _gate(board, "Compare", result, left, right, config=config)


def _advance(enable, phase, found, tap, valid, initial_phase):
    inputs = {"enable": enable, "phase": phase, "found": found, "tap": tap, "valid": valid}
    if initial_phase is not None:
        inputs["initial_phase"] = initial_phase
    board = Module(inputs)
    end = _SLOT_COUNT + 1
    board.lookup("phase", "next", [(None, 1), *((n, min(n + 1, end)) for n in range(end + 1))])
    _gate(board, "If", "next_phase", "next", "advance")
    off = _gate(board, "Not", "off", _compare(board, "on", "enable", 1))
    first = _gate(board, "Or", "first", _compare(board, "idle", "phase", 0),
                  _compare(board, "empty", "phase", None))
    active = _gate(board, "And", "active", _compare(board, "started", "phase", 0, "Aw=="),
                   _compare(board, "remaining", "phase", end, "BQ=="))
    sampled = _gate(board, "And", "sampled", active, _compare(board, "same", "tap", "phase"))
    accepted = _compare(board, "accepted", "valid", 1)
    match = _gate(board, "And", "match", sampled, accepted)
    previous = _compare(board, "previous", "found", 1)
    _gate(board, "And", "next_found", "on", _gate(board, "Or", "any_found", previous, match))
    rejected = _gate(board, "And", "rejected", sampled, _gate(board, "Not", "invalid", accepted))
    step = _gate(board, "And", "step", _gate(board, "Not", "searching", previous),
                 _gate(board, "Or", "eligible", first, rejected))
    advance = _gate(board, "And", "advance_requested" if initial_phase is not None else "advance", "on", step)
    if initial_phase is not None:
        _gate(board, "And", "advance", advance, _gate(board, "Not", "next_slot", first))
        start = _gate(board, "And", "start", advance, first)
        missing = _compare(board, "missing", "initial_phase", None)
        _gate(board, "If", "next_phase", "initial_phase", start)
        _gate(board, "If", "next_phase", end, _gate(board, "And", "invalid_start", start, missing))
    _gate(board, "If", "next_phase", "phase", _gate(board, "And", "hold", "on",
                                                     _gate(board, "Not", "no_step", step)))
    _gate(board, "If", "next_phase", 0, off)
    board.outputs = {"next_phase": phase, "next_found": found}
    return board


def _start_phase(start_slot, initial_phase):
    board = Module({"start_slot": start_slot})
    board.lookup("start_slot", "phase", [(slot, slot + 1) for slot in range(_SLOT_COUNT + 1)])
    board.outputs = {"phase": initial_phase}
    return board


def _status(enable, phase, found, slot, valid, status, next_slot):
    board = Module({"enable": enable, "phase": phase, "found": found})
    board.lookup("phase", "slot", [(None, 0), *((n, max(n - 1, 0)) for n in range(_SLOT_COUNT + 2))])
    on = _compare(board, "on", "enable", 1)
    matched = _compare(board, "matched", "found", 1)
    end = _compare(board, "end", "phase", _SLOT_COUNT + 1)
    success = _gate(board, "And", "valid", on, matched)
    exhausted = _gate(board, "And", "exhausted", on, end)
    _gate(board, "If", "status", 1, success)
    _gate(board, "If", "status", 2, exhausted)
    board.outputs = {"slot": slot, "valid": valid, "status": status}
    if next_slot is not None:
        _gate(board, "If", "next_slot", "phase", success)
        _gate(board, "If", "next_slot", _SLOT_COUNT, exhausted)
        board.outputs["next_slot"] = next_slot
    return board


def _materials(status, done, raw, result):
    board = Module({"status": status, **{f"raw_{name}": channel for name, channel in raw.items()}})
    publish = _compare(board, "publish", "status", 1)
    hide = _gate(board, "Not", "hide", publish)
    for name in result:
        _gate(board, "If", name, f"raw_{name}", publish)
        _gate(board, "If", name, -1, hide)
    _compare(board, "done", "status", 0, "Aw==")
    board.outputs = {**result, "done": done}
    return board


def _cursor_modules(column_base, cursor_base, hold_signal_ticks, start_slot_channel):
    plan = {name: (inputs, outputs) for name, _, inputs, outputs in pin_column_stage_plan(column_base)}
    raw = plan["materials"][1]
    word = plan["read"][0]["word"]
    slot = plan["pack_0"][0]["slot"]
    enable, done, valid = range(cursor_base, cursor_base + 3)
    result = {name: cursor_base + 3 + i for i, name in enumerate(n for n in raw if n != "valid")}
    phase, found = cursor_base + 7, cursor_base + 8
    timer_channels = tuple(range(cursor_base + 9, cursor_base + 14))
    status = cursor_base + 14
    initial_phase = next_slot = None
    if start_slot_channel is not None:
        initial_phase, next_slot = cursor_base + 15, cursor_base + 16
    # 相位到槽号再到查表各经过一次无线。另留一拍覆盖计数边界。
    steps = (hold_signal_ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 3
    if steps >= _WAIT_RADIX ** 2:
        raise ValueError("单槽保持时间超出两位计数器范围")
    timers, _, tap = _wait_timer(phase, timer_channels, steps, steps)
    modules = [
        _advance(enable, phase, found, tap, raw["valid"], initial_phase),
        _status(enable, phase, found, slot, valid, status, next_slot),
        _materials(status, done, {name: raw[name] for name in result}, result),
        *timers,
    ]
    report = {
        "inputs": {"enable": enable, "word": word},
        "column": {"slot": slot, **raw},
        "outputs": {"slot": slot, "done": done, "valid": valid, **result},
        "cursor_channels": list(range(cursor_base, cursor_base + _CURSOR_WIDTH)),
        "reset_signal_ticks": _RESET_TICKS,
        "column_hold_signal_ticks": hold_signal_ticks,
        "phase_hold_signal_ticks": steps * _RADIO_TICKS,
        # 余量覆盖启动、无线状态更新和结果发布。
        "max_search_signal_ticks": _SLOT_COUNT * (steps + 3) * _RADIO_TICKS + _RESET_TICKS,
    }
    if start_slot_channel is not None:
        modules.append(_start_phase(start_slot_channel, initial_phase))
        report["inputs"]["start_slot"] = start_slot_channel
        report["outputs"]["next_slot"] = next_slot
        report["cursor_channels"] = list(range(cursor_base, cursor_base + _ENUMERATION_WIDTH))
        report["start_slot_hold_signal_ticks"] = 2 * _RADIO_TICKS
    return modules, report


def compile_pin_column_cursor(column_base: int, cursor_base: int, *, hold_signal_ticks: int = _HOLD_TICKS,
                              start_slot_channel: int | None = None):
    if type(column_base) is not int or not 1 <= column_base <= (1 << 24) - 23:
        raise ValueError("单列校验需要 23 条连续合法频道")
    width = _CURSOR_WIDTH if start_slot_channel is None else _ENUMERATION_WIDTH
    if type(cursor_base) is not int or not 1 <= cursor_base <= (1 << 24) - width:
        raise ValueError(f"槽推进器需要 {width} 条连续合法频道")
    if column_base < cursor_base + width and cursor_base < column_base + 23:
        raise ValueError("槽推进器频道不得与单列校验频道重叠")
    if start_slot_channel is not None:
        if type(start_slot_channel) is not int or not 1 <= start_slot_channel < 1 << 24:
            raise ValueError("起始槽频道必须在 1～16777215 内")
        if (start_slot_channel in range(column_base, column_base + 23)
                or start_slot_channel in range(cursor_base, cursor_base + width)):
            raise ValueError("起始槽频道必须单独分配")
    if type(hold_signal_ticks) is not int or hold_signal_ticks < _HOLD_TICKS:
        raise ValueError(f"单槽保持时间至少为 {_HOLD_TICKS} 信号刻")
    modules, report = _cursor_modules(column_base, cursor_base, hold_signal_ticks, start_slot_channel)
    entries = []
    for i, module in enumerate(modules):
        entry, = module.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 3), "Y": 3 * (i // 3)})
    report["platforms"] = len(entries)
    report["buildings"] = sum(len(entry["B"]["Entries"]) for entry in entries)
    return {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}, report


def main() -> int:
    parser = argparse.ArgumentParser(description="编译顶针单列的原生槽推进器")
    parser.add_argument("--column-base", required=True, type=int, help="单列校验的首频道")
    parser.add_argument("--channel-base", required=True, type=int, help="槽推进器的首频道")
    parser.add_argument("--start-slot-channel", type=int, help="分配给起始槽信号的频道")
    parser.add_argument("--output", required=True, type=Path, help="蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = compile_pin_column_cursor(args.column_base, args.channel_base,
                                                     start_slot_channel=args.start_slot_channel)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError) as error:
        parser.exit(2, f"导出失败。{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
