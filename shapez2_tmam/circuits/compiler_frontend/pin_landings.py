"""核对顶针逆像的非晶格落点、同组移动和落点下挡。"""

import argparse
from copy import deepcopy
from pathlib import Path

from ...mari.blueprint import Wiring
from ...synthesis.physics import Shape
from ...synthesis.shape_methods import analyze_color, analyze_part, rotate_ccw, shape_literal
from ..compiler_backend import _write_blueprint
from ..compiler_backend.fields import compile_fields
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _wait_digit, _WAIT_RADIX
from ..local_module import Module
from .pin_candidate_closure import _radio_ports, _rewire
from .pin_candidate_row import _RADIO, _read_report
from . import compile_field_methods
from .pin_cap_crystals import _forward_mode, _local_reply, _relay, _reply


_BASE = 1704500
_WINDOW = 100


def _kind(row: Shape | None) -> int:
    part = analyze_part(row)
    if part is None:
        return 0
    if part == shape_literal("P-------"):
        return 2
    if part == shape_literal("cu------"):
        return 3
    return 1


def target_q0(row: Shape | None) -> int:
    return _kind(row)


def target_q1(row: Shape | None) -> int:
    return _kind(rotate_ccw(row))


def target_q2(row: Shape | None) -> int:
    return _kind(rotate_ccw(rotate_ccw(row)))


def target_q3(row: Shape | None) -> int:
    return _kind(rotate_ccw(rotate_ccw(rotate_ccw(row))))


def _land(level: int, ceiling: int, barrier: int) -> int:
    if (level > ceiling) | (level < barrier):
        return -2
    return level


def next_landing(material: int, cursor: int, height: int, c0: int, c1: int, c2: int, c3: int, c4: int) -> int:
    if cursor < -1:
        return -2
    if (material != 1) & (material != 2):
        return cursor
    barrier = 0
    if c1 == 3:
        barrier = 1
    if (c2 == 3) & (height >= 2):
        barrier = 2
    if (c3 == 3) & (height >= 3):
        barrier = 3
    if (c4 == 3) & (height >= 4):
        barrier = 4
    if (cursor < 0) & (c0 == 1):
        return _land(0, height, barrier)
    if (cursor < 1) & ((c1 == 1) | (c1 == 2)):
        return _land(1, height, barrier)
    if (cursor < 2) & ((c2 == 1) | (c2 == 2)):
        return _land(2, height, barrier)
    if (cursor < 3) & ((c3 == 1) | (c3 == 2)):
        return _land(3, height, barrier)
    if (cursor < 4) & ((c4 == 1) | (c4 == 2)):
        return _land(4, height, barrier)
    return -2


def _row_at(z: int, t0: Shape | None, t1: Shape | None, t2: Shape | None,
            t3: Shape | None, t4: Shape | None) -> Shape | None:
    if z == 0:
        return t0
    if z == 1:
        return t1
    if z == 2:
        return t2
    if z == 3:
        return t3
    return t4


def _label_matches(source: Shape | None, target: Shape | None, material: int, landing: int) -> int:
    if (material != 1) & (material != 2):
        return landing
    if (landing < 0) | (analyze_part(source) != analyze_part(target)) | (analyze_color(source) != analyze_color(target)):
        return -2
    return landing


def label_q0(source: Shape | None, t0: Shape | None, t1: Shape | None, t2: Shape | None,
             t3: Shape | None, t4: Shape | None, material: int, landing: int) -> int:
    return _label_matches(source, _row_at(landing, t0, t1, t2, t3, t4), material, landing)


def label_q1(source: Shape | None, t0: Shape | None, t1: Shape | None, t2: Shape | None,
             t3: Shape | None, t4: Shape | None, material: int, landing: int) -> int:
    target = _row_at(landing, t0, t1, t2, t3, t4)
    return _label_matches(rotate_ccw(source), rotate_ccw(target), material, landing)


