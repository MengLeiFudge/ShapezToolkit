"""连接尾部搜索、父帧存储和成功路径的逐层读取。"""

import argparse
from pathlib import Path

from ..synthesis import tail_search as search
from .compile_tail_search import _ELAPSED, _ENABLE, _FLAGS, _PHASE
from .compiler_backend import _write_blueprint
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _compare, _gate, _local_wiring
from .compiler_backend.prefix_scan_wiring import _append, _native_wiring
from .local_module import Module


_DEPTH, _EVENT, _PREVIOUS_EVENT = range(1705344, 1705347)
_TAKE_CHILD, _TAKE_PARENT, _PARENT = range(1705347, 1705350)
_NODE_ROWS = tuple(range(1705350, 1705355))
_REPLAY_READ, _NODE_ELIGIBLE, _MEMBER_READY, _FRAME_RELEASE = range(1705355, 1705359)
_BANK = tuple(range(1705360, 1705365))
_ROOT = tuple(range(1701200, 1701205))
_CHILD = tuple(range(1702289, 1702294))
_PUSHED = tuple(range(1703513, 1703518))
_PARENT_ROWS = tuple(range(1704220, 1704225))
_FRAME_TARGET = tuple(range(1704230, 1704235))
_FRAME_PUSHED = tuple(range(1704235, 1704240))
_FRAME_HOLD, _FRAME_READ, _FRAME_WRITE, _FRAME_CAPTURE = range(1704200, 1704204)


def _events():
    board = Module({"phase": _PHASE, "settled": _ELAPSED, "child": _MEMBER_READY})
    down = _compare(board, "down", "phase", search.DESCEND)
    restore = _compare(board, "restore", "phase", search.RESTORE)
    resumed = _compare(board, "resumed", "phase", search.PIN_RESUME)
    pending = _gate(board, "Not", "pending", "settled")
    for phase, kind in ((down, 1), (restore, 2)):
        after_hold = _gate(board, "And", f"settled_{kind}", phase, "settled")
        _gate(board, "If", "event", kind, after_hold)
    _gate(board, "If", "event", 3, resumed)
    board.outputs = {"event": _EVENT, _gate(board, "And", "read_child", down,
                     _gate(board, "And", "child_ready", pending, "child")): _TAKE_CHILD,
                     _gate(board, "And", "read_parent", restore, pending): _TAKE_PARENT}
    return board


def _depth():
    board = Module({"enable": _ENABLE, "event": _EVENT, "previous": _PREVIOUS_EVENT, "depth": _DEPTH})
    running = _compare(board, "running", "enable", 1)
    new = _gate(board, "Not", "new", _compare(board, "seen_event", "event", "previous"))
    active = _gate(board, "And", "active", running, new)
    down = _gate(board, "And", "go_down", active, _compare(board, "down", "event", 1))
    up = _gate(board, "And", "go_up", active, _compare(board, "up", "event", 2))
    changed = _gate(board, "Or", "changed", down, up)
    hold = _gate(board, "And", "keep_depth", running, _gate(board, "Not", "same_depth", changed))
    for depth in range(4):
        current = _compare(board, f"depth{depth}", "depth", depth)
        lower = _gate(board, "And", f"lower{depth}", current, down)
        higher = _gate(board, "And", f"higher{depth}", current, up)
        _gate(board, "If", "next", min(depth + 1, 3), lower)
        _gate(board, "If", "next", max(depth - 1, 0), higher)
    _gate(board, "If", "next", "depth", hold)
    _gate(board, "If", "next", 0, _gate(board, "Not", "clear", running))
    board.outputs = {"next": _DEPTH, _gate(board, "If", "record_event", "event", running): _PREVIOUS_EVENT}
    return board


def _resume():
    board = Module({"enable": _ENABLE, "event": _EVENT, "resuming": 1705306})
    returning = _compare(board, "returning", "event", 2)
    resumed = _compare(board, "retraced", "event", 3)
    hold = _gate(board, "And", "keep", "resuming", _gate(board, "Not", "still_resuming", resumed))
    requested = _gate(board, "Or", "request", returning, hold)
    board.outputs = {_gate(board, "And", "resume", "enable", requested): 1705306}
    return board


def _bank(rows):
    board = Module({"enable": _ENABLE, "child": _TAKE_CHILD, "parent": _TAKE_PARENT})
    take_child = _gate(board, "And", "take_child", "enable", "child")
    take_parent = _gate(board, "And", "take_parent", "enable", "parent")
    writing = _gate(board, "Or", "writing", take_child, take_parent)
    retain = _gate(board, "And", "retain", "enable", _gate(board, "Not", "not_writing", writing))
    for i in rows:
        slots = (f"child{i}", f"parent{i}", f"saved{i}")
        board.inputs.update(zip(slots, (_CHILD[i], _PARENT_ROWS[i], _BANK[i]), strict=True))
        result = f"row{i}"
        for source, condition in zip(slots, (take_child, take_parent, retain), strict=True):
            _gate(board, "If", result, source, condition)
        board.outputs[result] = _BANK[i]
    return board


