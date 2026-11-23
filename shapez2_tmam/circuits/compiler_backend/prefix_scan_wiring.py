"""把原层读取、五行编码和双半形前缀闭包的公开端口接起来。"""

import argparse
import base64
import gzip
import json
from pathlib import Path

from ...mari.blueprint import Wiring, _kind
from ...mari.signals import decode_constant
from ..circuit import constant
from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .module_caller import (_RADIO_RECEIVER, _RADIO_TICKS, _RADIO_TRANSMITTER, _WAIT_RADIX,
                            _compare, _gate, _local_wiring, _wait_timer, build_calls)


_READ_CHANNELS = tuple(range(1701200, 1701205))
_PACK_BASE = 1701250
_PACK_INPUTS = {"row": 1701240, "below": 1701241, "ground": 1701242}
_START_PHASE = 1701270


def _report(path: Path) -> dict:
    return json.loads(path.with_suffix(".json").read_text(encoding="utf-8-sig"))


def _channel(report: dict, side: str, name: str) -> int:
    return report[side][name]["channel"]


def _append(document: dict, platforms: list[dict]) -> None:
    entries = document["BP"]["Entries"]
    shift = 3 + max(p.get("X", 0) for p in entries) - min(p.get("X", 0) for p in platforms)
    entries.extend({**p, "X": p.get("X", 0) + shift} for p in platforms)


def _native_wiring(path: Path) -> Wiring:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text.startswith("SHAPEZ2-4-") or not text.endswith("$"):
        raise ValueError(f"{path.name} 需要 SHAPEZ2-4 原生蓝图")
    bp = json.loads(gzip.decompress(base64.b64decode(text[10:-1], validate=True)))["BP"]
    return Wiring(bp)


def _pack_ports(path: Path) -> tuple[dict, list[dict]]:
    report = _report(path)
    wiring = _native_wiring(path)
    inputs = report["inputs"]
    replacements = {inputs[name]["channel"]: channel for name, channel in _PACK_INPUTS.items()}
    expected = set(replacements)
    seen = set()
    sent = set()
    for i, (_, entry) in enumerate(wiring.entries):
        if entry["T"] not in (_RADIO_RECEIVER, _RADIO_TRANSMITTER):
            continue
        (source, _), = wiring.sources(i, 0)
        config = wiring.entries[source][1]
        old = decode_constant(config["C"])
        if entry["T"] == _RADIO_RECEIVER and old in expected and old not in seen:
            if _kind(config) != "ConstantSignal":
                raise ValueError("行编码的公开频道必须由常量指定")
            config["C"] = constant(replacements[old])
            seen.add(old)
        elif entry["T"] == _RADIO_TRANSMITTER and old not in sent:
            sent.add(old)
        else:
            raise ValueError("行编码含重复或未声明的无线端口")
    if seen != expected or sent != {_channel(report, "outputs", "support")}:
        raise ValueError("行编码蓝图与接口表的公开端口不符")
    report["inputs"] = {name: {**port, "channel": _PACK_INPUTS[name]} for name, port in inputs.items()}
    report["reserved_channels"] = [replacements.get(ch, ch) for ch in report["reserved_channels"]]
    return report, wiring.platforms


def _read_rows(path: Path, target: int) -> tuple[list[dict], int]:
    report = _report(path)
    inputs = report["inputs"].values()
    outputs = report["outputs"].values()
    if ({(p["channel"], p["type"]) for p in inputs} != {(target, "shape")}
            or {(p["channel"], p["type"]) for p in outputs} != {(ch, "shape") for ch in _READ_CHANNELS}):
        raise ValueError("并行原层读取须接已换向目标，并将第 1～5 层输出到 1701200～1701204")
    wiring = _native_wiring(path)
    received = []
    sent = []
    for i, (_, entry) in enumerate(wiring.entries):
        if entry["T"] in (_RADIO_RECEIVER, _RADIO_TRANSMITTER):
            (source, _), = wiring.sources(i, 0)
            channel = decode_constant(wiring.entries[source][1]["C"])
            (received if entry["T"] == _RADIO_RECEIVER else sent).append(channel)
    if received != [target] or sorted(sent) != list(_READ_CHANNELS):
        raise ValueError("并行原层读取蓝图的原生频道与接口表不符")
    return wiring.platforms, report["settling"]["hold_signal_ticks"]


def _closure_links(items: list[tuple[int, int]], enable: int, pack_done: int, seed_done: int,
                   run: int, wait: int) -> list[dict]:
    inputs = {f"item{i}": source for i, (source, _) in enumerate(items)}
    publish = Module(inputs)
    for i, (_, target) in enumerate(items):
        out = _gate(publish, "If", f"published{i}", f"item{i}", 1)
        publish.outputs[out] = target

    ready = Module({"enable": enable, "rows": pack_done, "seed": seed_done})
    done = _gate(ready, "And", "both_done", _compare(ready, "rows_done", "rows", 1),
                 _compare(ready, "seed_done", "seed", 1))
    valid = _gate(ready, "And", "valid", done, _compare(ready, "enabled", "enable", 1))
    ready.outputs[valid] = _START_PHASE

    steps = (wait + _RADIO_TICKS - 1) // _RADIO_TICKS
    if not 1 <= steps <= _WAIT_RADIX ** 2:
        raise ValueError("闭包启动等待超出计数器范围")
    width = steps if steps <= 3 else 5 if steps > _WAIT_RADIX else 4
    timers, elapsed, _ = _wait_timer(_START_PHASE, tuple(range(_START_PHASE + 1, _START_PHASE + 1 + width)), steps, 1)
    start = Module({"eligible": _START_PHASE, "elapsed": elapsed})
    start.outputs[_gate(start, "And", "run", "eligible", _compare(start, "wait_met", "elapsed", 1))] = run

    platforms = [module.layout()["BP"]["Entries"][0] for module in (publish, ready, *timers, start)]
    stack_platforms(platforms)
    return platforms