def label_q2(source: Shape | None, t0: Shape | None, t1: Shape | None, t2: Shape | None,
             t3: Shape | None, t4: Shape | None, material: int, landing: int) -> int:
    target = _row_at(landing, t0, t1, t2, t3, t4)
    return _label_matches(rotate_ccw(rotate_ccw(source)), rotate_ccw(rotate_ccw(target)), material, landing)


def label_q3(source: Shape | None, t0: Shape | None, t1: Shape | None, t2: Shape | None,
             t3: Shape | None, t4: Shape | None, material: int, landing: int) -> int:
    target = _row_at(landing, t0, t1, t2, t3, t4)
    return _label_matches(rotate_ccw(rotate_ccw(rotate_ccw(source))),
                          rotate_ccw(rotate_ccw(rotate_ccw(target))), material, landing)


def _missing_support(cell: int, left: int, right: int, far: int) -> bool:
    # 与 addition_needs_lower 的四列支撑规则一致。
    near = (left == 2) | (right == 2)
    bridge = (left == 1) | (right == 1)
    return (cell == 3) | ((cell == 1) & (not near) & (not ((far == 2) & bridge)))


def _plain(state: int) -> bool:
    return (state == 1) | (state == 2) | (state == 5)


def moving_blocks_supported(a: int, b: int, c: int, d: int, la: int, lb: int, lc: int, ld: int) -> bool:
    pa = _plain(a)
    pb = _plain(b)
    pc = _plain(c)
    pd = _plain(d)
    unequal = ((pa & pb & (la != lb)) | (pb & pc & (lb != lc))
               | (pc & pd & (lc != ld)) | (pd & pa & (ld != la)))
    return not (unequal | _missing_support(a, d, b, c) | _missing_support(b, a, c, d)
                | _missing_support(c, b, d, a) | _missing_support(d, c, a, b))


def _compile(methods, inputs):
    programs, _ = compile_field_methods(Path(__file__), methods)
    source = dict(zip(inputs, range(1, len(inputs) + 1), strict=True))
    outputs = dict(zip(methods, range(len(inputs) + 1, len(inputs) + len(methods) + 1), strict=True))
    document, report = compile_fields(programs, input_channels=source, output_channels=outputs)
    return document, (*source.values(), *outputs.values()), report["settling"]["hold_signal_ticks"]


def _place_kernel(groups, kernel, channels):
    document, ports, _ = kernel
    wiring = Wiring(deepcopy(document["BP"]))
    groups.append(_rewire(wiring, dict(zip(ports, channels, strict=True))))


def _constants(before, heights):
    board = Module({})
    for value, output in zip((-1, 1, 2, 3, 4), (before, *heights), strict=True):
        board.outputs[_gate(board, "If", f"value{value}", value, 1)] = output
    return board


def _column_check(classes, first, cursor, output):
    board = Module({**{f"c{z}": ch for z, ch in enumerate(classes)}, "first": first, "cursor": cursor})
    target_pin = _compare(board, "target_pin", "c0", 2)
    occupied = _compare(board, "occupied", "first", 0, "Aw==")
    same = _compare(board, "same", target_pin, occupied)
    left = []
    for z in range(5):
        material = _compare(board, f"normal{z}", f"c{z}", 1)
        if z:
            needle = _compare(board, f"needle{z}", f"c{z}", 2)
            material = _gate(board, "Or", f"npc{z}", material, needle)
        further = _compare(board, f"further{z}", "cursor", z, "BA==")
        left.append(_gate(board, "And", f"unused{z}", material, further))
    finished = _gate(board, "Not", "finished", _any(board, "extra", tuple(left)))
    legal = _compare(board, "legal", "cursor", -1, "Ag==")
    board.outputs = {_gate(board, "And", "valid", same, _gate(board, "And", "matched", legal, finished)): output}
    return board


