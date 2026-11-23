"""顶盖查询的触顶晶体删除与保留标签筛选。"""

import argparse
from copy import deepcopy
from pathlib import Path

from ...mari.blueprint import Wiring
from ...synthesis.physics import Shape
from ...synthesis.shape_methods import analyze_color, analyze_part, rotate_ccw, shape_literal
from ..compiler_backend import _write_blueprint
from ..compiler_backend.fields import compile_fields
from ..compiler_backend.module_caller import _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from . import compile_field_methods
from .pin_candidate_closure import _radio_ports, _rewire
from .pin_candidate_row import _RADIO, _read_report


_BASE = 1704300
_WINDOW = 100


def _row_reach(own: int, left: int, right: int, opposite: int,
               above: bool, above_left: bool, above_right: bool, above_opposite: bool) -> bool:
    l = left == 3
    r = right == 3
    return (own == 3) & (above | (l & above_left) | (r & above_right)
                        | ((opposite == 3) & (l | r) & above_opposite))


def down_q0(c0: int, c1: int, c2: int, c3: int, a0: bool, a1: bool, a2: bool, a3: bool) -> bool:
    return _row_reach(c0, c3, c1, c2, a0, a3, a1, a2)


def down_q1(c0: int, c1: int, c2: int, c3: int, a0: bool, a1: bool, a2: bool, a3: bool) -> bool:
    return _row_reach(c1, c0, c2, c3, a1, a0, a2, a3)


def down_q2(c0: int, c1: int, c2: int, c3: int, a0: bool, a1: bool, a2: bool, a3: bool) -> bool:
    return _row_reach(c2, c1, c3, c0, a2, a1, a3, a0)


def down_q3(c0: int, c1: int, c2: int, c3: int, a0: bool, a1: bool, a2: bool, a3: bool) -> bool:
    return _row_reach(c3, c2, c0, c1, a3, a2, a0, a1)


def up_q0(c0: int, c1: int, d0: bool, d1: bool, b0: bool, b1: bool) -> bool:
    # 行中新增分量至多是与向下结果相对的单格，只能从正下方接入。
    return d0 | ((c0 == 3) & b0)


def up_q1(c0: int, c1: int, d0: bool, d1: bool, b0: bool, b1: bool) -> bool:
    return d1 | ((c1 == 3) & b1)


def _crystal(row: Shape | None) -> bool:
    return analyze_part(row) == shape_literal("cu------")


def _preserved(source: Shape | None, target: Shape | None, deleted: bool) -> bool:
    return (not _crystal(target)) | ((not deleted) & _crystal(source)
                                     & (analyze_color(source) == analyze_color(target)))


def retained_row(source: Shape | None, target: Shape | None, d0: bool, d1: bool, d2: bool, d3: bool) -> bool:
    s1 = rotate_ccw(source)
    s2 = rotate_ccw(s1)
    s3 = rotate_ccw(s2)
    t1 = rotate_ccw(target)
    t2 = rotate_ccw(t1)
    t3 = rotate_ccw(t2)
    return (_preserved(source, target, d0) & _preserved(s1, t1, d1)
            & _preserved(s2, t2, d2) & _preserved(s3, t3, d3))


def ground_clear(target: Shape | None) -> bool:
    t1 = rotate_ccw(target)
    t2 = rotate_ccw(t1)
    t3 = rotate_ccw(t2)
    return not (_crystal(target) | _crystal(t1) | _crystal(t2) | _crystal(t3))


def _compile(methods, inputs):
    programs, _ = compile_field_methods(Path(__file__), methods)
    channels = iter(range(1, 1 + len(inputs) + len(methods)))
    source = {name: next(channels) for name in inputs}
    outputs = {name: next(channels) for name in methods}
    document, report = compile_fields(programs, input_channels=source, output_channels=outputs)
    return document, (*source.values(), *outputs.values()), report["settling"]["hold_signal_ticks"]


def _place_kernel(platforms, kernel, channels):
    document, ports, _ = kernel
    wiring = Wiring(deepcopy(document["BP"]))
    if len(wiring.platforms) != 1:
        raise ValueError("晶体行计算需要单平台布局")
    platforms.extend(_rewire(wiring, dict(zip(ports, channels, strict=True))))


