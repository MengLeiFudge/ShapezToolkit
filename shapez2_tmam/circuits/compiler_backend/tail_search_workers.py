"""合装尾部搜索的候选计算、静止格核对、递归准入和支撑扫描。"""

import argparse
from hashlib import sha256
from pathlib import Path

from ...mari.blueprint import Wiring
from ...mari.signals import decode_constant
from ..circuit import constant
from ..circuit_packing import stack_platforms
from ..factory_assembly.layout import _check_footprints
from ..local_module import Module
from . import _write_blueprint
from .auto_prefix_scan import _radio_ports
from .method_sequence import _radio_channels
from .module_caller import _RADIO_RECEIVER, _compare, _gate, _local_wiring
from .prefix_scan_wiring import _append, _native_wiring, _report
from .shared_support_scan import _SUPPORT


_NODE_ROWS = tuple(range(1705350, 1705355))
_PREFLIGHT = 1705330
_CHECKED, _LEGAL = 1705303, 1705304


def _without_scan(source: Wiring, support: Wiring, name: str, *, restored_inputs=None) -> Wiring:
    boundary = len(source.platforms) - len(support.platforms)
    if boundary <= 0:
        raise ValueError(f"{name} 缺少独立运算板与扫描板")
    suffix = source.platforms[boundary:]
    if restored_inputs:
        _rewire(Wiring({"Entries": suffix}), inputs=restored_inputs, outputs={}, name=name)
    shift = suffix[0].get("X", 0) - support.platforms[0].get("X", 0)
    if suffix != [{**board, "X": board.get("X", 0) + shift} for board in support.platforms]:
        raise ValueError(f"{name} 的末尾平台与指定 support-scan 不一致")
    return Wiring({"Entries": source.platforms[:boundary]})


def _rewire(wiring: Wiring, *, inputs: dict[int, int], outputs: dict[int, int], name: str) -> None:
    seen_inputs, seen_outputs = set(), set()
    for kind, config in _radio_ports(wiring):
        channel = decode_constant(config["C"])
        mapping, seen = (inputs, seen_inputs) if kind == _RADIO_RECEIVER else (outputs, seen_outputs)
        if channel in mapping:
            config["C"] = constant(mapping[channel])
            seen.add(channel)
    if seen_inputs != inputs.keys() or seen_outputs != outputs.keys():
        raise ValueError(f"{name} 找不到接点，收 {sorted(inputs.keys() - seen_inputs)}，发 {sorted(outputs.keys() - seen_outputs)}")


def _rows(sources: tuple[int, ...], targets: list[int]) -> Module:
    board = Module({f"row{i}": channel for i, channel in enumerate(sources)})
    for i, channel in enumerate(targets):
        board.outputs[_gate(board, "If", f"output{i}", f"row{i}", 1)] = channel
    return board


def _support_flags(s: dict, preflight: dict) -> Module:
    board = Module({"preflight": _PREFLIGHT, "s": s["enable"]})
    request = _compare(board, "request", "preflight", 1)
    board.outputs[request] = preflight["enable"]
    s_enabled = _compare(board, "s_enabled", "s", 1)
    for name, route, active in (("s", s, s_enabled), ("preflight", preflight, request)):
        board.outputs[_gate(board, "If", f"{name}_grounded", 1, active)] = route["grounded"]
        board.outputs[_gate(board, "If", f"{name}_required_top", 0, active)] = route["optional_top"]
    return board


def _preflight_reply(route: dict) -> Module:
    board = Module({"request": _PREFLIGHT, "done": route["done"], "accepted": route["accepted"]})
    enabled = _compare(board, "enabled", "request", 1)
    done = _gate(board, "And", "checked", enabled, "done")
    board.outputs = {done: _CHECKED, _gate(board, "And", "legal", done, "accepted"): _LEGAL}
    return board


def _route_outputs(old: dict, new: dict) -> dict[int, int]:
    return {**{old[k]: new[k] for k in ("enable", "grounded", "optional_top")},
            **dict(zip(old["rows"], new["rows"], strict=True))}


def _stack(path: Path, support: Wiring, scanner_rows: list[int], route: dict) -> tuple[Wiring, dict]:
    report = _report(path)
    original_rows = dict(zip(report["outputs"]["rows"], scanner_rows, strict=True))
    wiring = _without_scan(_native_wiring(path), support, path.name, restored_inputs=original_rows)
    start, done, ok = report["controls"]["support"]
    target = dict(zip(report["inputs"]["target_rows"], _NODE_ROWS, strict=True))
    _rewire(wiring, inputs={**target, done: route["done"], ok: route["accepted"]},
            outputs={start: route["enable"]}, name=path.name)
    return wiring, report


def _stationary(path: Path, support: Wiring, route: dict, reached: list[int]) -> tuple[Wiring, dict]:
    report = _report(path)
    if report["support_reached"] != reached:
        raise ValueError(f"{path.name} 的 Pin 可达行与共享扫描不一致")
    wiring = _without_scan(_native_wiring(path), support, path.name)
    _rewire(wiring, inputs={report["support_done"]: route["done"]},
            outputs=_route_outputs(report["support_inputs"], route), name=path.name)
    return wiring, report


