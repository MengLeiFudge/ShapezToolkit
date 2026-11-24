"""编译根订单的闭包启动和状态分流。"""

import argparse
from pathlib import Path

from .circuit import constant
from .compile_order_entry import build as build_order_entry
from .compile_pair_writer import _compile
from .compiler_backend import _write_blueprint
from .compiler_backend.leaf_snapshot import build as build_leaf_snapshot
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _RADIO_TICKS, _WAIT_RADIX, _compare, _gate, _local_wiring, _wait_timer
from .compiler_backend.prefix_scan_wiring import _append, _native_wiring
from .compiler_frontend import FrontendError
from .compiler_frontend.pin_candidate_closure import _radio_ports
from .local_module import Module


_ENABLE, _PHASE, _ROWS_READY = range(1704673, 1704676)
_FLAGS = {name: 1704676 + i for i, name in enumerate(("closure", "snapshot", "tail", "unknown", "invalid", "fault"))}
_FLAGS["replay"] = 1704687
_TIMERS = tuple(range(1704682, 1704687))


def _row_timer(elapsed):
    board = Module({"elapsed": elapsed})
    board.outputs = {_compare(board, "ready", "elapsed", 1): _ROWS_READY}
    return board


def build(input_hold_ticks: int):
    steps = (input_hold_ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 2
    if not _WAIT_RADIX < steps <= _WAIT_RADIX ** 2:
        raise ValueError("根订单原色保持时间超出计数范围")
    inputs = {"phase": _PHASE, "enable": _ENABLE, "rows_ready": _ROWS_READY, "nonempty": 1704670,
              "unknown": 1704671, "chosen": 1703004, "exhausted": 1703005, "snapshot_ready": 1704602}
    document, _ = _compile("root_search", {"next": "root_search_next"}, inputs, {"next": _PHASE + 20})
    for _, transmitter, channel, config in _radio_ports(_local_wiring(document["BP"])):
        if transmitter and channel == _PHASE + 20:
            config["C"] = constant(_PHASE)
    flags, _ = _compile("root_search", {name: f"root_search_{name}" for name in _FLAGS},
                        {"phase": _PHASE, "enable": _ENABLE}, _FLAGS)
    _append(document, flags["BP"]["Entries"])
    timers, elapsed, _ = _wait_timer(_PHASE, _TIMERS, steps, 1)
    for board in (*timers, _row_timer(elapsed)):
        _append(document, board.layout()["BP"]["Entries"])
    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    external = {key: ch for key, ch in inputs.items() if key not in ("phase", "rows_ready")}
    if receivers.keys() - senders.keys() != set(external.values()) or any(count != 1 for count in senders.values()):
        raise ValueError("根订单调度的原生接口不一致")
    return document, {"inputs": external, "outputs": _FLAGS, "phase": _PHASE,
                      "input_hold_signal_ticks": steps * _RADIO_TICKS,
                      "platforms": len(wiring.platforms), "building_entries": len(wiring.entries)}

def _attach(document, path, channels):
    wiring = _native_wiring(path)
    received, sent = _radio_channels(wiring)
    if channels.keys() - (received.keys() - sent.keys()):
        raise ValueError(f"{path.name} 缺少根订单需要重接的输入")
    for _, transmitter, channel, config in _radio_ports(wiring):
        if not transmitter and channel in channels:
            config["C"] = constant(channels[channel])
    _append(document, wiring.platforms)


def _direct_controls():
    board = Module({"order": _ENABLE, "capture": _FLAGS["snapshot"], "replay": _FLAGS["replay"]})
    board.outputs = {
        _gate(board, "If", "hold_leaf", 1, "order"): 1704600,
        _gate(board, "If", "capture_leaf", 1, "capture"): 1704601,
        _gate(board, "If", "run_replay", 1, "replay"): 1702850,
        _gate(board, "If", "raw_mode", 0, "order"): 1703001,
        _gate(board, "If", "strict_top", 0, "order"): 1703002,
        _gate(board, "If", "no_frames", 0, "order"): 1704000,
    }
    return board.layout()["BP"]["Entries"]


def build_direct(reader: Path, closure: Path, path: Path, input_hold_ticks: int, *, stacked_leaf: bool = False):
    document, report = build(input_hold_ticks)
    intake, _ = build_order_entry()
    replay, _ = build_leaf_snapshot(path, stacked=stacked_leaf)
    _attach(document, reader, {1700872: 1600000})
    _append(document, intake["BP"]["Entries"])
    _attach(document, closure, {1703000: _FLAGS["closure"]})
    _append(document, _direct_controls())
    _append(document, replay["BP"]["Entries"])
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    duplicate = sorted(channel for channel, count in sent.items() if count != 1)
    if duplicate:
        raise ValueError(f"根订单合装有重复发射频道 {duplicate}")
    report.update({"inputs": {"enable": _ENABLE, "target": 1600000, "feed_request": 1702851},
                   "external_inputs": sorted(received.keys() - sent.keys()),
                   "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
                   "global_transmitters": len(sent)})
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="生成共用闭包的根订单启动和结果分流")
    parser.add_argument("--input-hold", type=int, default=4096, help="根图形读取和供料判定的稳定期")
    parser.add_argument("--reader", type=Path, help="合装时使用的五层原色读取蓝图")
    parser.add_argument("--closure", type=Path, help="合装时使用的双来源闭包蓝图")
    parser.add_argument("--path", type=Path, help="合装时使用的两遍成功路径蓝图")
    parser.add_argument("--stacked-leaf", action="store_true", help="使用三个岛层的叶端锁存")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图路径")
    args = parser.parse_args()
    parts = (args.reader, args.closure, args.path)
    if any(parts) and not all(parts):
        parser.error("合装需要同时给出 --reader、--closure 和 --path")
    try:
        if all(parts):
            document, report = build_direct(*parts, args.input_hold, stacked_leaf=args.stacked_leaf)
        else:
            document, report = build(args.input_hold)
        _write_blueprint(document, report, args.output)
    except FrontendError as error:
        parser.error(f"{error.filename}:{error.lineno}:{error.offset} {error.msg}")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
