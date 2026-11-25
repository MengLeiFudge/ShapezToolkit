"""编译三层父帧的行存储，每个原层复用同一份寄存器电路。"""

import argparse
from copy import deepcopy
from pathlib import Path

from .circuit import constant
from .compile_pair_writer import _compile
from .compiler_backend import _write_blueprint
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _compare, _gate, _local_wiring
from .compiler_backend.prefix_scan_wiring import _append
from .compiler_frontend import FrontendError
from .compiler_frontend.pin_candidate_closure import _radio_ports
from .local_module import Module


_ENABLE, _READ, _WRITE, _CAPTURE = range(1704200, 1704204)
_VALID = 1704205
_DATA_OUT = tuple(range(1704220, 1704230))
_DATA_IN = tuple(range(1704230, 1704240))
_REGISTERS = tuple(range(1704240, 1704270))
_VALID_REGISTERS = tuple(range(1704270, 1704273))
_ACTION, _SELECT = range(1704280, 1704282)
_NEXT = tuple(range(1704292, 1704295))


def _signals(registers):
    return {**{f"f{i}": channel for i, channel in enumerate(registers)},
            "write": _WRITE, "read": _READ, "capture": _CAPTURE, "enable": _ENABLE}


def _compile_bank(fields, inputs, output):
    outputs = {**{f"next{i}": channel for i, channel in enumerate(_NEXT)}, "selected": output}
    return _compile("tail_frames", fields, inputs, outputs)


def _wire(document, mapping):
    result = deepcopy(document)
    for _, _, channel, config in _radio_ports(_local_wiring(result["BP"])):
        if channel in mapping:
            config["C"] = constant(mapping[channel])
    return result["BP"]["Entries"]


def _row_controls():
    board = Module({"enable": _ENABLE, "capture": _CAPTURE, "write": _WRITE, "read": _READ})
    enabled = _compare(board, "enabled", "enable", 1)
    lower = _compare(board, "lower", "write", 0, "Ag==")
    upper = _compare(board, "upper", "write", 2, "BQ==")
    usable = _gate(board, "And", "usable", lower, upper)
    capture = _compare(board, "capturing", "capture", 1)
    write = _gate(board, "And", "requested", usable, capture)
    load = _gate(board, "And", "load", enabled, write)
    keep = _gate(board, "And", "keep", enabled, _gate(board, "Not", "no_write", write))
    reset = _gate(board, "Not", "reset", enabled)
    # -2 清空，0～2 写入指定帧并清除更深帧，3 保持全部帧。
    _gate(board, "If", "action", -2, reset)
    _gate(board, "If", "action", "write", load)
    _gate(board, "If", "action", 3, keep)
    board.outputs = {"action": _ACTION, _gate(board, "If", "selected", "read", enabled): _SELECT}
    return board.layout()["BP"]["Entries"]


def _row_bank(incoming, output, registers):
    board = Module({"input": incoming, "action": _ACTION, "select": _SELECT,
                    **{f"f{i}": channel for i, channel in enumerate(registers)}})
    for i, channel in enumerate(registers):
        previous, stored = f"f{i}", f"stored{i}"
        load = _compare(board, f"load{i}", "action", i)
        hold = _compare(board, f"hold{i}", "action", i + 1, "Ag==")
        choose = _compare(board, f"choose{i}", "select", i)
        _gate(board, "If", stored, "input", load)
        _gate(board, "If", stored, previous, hold)
        _gate(board, "If", "output", previous, choose)
        board.outputs[stored] = channel
    board.outputs["output"] = output
    return board.layout()["BP"]["Entries"]


def build():
    valid_fields = {**{f"next{i}": f"tail_frame_valid{i}" for i in range(3)}, "selected": "tail_frame_read_valid"}
    valid, valid_report = _compile_bank(valid_fields, _signals(_VALID_REGISTERS), _VALID)
    document = deepcopy(valid)
    document["BP"]["Entries"] = _wire(valid, dict(zip(_NEXT, _VALID_REGISTERS, strict=True)))
    _append(document, _row_controls())
    for i, (incoming, output) in enumerate(zip(_DATA_IN, _DATA_OUT, strict=True)):
        _append(document, _row_bank(incoming, output, _REGISTERS[i * 3:i * 3 + 3]))
    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    inputs = {"enable": _ENABLE, "read": _READ, "write": _WRITE, "capture": _CAPTURE,
              "target_rows": _DATA_IN[:5], "pushed_rows": _DATA_IN[5:]}
    outputs = {"valid": _VALID, "target_rows": _DATA_OUT[:5], "pushed_rows": _DATA_OUT[5:]}
    exclusive = {_VALID, _ACTION, _SELECT, *_DATA_OUT, *_REGISTERS, *_VALID_REGISTERS}
    expected = {_ENABLE, _READ, _WRITE, _CAPTURE, *_DATA_IN}
    if senders.keys() != exclusive or any(count != 1 for count in senders.values()) or receivers.keys() - senders.keys() != expected:
        raise ValueError("父帧存储的原生收发与接口不符")
    hold = max(96, valid_report["settling"]["hold_signal_ticks"])
    report = {"inputs": inputs, "outputs": outputs, "frames": 3, "platforms": len(wiring.platforms),
              "building_entries": len(wiring.entries), "hold_signal_ticks": 2 * hold + 24}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出三层顶针父帧存储")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
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
