"""合装双切向选择、可选顶格与五轮前缀闭包。"""

import argparse
from collections import Counter
import json
from pathlib import Path

from ...mari.signals import decode_constant
from ..circuit import constant
from . import _write_blueprint
from . import prefix_scan_wiring as prefix
from .module_caller import _RADIO_RECEIVER, _RADIO_TRANSMITTER, _attach_callee, _local_wiring, build_calls


_PARTS = ("choose-cut", "choose-cut-clock", "orient-cut", "four-column-targets", "read-four-columns",
          "seed-pair-0", "seed-pair-1", "seed-two-halves", "restore-seed-0", "restore-seed-1",
          "paired-prefix-scan", "check-column-0", "check-column-1", "check-column-2", "check-column-3",
          "check-prefix")


def _radio_ports(wiring):
    for i, (_, entry) in enumerate(wiring.entries):
        kind = entry["T"]
        if kind in (_RADIO_RECEIVER, _RADIO_TRANSMITTER):
            (source, _), = wiring.sources(i, 0)
            yield kind, wiring.entries[source][1]


def _rewire(wiring, replacements: dict[int, int], name: str) -> list[dict]:
    sent = Counter()
    for kind, config in _radio_ports(wiring):
        channel = decode_constant(config["C"])
        if channel in replacements:
            config["C"] = constant(replacements[channel])
            if kind == _RADIO_TRANSMITTER:
                sent[channel] += 1
    if sent != Counter(replacements.keys()):
        raise ValueError(f"{name} 的原生发射频道与接口表不符")
    return wiring.platforms


def _compact_caller(root: Path, name: str, callee: str):
    original = prefix._report(root / name)
    interface = prefix._report(root / callee)
    path = root / f"{name}-calls.json"
    calls = json.loads(path.read_text(encoding="utf-8-sig"))
    outputs = original["outputs"]
    document, report = build_calls(
        interface, calls, original["reserved_channels"][0], result_names=tuple(outputs["calls"][0]),
        enable_channel=prefix._channel(original, "inputs", "enable"),
        parameter_hold_signal_ticks=original["timing"].get("parameter_hold_signal_ticks", 0), compact_results=True,
    )
    if report["outputs"] != outputs or report["timing"] != original["timing"]:
        raise ValueError(f"{name} 的压缩调用与原频道或采样时序不符")
    _attach_callee(document, report, root / f"{callee}.spz2bp")
    return _local_wiring(document["BP"])


def build(root: Path) -> tuple[dict, dict]:
    halves = root / "双半形"
    top_path = root / "顶针逆推" / "optional-top-prefix.spz2bp"
    top = prefix._report(top_path)
    closure = prefix._report(halves / "paired-prefix-scan")
    cursor = prefix._report(halves / "choose-cut")
    orientation = prefix._report(halves / "orient-cut")
    check = prefix._report(halves / "check-prefix")
    rows = root / "原层读取" / "read-five-rows.spz2bp"
    document, routes = prefix.build(root, rows, top_adapter=top, compact_results=True)
    part_platforms = {"prefix-scan-wiring": len(document["BP"]["Entries"])}
    initial = [prefix._channel(closure, "inputs", f"initial_h{i}") for i in range(4)]
    routed = routes["inputs"]["closure_initial"]
    rewired = {f"restore-seed-{pair}": dict(zip(initial[2 * pair:2 * pair + 2], routed[2 * pair:2 * pair + 2], strict=True))
               for pair in range(2)}
    reader = prefix._report(halves / "read-four-columns")
    reader_height = prefix._channel(reader["callee"], "inputs", "prefix_height")
    # 四列读取器的固定高度与总校验的选中列结果原来共用一个频道。
    private_height = 1701605
    rewired["read-four-columns"] = {reader_height: private_height}
    callees = {"read-four-columns": "read-prefix-column", "seed-two-halves": "seed-crystal-half"}
    for name in _PARTS:
        wiring = (_compact_caller(halves, name, callees[name]) if name in callees else
                  prefix._native_wiring(halves / f"{name}.spz2bp"))
        platforms = _rewire(wiring, rewired.get(name, {}), name)
        prefix._append(document, platforms)
        part_platforms[name] = len(platforms)
    top_board = prefix._native_wiring(top_path).platforms
    prefix._append(document, top_board)
    part_platforms[top_path.stem] = len(top_board)

    wiring = _local_wiring(document["BP"])
    receivers, senders = Counter(), Counter()
    for kind, config in _radio_ports(wiring):
        counts = receivers if kind == _RADIO_RECEIVER else senders
        counts[decode_constant(config["C"])] += 1
    duplicated = sorted(ch for ch, count in senders.items() if count != 1)
    if duplicated:
        raise ValueError(f"合装存在重复发射频道 {duplicated}")
    inputs = {name: prefix._channel(report, "inputs", port) for name, report, port in (
        ("target", orientation, "target"), ("enable", cursor, "enable"), ("optional_top", top, "optional"),
        ("column", check, "column"))}
    unconnected = sorted(set(receivers) - set(senders) - set(inputs.values()))
    if unconnected:
        raise ValueError(f"合装缺少频道来源 {unconnected}")
    if senders.keys() & set(inputs.values()):
        raise ValueError("合装内部发射与外部输入重叠")
    outputs = {name: prefix._channel(cursor, "outputs", name) for name in ("chosen", "exhausted", "alternate")}
    outputs["height"] = prefix._channel(check, "outputs", "height")
    outputs["heights"] = [prefix._channel(closure, "outputs", f"result_h{i}") for i in range(4)]
    report = {
        "inputs": inputs, "outputs": outputs,
        "top_adapter": {"raw_heights": routed, "raw_top_item": routes["layers"][0]["closure_item"],
                        "closure_initial": initial, "closure_top_item": prefix._channel(closure, "inputs", "item0")},
        "timing": {**routes["timing"], "top_adapter_hold_signal_ticks": top["settling"]["hold_signal_ticks"]},
        "column_reader_private_height": private_height,
        "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
        "part_platforms": part_platforms,
        "global_receivers": sum(receivers.values()), "global_transmitters": len(senders),
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="合装自动双切向与可选顶格闭包的原生蓝图")
    parser.add_argument("--circuits", required=True, type=Path, help="验收册的电路目录")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.circuits)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
