"""导出顶针逆像的静止格核对，并复用五层地面可达扫描。"""

import argparse
from pathlib import Path

from .compile_pair_writer import _one
from .compiler_backend import _write_blueprint
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _RADIO_TICKS, _compare, _gate, _local_wiring, _wait_timer
from .compiler_backend.prefix_scan_wiring import _append, _native_wiring, _report
from .compiler_frontend import FrontendError
from .compiler_frontend.pin_cap_crystals import _relay
from .local_module import Module


_DESCENT_READY, _DESCENT_OK, _DESCENT_REQUEST, _DESCENT_WANTED, _DESCENT_STORED = range(1704900, 1704905)
_IMAGE, _IMAGE_OK = 1704905, 1704908
_SETTLED = 1704910
_TIMERS = tuple(range(1704910, 1704915))
_LEVELS = tuple(range(1704921, 1704925))
_GROUND_MARK = 1704925
_LIVE_HALVES = tuple(range(1704930, 1704938))
_FIXED_HALVES = tuple(range(1704940, 1704948))
_FIXED_ROWS = (_GROUND_MARK, *range(1704951, 1704955))
_ROW_MATCHES = tuple(range(1704960, 1704965))


def _row_methods(crystal, landing, scan):
    source = crystal["inputs"]["source_materials"]
    target = crystal["inputs"]["target_rows"]
    deleted = crystal["outputs"]["deleted"]
    cursors = landing["outputs"]["cursors"]
    rows = scan["inputs"]["rows"]
    yield "ground", _one("pin_stationary_rows", "pin_stationary_ground", "row",
                         {f"m{q}": ch for q, ch in enumerate(source[0])}, rows[0])
    yield "ground_mark", _one("pin_stationary_rows", "pin_stationary_ground_mark", "row",
                              {f"m{q}": ch for q, ch in enumerate(source[0])}, _GROUND_MARK)
    for z in range(4):
        for i, side in enumerate(("front", "back")):
            q = i * 2
            index = z * 2 + i
            inputs = {"left": source[z][q], "right": source[z][q + 1],
                      "deleted_left": deleted[z][q], "deleted_right": deleted[z][q + 1]}
            yield "live_half", _one("pin_stationary_rows", "pin_live_half", "half", inputs, _LIVE_HALVES[index])
            yield "fixed_half", _one("pin_stationary_rows", f"pin_fixed_{side}", "half",
                                     {**inputs, "landing_left": cursors[z][q], "landing_right": cursors[z][q + 1],
                                      "height": _LEVELS[z], "target": target[z + 1]}, _FIXED_HALVES[index])
        front, back = _LIVE_HALVES[2 * z:2 * z + 2]
        yield "live_row", _one("pin_stationary_rows", "pin_live_row", "row", {"front": front, "back": back}, rows[z + 1])
        front, back = _FIXED_HALVES[2 * z:2 * z + 2]
        yield "fixed_row", _one("support_rows", "support_join_halves", "row",
                                {"front": front, "back": back}, _FIXED_ROWS[z + 1])


def _activate(request, scan):
    board = Module({"request": request, "settled": _SETTLED})
    image = _compare(board, "image", "request", 1)
    descent = _compare(board, "descent", "request", 2)
    run = _gate(board, "And", "run", image, _compare(board, "on_time", "settled", 1))
    board.outputs = {image: _IMAGE, run: scan["enable"],
                     _gate(board, "If", "grounded", 1, run): scan["grounded"],
                     _gate(board, "If", "required_top", 0, run): scan["optional_top"],
                     _gate(board, "If", "want_descent", 2, descent): _DESCENT_WANTED}
    return board


def _levels():
    board = Module({"image": _IMAGE})
    for z, channel in enumerate(_LEVELS, 1):
        board.outputs[_gate(board, "If", f"level{z}", z, "image")] = channel
    return board


def _match(expected, reached, output):
    board = Module({"expected": expected, "reached": reached})
    board.outputs = {_compare(board, "matched", "expected", "reached"): output}
    return board


