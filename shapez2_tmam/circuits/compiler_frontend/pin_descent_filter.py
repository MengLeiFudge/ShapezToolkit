"""顶针族模板的递归准入及可重绑的 G 扫描调用。"""

import argparse
from copy import deepcopy
from pathlib import Path

from ...mari.blueprint import Wiring
from ...synthesis.physics import Rules
from ..compiler_backend import _write_blueprint
from ..compiler_backend.fields import compile_fields
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from . import compile_method
from .pin_candidate_closure import _radio_ports, _rewire
from .pin_candidate_row import _RADIO, _read_report
from .pin_cap_crystals import _local_reply


_BASE = 1705100
_WINDOW = 100
_REQUEST, _READY, _OK = 1704902, 1704900, 1704901
_RULES = Rules()
_CRYSTAL = _RULES.parse("cu------")
_SYNTHESIS = Path(__file__).resolve().parents[2] / "synthesis"


def _port(report, direction, name):
    return report[direction][name]


def _kernel(path, method, names):
    program = compile_method(path.read_text(encoding="utf-8"), method, filename=str(path))
    inputs = dict(zip(names, range(1, 6), strict=True))
    document, report = compile_fields({"result": program}, input_channels=inputs, output_channels={"result": 6})
    return document, report["settling"]["hold_signal_ticks"]


def _clone(kernel, connections):
    wiring = Wiring(deepcopy(kernel[0]["BP"]))
    if len(wiring.platforms) != 1:
        raise ValueError("递归列判定需要单平台布局")
    return _rewire(wiring, dict(zip(range(1, 7), connections, strict=True)))[0]


def _active(request, mask, rows_ready, active):
    board = Module({"request": request, "mask": mask, "rows_ready": rows_ready})
    descent = _compare(board, "descent", "request", 2)
    rows = _compare(board, "rows", "rows_ready", 1)
    low = _compare(board, "low", "mask", 0, "Ag==")
    high = _compare(board, "high", "mask", 15, "BQ==")
    mask_valid = _gate(board, "And", "mask_valid", low, high)
    ready = _gate(board, "And", "ready", descent, rows)
    board.outputs = {_gate(board, "And", "active", ready, mask_valid): active}
    return board


def _template(mask, output):
    board = Module({"mask": mask})
    board.lookup("mask", "template", ((n, _RULES.parse("".join("cr" if n & (1 << q) else "Cu" for q in range(4))))
                                      for n in range(16)))
    board.outputs = {"template": output}
    return board


def _top_material(mask, q, output):
    board = Module({"mask": mask})
    # 对列 A，空顶格和普通顶格的判定等价。
    board.lookup("mask", "material", ((n, 3 if n & (1 << q) else 1) for n in range(16)))
    board.outputs = {"material": output}
    return board


def _has_crystal(row, output):
    board = Module({"row": row})
    cells = []
    for q in range(4):
        level = "row" if q == 0 else f"turned{q}"
        if q:
            board.gate("VirtualRotatorCCW", ("row" if q == 1 else f"turned{q - 1}",), (level,))
        board.gate("VirtualAnalyzer", (level,), (f"part{q}", f"color{q}"))
        cells.append(_compare(board, f"crystal{q}", f"part{q}", _CRYSTAL))
    board.outputs = {_any(board, "has_crystal", tuple(cells)): output}
    return board


def _lowest(flags, output):
    board = Module({f"row{z}": ch for z, ch in enumerate(flags)})
    no_lower = 1
    for z in range(5):
        found = _gate(board, "And", f"first{z}", no_lower, f"row{z}")
        _gate(board, "If", "lowest", z, found)
        clear = _gate(board, "Not", f"clear{z}", f"row{z}")
        no_lower = _gate(board, "And", f"empty_below{z}", no_lower, clear)
    _gate(board, "If", "lowest", 5, no_lower)
    board.outputs = {"lowest": output}
    return board


def _descent(source, pushed, output):
    board = Module({"source": source, "pushed": pushed})
    lower = _compare(board, "lower", "source", "pushed", "BA==")
    target_has_crystal = _compare(board, "target_has_crystal", "pushed", 4, "BQ==")
    board.outputs = {_gate(board, "And", "valid", lower, target_has_crystal): output}
    return board


def _column_limit(limit, output):
    board = Module({"limit": limit})
    board.outputs = {_compare(board, "possible", "limit", 0, "Ag=="): output}
    return board


