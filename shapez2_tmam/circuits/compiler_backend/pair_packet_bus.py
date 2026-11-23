"""将四角制造方法的当前指令接入同一份配方写入接口。"""

import argparse
import json
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..factory_assembly.interface import FIELDS
from ..local_module import Module
from . import _write_blueprint
from .confirmed_call import build as build_confirmed_call
from .dense_write_bridge import build as build_write_bridge
from .module_caller import _check_channel, _compare, _gate, _local_wiring


_SOURCES = ("dense", "release", "join", "append")
_FIELDS = tuple(FIELDS)


def _select_fields(selector: int, sources: dict, outputs: dict) -> Module:
    inputs = {f"{source}_{field}": ports[field]
              for source, ports in sources.items() for field in outputs if field in ports}
    board = Module({"selector": selector, **inputs})
    for number, source in enumerate(_SOURCES, 1):
        available = [field for field in outputs if field in sources[source]]
        if not available:
            continue
        selected = _compare(board, f"use_{source}", "selector", number)
        for field in available:
            _gate(board, "If", field, f"{source}_{field}", selected)
    board.outputs = outputs
    return board


def build(reports: dict, selector: int, output_base: int) -> tuple[dict, dict]:
    sources = {name: {field: reports[name]["outputs"][field]["channel"]
                      for field in _FIELDS if field in reports[name]["outputs"]} for name in _SOURCES}
    for name, fields in sources.items():
        if any(field not in fields for field in _FIELDS[:4]):
            raise ValueError(f"{name} 缺少操作号、输入槽或目的槽")
    outputs = {field: output_base + index for index, field in enumerate(_FIELDS)}
    channels = [selector, *outputs.values(), *(ch for fields in sources.values() for ch in fields.values())]
    for channel in channels:
        _check_channel(channel)
    if len(channels) != len(set(channels)):
        raise ValueError("选择器、指令来源与写入频道须独占")
    groups = [(field,) for field in _FIELDS[:4]] + [_FIELDS[4:]]
    modules = [_select_fields(selector, sources, {field: outputs[field] for field in group})
               for group in groups]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    wiring = _local_wiring(document["BP"])
    report = {
        "inputs": {"selector": selector, "packets": sources},
        "outputs": {field: {"channel": channel, "type": "shape" if field == "base" else
                            "color" if field == "color" else "int"} for field, channel in outputs.items()},
        "selector_values": {source: i for i, source in enumerate(_SOURCES, 1)},
        "reserved_channels": sorted(channels),
        "platforms": len(wiring.platforms),
        "building_entries": len(wiring.entries),
    }
    return document, report


def _dispatch(selector):
    enabled = Module({"selector": selector, "run": 1701761, "operator": 1701760})
    can_run = _gate(enabled, "And", "can_run", "run", "operator")
    dense = _compare(enabled, "is_dense", "selector", 1)
    other = _gate(enabled, "And", "other", _compare(enabled, "is_packet", "selector", 2, "Ag=="),
                  _compare(enabled, "is_bounded", "selector", 4, "BQ=="))
    enabled.outputs = {_gate(enabled, "And", "dense", can_run, dense): 1701461,
                       _gate(enabled, "And", "packet", can_run, other): 1701741}

    request = Module({"dense": 1701482, "packet": 1701765, "dense_run": 1701461,
                      "packet_run": 1701741, "step": 1701710})
    _gate(request, "If", "request", "dense", "dense_run")
    _gate(request, "If", "request", "packet", "packet_run")
    request.outputs = {"request": 1701762, _gate(request, "If", "release_step", "step", "packet_run"): 1701661}

    reply = Module({"address": 1701763, "ack": 1701764, "dense_run": 1701461, "packet_run": 1701741,
                    "dense_done": 1701464, "packet_done": 1701746})
    _gate(reply, "If", "done", "dense_done", "dense_run")
    _gate(reply, "If", "done", "packet_done", "packet_run")
    reply.outputs = {"done": 1701766, _gate(reply, "If", "dense_address", "address", "dense_run"): 1701480,
                     _gate(reply, "If", "dense_ack", "ack", "dense_run"): 1701481}
    return (enabled, request, reply)


def attach_writer(document, bus, *, settle_ticks, update_ticks):
    opcode = bus["outputs"]["opcode"]["channel"]
    selector = bus["inputs"]["selector"]
    clock, clock_report = build_confirmed_call(
        enable=1701741, address=1701763, ack=1701764, finished=1701746, opcode=opcode,
        settled=1701742, has_packet=1701743, confirmed=1701744, request=1701765,
        states={"step": (1701710, 1701745, 0), "appended": (1701747, 1701748, 0)},
        settle_ticks=settle_ticks, update_ticks=update_ticks, channel_base=1701770,
    )
    ports = {**clock_report, "inputs": {**clock_report["inputs"], "enable": 1701760},
             "outputs": {**clock_report["outputs"], "request_address": 1701762}}
    bridge, bridge_report = build_write_bridge(ports, bus, 1701780)
    platforms = document["BP"]["Entries"]
    platforms.extend(board.layout()["BP"]["Entries"][0] for board in _dispatch(selector))
    for part in (clock, bridge):
        platforms.extend(part["BP"]["Entries"])
    stack_platforms(platforms)
    wiring = _local_wiring(document["BP"])
    return {**bus, "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
            "method_run": 1701761, "method_done": 1701766,
            "clock": clock_report, "write_bridge": bridge_report}


def main() -> int:
    parser = argparse.ArgumentParser(description="导出共用的制作配方选择板")
    for name in _SOURCES:
        parser.add_argument(f"--{name}", required=True, type=Path, help=f"{name} 指令接口表")
    parser.add_argument("--selector", required=True, type=int, help="指令来源选择频道")
    parser.add_argument("--output-base", required=True, type=int, help="首个输出字段频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    parser.add_argument("--settle-ticks", type=int, help="接实体写入，输入到配方稳定的信号刻数")
    parser.add_argument("--update-ticks", type=int, help="接实体写入，确认到下一状态稳定的信号刻数")
    args = parser.parse_args()
    try:
        reports = {name: json.loads(getattr(args, name).read_text(encoding="utf-8-sig")) for name in _SOURCES}
        document, report = build(reports, args.selector, args.output_base)
        if args.settle_ticks is not None or args.update_ticks is not None:
            if args.settle_ticks is None or args.update_ticks is None:
                raise ValueError("接实体写入须同时给出配方及状态稳定时间")
            report = attach_writer(document, report, settle_ticks=args.settle_ticks, update_ticks=args.update_ticks)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