def _image_ok():
    board = Module({f"pass{i}": channel for i, channel in enumerate(_ROW_MATCHES)})
    result = "pass0"
    for i in range(1, len(_ROW_MATCHES)):
        result = _gate(board, "And", f"through{i}", result, f"pass{i}")
    board.outputs = {result: _IMAGE_OK}
    return board


def _reply(request, scan_done, ready, ok):
    board = Module({"request": request, "image": _IMAGE, "done": scan_done, "matched": _IMAGE_OK,
                    "descent": _DESCENT_REQUEST, "descent_ready": _DESCENT_READY, "descent_ok": _DESCENT_OK})
    image_done = _gate(board, "And", "image_done", "image", _compare(board, "finished", "done", 1))
    descent = _gate(board, "And", "checking_descent", _compare(board, "want_descent", "request", 2),
                    _compare(board, "sent_descent", "descent", 2))
    descent_done = _gate(board, "And", "descent_done", descent, "descent_ready")
    _gate(board, "If", "answer", "matched", image_done)
    _gate(board, "If", "answer", "descent_ok", descent_done)
    board.outputs = {_gate(board, "Or", "ready", image_done, descent_done): ready, "answer": ok}
    return board


def build(crystal, landing, support, support_blueprint: Path | None):
    scan = support["inputs"]
    marked = support["outputs"]["reached_rows"]
    done = support["outputs"]["done"]
    request = landing["outputs"]["rest_request"]
    ready, ok = (landing["inputs"][name] for name in ("rest_ready", "rest_ok"))
    document = None
    holds = {}
    for name, (part, report) in _row_methods(crystal, landing, support):
        if document is None:
            document = part
        else:
            _append(document, part["BP"]["Entries"])
        hold = report["settling"]["hold_signal_ticks"]
        holds[name] = max(holds.get(name, 0), hold)
    settle = max(holds["ground"], holds["live_half"] + holds["live_row"],
                 holds["fixed_half"] + holds["fixed_row"]) + 4 * _RADIO_TICKS
    timer, _, _ = _wait_timer(_IMAGE, _TIMERS, (settle + _RADIO_TICKS - 1) // _RADIO_TICKS, 1)
    parts = (*timer, _activate(request, scan), _levels(), _image_ok(),
             *(_match(a, b, ch) for a, b, ch in zip(_FIXED_ROWS, marked, _ROW_MATCHES, strict=True)),
             _relay(_DESCENT_WANTED, _DESCENT_STORED, _DESCENT_READY, _DESCENT_REQUEST),
             _reply(request, done, ready, ok))
    for board in parts:
        _append(document, board.layout()["BP"]["Entries"])
    if support_blueprint is not None:
        _append(document, _native_wiring(support_blueprint).platforms)
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    if any(count != 1 for count in sent.values()):
        raise ValueError("顶针静止格合装含重复发射频道")
    return document, {"inputs": {"request": request, "descent_ready": _DESCENT_READY, "descent_ok": _DESCENT_OK},
                      "outputs": {"ready": ready, "ok": ok, "descent_request": _DESCENT_REQUEST,
                                  "support_activate": scan["enable"], "live": scan["rows"], "expected": _FIXED_ROWS},
                      "external_inputs": sorted(received.keys() - sent.keys()),
                      "support_inputs": scan, "support_reached": marked, "support_done": done,
                      "preparation_signal_ticks": settle, "platforms": len(wiring.platforms),
                      "building_entries": len(wiring.entries)}


def main() -> int:
    parser = argparse.ArgumentParser(description="导出地面可达的顶针静止格核对")
    parser.add_argument("crystal", type=Path, help="触顶晶体筛选的接口表")
    parser.add_argument("landing", type=Path, help="同列落点筛选的接口表")
    parser.add_argument("support", type=Path, help="K/G 支撑行扫描的接口表")
    parser.add_argument("--include-support", action="store_true", help="一并导入同名支撑扫描蓝图")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        blueprint = args.support.with_suffix(".spz2bp") if args.include_support else None
        _write_blueprint(*build(_report(args.crystal), _report(args.landing), _report(args.support), blueprint), args.output)
    except FrontendError as error:
        parser.error(f"{error.filename}:{error.lineno}:{error.offset} {error.msg}")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
