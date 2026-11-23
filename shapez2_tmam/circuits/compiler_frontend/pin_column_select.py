"""将一个冻结的顶针候选按列送给顶盖和保序标签模块。"""

import argparse
import json
from pathlib import Path

from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _compare, _gate, _local_wiring
from ..local_module import Module


def _select_field(column, ready, sources, field, output, valid=None):
    inputs = {f"q{i}": channel for i, channel in enumerate(sources)}
    board = Module({"column": column, "ready": ready, **inputs})
    for i, name in enumerate(inputs):
        match = _compare(board, f"selected_{i}", "column", i)
        _gate(board, "If", "selected", name, match)
    enabled = _compare(board, "enabled", "ready", 1)
    _gate(board, "If", field, "selected", enabled)
    board.outputs = {field: output}
    if valid is not None:
        _compare(board, "valid", field, None, "Bg==")
        board.outputs["valid"] = valid
    return board


def build(sample: dict, cap: dict, channel_base: int) -> tuple[dict, dict]:
    lanes = sample["outputs"]["columns"]
    if len(lanes) != 4:
        raise ValueError("需要四个冻结候选列")
    column, slot, valid = range(channel_base, channel_base + 3)
    ready = sample["outputs"]["ready"]
    outputs = {field: cap["inputs"][field]["channel"] for field in ("word", "z0", "z1", "z2", "z3")}
    outputs.update(slot=slot, valid=valid)
    words = tuple(sample["inputs"][f"q{i}"] for i in range(4))
    sources = {"word": words, "slot": tuple(lane["slot"] for lane in lanes)}
    for level in range(4):
        sources[f"z{level}"] = tuple(lane[f"material_{level}"] for lane in lanes)

    supplied = {ready} | {channel for fields in sources.values() for channel in fields}
    channels = {column, *outputs.values()}
    first, last = sample["reserved_channels"]
    cap_results = {port["channel"] for port in cap["outputs"].values()}
    if any(type(channel) is not int or not 1 <= channel < 1 << 24 for channel in channels | supplied):
        raise ValueError("接口频道须为 1～16777215 内的整数")
    if (len(channels) != len(outputs) + 1 or channels & supplied
            or any(first <= channel <= last for channel in channels)
            or channels & cap_results or {column, slot, valid} & set(cap["reserved_channels"])):
        raise ValueError("选择器频道与候选样件或顶盖接口重叠")

    entries = []
    for i, (field, inputs) in enumerate(sources.items()):
        board = _select_field(column, ready, inputs, field, outputs[field], valid if field == "slot" else None)
        entry, = board.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 3), "Y": 3 * (i // 3)})
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    _local_wiring(document["BP"])
    report = {
        "inputs": {"column": column, "ready": ready, "words": list(words),
                   "columns": [{name: channel for name, channel in lane.items() if name != "next_slot"}
                               for lane in lanes]},
        "outputs": outputs,
        "cap_inputs": {name: outputs[name] for name in ("word", "z0", "z1", "z2", "z3")},
        "label_rank_inputs": {name: outputs[name] for name in ("z0", "z1", "z2")},
        "reserved_channels": sorted(channels),
        "settling": {"max_gate_depth": 4, "hold_signal_ticks": 384},
        "platforms": len(entries),
        "building_entries": sum(len(entry["B"]["Entries"]) for entry in entries),
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出冻结顶针候选的原生列选择器")
    parser.add_argument("sample", type=Path, help="四列顶针候选样件的 JSON 频道表")
    parser.add_argument("cap", type=Path, help="单列顶盖的 JSON 频道表")
    parser.add_argument("--channel-base", type=int, default=1701904, help="列号、槽号和有效位的首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        sample = json.loads(args.sample.read_text(encoding="utf-8-sig"))
        cap = json.loads(args.cap.read_text(encoding="utf-8-sig"))
        _write_blueprint(*build(sample, cap, args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