def _support(material, landing, raised, classes, output):
    board = Module({"material": material, "landing": landing, **{f"below{z}": ch for z, ch in enumerate(classes[:4])}})
    anchors = [_compare(board, "ground", "landing", 0)]
    for z in range(4):
        at = _compare(board, f"at{z}", "landing", z + 1)
        occupied = _compare(board, f"occupied{z}", f"below{z}", 0, "Aw==")
        anchors.append(_gate(board, "And", f"has_below{z}", at, occupied))
    stable = _any(board, "supported", tuple(anchors))
    loose = _gate(board, "Not", "loose", stable)
    moving = _compare(board, "moving", "landing", raised, "BA==")
    for value, base in ((1, 1), (2, 3)):
        kind = _compare(board, f"kind{value}", "material", value)
        present = _gate(board, "And", f"moving{value}", moving, kind)
        _gate(board, "If", "state", base, _gate(board, "And", f"floating{value}", present, loose))
        _gate(board, "If", "state", base + 1, _gate(board, "And", f"anchored{value}", present, stable))
    plain = _compare(board, "plain", "material", 1)
    fixed = _gate(board, "Not", "fixed", moving)
    _gate(board, "If", "state", 5, _gate(board, "And", "fixed_plain", plain, fixed))
    board.outputs = {"state": output}
    return board


def _checks(inputs, output):
    board = Module({f"ok{i}": ch for i, ch in enumerate(inputs)})
    valid = "ok0"
    for i in range(1, len(inputs)):
        valid = _gate(board, "And", f"checked{i}", valid, f"ok{i}")
    board.outputs[valid] = output
    return board


def _start(request, rows_ready, phase):
    board = Module({"request": request, "rows_ready": rows_ready})
    image = _compare(board, "image", "request", 1)
    ready = _compare(board, "ready", "rows_ready", 1)
    board.outputs[_gate(board, "And", "start", image, ready)] = phase
    return board


def _timers(phase, take, ticks):
    modules = []
    stages = []
    remaining = (ticks + _RADIO - 1) // _RADIO + 8
    while remaining:
        step = min(remaining, _WAIT_RADIX ** 2 - 1)
        stamp, low, high, elapsed = take(4)
        modules.extend((_wait_digit(phase, stamp, low, high), _wait_digit(phase, stamp, high, low, high=True)))
        tap = Module({"phase": phase, "stamp": stamp, "low": low, "high": high})
        upper, lower = divmod(step - 1, _WAIT_RADIX)
        same = _compare(tap, "same", "phase", "stamp")
        equal = _compare(tap, "upper", "high", upper)
        above = _compare(tap, "above", "high", upper, "Aw==")
        reached = _compare(tap, "low_reached", "low", lower, "Ag==")
        threshold = _gate(tap, "Or", "threshold", above, _gate(tap, "And", "bottom", equal, reached))
        timed = _gate(tap, "And", "timed", same, threshold)
        tap.outputs = {_gate(tap, "If", "out", "phase", timed): elapsed}
        modules.append(tap)
        stages.append(elapsed)
        phase = elapsed
        remaining -= step
    return modules, stages[-1]


