"""冻结成功叶端的输入，供两遍配方回放共用。"""

import argparse
from pathlib import Path

from ...mari.signals import decode_constant
from ..circuit import constant
from ..local_module import Module
from . import _write_blueprint
from ._snapshot_layout import compact_batch, compact_snapshot
from ._stacked_snapshot import stacked_snapshot
from .auto_prefix_scan import _radio_ports
from .method_sequence import _radio_channels
from .module_caller import _RADIO_RECEIVER, _compare, _gate, _local_wiring
from .prefix_scan_wiring import _append, _native_wiring


_HOLD, _CAPTURE, _READY, _PHASE = range(1704600, 1704604)
_BATCH_READY = 1704605
_CHOSEN, _COLUMN, _BATCH = 1703004, 1703003, 1702850
_SOURCE = (1703002, 1703006, *range(1703008, 1703017), *range(1703116, 1703120))
_STORED = tuple(range(1704620, 1704635))
_HEIGHT = 1704635
_REPLAY_INPUTS = {**dict(zip(_SOURCE, _STORED, strict=True)), 1703007: _HEIGHT, _BATCH: _BATCH_READY}


def _capture() -> Module:
    board = Module({"hold": _HOLD, "capture": _CAPTURE, "chosen": _CHOSEN, "phase": _PHASE})
    holding = _compare(board, "holding", "hold", 1)
    requested = _compare(board, "requested", "capture", 1)
    chosen = _compare(board, "chosen_leaf", "chosen", 1)
    idle = _compare(board, "idle", "phase", None)
    accepted = _gate(board, "And", "accept", idle, _gate(board, "And", "capture_chosen", requested, chosen))
    phase1, phase2, phase3 = (_compare(board, f"phase{i}", "phase", i) for i in range(1, 4))
    _gate(board, "If", "next", 1, accepted)
    _gate(board, "If", "next", 2, phase1)
    _gate(board, "If", "next", 3, _gate(board, "Or", "settled", phase2, phase3))
    _gate(board, "If", "state", "next", holding)
    # 读到阶段 2 时写入，等于旧阶段 1 的 commit 再经过一次无线传输。
    _gate(board, "And", "load", holding, phase2)
    _gate(board, "And", "retain", holding, _gate(board, "Not", "no_load", phase2))
    board.outputs = {"state": _PHASE, _gate(board, "And", "ready", holding, phase3): _READY}
    return board


def _height() -> Module:
    heights = _STORED[2:6]
    board = Module({"column": _COLUMN, **{f"height{q}": ch for q, ch in enumerate(heights)}})
    for q in range(len(heights)):
        selected = _compare(board, f"column{q}", "column", q)
        _gate(board, "If", "current_height", f"height{q}", selected)
    board.outputs = {"current_height": _HEIGHT}
    return board


def _batch() -> Module:
    board = Module({"request": _BATCH, "ready": _READY})
    requested = _compare(board, "requested", "request", 1)
    board.outputs = {_gate(board, "And", "start", requested, "ready"): _BATCH_READY}
    return board


def _attach_path(document: dict, path: Path) -> None:
    wiring = _native_wiring(path)
    received, sent = _radio_channels(wiring)
    external = received.keys() - sent.keys()
    absent = sorted(_REPLAY_INPUTS.keys() - external)
    if absent:
        raise ValueError(f"成功路径缺少可重绑的叶端或批次输入 {absent}")
    for kind, entry in _radio_ports(wiring):
        channel = decode_constant(entry["C"])
        if kind == _RADIO_RECEIVER and channel in _REPLAY_INPUTS:
            entry["C"] = constant(_REPLAY_INPUTS[channel])
    _append(document, wiring.platforms)


def build(path: Path | None = None, *, stacked: bool = False) -> tuple[dict, dict]:
    fields = tuple(zip(_SOURCE, _STORED, strict=True))
    args = fields, _capture(), _height(), _COLUMN
    platforms = stacked_snapshot(*args) if stacked else [compact_snapshot(*args)]
    if path is not None:
        batch = {**compact_batch(_batch()), "Z": 1}
        if stacked:
            batch["Y"] = 1
        platforms.append(batch)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    if path is not None:
        _attach_path(document, path)
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    duplicate = sorted(ch for ch, count in sent.items() if count != 1)
    if duplicate:
        raise ValueError(f"叶端锁存合装有重复发射频道 {duplicate}")
    report = {"inputs": {"hold": _HOLD, "capture": _CAPTURE, "chosen": _CHOSEN, "column": _COLUMN,
                         "optional_top": _SOURCE[0], "alternate": _SOURCE[1], "heights": _SOURCE[2:6],
                         "rows": _SOURCE[6:11], "material_words": _SOURCE[11:]},
              "outputs": {"ready": _READY, "optional_top": _STORED[0], "alternate": _STORED[1],
                          "current_height": _HEIGHT, "heights": _STORED[2:6], "rows": _STORED[6:11],
                          "material_words": _STORED[11:]},
              "path_rebinding": _REPLAY_INPUTS if path is not None else None,
              "external_inputs": sorted(received.keys() - sent.keys()), "reserved_channels": [1704600, 1704659],
              "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
              "global_transmitters": len(sent)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出成功叶端的输入锁存")
    parser.add_argument("--path", type=Path, help="将两遍成功路径的读口改接冻结输入")
    parser.add_argument("--stacked", action="store_true", help="将锁存和读高布置在三个岛层")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.path, stacked=args.stacked)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
