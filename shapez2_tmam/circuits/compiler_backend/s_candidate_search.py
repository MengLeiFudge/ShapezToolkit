"""按顺序枚举 S 前态，并行核对追加许可和 K/G 支撑。"""

import argparse
from pathlib import Path

from ...mari.signals import decode_constant
from ..circuit import constant
from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .auto_prefix_scan import _radio_ports
from .method_sequence import _radio_channels
from .module_caller import _RADIO_RECEIVER, _RADIO_TICKS, _any, _compare, _gate, _local_wiring, _wait_timer
from .prefix_scan_wiring import _append, _native_wiring


_ENABLE, _REJECT, _READY, _EXHAUSTED = range(1704800, 1704804)
_PHASE, _ENUM_NEXT, _FILTER_NEXT, _CLEAR = range(1704804, 1704808)
_TIMERS = tuple(range(1704810, 1704815))
_ENUM_ENABLE, _ADVANCE, _ENUM_READY, _ENUM_EXHAUSTED = range(1703500, 1703504)
_ENUM_TARGET, _LIMITS = tuple(range(1703504, 1703509)), tuple(range(1703509, 1703513))
_ROWS, _COUNTS = tuple(range(1703513, 1703518)), tuple(range(1703518, 1703522))
_ADD_START, _ADD_DONE, _ADD_OK = range(1704700, 1704703)
_TARGET = tuple(range(1704710, 1704715))
_SUPPORT_START, _SUPPORT_DONE, _GROUNDED, _SUPPORT_OK = 1704410, 1704412, 1704413, 1704416
_SUPPORT_ROWS = tuple(range(1704420, 1704425))
_BOOT, _SEEK, _FILTER, _OFFER, _ARMED, _RESET_FILTERS, _STEP, _END = range(8)
_ENUM_RESET_TICKS = 4096
_FILTER_RESET_TICKS = 96


def _checker_reset() -> Module:
    board = Module({"add": _ADD_DONE, "support": _SUPPORT_DONE})
    add = _compare(board, "add_clear", "add", 0)
    support = _compare(board, "support_clear", "support", 0)
    board.outputs = {_gate(board, "And", "clear", add, support): _CLEAR}
    return board


def _enum_transitions(boot_at: int, reset_at: int) -> Module:
    board = Module({"phase": _PHASE, "ready": _ENUM_READY, "exhausted": _ENUM_EXHAUSTED,
                    "clear": _CLEAR, "boot_at": boot_at, "reset_at": reset_at})
    boot = _compare(board, "boot", "phase", _BOOT)
    seek = _compare(board, "seek", "phase", _SEEK)
    reset = _compare(board, "reset", "phase", _RESET_FILTERS)
    step = _compare(board, "step", "phase", _STEP)
    ready = _compare(board, "ready_high", "ready", 1)
    ready_low = _compare(board, "ready_low", "ready", 0)
    exhausted = _compare(board, "exhausted_high", "exhausted", 1)
    exhausted_low = _compare(board, "exhausted_low", "exhausted", 0)
    enum_clear = _gate(board, "And", "enum_clear", ready_low, exhausted_low)
    boot_wait = _compare(board, "boot_mature", "boot_at", _BOOT)
    boot_clear = _gate(board, "And", "boot_clear", enum_clear, "clear")
    launch = _gate(board, "And", "launch", boot, _gate(board, "And", "boot_ready", boot_wait, boot_clear))
    next_item = _gate(board, "And", "next_item", step, ready_low)
    found = _gate(board, "And", "found", seek, _gate(board, "And", "valid", ready, exhausted_low))
    end = _gate(board, "And", "end", seek, _gate(board, "And", "depleted", exhausted, ready_low))
    reset_wait = _compare(board, "reset_mature", "reset_at", _RESET_FILTERS)
    step_ready = _gate(board, "And", "step_ready", reset, _gate(board, "And", "filters_reset", reset_wait, "clear"))
    for value, guard in ((_SEEK, _gate(board, "Or", "seeking", launch, next_item)),
                         (_FILTER, found), (_END, end), (_STEP, step_ready)):
        _gate(board, "If", "next", value, guard)
    board.outputs = {"next": _ENUM_NEXT}
    return board