def build(crystals: dict, channel_base: int = _BASE) -> tuple[dict, dict]:
    ci, co = crystals["inputs"], crystals["outputs"]
    request, rows_ready = co["rest_request"], ci["rows_ready"]
    ready, ok = ci["rest_ready"], ci["rest_ok"]
    source, target = tuple(ci["source_rows"]), tuple(ci["target_rows"])
    mats = tuple(tuple(row) for row in ci["source_materials"])
    external = {request, rows_ready, *source, *target, *(p for row in mats for p in row)}
    window = range(channel_base, channel_base + _WINDOW)
    if (len(source) != 4 or len(target) != 5 or len(mats) != 4 or any(len(row) != 4 for row in mats)
            or len(external) != 27 or len({ready, ok}) != 2 or external & {ready, ok}
            or (external | {ready, ok}).intersection(window) or not 1 <= window[0] <= window[-1] < (1 << 24)):
        raise ValueError("晶体接口或落点板预留频道不兼容")
    channels = iter(window)

    def take(n):
        return tuple(next(channels) for _ in range(n))

    rest_ready, rest_ok, rest_request, local_ready, local_ok, phase, want, stored = take(8)
    before, *heights = take(5)
    classes = tuple(take(4) for _ in range(5))
    choices = tuple(take(4) for _ in range(4))
    cursors = tuple(take(4) for _ in range(4))
    states = tuple(take(4) for _ in range(4))
    columns, supported = take(4), take(4)
    columns_ok, support_ok = take(2)
    classes_kernel = _compile({f"q{i}": f"target_q{i}" for i in range(4)}, ("row",))
    pick = _compile({"landing": "next_landing"}, ("material", "cursor", "height", "c0", "c1", "c2", "c3", "c4"))
    labels = tuple(_compile({"cursor": f"label_q{q}"}, ("source", "t0", "t1", "t2", "t3", "t4", "material", "landing"))
                   for q in range(4))
    support = _compile({"ok": "moving_blocks_supported"}, ("a", "b", "c", "d", "la", "lb", "lc", "ld"))
    settle = classes_kernel[2] + 4 * (pick[2] + max(kernel[2] for kernel in labels)) + support[2] + 1536
    timers, elapsed = _timers(phase, take, settle)
    modules = [_start(request, rows_ready, phase), _constants(before, heights), *timers,
               _checks(columns, columns_ok), _checks(supported, support_ok),
               _local_reply(phase, elapsed, (columns_ok, support_ok), local_ready, local_ok),
               _forward_mode(request, local_ready, local_ok, want), _relay(want, stored, rest_ready, rest_request),
               _reply(request, local_ready, local_ok, rest_request, rest_ready, rest_ok, ready, ok)]
    for q, column in enumerate(zip(*classes, strict=True)):
        modules.append(_column_check(column, mats[0][q], cursors[-1][q], columns[q]))
        for r in range(4):
            modules.append(_support(mats[r][q], cursors[r][q], r + 1, column, states[r][q]))
    platforms = [module.layout()["BP"]["Entries"] for module in modules]
    for channel, row in zip(target, classes, strict=True):
        _place_kernel(platforms, classes_kernel, (channel, *row))
    for r, channel in enumerate(source):
        for q, column in enumerate(zip(*classes, strict=True)):
            previous = before if r == 0 else cursors[r - 1][q]
            _place_kernel(platforms, pick, (mats[r][q], previous, heights[r], *column, choices[r][q]))
            _place_kernel(platforms, labels[q], (channel, *target, mats[r][q], choices[r][q], cursors[r][q]))
        _place_kernel(platforms, support, (*states[r], *cursors[r], supported[r]))
    entries = []
    for i, group in enumerate(platforms):
        x = min(board.get("X", 0) for board in group)
        y = min(board.get("Y", 0) for board in group)
        entries.extend({**board, "X": board.get("X", 0) - x + 8 * (i % 6),
                        "Y": board.get("Y", 0) - y + 8 * (i // 6)} for board in group)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    senders = [ch for _, tx, ch, _ in _radio_ports(wiring) if tx]
    receivers = {ch for _, tx, ch, _ in _radio_ports(wiring) if not tx}
    external.update((rest_ready, rest_ok))
    if (len(senders) != len(set(senders)) or set(senders) & external
            or receivers - set(senders) != external or set(senders) - set(window) != {ready, ok}):
        raise ValueError("落点板的原生收发频道与接口表不符")
    return document, {
        "inputs": {"request": request, "rows_ready": rows_ready, "source_rows": source, "target_rows": target,
                   "source_materials": mats, "rest_ready": rest_ready, "rest_ok": rest_ok},
        "outputs": {"ready": ready, "ok": ok, "landing_ready": local_ready, "landing_ok": local_ok,
                    "rest_request": rest_request, "cursors": cursors, "columns_ok": columns_ok,
                    "blocks_ok": support_ok},
        "channels": {"reserved_range": [window[0], window[-1]]},
        "timing": {"channel_signal_ticks": _RADIO, "settling_budget_ticks": settle},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出顶针逆像的非晶格落点筛选")
    parser.add_argument("crystals", type=Path, help="触顶晶体筛选 JSON 接口")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="预留频道首号")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(_read_report(args.crystals), args.channel_base), args.output)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
