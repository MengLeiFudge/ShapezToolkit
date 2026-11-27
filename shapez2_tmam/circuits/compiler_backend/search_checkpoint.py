"""保存三层父搜索游标，并按恢复阶段比较当前游标。"""

import argparse
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .method_sequence import _radio_channels
from .module_caller import _RADIO_TICKS, _compare, _copy, _gate, _local_wiring


_ENABLE, _READ, _WRITE, _CAPTURE = range(1704200, 1704204)
_READY, _S_MATCH, _SLOTS_MATCH, _CAP_MATCH = range(1705000, 1705004)
_COUNTS = tuple(range(1703518, 1703522))
_SLOTS = (1701865, 1701871, 1701877, 1701883)
_MASK = 1703303
_MEMBERS = tuple(range(1703308, 1703312))
_INPUTS = (*_COUNTS, *_SLOTS, _MASK, *_MEMBERS)
_SAVED = tuple(range(1705010, 1705023))
_ACTION, _SELECT, _READ_TAP, _READ_BACK, _READY_GATE = range(1705023, 1705028)
_PRESENT = tuple(range(1705030, 1705034))
_EQUAL = tuple(range(1705034, 1705038))
_REGISTERS = 1705040
_DEPTHS = range(3)
_GROUPS = (range(4), range(4, 8), range(8, 11), range(11, 13))
_HOLD_TICKS = 8 * _RADIO_TICKS


def _all(board: Module, name: str, values) -> str:
    first, *rest = values
    for index, value in enumerate(rest):
        first = _gate(board, "And", f"{name}{index}", first, value)
    return first


def _valid_depth(board: Module, name: str, signal: str) -> str:
    lower = _compare(board, f"{name}_lower", signal, 0, "Ag==")
    upper = _compare(board, f"{name}_upper", signal, _DEPTHS[-1], "BQ==")
    return _gate(board, "And", name, lower, upper)


def _controls() -> Module:
    board = Module({"enable": _ENABLE, "read": _READ, "write": _WRITE, "capture": _CAPTURE})
    enabled = _compare(board, "enabled", "enable", 1)
    capture = _compare(board, "capture_on", "capture", 1)
    reading = _all(board, "reading", (enabled, _gate(board, "Not", "read_mode", capture),
                                      _valid_depth(board, "read_valid", "read")))
    writing = _all(board, "writing", (enabled, capture, _valid_depth(board, "write_valid", "write")))
    _gate(board, "If", "action", "write", writing)
    _gate(board, "If", "action", -1, _gate(board, "Not", "clear", enabled))
    board.outputs = {"action": _ACTION, _gate(board, "If", "select", "read", reading): _SELECT}
    return board


def _field(source: int, selected: int, register_base: int) -> Module:
    board = Module({"action": _ACTION, "select": _SELECT, "incoming": source,
                    **{f"frame{depth}": register_base + depth for depth in _DEPTHS}})
    idle = _compare(board, "idle", "action", None)
    for depth in _DEPTHS:
        load = _compare(board, f"load{depth}", "action", depth)
        deeper_write = _compare(board, f"deeper_write{depth}", "action", depth, "Aw==")
        keep = _gate(board, "Or", f"keep{depth}", idle, deeper_write)
        old = f"frame{depth}"
        next_value = f"next{depth}"
        _gate(board, "If", next_value, "incoming", load)
        _gate(board, "If", next_value, old, keep)
        address = _compare(board, f"select{depth}", "select", depth)
        _gate(board, "If", "selected", old, address)
        board.outputs[next_value] = register_base + depth
    board.outputs["selected"] = selected
    return board


def _compare_fields(indices, present: int, equal: int) -> Module:
    inputs = {}
    for index in indices:
        inputs[f"current{index}"] = _INPUTS[index]
        inputs[f"saved{index}"] = _SAVED[index]
    board = Module(inputs)
    available = []
    matches = []
    for index in indices:
        saved = f"saved{index}"
        available.append(_compare(board, f"has{index}", saved, None, "Bg=="))
        matches.append(_compare(board, f"equal{index}", f"current{index}", saved))
    board.outputs = {_all(board, "available", available): present, _all(board, "match", matches): equal}
    return board


def _ready() -> Module:
    board = Module({"enable": _ENABLE, "capture": _CAPTURE, "read": _READ, "echo": _READ_BACK,
                    **{f"group{i}": channel for i, channel in enumerate(_PRESENT)}})
    enabled = _compare(board, "enabled", "enable", 1)
    capture = _compare(board, "capture_on", "capture", 1)
    read = _valid_depth(board, "read_valid", "read")
    same_depth = _compare(board, "same_depth", "read", "echo")
    complete = _all(board, "complete", (f"group{i}" for i in range(len(_PRESENT))))
    available = _all(board, "available", (enabled, _gate(board, "Not", "read_mode", capture),
                                          read, same_depth, complete))
    board.outputs = {available: _READY_GATE}
    return board


def _matches() -> Module:
    board = Module({"ready": _READY_GATE, **{f"equal{i}": channel for i, channel in enumerate(_EQUAL)}})
    board.outputs[_compare(board, "ready_out", "ready", 1)] = _READY
    cap = _gate(board, "And", "cap", "equal2", "equal3")
    for name, check, output in (("s", "equal0", _S_MATCH), ("slots", "equal1", _SLOTS_MATCH),
                                ("top", cap, _CAP_MATCH)):
        board.outputs[_gate(board, "And", name, "ready", check)] = output
    return board


def build() -> tuple[dict, dict]:
    fields = [_field(source, selected, _REGISTERS + len(_DEPTHS) * i)
              for i, (source, selected) in enumerate(zip(_INPUTS, _SAVED, strict=True))]
    comparisons = [_compare_fields(group, present, equal)
                   for group, present, equal in zip(_GROUPS, _PRESENT, _EQUAL, strict=True)]
    modules = [_controls(), *fields, *comparisons, _copy(_SELECT, _READ_TAP), _copy(_READ_TAP, _READ_BACK),
               _ready(), _matches()]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    external = {_ENABLE, _READ, _WRITE, _CAPTURE, *_INPUTS}
    if (received.keys() - sent.keys() != external
            or any(count != 1 or not 1705000 <= channel <= 1705099 for channel, count in sent.items())):
        raise ValueError("父搜索游标存取的原生收发不匹配")
    report = {"inputs": {"enable": _ENABLE, "read_depth": _READ, "write_depth": _WRITE, "capture": _CAPTURE,
                         "s_counts": _COUNTS, "source_slots": _SLOTS, "mask": _MASK, "members": _MEMBERS},
              "outputs": {"ready": _READY, "s_match": _S_MATCH, "slots_match": _SLOTS_MATCH,
                          "cap_match": _CAP_MATCH, "s_counts": _SAVED[:4], "source_slots": _SAVED[4:8],
                          "mask": _SAVED[8], "members": _SAVED[9:]},
              "depths": list(_DEPTHS), "reserved_channels": [1705000, 1705099],
              "timing": {"hold_signal_ticks": _HOLD_TICKS}, "platforms": len(wiring.platforms),
              "building_entries": len(wiring.entries), "global_transmitters": len(sent)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出父搜索游标存取与阶段比较")
    parser.add_argument("--output", type=Path, required=True, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build()
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
