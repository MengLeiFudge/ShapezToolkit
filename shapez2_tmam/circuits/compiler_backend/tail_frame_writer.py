"""把一层冻结的顶针结果接到共用六字段配方写入。"""

import argparse
from pathlib import Path

from ...mari.signals import decode_constant
from ..circuit import constant
from ..circuit_packing import stack_platforms
from ..factory_assembly.interface import FIELDS
from ..local_module import Module
from . import _write_blueprint
from .auto_prefix_scan import _radio_ports
from .confirmed_call import build as build_confirmed_call
from .dense_write_bridge import build as build_write_bridge
from .method_sequence import _radio_channels
from .module_caller import _RADIO_TICKS, _RADIO_TRANSMITTER, _compare, _gate, _local_wiring
from .prefix_scan_wiring import _append, _native_wiring, _report


_START, _DONE = 1703900, 1703901
_TARGET_ROWS = tuple(range(1703902, 1703907))
_PUSHED_ROWS = tuple(range(1703907, 1703912))
_ENABLE, _NEXT, _SETTLED, _HAS_PACKET, _CONFIRMED, _REQUEST = range(1703912, 1703918)
_CLOCK, _BRIDGE = 1703920, 1703930
_MAIN_OUTPUTS = (*range(1701750, 1701756), 1701762)
_MAIN_PRIVATE = tuple(range(1703940, 1703947))
_MAIN_RUN, _WRITER_ENABLE, _ADDRESS, _ACK = 1701761, 1701760, 1701763, 1701764
_STEP, _LEVEL = 1703706, 1703712
_LAST_STEP = 11
_TAIL_FIELDS = dict(zip(FIELDS, (*range(1703707, 1703712), None), strict=True))
_PARTS = {
    "level": ({"step": _STEP}, {"level": _LEVEL}),
    "row": ({"target": 1703700, "pushed": 1703701}, {"row": 1703702}),
    "packet": ({"step": _STEP, "row": 1703702}, {name: ch for name, ch in _TAIL_FIELDS.items() if ch is not None}),
}


def _load_frames(document, root: Path) -> int:
    hold = 0
    for name, (inputs, outputs) in _PARTS.items():
        path = root / f"tail-frame-{name}.spz2bp"
        report = _report(path)
        native = _native_wiring(path)
        received, sent = _radio_channels(native)
        for side, channels in (("inputs", inputs), ("outputs", outputs)):
            if {key: port["channel"] for key, port in report[side].items()} != channels:
                raise ValueError(f"{path.name} 的{side}频道与尾帧接口不匹配")
        if set(received) != set(inputs.values()) or sent != dict.fromkeys(outputs.values(), 1):
            raise ValueError(f"{path.name} 的原生收发与接口表不匹配")
        part_hold = report["settling"]["hold_signal_ticks"]
        if type(part_hold) is not int or part_hold < 1:
            raise ValueError(f"{path.name} 未给出有效的稳定时间")
        hold += part_hold
        _append(document, native.platforms)
    return hold


def _row_bank(rows: tuple[int, ...], output: int) -> Module:
    board = Module({"level": _LEVEL, **{f"row{i}": ch for i, ch in enumerate(rows)}})
    for i in range(len(rows)):
        selected = _compare(board, f"level{i}", "level", i)
        _gate(board, "If", "row", f"row{i}", selected)
    board.outputs = {"row": output}
    return board


def _run_gate(shared: bool) -> Module:
    board = Module({"start": _START, "writer": _WRITER_ENABLE})
    ready = _compare(board, "ready", "start", 1)
    run = _gate(board, "And", "enabled", ready, "writer")
    if shared:
        board.inputs["main"] = _MAIN_RUN
        idle = _compare(board, "main_idle", "main", 0)
        run = _gate(board, "And", "selected", run, idle)
    board.outputs = {run: _ENABLE}
    return board


def _advance() -> Module:
    board = Module({"enable": _ENABLE, "step": _STEP, "settled": _SETTLED})
    board.lookup("step", "increment", ((step, step + 1) for step in range(_LAST_STEP)))
    _gate(board, "If", "next", "increment", "settled")
    final = _compare(board, "last", "step", _LAST_STEP)
    board.outputs = {"next": _NEXT, _gate(board, "And", "done", "enable", final): _DONE}
    return board