def _cap(q, mask, deleted):
    board = Module({"mask": mask})
    board.lookup("mask", "bit", ((m, (m >> q) & 1) for m in range(16)))
    board.outputs = {"bit": deleted}
    return board


def _start(request, mask, rows_ready, phase):
    board = Module({"request": request, "mask": mask, "rows_ready": rows_ready})
    image = _compare(board, "image", "request", 1)
    rows = _compare(board, "rows_ready_bit", "rows_ready", 1)
    nonnegative = _compare(board, "nonnegative", "mask", 0, "Ag==")
    bounded = _compare(board, "bounded", "mask", 16, "BQ==")
    valid = _gate(board, "And", "valid", nonnegative, bounded)
    _gate(board, "And", "run", valid, _gate(board, "And", "read", image, rows))
    board.outputs = {"run": phase}
    return board


def _local_reply(phase, elapsed, results, ready, ok):
    board = Module({"phase": phase, "elapsed": elapsed, **{f"valid{i}": ch for i, ch in enumerate(results)}})
    _gate(board, "And", "ready", "phase", _compare(board, "settled", "elapsed", 1))
    valid = "ready"
    for i in range(len(results)):
        valid = _gate(board, "And", f"preserved{i}", valid, f"valid{i}")
    board.outputs = {"ready": ready, valid: ok}
    return board


def _forward_mode(request, ready, ok, want):
    board = Module({"request": request, "ready": ready, "ok": ok})
    image = _compare(board, "image", "request", 1)
    descent = _compare(board, "descent", "request", 2)
    forward = _gate(board, "And", "forward", image, _gate(board, "And", "passed", "ready", "ok"))
    _gate(board, "If", "mode", 1, forward)
    _gate(board, "If", "mode", 2, descent)
    board.outputs = {"mode": want}
    return board


def _relay(want, stored, rest_ready, rest_request):
    board = Module({"want": want, "stored": stored, "rest_ready": rest_ready})
    clear = _gate(board, "Or", "clear", _compare(board, "absent", "rest_ready", None),
                  _compare(board, "zero", "rest_ready", 0))
    same = _compare(board, "same", "want", "stored")
    set_mode = _gate(board, "Or", "set_mode", same, clear)
    _gate(board, "If", "hold", "want", set_mode)
    _gate(board, "If", "send", "want", same)
    board.outputs = {"hold": stored, "send": rest_request}
    return board


def _reply(request, local_ready, local_ok, rest_request, rest_ready, rest_ok, ready, ok):
    board = Module({"request": request, "local_ready": local_ready, "local_ok": local_ok,
                    "relayed": rest_request, "rest_ready": rest_ready, "rest_ok": rest_ok})
    image = _compare(board, "image", "request", 1)
    _gate(board, "And", "rejected", _gate(board, "And", "local_done", "local_ready", image),
          _compare(board, "bad_crystal", "local_ok", 0))
    live = _compare(board, "forwarded", "relayed", None, "Bg==")
    same = _compare(board, "same", "request", "relayed")
    returned = _compare(board, "returned", "rest_ready", 1)
    result_true = _compare(board, "true", "rest_ok", 1)
    result_false = _compare(board, "false", "rest_ok", 0)
    valid = _gate(board, "Or", "valid", result_true, result_false)
    forwarded = _gate(board, "And", "forwarded_done", live, same)
    answered = _gate(board, "And", "answered", forwarded, _gate(board, "And", "has_result", returned, valid))
    _gate(board, "Or", "ready", "rejected", answered)
    _gate(board, "If", "ok", 0, "rejected")
    _gate(board, "If", "ok", "rest_ok", _gate(board, "And", "pass_rest", answered,
          _gate(board, "Not", "not_local_reject", "rejected")))
    board.outputs = {"ready": ready, "ok": ok}
    return board


