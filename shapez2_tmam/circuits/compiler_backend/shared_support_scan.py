"""在多路调用之间复用一件 K/G 支撑行扫描。"""

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .method_sequence import _radio_channels
from .module_caller import _RADIO_TICKS, _any, _check_channel, _compare, _gate, _local_wiring, _wait_timer
from .prefix_scan_wiring import _append, _native_wiring, _report


_SUPPORT = Path(__file__).resolve().parents[2] / "blueprints/验收/电路/顶针逆推/support-scan.spz2bp"
_NAMES = ("s", "pin", "recursive_g")
_PARAMS = ("grounded", "optional_top")
_FIELDS = ("enable", *_PARAMS, "rows", "done", "accepted")
_BASE, _LAST = 1705200, 1705299
_PREFLIGHT = 1705240
_FAULT, _SELECT, _ACTIVE = range(1705230, 1705233)
_TIMERS = tuple(range(1705233, 1705237))
_WARM_STEPS = 10


def _ports(base: int) -> dict:
    return {"enable": base, "grounded": base + 1, "optional_top": base + 2, "rows": tuple(range(base + 3, base + 8)),
            "done": base + 8, "accepted": base + 9}


def _data(ports: dict) -> tuple[int, ...]:
    return (*(ports[name] for name in _PARAMS), *ports["rows"])


def _routes(routes: Mapping | None, scan_channels: set[int], *, preflight: bool) -> tuple[dict, set[int], set[int]]:
    defaults = {name: _ports(_BASE + 10 * index) for index, name in enumerate(_NAMES)}
    if preflight:
        defaults["preflight"] = _ports(_PREFLIGHT)
    if routes is None:
        routes = defaults
    elif preflight and "preflight" not in routes:
        routes = {**routes, "preflight": defaults["preflight"]}
    if set(routes) != defaults.keys():
        raise ValueError(f"频道绑定须提供 {'、'.join(defaults)}")
    inputs, outputs, enables = set(), [], []
    for name in defaults:
        ports = routes[name]
        if set(ports) != set(_FIELDS) or len(ports["rows"]) != 5:
            raise ValueError(f"{name} 须提供 enable、grounded、optional_top、五行、done 和 accepted")
        enable = ports["enable"]
        incoming = (enable, *_data(ports))
        outgoing = (ports["done"], ports["accepted"])
        for channel in (*incoming, *outgoing):
            _check_channel(channel)
        inputs.update(incoming)
        outputs.extend(outgoing)
        enables.append(enable)
    reserved = {_FAULT, _SELECT, _ACTIVE, *_TIMERS} | scan_channels
    if (len(set(enables)) != len(enables) or len(set(outputs)) != len(outputs)
            or inputs.intersection(outputs) or reserved.intersection(inputs | set(outputs))):
        raise ValueError("各路 enable 须独占。回报、控制专用口和扫描频道须避免重叠")
    return {name: routes[name] for name in defaults}, inputs, set(outputs)


def _arbiter(enables: tuple[int, ...]) -> Module:
    board = Module({"previous": _SELECT, **{f"enable{i}": ch for i, ch in enumerate(enables)}})
    requests = tuple(_compare(board, f"request{i}", f"enable{i}", 1) for i in range(len(enables)))
    pairs = [(i - 1, i) for i in range(len(requests))]
    if len(requests) == 4:
        pairs.extend(((0, 2), (1, 3)))
    overlap = _any(board, "overlap", tuple(_gate(board, "And", f"pair{i}", requests[left], requests[right])
                                           for i, (left, right) in enumerate(pairs)))
    any_request = _any(board, "requests", requests)
    previous_fault = _compare(board, "previous_fault", "previous", -1)
    held = _gate(board, "And", "held_fault", previous_fault, any_request)
    fault = _gate(board, "Or", "fault", overlap, held)
    permitted = _gate(board, "Not", "permitted", fault)
    for owner, request in enumerate(requests, 1):
        _gate(board, "If", "owner", owner, _gate(board, "And", f"allow{owner}", request, permitted))
    _gate(board, "If", "owner", -1, fault)
    board.outputs = {"owner": _SELECT, fault: _FAULT}
    return board


def _select_data(sources: tuple[tuple[int, ...], ...], outputs: tuple[int, ...]) -> Module:
    board = Module({"owner": _SELECT, **{f"field{i}_{j}": channel for i, route in enumerate(sources, 1)
                                        for j, channel in enumerate(route)}})
    for owner in range(1, len(sources) + 1):
        selected = _compare(board, f"select{owner}", "owner", owner)
        for j in range(len(outputs)):
            _gate(board, "If", f"value{j}", f"field{owner}_{j}", selected)
    board.outputs = {f"value{j}": channel for j, channel in enumerate(outputs)}
    return board


def _start(mature: int, enable: int, done: int) -> Module:
    board = Module({"owner": _SELECT, "mature": mature, "previous": _ACTIVE, "done": done})
    selected = _compare(board, "selected", "owner", 0, "Aw==")
    elapsed = _compare(board, "elapsed", "owner", "mature")
    clear = _compare(board, "clear", "done", 0)
    continuing = _compare(board, "continuing", "previous", "owner")
    available = _gate(board, "Or", "available", clear, continuing)
    warmed = _gate(board, "And", "warmed", selected, elapsed)
    running = _gate(board, "And", "running", warmed, available)
    board.outputs = {running: enable, _gate(board, "If", "active", "owner", running): _ACTIVE}
    return board