def _filter_transitions() -> Module:
    board = Module({"phase": _PHASE, "reject": _REJECT, "add_done": _ADD_DONE, "add_ok": _ADD_OK,
                    "support_done": _SUPPORT_DONE, "support_ok": _SUPPORT_OK})
    filtering = _compare(board, "filtering", "phase", _FILTER)
    offered = _compare(board, "offered", "phase", _OFFER)
    armed = _compare(board, "armed", "phase", _ARMED)
    reject = _compare(board, "reject_high", "reject", 1)
    reject_low = _compare(board, "reject_low", "reject", 0)
    passes, failures = [], []
    for name in ("add", "support"):
        done = _compare(board, f"{name}_finished", f"{name}_done", 1)
        passed = _compare(board, f"{name}_passed", f"{name}_ok", 1)
        failed = _compare(board, f"{name}_failed", f"{name}_ok", 0)
        passes.append(_gate(board, "And", f"{name}_pass", done, passed))
        failures.append(_gate(board, "And", f"{name}_fail", done, failed))
    passed = _gate(board, "And", "both_pass", *passes)
    failed = _gate(board, "Or", "any_fail", *failures)
    skip = _gate(board, "And", "skip", filtering, failed)
    rejected = _gate(board, "And", "reject_offer", armed, reject)
    _gate(board, "If", "next", _OFFER, _gate(board, "And", "offer", filtering, passed))
    _gate(board, "If", "next", _ARMED, _gate(board, "And", "arm", offered, reject_low))
    _gate(board, "If", "next", _RESET_FILTERS, _gate(board, "Or", "reset", skip, rejected))
    board.outputs = {"next": _FILTER_NEXT}
    return board


def _state() -> Module:
    board = Module({"enable": _ENABLE, "phase": _PHASE, "enum": _ENUM_NEXT, "filter": _FILTER_NEXT})
    enabled = _compare(board, "enabled", "enable", 1)
    idle = _compare(board, "idle", "phase", -1)
    cold = _compare(board, "cold", "phase", None)
    _gate(board, "If", "next", _BOOT, _gate(board, "Or", "start", idle, cold))
    for source in ("enum", "filter"):
        _gate(board, "If", "next", source, 1)
    hold = _compare(board, "hold", "next", None)
    _gate(board, "If", "phase_out", "next", enabled)
    _gate(board, "If", "phase_out", "phase", _gate(board, "And", "keep", enabled, hold))
    _gate(board, "If", "phase_out", -1, _gate(board, "Not", "disabled", enabled))
    board.outputs = {"phase_out": _PHASE}
    return board


def _outputs() -> Module:
    board = Module({"enable": _ENABLE, "phase": _PHASE})
    enabled = _compare(board, "enabled", "enable", 1)
    enumerating = _compare(board, "enumerating", "phase", _SEEK, "Ag==")
    board.outputs[_gate(board, "And", "enum", enabled, enumerating)] = _ENUM_ENABLE
    for name, phase, channel in (("advance", _STEP, _ADVANCE), ("exhausted", _END, _EXHAUSTED)):
        selected = _compare(board, f"phase_{name}", "phase", phase)
        board.outputs[_gate(board, "And", name, enabled, selected)] = channel
    filtering = _compare(board, "filtering", "phase", _FILTER)
    for name, channel in (("add", _ADD_START), ("support", _SUPPORT_START)):
        board.outputs[_gate(board, "And", name, enabled, filtering)] = channel
    visible = _any(board, "visible", tuple(_compare(board, f"offered{i}", "phase", i) for i in (_OFFER, _ARMED)))
    board.outputs[_gate(board, "And", "ready", enabled, visible)] = _READY
    return board


