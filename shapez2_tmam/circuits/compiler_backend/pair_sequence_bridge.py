"""将方法确认器接到共用的双半形配方写入桥。"""

import argparse
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .method_sequence import _DEFAULT_BASE, _DEFAULT_METHODS, _ENABLE, _KIND, _radio_channels
from .method_sequence import build as build_sequence
from .module_caller import _RADIO_TICKS, _any, _compare, _gate, _local_wiring
from .prefix_scan_wiring import _append, _native_wiring, _report


_SELECTOR = 1701740
_WRITE_RUN, _WRITE_DONE = 1701761, 1701766
_PACKET_RUN, _PACKET_DONE = 1701741, 1701746
_STEP, _APPENDED = 1701710, 1701747
_SELECTORS = {2: 3, 3: 3, 4: 4, 5: 3}
_SHARED_DONE = 1702062


def _select(runs: dict[int, int], selector: int = _SELECTOR, run: int = _WRITE_RUN) -> Module:
    board = Module({"kind": _KIND, "enable": _ENABLE, **{f"run{kind}": ch for kind, ch in runs.items()}})
    enabled = _compare(board, "enabled", "enable", 1)
    selected = {kind: _compare(board, f"selected{kind}", "kind", kind) for kind in runs}
    for source in sorted(set(_SELECTORS.values())):
        candidates = tuple(selected[kind] for kind, value in _SELECTORS.items() if value == source)
        choose = _gate(board, "And", f"choose{source}", enabled, _any(board, f"source{source}", candidates))
        _gate(board, "If", "selector", source, choose)
    running = tuple(_gate(board, "And", f"running{kind}", selected[kind], f"run{kind}") for kind in runs)
    board.outputs = {"selector": selector,
                     _gate(board, "And", "write_run", enabled, _any(board, "requested", running)): run}
    return board


def _completion(run=_PACKET_RUN, done=_PACKET_DONE, step=_STEP, appended=_APPENDED, output=_SHARED_DONE) -> Module:
    board = Module({"write_done": _WRITE_DONE, "running": run, "packet_done": done,
                    "step": step, "appended": appended})
    waiting = _compare(board, "waiting", "running", 0)
    cleared = _compare(board, "cleared", "write_done", None)
    published = _compare(board, "published", "write_done", 1)
    raw_done = _compare(board, "raw_done", "packet_done", 1)
    raw_clear = _compare(board, "raw_clear", "packet_done", 0)
    step_zero = _compare(board, "step_zero", "step", 0)
    empty = _compare(board, "empty", "appended", 0)
    reset = _gate(board, "And", "reset", _gate(board, "And", "idle", waiting, cleared),
                  _gate(board, "And", "zeroed", raw_clear, _gate(board, "And", "initial", step_zero, empty)))
    complete = _gate(board, "And", "complete", published, _gate(board, "And", "finished", "running", raw_done))
    _gate(board, "If", "done", 0, reset)
    _gate(board, "If", "done", 1, complete)
    board.outputs = {"done": output}
    return board


def build(writer: Path) -> tuple[dict, dict]:
    return _build(writer, lambda runs: (_select(runs),), ())


def _build(writer, dispatch, writer_returns):
    interface = _report(writer)
    clock = interface["clock"]
    if (interface["inputs"]["selector"], interface["method_run"], interface["method_done"],
            clock["inputs"]["enable"], clock["inputs"]["done"],
            clock["states"]["step"]["current"], clock["states"]["appended"]["current"]) != (
            _SELECTOR, _WRITE_RUN, _WRITE_DONE, _PACKET_RUN, _PACKET_DONE, _STEP, _APPENDED):
        raise ValueError("pair-writer 的写入与复位频道不匹配")
    if interface["selector_values"]["join"] != 3 or interface["selector_values"]["append"] != 4:
        raise ValueError("pair-writer 的拼合和追加来源编号不匹配")
    reset_ticks = clock["timing"]["reset_hold_signal_ticks"] + 4 * _RADIO_TICKS
    methods = tuple((kind, run, _SHARED_DONE, max(reset, reset_ticks), sample) if kind in _SELECTORS
                    else (kind, run, done, reset, sample)
                    for kind, run, done, reset, sample in _DEFAULT_METHODS)
    document, report = build_sequence(methods, channel_base=_DEFAULT_BASE, settle_ticks=1536, update_ticks=1536)
    runs = {kind: run for kind, run, _, _, _ in methods if kind in _SELECTORS}
    boards = [module.layout()["BP"]["Entries"][0] for module in (*dispatch(runs), _completion())]
    stack_platforms(boards)
    _append(document, boards)

    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    writer_wiring = _native_wiring(writer)
    writer_receivers, writer_senders = _radio_channels(writer_wiring)
    duplicate = sorted(ch for ch, count in (senders + writer_senders).items() if count > 1)
    if duplicate:
        raise ValueError(f"与 pair-writer 合装时频道有重复发射器 {duplicate}")
    expected_inputs = {_KIND, _WRITE_DONE, _PACKET_RUN, _PACKET_DONE, _STEP, _APPENDED,
                       report["inputs"]["next"], report["inputs"]["done"], *writer_returns}
    expected_outputs = {**report["outputs"], "selector": _SELECTOR, "write_run": _WRITE_RUN}
    if (receivers.keys() & writer_senders.keys() != expected_inputs
            or senders.keys() & writer_receivers.keys() != set(expected_outputs.values())):
        raise ValueError("pair-writer 的原生收发与确认器连接不匹配")
    report.update(
        writer={"inputs": {"done": _WRITE_DONE, "packet_run": _PACKET_RUN, "packet_done": _PACKET_DONE,
                           "step": _STEP, "appended": _APPENDED},
                "outputs": {"selector": _SELECTOR, "run": _WRITE_RUN},
                "selectors_by_kind": _SELECTORS, "shared_done": _SHARED_DONE},
        platforms=len(wiring.platforms), building_entries=len(wiring.entries),
        combined_platforms=len(wiring.platforms) + len(writer_wiring.platforms),
        combined_building_entries=len(wiring.entries) + len(writer_wiring.entries),
        combined_global_transmitters=len(senders) + len(writer_senders),
    )
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出共用写入桥的方法启停与完成确认器")
    parser.add_argument("--writer", type=Path, required=True, help="pair-writer 原生蓝图路径，同目录需有接口表")
    parser.add_argument("--output", type=Path, required=True, help="确认器的原生蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.writer)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
