"""从五层原色信号生成 S 前态的保晶下界与候选。"""

import argparse
from pathlib import Path

from ...mari.blueprint import Wiring
from ...synthesis.physics import Rules
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from .pin_candidate_closure import _radio_ports, _rewire
from .pin_candidate_row import _RADIO, _read_blueprint
from .s_predecessor_scan import _carry, _control, _count, _nonempty


_BASE = 1703500
_WINDOW = 200
_RESET_TICKS = 4096
_SETTLE_STEPS = 136
_RULES = Rules()
_CRYSTAL = _RULES.parse("cu------")
_PIN = _RULES.parse("P-------")
_ASSETS = Path(__file__).resolve().parents[2] / "blueprints" / "验收" / "电路"


def _rotations(row, sources):
    board = Module({"row": row})
    board.gate("VirtualRotatorCCW", ("row",), ("q1",))
    board.gate("VirtualRotatorCCW", ("q1",), ("q2",))
    board.gate("VirtualRotator", ("row",), ("q3",))
    board.outputs = dict(zip(("q1", "q2", "q3"), sources, strict=True))
    return board


def _cell(z, label, count, previous, outputs):
    inputs = {"label": label, "count": count}
    if previous is not None:
        inputs.update(before=previous["rank"], seed=previous["seed"], below=previous["label"])
    board = Module(inputs)
    board.gate("VirtualAnalyzer", ("label",), ("part", "color"))
    occupied = _compare(board, "occupied", "part", None, "Bg==")
    before = "before" if previous is not None else 0
    seed = "seed" if previous is not None else 0
    if previous is None:
        _gate(board, "If", "rank", 1, occupied)
    else:
        board.lookup("before", "incremented", ((n, n + 1) for n in range(5)))
        _gate(board, "If", "rank", "incremented", occupied)
    vacant = _gate(board, "Not", "vacant", occupied)
    _gate(board, "If", "rank", before, vacant)
    crystal = _compare(board, "crystal", "part", _CRYSTAL)
    _gate(board, "If", "seed_height", z + 1, crystal)
    _gate(board, "If", "seed_height", seed, _gate(board, "Not", "other", crystal))
    keep_count = _compare(board, "keep_count", "count", "rank", "Ag==")
    _gate(board, "If", "kept", "label", keep_count)
    board.outputs = {"rank": outputs["rank"], "seed_height": outputs["seed"], "kept": outputs["kept"]}
    if z > 0:
        pin = _compare(board, "pin", "part", _PIN)
        plain = _gate(board, "And", "plain", occupied, _gate(board, "Not", "not_pin", pin))
        anchor = _compare(board, "anchor", "below", None, "Bg==")
        loose = _gate(board, "Not", "loose", anchor)
        for material, start in ((plain, 1), (pin, 3)):
            for condition, code in ((loose, start), (anchor, start + 1)):
                live = _gate(board, "And", f"state{code}", material, condition)
                _gate(board, "If", "state", code, live)
        board.outputs["state"] = outputs["state"]
    return board


def _new_cells(z, lanes, states, heights, outputs):
    board = Module({key + str(q): channels[q] for q in lanes
                    for key, channels in (("state", states), ("height", heights))})
    for q in lanes:
        fresh = _compare(board, f"fresh{q}", f"height{q}", z + 1, "BA==")
        board.outputs[_gate(board, "If", f"added{q}", f"state{q}", fresh)] = outputs[q]
    return board


def _close_height(z, lanes, added, heights, outputs):
    board = Module({**{f"added{q}": ch for q, ch in enumerate(added)},
                    **{f"height{q}": heights[q] for q in lanes}})
    loose = tuple(_compare(board, f"loose{q}", f"added{q}", 1) for q in range(4))
    anchor = tuple(_compare(board, f"anchor{q}", f"added{q}", 2) for q in range(4))
    # 与 addition_needs_lower 相同，整层都读取推进前的四个高度。
    for q in lanes:
        left, right, far = (q - 1) % 4, (q + 1) % 4, (q + 2) % 4
        near = _gate(board, "Or", f"near{q}", anchor[left], anchor[right])
        bridge = _gate(board, "Or", f"bridge{q}", loose[left], loose[right])
        via_bridge = _gate(board, "And", f"via_bridge{q}", anchor[far], bridge)
        supported = _gate(board, "Or", f"supported{q}", near, via_bridge)
        blocked = _gate(board, "Not", f"blocked{q}", supported)
        lower_plain = _gate(board, "And", f"lower_plain{q}", loose[q], blocked)
        lower_pin = _compare(board, f"lower_pin{q}", f"added{q}", 3)
        raise_height = _gate(board, "Or", f"raise{q}", lower_plain, lower_pin)
        _gate(board, "If", f"next{q}", z + 1, raise_height)
        _gate(board, "If", f"next{q}", f"height{q}", _gate(board, "Not", f"keep{q}", raise_height))
        board.outputs[f"next{q}"] = outputs[q]
    return board


def _bounds(ranks, height, limit, lower, upper, valid):
    board = Module({"height": height, "limit": limit, **{f"rank{i}": ch for i, ch in enumerate(ranks, 1)}})
    for i in range(6):
        selected = _compare(board, f"height{i}", "height", i)
        _gate(board, "If", "lower", f"rank{i}" if i else 0, selected)
    limited = _compare(board, "limited", "limit", "rank5", "BQ==")
    _gate(board, "If", "upper", "limit", limited)
    _gate(board, "If", "upper", "rank5", _gate(board, "Not", "all", limited))
    nonnegative = _compare(board, "nonnegative", "limit", 0, "Ag==")
    within_max = _compare(board, "within_max", "limit", 5, "BQ==")
    ordered = _compare(board, "ordered", "upper", "lower", "Ag==")
    _gate(board, "And", "valid", ordered, _gate(board, "And", "typed", nonnegative, within_max))
    board.outputs = {"lower": lower, "upper": upper, "valid": valid}
    return board