def _all(inputs, output):
    board = Module({f"pass{i}": ch for i, ch in enumerate(inputs)})
    ok = "pass0"
    for i in range(1, len(inputs)):
        ok = _gate(board, "And", f"checked{i}", ok, f"pass{i}")
    board.outputs = {ok: output}
    return board


def _g_rows(active, rows, output):
    board = Module({"active": active, **{f"row{i}": ch for i, ch in enumerate(rows)}})
    for i, channel in enumerate(output):
        board.outputs[_gate(board, "If", f"expose{i}", f"row{i}", "active")] = channel
    return board


def _g_run(eligible, timer, done, enable, grounded, optional):
    board = Module({"eligible": eligible, "timer": timer, "done": done, "running": enable})
    passed = _compare(board, "elapsed", "timer", 1)
    clear = _compare(board, "cleared", "done", 0)
    can_start = _gate(board, "And", "can_start", passed, clear)
    ready = _gate(board, "Or", "owned", can_start, _compare(board, "holding", "running", 1))
    _gate(board, "And", "enable", "eligible", ready)
    _gate(board, "If", "grounded", 1, "eligible")
    _gate(board, "If", "optional", 1, "eligible")
    board.outputs = {"enable": enable, "grounded": grounded, "optional": optional}
    return board


def _reply(active, local_ready, local_ok, run, g_done, g_ok):
    board = Module({"active": active, "local_ready": local_ready, "local_ok": local_ok,
                    "run": run, "g_done": g_done, "g_ok": g_ok})
    fail = _compare(board, "local_fail", "local_ok", 0)
    failed = _gate(board, "And", "failed", "local_ready", fail)
    done = _compare(board, "done", "g_done", 1)
    valid = _gate(board, "Or", "valid_answer", _compare(board, "yes", "g_ok", 1), _compare(board, "no", "g_ok", 0))
    checked = _gate(board, "And", "checked", "run", _gate(board, "And", "answered", done, valid))
    ready = _gate(board, "And", "ready", "active", _gate(board, "Or", "complete", failed, checked))
    accepted = _gate(board, "And", "accepted", checked, _gate(board, "Not", "local_pass", failed))
    _gate(board, "If", "ok", 0, _gate(board, "And", "reject", "active", failed))
    _gate(board, "If", "ok", "g_ok", _gate(board, "And", "publish", "active", accepted))
    board.outputs = {ready: _READY, "ok": _OK}
    return board