def _attach(document: dict, path: Path, inputs, outputs, mapping: dict[int, int]) -> None:
    native = _native_wiring(path)
    received, sent = _radio_channels(native)
    if not set(inputs) <= received.keys() - sent.keys() or any(sent[ch] != 1 for ch in outputs):
        raise ValueError(f"{path.name} 的公开收发频道与 S 筛选接口不匹配")
    for kind, entry in _radio_ports(native):
        channel = decode_constant(entry["C"])
        if kind == _RADIO_RECEIVER and channel in mapping:
            entry["C"] = constant(mapping[channel])
    _append(document, native.platforms)


def build(*, enumerator: Path | None = None, addition: Path | None = None, support: Path | None = None,
          grounded: int = _GROUNDED) -> tuple[dict, dict]:
    parts = (enumerator, addition, support)
    if any(part is not None for part in parts) and not all(part is not None for part in parts):
        raise ValueError("合装时须同时指定枚举、追加许可和 K/G 支撑三件蓝图")
    boot_steps = (_ENUM_RESET_TICKS + _RADIO_TICKS - 1) // _RADIO_TICKS + 2
    reset_steps = _FILTER_RESET_TICKS // _RADIO_TICKS + 2
    timers, boot_at, reset_at = _wait_timer(_PHASE, _TIMERS, boot_steps, reset_steps)
    modules = [_checker_reset(), _enum_transitions(boot_at, reset_at), _filter_transitions(), _state(), _outputs(), *timers]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    if enumerator is not None:
        _attach(document, enumerator, (_ENUM_ENABLE, _ADVANCE, *_ENUM_TARGET, *_LIMITS),
                (_ENUM_READY, _ENUM_EXHAUSTED, *_ROWS, *_COUNTS), dict(zip(_ENUM_TARGET, _TARGET, strict=True)))
        _attach(document, addition, (_ADD_START, *_TARGET, *_ROWS), (_ADD_DONE, _ADD_OK), {})
        mapping = {**dict(zip(_SUPPORT_ROWS, _ROWS, strict=True)), _GROUNDED: grounded}
        _attach(document, support, (_SUPPORT_START, _GROUNDED, *_SUPPORT_ROWS), (_SUPPORT_DONE, _SUPPORT_OK), mapping)
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    duplicate = sorted(ch for ch, count in sent.items() if count != 1)
    external = received.keys() - sent.keys()
    required = {_ENABLE, _REJECT}
    if enumerator is not None:
        required.update((*_TARGET, *_LIMITS, grounded))
    if duplicate or not required <= external:
        raise ValueError(f"S 筛选合装收发不匹配，重复发射 {duplicate}，缺少外部输入 {sorted(required - external)}")
    report = {"inputs": {"enable": _ENABLE, "reject": _REJECT, "target_rows": _TARGET,
                         "limits": _LIMITS, "grounded": grounded},
              "outputs": {"ready": _READY, "exhausted": _EXHAUSTED, "rows": _ROWS, "counts": _COUNTS},
              "controls": {"enumerator": [_ENUM_ENABLE, _ADVANCE, _ENUM_READY, _ENUM_EXHAUSTED],
                           "addition": [_ADD_START, _ADD_DONE, _ADD_OK],
                           "support": [_SUPPORT_START, _SUPPORT_DONE, _SUPPORT_OK]},
              "includes_parts": enumerator is not None, "external_inputs": sorted(external),
              "timing": {"enumerator_reset_signal_ticks": boot_steps * _RADIO_TICKS,
                         "filter_reset_signal_ticks": reset_steps * _RADIO_TICKS},
              "reserved_channels": [1704800, 1704899], "platforms": len(wiring.platforms),
              "building_entries": len(wiring.entries), "global_transmitters": len(sent)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 S 枚举与两项并行许可的组合控制")
    parser.add_argument("--enumerator", type=Path, help="动态 S 枚举原生蓝图")
    parser.add_argument("--addition", type=Path, help="S 追加许可原生蓝图")
    parser.add_argument("--support", type=Path, help="K/G 支撑扫描原生蓝图")
    parser.add_argument("--grounded-channel", type=int, default=_GROUNDED, help="合装时的 G 模式输入频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(enumerator=args.enumerator, addition=args.addition, support=args.support,
                                 grounded=args.grounded_channel)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