def _descent(path: Path, route: dict, stationary: dict) -> tuple[Wiring, dict]:
    report = _report(path)
    if (report["inputs"]["request"] != stationary["outputs"]["descent_request"]
            or report["outputs"]["ready"] != stationary["inputs"]["descent_ready"]
            or report["outputs"]["ok"] != stationary["inputs"]["descent_ok"]):
        raise ValueError(f"{path.name} 的递归请求与静止格核对不匹配")
    wiring = _native_wiring(path)
    old = report["support"]
    inputs = {old["inputs"]["enable"]: route["enable"], old["outputs"]["done"]: route["done"],
              old["outputs"]["accepted"]: route["accepted"]}
    _rewire(wiring, inputs=inputs, outputs=_route_outputs(old["inputs"], route), name=path.name)
    return wiring, report


def build(*, s_search: Path, pin_stationary: Path, descent: Path, shared_scan: Path,
          support: Path = _SUPPORT) -> tuple[dict, dict]:
    common = _native_wiring(support)
    scan = _report(shared_scan)
    routes = scan["routes"]
    if not scan["includes_scan"] or set(routes) != {"s", "pin", "recursive_g", "preflight"}:
        raise ValueError("共享支撑蓝图须使用 --preflight 并包含原扫描")
    shared = _native_wiring(shared_scan)
    _without_scan(shared, common, shared_scan.name)
    s, s_report = _stack(s_search, common, scan["scanner"]["inputs"]["rows"], routes["s"])
    pin, pin_report = _stationary(pin_stationary, common, routes["pin"], scan["outputs"]["pin_reached_rows"])
    recursive, descent_report = _descent(descent, routes["recursive_g"], pin_report)
    preflight = routes["preflight"]
    glue = (_rows(tuple(s_report["outputs"]["rows"]), routes["s"]["rows"]), _rows(_NODE_ROWS, preflight["rows"]),
            _support_flags(routes["s"], preflight), _preflight_reply(preflight))
    platforms = [board.layout()["BP"]["Entries"][0] for board in glue]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    glue_count = len(platforms)
    for wiring in (s, pin, recursive, shared):
        _append(document, wiring.platforms)
    _check_footprints(platforms)
    wiring = _local_wiring(document["BP"])
    rx, tx = _radio_channels(wiring)
    duplicates = {channel: count for channel, count in tx.items() if count != 1}
    if duplicates:
        raise ValueError(f"尾部运算板有重复发射 {dict(sorted(duplicates.items()))}")
    links = {channel for route in routes.values()
             for channel in (*route["rows"], route["enable"], route["grounded"], route["optional_top"],
                             route["done"], route["accepted"])}
    links.remove(routes["pin"]["accepted"])
    unlinked = links - (rx.keys() & tx.keys())
    required = {_CHECKED, _LEGAL, s_report["outputs"]["ready"], s_report["outputs"]["exhausted"],
                pin_report["outputs"]["ready"], pin_report["outputs"]["ok"], scan["outputs"]["fault"]}
    if unlinked or not required <= tx.keys() or not {_PREFLIGHT, *_NODE_ROWS} <= rx.keys() - tx.keys():
        raise ValueError(f"尾部运算板缺少收发接点 {sorted(unlinked | (required - tx.keys()))}")
    report = {
        "inputs": {"node_rows": _NODE_ROWS, "preflight": _PREFLIGHT, "s_enable": s_report["inputs"]["enable"],
                   "s_reject": s_report["inputs"]["reject"], "s_limits": s_report["inputs"]["limits"],
                   "pin_request": pin_report["inputs"]["request"],
                   "pin_pushed_rows": descent_report["inputs"]["pushed_rows"]},
        "outputs": {"preflight_done": _CHECKED, "preflight_ok": _LEGAL, "s": s_report["outputs"],
                    "pin_ready": pin_report["outputs"]["ready"], "pin_ok": pin_report["outputs"]["ok"],
                    "support_fault": scan["outputs"]["fault"]},
        "support_routes": routes,
        "platforms_by_part": {"adapters": glue_count, "s_search": len(s.platforms), "pin_stationary": len(pin.platforms),
                              "descent": len(recursive.platforms), "shared_scan": len(shared.platforms)},
        "platforms": len(platforms), "building_entries": len(wiring.entries),
        "radio": {"duplicates": duplicates, "tx_channels": sorted(tx), "external_rx_channels": sorted(rx.keys() - tx.keys())},
        "parts": {name: {"file": path.name, "sha256": sha256(path.read_bytes()).hexdigest()} for name, path in
                  (("s_search", s_search), ("pin_stationary", pin_stationary), ("descent", descent),
                   ("shared_scan", shared_scan), ("support", support))},
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出共用扫描的尾部搜索运算蓝图")
    parser.add_argument("--s-search", required=True, type=Path, help="带原扫描的 S 搜索蓝图")
    parser.add_argument("--pin-stationary", required=True, type=Path, help="带原扫描的 Pin 静止格核对蓝图")
    parser.add_argument("--descent", required=True, type=Path, help="递归准入蓝图")
    parser.add_argument("--shared-scan", required=True, type=Path, help="四路共享扫描蓝图")
    parser.add_argument("--support", type=Path, default=_SUPPORT, help="作为拆分对照的原扫描蓝图")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(s_search=args.s_search, pin_stationary=args.pin_stationary,
                                 descent=args.descent, shared_scan=args.shared_scan, support=args.support)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，{report['platforms']} 块平台，{len(report['radio']['tx_channels'])} 条发射频道。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