def build(crystals: dict, support: dict | None = None, channel_base: int = _BASE) -> tuple[dict, dict]:
    """生成准入判定，按接口表调用支撑扫描。"""
    inputs = crystals["inputs"]
    source, pushed = tuple(inputs["source_rows"]), tuple(inputs["target_rows"])
    mask, rows_ready = inputs["mask"], inputs["rows_ready"]
    materials = tuple(tuple(row) for row in inputs["source_materials"])
    public_inputs = {_REQUEST, mask, rows_ready, *source, *pushed, *(ch for row in materials for ch in row)}
    window = range(channel_base, channel_base + _WINDOW)
    if (len(source) != 4 or len(pushed) != 5 or len(materials) != 4 or any(len(row) != 4 for row in materials)
            or len(public_inputs) != 28 or (public_inputs | {_READY, _OK}).intersection(window)
            or not 1 <= window[0] <= window[-1] < (1 << 24)):
        raise ValueError("递归准入的原色行、冻结材料或预留频道无效")
    channels = iter(window)

    def take(n):
        return tuple(next(channels) for _ in range(n))

    reset_ticks = 96
    support_sends = set()
    if support is None:
        enable, grounded, optional = take(3)
        rows = take(5)
        done, accepted = take(2)
    else:
        enable, grounded, optional = (_port(support, "inputs", name) for name in ("enable", "grounded", "optional_top"))
        rows = tuple(_port(support, "inputs", "rows"))
        done, accepted = (_port(support, "outputs", name) for name in ("done", "accepted"))
        support_sends = {enable, grounded, optional, *rows}
        ports = support_sends | {done, accepted}
        if (len(rows) != 5 or len(ports) != 10 or ports & (public_inputs | {_READY, _OK} | set(window))
                or any(type(ch) is not int or not 1 <= ch < (1 << 24) for ch in ports)):
            raise ValueError("G 扫描接口与递归准入频道冲突")
        reset_ticks = max(reset_ticks, support["timing"]["reset_hold_signal_ticks"])

    active, template = take(2)
    top, source_flags, pushed_flags = take(4), take(5), take(5)
    source_low, pushed_low, descent = take(3)
    column_a, base_limit, base_ok = take(4), take(4), take(4)
    all_a, all_base, local_ready, local_ok, eligible = take(5)
    a_kernel = _kernel(_SYNTHESIS / "column_rules.py", "column_admissible", ("z0", "z1", "z2", "z3", "z4"))
    base_kernel = _kernel(_SYNTHESIS / "pin_prefix.py", "pin_prefix_limit", ("ground", "z1", "z2", "z3", "z4"))
    settle_ticks = max(a_kernel[1], base_kernel[1]) + 768
    steps = (settle_ticks + _RADIO - 1) // _RADIO
    reset_steps = (reset_ticks + _RADIO - 1) // _RADIO + 2
    timers, elapsed, _ = _wait_timer(active, take(5), steps, steps)
    g_timers, g_elapsed, _ = _wait_timer(eligible, take(5), reset_steps, reset_steps)
    modules = [_active(_REQUEST, mask, rows_ready, active), _template(mask, template),
               *(_top_material(mask, q, top[q]) for q in range(4)),
               *(_has_crystal(row, flag) for row, flag in zip((*source, template), source_flags, strict=True)),
               *(_has_crystal(row, flag) for row, flag in zip(pushed, pushed_flags, strict=True)),
               _lowest(source_flags, source_low), _lowest(pushed_flags, pushed_low), _descent(source_low, pushed_low, descent),
               *(_column_limit(limit, ok) for limit, ok in zip(base_limit, base_ok, strict=True)),
               _all(column_a, all_a), _all(base_ok, all_base), *timers, *g_timers,
               _local_reply(active, elapsed, (all_a, all_base, descent), local_ready, local_ok),
               _all((local_ready, local_ok), eligible), _g_rows(active, source[:3], rows[:3]),
               _g_rows(active, (source[3], template), rows[3:]),
               _g_run(eligible, g_elapsed, done, enable, grounded, optional),
               _reply(active, local_ready, local_ok, enable, done, accepted)]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    for q, lower in enumerate(zip(*materials, strict=True)):
        platforms.append(_clone(a_kernel, (*lower, top[q], column_a[q])))
        platforms.append(_clone(base_kernel, (*lower, top[q], base_limit[q])))
    entries = [{**board, "X": 4 * (i % 7), "Y": 4 * (i // 7)} for i, board in enumerate(platforms)]
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    senders = [ch for _, tx, ch, _ in _radio_ports(wiring) if tx]
    receivers = {ch for _, tx, ch, _ in _radio_ports(wiring) if not tx}
    public_inputs.update((done, accepted))
    if (len(senders) != len(set(senders)) or set(senders) & public_inputs
            or receivers - set(senders) != public_inputs or set(senders) - set(window) != {_READY, _OK, *support_sends}):
        raise ValueError("递归准入的原生收发频道与接口表不符")
    return document, {
        "inputs": {"request": _REQUEST, "mask": mask, "rows_ready": rows_ready, "source_rows": source,
                   "source_materials": materials, "pushed_rows": pushed},
        "outputs": {"ready": _READY, "ok": _OK, "template_top": template, "source_lowest": source_low,
                    "pushed_lowest": pushed_low, "member_column_a": all_a, "pin_base_possible": all_base,
                    "strict_descent": descent, "local_ready": local_ready, "local_ok": local_ok},
        "support": {"inputs": {"enable": enable, "grounded": grounded, "optional_top": optional, "rows": rows},
                    "outputs": {"done": done, "accepted": accepted}},
        "channels": {"reserved_range": [window[0], window[-1]]},
        "timing": {"channel_signal_ticks": _RADIO, "local_hold_signal_ticks": steps * _RADIO,
                   "support_reset_signal_ticks": reset_steps * _RADIO},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出顶针族递归准入与 G 扫描接口")
    parser.add_argument("crystals", type=Path, help="触顶晶体筛选的 JSON 接口")
    parser.add_argument("--support", type=Path, help="直接绑定现有 G 扫描的 JSON 接口")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="私有频道首号")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        support = _read_report(args.support) if args.support is not None else None
        _write_blueprint(*build(_read_report(args.crystals), support, args.channel_base), args.output)
    except (KeyError, OSError, SyntaxError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