def _qualify(valid, raw_full, raw_nonempty, full, nonempty):
    board = Module({"full": raw_full, "nonempty": raw_nonempty, **{f"valid{q}": ch for q, ch in enumerate(valid)}})
    pair0 = _gate(board, "And", "pair0", "valid0", "valid1")
    pair1 = _gate(board, "And", "pair1", "valid2", "valid3")
    ok = _gate(board, "And", "ok", pair0, pair1)
    _gate(board, "Or", "stop", "full", _gate(board, "Not", "impossible", ok))
    _gate(board, "And", "nonempty_valid", "nonempty", ok)
    board.outputs = {"stop": full, "nonempty_valid": nonempty}
    return board


def _count_input(enable, phase, step, count, status, lower, upper):
    board = _count(enable, phase, step, count, status, "lower", "upper")
    board.inputs.update(lower=lower, upper=upper)
    return board


def build(channel_base: int = _BASE) -> tuple[dict, dict]:
    """把五层原色、四列目标上界和候选读口合装为独立原生蓝图。"""
    if type(channel_base) is not int or not 1 <= channel_base <= (1 << 24) - _WINDOW:
        raise ValueError("首频道须为整个预留段留出空间")
    channels = iter(range(channel_base, channel_base + _WINDOW))

    def take(n):
        return tuple(next(channels) for _ in range(n))

    enable, advance, ready, exhausted = take(4)
    target_rows, limits, rows, counts = take(5), take(4), take(5), take(4)
    phase, full, nonempty, raw_full, raw_nonempty = take(5)
    statuses, steps, lower, upper, valid = (take(4) for _ in range(5))
    timers, elapsed, _ = _wait_timer(phase, take(5), _SETTLE_STEPS, _SETTLE_STEPS)
    modules = [_control(enable, advance, phase, full, elapsed, nonempty, ready, exhausted, True),
               _carry(statuses, steps, raw_full), _nonempty(counts, raw_nonempty),
               _qualify(valid, raw_full, raw_nonempty, full, nonempty), *timers]
    parts = []
    cells = []
    for z, (source, row) in enumerate(zip(target_rows, rows, strict=True)):
        rotated = take(3)
        modules.append(_rotations(source, rotated))
        layer = []
        for q, rotated_row in enumerate((source, *rotated)):
            label, rank, seed, kept = take(4)
            cell = {"label": label, "rank": rank, "seed": seed, "kept": kept}
            if z > 0:
                cell["state"], = take(1)
            previous = cells[-1][q] if cells else None
            modules.append(_cell(z, label, counts[q], previous, cell))
            # 重用已编译的原色读格和拼行。无线口逐份重编号。
            parts.append(("双半形/read-labeled-corner", {1700620: rotated_row, 1700621: label}))
            layer.append(cell)
        cells.append(layer)
        parts.append(("顶针逆推/pin-source-row", dict(zip(range(1701560, 1701565),
                      (*(cell["kept"] for cell in layer), row), strict=True))))

    heights = tuple(cell["seed"] for cell in cells[-1])
    for z in range(4, 0, -1):
        added, next_heights = take(4), take(4)
        states = tuple(cell["state"] for cell in cells[z])
        for pair in ((0, 1), (2, 3)):
            modules.append(_new_cells(z, pair, states, heights, added))
            modules.append(_close_height(z, pair, added, heights, next_heights))
        heights = next_heights
    for q in range(4):
        ranks = tuple(layer[q]["rank"] for layer in cells)
        modules.append(_bounds(ranks, heights[q], limits[q], lower[q], upper[q], valid[q]))
        modules.append(_count_input(enable, phase, steps[q], counts[q], statuses[q], lower[q], upper[q]))

    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    for name, mapping in parts:
        asset = _read_blueprint(_ASSETS / f"{name}.spz2bp")
        platforms.extend(_rewire(Wiring(asset["BP"]), mapping))
    entries = [{**board, "X": 3 * (i % 9), "Y": 3 * (i // 9)} for i, board in enumerate(platforms)]
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    senders = [ch for _, tx, ch, _ in _radio_ports(wiring) if tx]
    receivers = {ch for _, tx, ch, _ in _radio_ports(wiring) if not tx}
    external = {enable, advance, *target_rows, *limits}
    if (len(senders) != len(set(senders)) or receivers - set(senders) != external
            or set(senders) & external or not {*rows, *counts, ready, exhausted} <= set(senders)):
        raise ValueError("动态 S 前态的原生收发频道与接口表不符")
    return document, {
        "inputs": {"enable": enable, "advance": advance, "rows": target_rows, "limits": limits},
        "outputs": {"ready": ready, "exhausted": exhausted, "rows": rows, "counts": counts},
        "channels": {"reserved_range": [channel_base, channel_base + _WINDOW - 1], "phase": phase,
                     "lower": lower, "upper": upper},
        "timing": {"radio_signal_ticks": _RADIO, "settle_signal_ticks": _SETTLE_STEPS * _RADIO,
                   "reset_hold_signal_ticks": _RESET_TICKS},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出读取五层原色和逐列上界的动态 S 前态枚举器")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(args.channel_base), args.output)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