def _mux(indices, shared: bool) -> Module:
    board = Module({"tail": _ENABLE})
    if shared:
        main = _gate(board, "Not", "main", "tail")
    inputs = (*_TAIL_FIELDS.values(), _REQUEST)
    for i in indices:
        name = f"output{i}"
        if inputs[i] is not None:
            board.inputs[f"tail{i}"] = inputs[i]
            _gate(board, "If", name, f"tail{i}", "tail")
        if shared:
            board.inputs[f"main{i}"] = _MAIN_PRIVATE[i]
            _gate(board, "If", name, f"main{i}", main)
        elif inputs[i] is None:
            _gate(board, "If", name, 0, 0)
        board.outputs[name] = _MAIN_OUTPUTS[i]
    return board


def _attach_writer(document, writer: Path) -> None:
    native = _native_wiring(writer)
    _, sent = _radio_channels(native)
    bridge_outputs = {*range(1680001, 1680008), _WRITER_ENABLE, _ADDRESS, _ACK}
    if any(sent[ch] != 1 for ch in (*_MAIN_OUTPUTS, *bridge_outputs)):
        raise ValueError("共享接入需要已带一份六字段写入桥的 pair-writer")
    replacements = dict(zip(_MAIN_OUTPUTS, _MAIN_PRIVATE, strict=True))
    for kind, entry in _radio_ports(native):
        channel = decode_constant(entry["C"])
        if kind == _RADIO_TRANSMITTER and channel in replacements:
            entry["C"] = constant(replacements[channel])
    _append(document, native.platforms)


def build(root: Path, *, writer: Path | None = None) -> tuple[dict, dict]:
    modules = [_run_gate(writer is not None), _advance(), _row_bank(_TARGET_ROWS, 1703700),
               _row_bank(_PUSHED_ROWS, 1703701)]
    modules.extend(_mux(group, writer is not None) for group in ((0, 1, 2), (3, 4, 5), (6,)))
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    hold = _load_frames(document, root) + 2 * _RADIO_TICKS
    clock, timing = build_confirmed_call(
        enable=_ENABLE, address=_ADDRESS, ack=_ACK, finished=_DONE, opcode=_TAIL_FIELDS["opcode"],
        settled=_SETTLED, has_packet=_HAS_PACKET, confirmed=_CONFIRMED, request=_REQUEST,
        states={"step": (_STEP, _NEXT, 0)}, settle_ticks=hold, update_ticks=2 * _RADIO_TICKS,
        channel_base=_CLOCK,
    )
    _append(document, clock["BP"]["Entries"])
    if writer is None:
        caller = {**timing, "inputs": {**timing["inputs"], "enable": _WRITER_ENABLE, "opcode": _MAIN_OUTPUTS[0]},
                  "outputs": {**timing["outputs"], "request_address": _MAIN_OUTPUTS[-1]}}
        fields = dict(zip(FIELDS, _MAIN_OUTPUTS[:-1], strict=True))
        packet = {"outputs": {name: {"channel": ch} for name, ch in fields.items()},
                  "reserved_channels": list(fields.values())}
        bridge, _ = build_write_bridge(caller, packet, _BRIDGE)
        _append(document, bridge["BP"]["Entries"])
    else:
        _attach_writer(document, writer)
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    duplicate = sorted(channel for channel, count in sent.items() if count > 1)
    if duplicate:
        raise ValueError(f"尾帧合装有重复发射频道 {duplicate}")
    report = {"inputs": {"start": _START, "target_rows_bottom_to_top": _TARGET_ROWS,
                         "pushed_rows_bottom_to_top": _PUSHED_ROWS},
              "outputs": {"done": _DONE}, "shared_writer": writer is not None,
              "method_run": _MAIN_RUN if writer is not None else None,
              "reserved_channels": [1703900, 1703963], "external_inputs": sorted(received.keys() - sent.keys()),
              "writer_bus": {"address": _ADDRESS, "ack_address": _ACK, "request_address": _MAIN_OUTPUTS[-1],
                             "fields": dict(zip(FIELDS, _MAIN_OUTPUTS[:-1], strict=True))},
              "timing": {**timing["timing"], "restart_low_signal_ticks": 6 * _RADIO_TICKS},
              "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
              "global_transmitters": len(sent)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出冻结顶针帧的正向六槽写入")
    parser.add_argument("--frames", required=True, type=Path, help="层号、差量原料及指令三份蓝图和接口表所在目录")
    parser.add_argument("--writer", type=Path, help="与尾帧共用一份写入桥的 pair-writer 蓝图")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.frames, writer=args.writer)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
