"""复用冻结候选的四列步进拼出第五层顶盖。"""

import argparse
from pathlib import Path

from ...synthesis.shape_methods import shape_literal
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _results, _wait_timer
from ..local_module import Module
from .pin_candidate_row import (
    _CAPTURE, _DONE, _PREPARE, _RADIO, _RESET_TICKS, _SCAN, _SETTLE,
    _channel, _in_phases, _phase, _read_blueprint, _read_report, _rotate_row,
)
from .pin_column_loop import _place
from .pin_column_select import _select_field, build as build_selector


_BASE = 1701940
_COLUMN = 1701904


def _mask(enable, frozen, mode, mask, active, output):
    board = Module({"enable": enable, "frozen": frozen, "mode": mode, "mask": mask})
    # 标记掩码的针只用于识别当前列，不参与候选行拼合。
    masks = tuple(shape_literal("".join("P-" if n & (1 << q) else "--" for q in range(4)))
                  for n in range(1, 16))
    board.lookup("mask", "mask_row", ((0, shape_literal("Cu------")), *enumerate(masks, 1)))
    board.outputs = {"mask_row": output}
    legal_mode = _gate(board, "Or", "legal_mode", _compare(board, "member", "mode", 0),
                       _compare(board, "template", "mode", 1))
    legal_mask = _compare(board, "legal_mask", "mask_row", None, "Bg==")
    requested = _gate(board, "And", "requested", _compare(board, "enabled", "enable", 1),
                      _compare(board, "ready", "frozen", 1))
    _gate(board, "And", "active", requested, _gate(board, "And", "legal", legal_mode, legal_mask))
    board.outputs["active"] = active
    return board


def _stamp(phase, prepare_tap, settle_tap, selected, output):
    board = Module({"phase": phase, "prepare_tap": prepare_tap, "settle_tap": settle_tap,
                    "selected": selected})
    prepared = _gate(board, "And", "prepared", _compare(board, "columns_waited", "phase", "prepare_tap"),
                     "selected")
    ready = _compare(board, "row_waited", "phase", "settle_tap")
    for name, phases, condition in (("prepare", _PREPARE, prepared), ("scan", _SCAN, "selected"),
                                    ("settle", (_SETTLE,), ready)):
        take = _gate(board, "And", name, _in_phases(board, name, phases), condition)
        _gate(board, "If", "stamp", "phase", take)
    board.outputs = {"stamp": output}
    return board