def build(root: Path, read_path: Path) -> tuple[dict, dict]:
    halves = root / "双半形"
    orientation = _report(halves / "orient-cut")
    upstream = _report(halves / "read-four-columns")
    seed = _report(halves / "seed-two-halves")
    closure = _report(halves / "paired-prefix-scan")
    restores = [_report(halves / f"restore-seed-{pair}") for pair in range(2)]
    target = _channel(orientation, "outputs", "target")
    enable = _channel(upstream, "inputs", "enable")
    orientation_hold = orientation["settling"]["hold_signal_ticks"]
    read_boards, read_hold = _read_rows(read_path, target)
    if closure["round_values"] != [5, 4, 3, 2, 1]:
        raise ValueError("前缀闭包须按第 5 层到第 1 层扫描")
    layers = [*reversed(_READ_CHANNELS), None]

    pack_interface, pack_boards = _pack_ports(halves / "pack-prefix-row.spz2bp")
    calls = []
    for height, (row, below) in zip(range(5, 0, -1), zip(layers, layers[1:]), strict=True):
        calls.append({"row": {"channel": row}, "below": {"literal": None} if below is None else {"channel": below},
                      "ground": {"literal": height == 1}})
    doc, pack = build_calls(pack_interface, calls, _PACK_BASE, enable_channel=enable,
                            parameter_hold_signal_ticks=orientation_hold + read_hold)
    _append(doc, pack_boards)
    _append(doc, read_boards)

    run = _channel(closure, "inputs", "run")
    seed_done = _channel(seed, "outputs", "done")
    pack_done = _channel(pack, "outputs", "done")
    heights = [_channel(closure, "inputs", f"initial_h{i}") for i in range(4)]
    for pair, restore in enumerate(restores):
        if (_channel(restore, "inputs", "required") != seed["outputs"]["calls"][pair]["result_required"]["channel"]
                or [_channel(restore, "outputs", side) for side in ("left", "right")] != heights[pair * 2:pair * 2 + 2]):
            raise ValueError("恢复列序的端口与两半结果或闭包初值不符")
    wires = [(out["support"]["channel"], _channel(closure, "inputs", f"item{i}"))
             for i, out in enumerate(pack["outputs"]["calls"])]
    restore_wait = max(report["settling"]["hold_signal_ticks"] for report in restores)
    reset_wait = closure["timing"]["reset_hold_signal_ticks"]
    wait = restore_wait + reset_wait
    _append(doc, _closure_links(wires, enable, pack_done, seed_done, run, wait))
    wiring = _local_wiring(doc["BP"])
    transmitters = set()
    for i, (_, entry) in enumerate(wiring.entries):
        if entry["T"] == _RADIO_TRANSMITTER:
            (source, _), = wiring.sources(i, 0)
            channel = decode_constant(wiring.entries[source][1]["C"])
            if channel in transmitters:
                raise ValueError(f"频道 {channel} 有多个发送器")
            transmitters.add(channel)

    report = {
        "inputs": {"enable": enable, "oriented_target": target, "seed_done": seed_done, "closure_initial": heights},
        "outputs": {"pack_done": pack_done, "closure_run": run},
        "layers": [{"height": 5 - i, "row": layers[i], "below": layers[i + 1], "ground": i == 4,
                    "packed": source, "closure_item": destination} for i, (source, destination) in enumerate(wires)],
        "timing": {"orientation_hold_signal_ticks": orientation_hold,
                   "read_hold_signal_ticks": read_hold,
                   "first_pack_hold_signal_ticks": pack["timing"]["first_phase_hold_signal_ticks"],
                   "later_pack_hold_signal_ticks": pack["timing"]["phase_hold_signal_ticks"],
                   "restore_hold_signal_ticks": restore_wait,
                   "closure_reset_hold_signal_ticks": reset_wait,
                   "closure_wait_after_both_done_signal_ticks": ((wait + _RADIO_TICKS - 1) // _RADIO_TICKS) * _RADIO_TICKS,
                   "source_reset_hold_signal_ticks": max(pack["timing"]["reset_hold_signal_ticks"],
                                                        seed["timing"]["reset_hold_signal_ticks"]) + 6 * _RADIO_TICKS,
                   "closure_start_to_sample_signal_ticks": closure["timing"]["start_to_sample_signal_ticks"]},
        "channel_use": {"read": list(_READ_CHANNELS), "pack": pack["reserved_channels"],
                        "pack_inputs": _PACK_INPUTS, "transmitters": sorted(transmitters)},
        "platforms": len(wiring.platforms),
        "building_entries": len(wiring.entries),
    }
    return doc, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出原层读取、五行编码和双半形闭包的接线")
    parser.add_argument("--circuits", required=True, type=Path, help="验收册的电路目录")
    parser.add_argument("--rows", required=True, type=Path, help="五层原色并行读取蓝图，旁边须有同名接口表")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.circuits, args.rows)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