def _reply(owner: int, route: dict, scanner: dict, mature: int) -> Module:
    board = Module({"owner": _SELECT, "active": _ACTIVE, "mature": mature, "done": scanner["done"],
                    "accepted": scanner["accepted"]})
    selected = _compare(board, "selected", "owner", owner)
    active = _compare(board, "active_route", "active", owner)
    warm = _compare(board, "warm", "mature", owner)
    matching = _gate(board, "And", "matching", selected, active)
    running = _gate(board, "And", "running", matching, warm)
    done = _gate(board, "And", "reply", running, _compare(board, "done_on", "done", 1))
    accepted = _compare(board, "accepted_on", "accepted", 1)
    board.outputs = {done: route["done"], _gate(board, "And", "passed", done, accepted): route["accepted"]}
    return board


def build(*, support: Path = _SUPPORT, routes: Mapping | None = None, include_scan: bool = True,
          preflight: bool = False) -> tuple[dict, dict]:
    scan = _report(support)
    scanner_in, scanner_out = scan["inputs"], scan["outputs"]
    warm_ticks = _WARM_STEPS * _RADIO_TICKS
    reset_ticks = scan["timing"]["reset_hold_signal_ticks"]
    if type(reset_ticks) is not int or not 0 < reset_ticks <= warm_ticks:
        raise ValueError(f"{support.name} 的复位等待须在 1～{warm_ticks} 个信号刻内")
    native = _native_wiring(support)
    scan_rx, scan_tx = _radio_channels(native)
    parameters = _data(scanner_in)
    scan_inputs = {scanner_in["enable"], *parameters}
    scan_outputs = {scanner_out["done"], scanner_out["accepted"], *scanner_out["reached_rows"]}
    if (len(parameters) != 7 or len(scan_inputs) != 8 or len(scanner_out["reached_rows"]) != 5
            or len(scan_outputs) != 7 or not scan_inputs <= scan_rx.keys() - scan_tx.keys()
            or any(count != 1 for count in scan_tx.values()) or not scan_outputs <= scan_tx.keys()
            or set(range(_BASE, _LAST + 1)).intersection(scan_rx.keys() | scan_tx.keys())):
        raise ValueError(f"{support.name} 的原生收发与扫描接口不符或占用 1705200～1705299")
    routes, input_channels, output_channels = _routes(routes, scan_rx.keys() | scan_tx.keys(), preflight=preflight)
    timers, mature, _ = _wait_timer(_SELECT, _TIMERS, _WARM_STEPS, _WARM_STEPS)
    ports = tuple(routes.values())
    data = tuple(map(_data, ports))
    # 每板最多十个无线口。四路时，两组数据加选择口会占用十一个。
    width = 1 if preflight else 2
    muxes = [_select_data(tuple(route[i:i + width] for route in data), parameters[i:i + width])
             for i in range(0, len(parameters), width)]
    modules = [_arbiter(tuple(p["enable"] for p in ports)), *muxes, *timers,
               _start(mature, scanner_in["enable"], scanner_out["done"]),
               *(_reply(i, route, scanner_out, mature) for i, route in enumerate(ports, 1))]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    switch_platforms = len(platforms)
    if include_scan:
        _append(document, native.platforms)
    wiring = _local_wiring(document["BP"])
    rx, tx = _radio_channels(wiring)
    required = output_channels | {_FAULT} | scan_inputs
    if (any(count != 1 for count in tx.values()) or not required <= tx.keys()
            or not input_channels <= rx.keys() - tx.keys()):
        raise ValueError("共享支撑扫描合装存在重复发射或缺少公开频道")
    report = {"routes": routes, "outputs": {"fault": _FAULT, "pin_reached_rows": scanner_out["reached_rows"]},
              "scanner": {"inputs": scanner_in, "outputs": scanner_out, "timing": scan["timing"]},
              "reserved_channels": [_BASE, _LAST], "includes_scan": include_scan,
              "timing": {"channel_signal_ticks": _RADIO_TICKS, "warm_hold_signal_ticks": warm_ticks,
                         "all_low_fault_clear_signal_ticks": 2 * _RADIO_TICKS},
              "switch_platforms": switch_platforms, "platforms": len(wiring.platforms),
              "building_entries": len(wiring.entries), "global_transmitters": len(tx)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出多路共用的 K/G 支撑行扫描")
    parser.add_argument("--support", type=Path, default=_SUPPORT, help="支撑扫描蓝图，读取同名 JSON 接口表")
    parser.add_argument("--routes", type=Path, help="包含 routes 对象的频道绑定 JSON")
    parser.add_argument("--preflight", action="store_true", help="增加第四路完整目标的 G 预检")
    parser.add_argument("--controller-only", action="store_true", help="只导出选择与回报板")
    parser.add_argument("--output", type=Path, required=True, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        routes = json.loads(args.routes.read_text(encoding="utf-8-sig"))["routes"] if args.routes else None
        document, report = build(support=args.support, routes=routes, include_scan=not args.controller_only,
                                 preflight=args.preflight)
        _write_blueprint(document, report, args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