def _route(active, phase, column, captures):
    board = Module({"active": active, "phase": phase})
    board.lookup("phase", "lane", ((i + 1, i // 3) for i in range(12)))
    _gate(board, "If", "column", "lane", "active")
    board.outputs = {"column": column}
    for i, (state, channel) in enumerate(zip(_CAPTURE, captures, strict=True)):
        capture = _gate(board, "And", f"capture_{i}", "active", _compare(board, f"saving_{i}", "phase", state))
        board.outputs[capture] = channel
    return board


def _cell(mode, mask, member, allowed, cell, valid):
    board = Module({"mode": mode, "mask": mask, "member": member, **allowed})
    board.gate("VirtualAnalyzer", ("mask",), ("marker", "color"))
    in_mask = _compare(board, "in_mask", "marker", shape_literal("P-------"))
    outside = _gate(board, "Not", "outside", in_mask)
    template = _compare(board, "template", "mode", 1)
    member_mode = _compare(board, "member_mode", "mode", 0)
    member_column = _gate(board, "And", "member_column", member_mode, outside)
    crystal = _gate(board, "And", "use_crystal", in_mask, "crystal_allowed")
    ordinary = _gate(board, "Or", "use_ordinary", _gate(board, "And", "template_ordinary", template, outside),
                     _gate(board, "And", "member_ordinary", member_column,
                           _compare(board, "normal", "member", 1)))
    pin = _gate(board, "And", "use_pin", member_column,
                _gate(board, "And", "legal_pin", _compare(board, "needle", "member", 2), "pin_allowed"))
    empty = _gate(board, "And", "use_empty", member_column, _compare(board, "empty", "member", 0))
    for signal, take in (("cr------", crystal), ("Cu------", ordinary), ("P-------", pin)):
        _gate(board, "If", "cell", shape_literal(signal), take)
    status = _any(board, "valid", (crystal, ordinary, pin, empty))
    board.outputs = {"cell": cell, status: valid}
    return board


def _publish(active, phase, row, statuses, outputs):
    board = Module({"active": active, "phase": phase, "row": row,
                    **{f"valid_{i}": channel for i, channel in enumerate(statuses)}})
    ready = _gate(board, "And", "ready", "active", _compare(board, "complete", "phase", _DONE))
    valid = ready
    for i in range(4):
        valid = _gate(board, "And", f"checked_{i}", valid, f"valid_{i}")
    _gate(board, "If", "row_out", "row", valid)
    board.outputs = {"ready": outputs["ready"], valid: outputs["valid"], "row_out": outputs["row"]}
    return board


def build(circuits: Path, channel_base: int = _BASE) -> tuple[dict, dict]:
    sample = _read_report(circuits / "pin-column-sample.json")
    cap = _read_report(circuits / "pin-cap-column.json")
    row = _read_report(circuits / "pin-source-row.json")
    first, last = sample["reserved_channels"]
    window = range(channel_base, channel_base + 32)
    occupied = set(cap["reserved_channels"]) | set(row["reserved_channels"]) | set(range(first, last + 1))
    if not 1 <= window[0] <= window[-1] < 1 << 24 or occupied.intersection(window) or any(
        channel in window for channel in range(_COLUMN, _COLUMN + 3)
    ):
        raise ValueError("顶盖频道须合法并避开候选、选列和顶盖模块的原频道")
    selector, selected = build_selector(sample, cap, _COLUMN)
    frozen = sample["outputs"]["ready"]
    column = selected["inputs"]["column"]
    channels = iter(window)
    inputs = {name: next(channels) for name in ("enable", "mode", "crystal_mask")}
    members = tuple(next(channels) for _ in range(4))
    outputs = {name: next(channels) for name in ("ready", "valid", "row")}
    active, phase, stamp, mask, mask_column, member, cell, cell_valid = (next(channels) for _ in range(8))
    captures = tuple(next(channels) for _ in range(4))
    statuses = tuple(next(channels) for _ in range(4))
    timer = tuple(channels)
    labels = tuple(_channel(row, "inputs", f"q{i}") for i in range(4))
    allowed = {name: _channel(cap, "outputs", name) for name in ("crystal_allowed", "pin_allowed")}

    # 选列、顶盖许可和单格选值稳定后才捕获本列，最后等四格拼合稳定。
    prepare = selected["settling"]["hold_signal_ticks"] + cap["settling"]["hold_signal_ticks"] + 6 * _RADIO
    settle = row["settling"]["hold_signal_ticks"] + 4 * _RADIO
    prepare_steps, settle_steps = ((n + _RADIO - 1) // _RADIO for n in (prepare, settle))
    timers, prepare_tap, settle_tap = _wait_timer(phase, timer, prepare_steps, settle_steps)
    modules = [
        _mask(inputs["enable"], frozen, inputs["mode"], inputs["crystal_mask"], active, mask),
        _stamp(phase, prepare_tap, settle_tap, selected["outputs"]["valid"], stamp),
        _phase(active, phase, stamp),
        _route(active, phase, column, captures),
        _rotate_row(mask, column, mask_column),
        _select_field(column, active, members, "member", member),
        _cell(inputs["mode"], mask_column, member, allowed, cell, cell_valid),
        _publish(active, phase, _channel(row, "outputs", "row"), statuses, outputs),
        *timers,
    ]
    for index in range(0, 4, 2):
        for value, registers in ((cell, labels), (cell_valid, statuses)):
            pairs = tuple(zip(captures[index:index + 2], registers[index:index + 2], strict=True))
            modules.append(_results(active, value, pairs))

    entries = []
    for i, module in enumerate(modules):
        entry, = module.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 6), "Y": 3 * (i // 6)})
    _place(entries, selector)
    for name in ("pin-cap-column", "pin-source-row"):
        _place(entries, _read_blueprint(circuits / f"{name}.spz2bp"))
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    return document, {
        "inputs": {**inputs, "members": members, "candidate_ready": frozen},
        "outputs": outputs,
        "channels": {"control_range": [window[0], window[-1]], "selector": selected["reserved_channels"],
                     "cap": cap["reserved_channels"], "join_row": row["reserved_channels"]},
        "timing": {"channel_signal_ticks": _RADIO, "reset_hold_signal_ticks": _RESET_TICKS,
                   "column_hold_signal_ticks": prepare_steps * _RADIO,
                   "start_to_ready_signal_ticks": (4 * (prepare_steps + 6) + settle_steps + 8) * _RADIO},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出四列冻结候选的顶盖行读取器")
    parser.add_argument("circuits", type=Path, help="顶针逆推验收分册目录")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="顶盖读取器的首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(args.circuits, args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