def _current(rows):
    board = Module({"depth": _DEPTH})
    is_root = _compare(board, "root", "depth", 0)
    child = _gate(board, "Not", "nested", is_root)
    for i in rows:
        board.inputs.update({f"root{i}": _ROOT[i], f"saved{i}": _BANK[i], f"pushed{i}": _PUSHED[i]})
        row = f"row{i}"
        _gate(board, "If", row, f"root{i}", is_root)
        _gate(board, "If", row, f"saved{i}", child)
        board.outputs[row] = _NODE_ROWS[i]
        board.outputs[_gate(board, "If", f"target{i}", row, 1)] = _FRAME_TARGET[i]
        board.outputs[_gate(board, "If", f"intermediate{i}", f"pushed{i}", 1)] = _FRAME_PUSHED[i]
    return board


def _read():
    board = Module({"read": _FLAGS["read_parent"], "depth": _DEPTH, "resume": 1705306,
                    "solved": _FLAGS["solved"], "playback": _REPLAY_READ})
    board.lookup("depth", "previous_depth", ((1, 0), (2, 1), (3, 2)))
    recovering = _gate(board, "Or", "recovering", "read", "resume")
    _gate(board, "If", "address", "previous_depth", "read")
    find_cursor = _gate(board, "And", "find_cursor", "resume", _gate(board, "Not", "not_parent", "read"))
    _gate(board, "If", "address", "depth", find_cursor)
    play = _gate(board, "And", "play", "solved", _gate(board, "Not", "no_recovery", recovering))
    _gate(board, "If", "address", "playback", play)
    board.outputs = {"address": _FRAME_READ}
    return board


def _write():
    board = Module({"enable": _ENABLE, "save": _FLAGS["save"], "depth": _DEPTH, "frames": _FRAME_RELEASE})
    board.outputs = {_gate(board, "If", "write", "depth", "save"): _FRAME_WRITE,
                     _gate(board, "If", "capture", 1, "save"): _FRAME_CAPTURE,
                     _gate(board, "And", "frame_hold", "enable", "frames"): _FRAME_HOLD}
    return board


def _status():
    board = Module({"depth": _DEPTH, "budget": 1704672, "legal": _NODE_ELIGIBLE, "solved": _FLAGS["solved"]})
    available = _compare(board, "available", "depth", "budget", "BA==")
    board.lookup("depth", "count", ((0, 1), (1, 2), (2, 3)))
    board.outputs = {_gate(board, "And", "can_pin", available, "legal"): 1705305,
                     _compare(board, "has_parent", "depth", 0, "Aw=="): 1705309,
                     _gate(board, "If", "frame_count", "count", "solved"): 1704000}
    return board


def _candidate():
    board = Module({"frame_ok": 1704205, "cursor_ok": 1705000, "slots_match": 1705002,
                    "cap_match": 1705003, "kind": 1703302})
    board.outputs = {_gate(board, "And", "parent_ready", "frame_ok", "cursor_ok"): 1705310,
                     _gate(board, "And", "cursor_match", "slots_match", "cap_match"): 1705308,
                     _compare(board, "member", "kind", 2): 1705312}
    return board


def build(frames: Path | None = None, checkpoint: Path | None = None):
    parts = (_events(), _depth(), _resume(), *(_bank((i,)) for i in range(5)),
             *(_current((i,)) for i in range(5)), _read(), _write(), _status(), _candidate())
    boards = [part.layout()["BP"]["Entries"][0] for part in parts]
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": [boards[0]]}}
    for board in boards[1:]:
        _append(document, [board])
    for path in (frames, checkpoint):
        if path is not None:
            _append(document, _native_wiring(path).platforms)
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    if any(count != 1 for count in sent.values()):
        raise ValueError("尾部搜索的父帧控制含重复发射频道")
    return document, {"inputs": {"member_ready": _MEMBER_READY, "node_eligible": _NODE_ELIGIBLE,
                                 "frame_hold": _FRAME_RELEASE, "replay_read": _REPLAY_READ, "root_rows": _ROOT},
                      "outputs": {"depth": _DEPTH, "node_rows": _NODE_ROWS, "frame_count": 1704000},
                      "external_inputs": sorted(received.keys() - sent.keys()), "platforms": len(wiring.platforms),
                      "building_entries": len(wiring.entries)}


def main() -> int:
    parser = argparse.ArgumentParser(description="导出尾部搜索的三层父帧读写及回退控制")
    parser.add_argument("--frames", type=Path, help="一并导入父帧存储蓝图")
    parser.add_argument("--checkpoint", type=Path, help="一并导入父游标存储蓝图")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(args.frames, args.checkpoint), args.output)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