def build(plan: dict, channel_base: int = _BASE) -> tuple[dict, dict]:
    """导出纯方法编译的晶体计算板及顶盖过滤握手。"""
    pi, po = plan["inputs"], plan["outputs"]
    request, mask = po["filter_request"], po["mask"]
    reply_ready, reply_ok = pi["filter_ready"], pi["filter_ok"]
    materials = tuple(zip(*(lane["materials"] for lane in pi["columns"]), strict=True))
    window = range(channel_base, channel_base + _WINDOW)
    upstream = {member for row in materials for member in row} | {request, mask}
    replies = {reply_ready, reply_ok}
    if (len(materials) != 4 or len(upstream) != 18 or len(replies) != 2 or upstream & replies
            or (upstream | replies).intersection(window) or not 1 <= window[0] <= window[-1] < (1 << 24)):
        raise ValueError("顶盖接口或晶体板的预留频道无效")
    channels = iter(window)

    def take(n):
        return tuple(next(channels) for _ in range(n))

    source, target = take(4), take(5)
    rows_ready, rest_ready, rest_ok, rest_request, local_ready, local_ok = take(6)
    phase, want, relay = take(3)
    down = tuple(take(4) for _ in range(5))
    deleted = (down[0], *(take(4) for _ in range(3)), down[4])
    results = take(5)
    down_methods = {f"q{i}": f"down_q{i}" for i in range(4)}
    down_inputs = tuple(f"{prefix}{i}" for prefix in ("c", "a") for i in range(4))
    kernels = {
        "down": _compile(down_methods, down_inputs),
        "up": _compile({"q0": "up_q0", "q1": "up_q1"}, ("c0", "c1", "d0", "d1", "b0", "b1")),
        "retained": _compile({"ok": "retained_row"}, ("source", "target", "d0", "d1", "d2", "d3")),
        "ground": _compile({"ok": "ground_clear"}, ("target",)),
    }
    ticks = 4 * kernels["down"][2] + 3 * kernels["up"][2] + max(kernels[k][2] for k in ("retained", "ground"))
    steps = (ticks + _RADIO - 1) // _RADIO + 8
    timers, elapsed, _ = _wait_timer(phase, take(5), steps, steps)
    modules = [*(_cap(q, mask, ch) for q, ch in enumerate(down[-1])), _start(request, mask, rows_ready, phase),
               _local_reply(phase, elapsed, results, local_ready, local_ok), *timers,
               _forward_mode(request, local_ready, local_ok, want), _relay(want, relay, rest_ready, rest_request),
               _reply(request, local_ready, local_ok, rest_request, rest_ready, rest_ok, reply_ready, reply_ok)]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    for z, row in enumerate(materials):
        _place_kernel(platforms, kernels["down"], (*row, *down[z + 1], *down[z]))
        if z:
            for pair in (slice(0, 2), slice(2, 4)):
                _place_kernel(platforms, kernels["up"], (*row[pair], *down[z][pair], *deleted[z - 1][pair], *deleted[z][pair]))
        _place_kernel(platforms, kernels["retained"], (source[z], target[z + 1], *deleted[z], results[z + 1]))
    _place_kernel(platforms, kernels["ground"], (target[0], results[0]))
    entries = [{**board, "X": 4 * (i % 8), "Y": 4 * (i // 8)} for i, board in enumerate(platforms)]
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    senders = [ch for _, tx, ch, _ in _radio_ports(wiring) if tx]
    receivers = {ch for _, tx, ch, _ in _radio_ports(wiring) if not tx}
    external = upstream | {*source, *target, rows_ready, rest_ready, rest_ok}
    if (len(senders) != len(set(senders)) or set(senders) & external
            or receivers - set(senders) != external or set(senders) - set(window) != replies):
        raise ValueError("晶体板的原生收发频道与接口表不符")
    return document, {
        "inputs": {"request": request, "mask": mask, "source_materials": materials, "source_rows": source,
                   "target_rows": target, "rows_ready": rows_ready, "rest_ready": rest_ready, "rest_ok": rest_ok},
        "outputs": {"ready": reply_ready, "ok": reply_ok, "crystal_ready": local_ready, "crystal_ok": local_ok,
                    "rest_request": rest_request, "deleted": deleted},
        "channels": {"reserved_range": [window[0], window[-1]]},
        "timing": {"channel_signal_ticks": _RADIO, "crystal_hold_signal_ticks": steps * _RADIO},
        "kernels_hold_signal_ticks": {name: kernel[2] for name, kernel in kernels.items()},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main():
    parser = argparse.ArgumentParser(description="导出顶盖触顶晶体筛选与剩余过滤接线")
    parser.add_argument("plan", type=Path, help="顶盖参数板 JSON")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="私有首频道")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(_read_report(args.plan), args.channel_base), args.output)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
