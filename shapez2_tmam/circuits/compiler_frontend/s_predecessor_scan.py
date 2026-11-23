"""按非空格前缀枚举 S 前态，输出保持原层位的原色行。"""

import argparse
from enum import IntEnum
from pathlib import Path

from ...synthesis.physics import EMPTY, Rules, Shape
from ...synthesis.prefix_closure import close_stack_prefix
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from .pin_candidate_closure import _radio_ports
from .pin_candidate_row import _RADIO


_BASE = 1703400
_SETTLE_STEPS = 40


class _Phase(IntEnum):
    SETTLE = 0
    READY = 1
    STEP = 2
    EXHAUSTED = 3


def _prefixes(target, limits):
    rules = Rules()
    cells = rules.cells(target)
    columns = tuple(tuple((z, row[q]) for z, row in enumerate(target.layers) if row[q] != EMPTY)
                    for q in range(4))
    heights = [max((z + 1 for z, label in column if label[0] == "c"), default=0) for column in columns]
    close_stack_prefix(cells, heights, len(target.layers))
    lower = tuple(sum(z < height for z, _ in column) for column, height in zip(columns, heights, strict=True))
    upper = tuple(min(len(column), limit) for column, limit in zip(columns, limits, strict=True))
    return columns, lower, upper


def _count(enable, phase, step, count, status, low, high):
    board = Module({"enable": enable, "phase": phase, "step": step, "count": count})
    board.lookup("count", "incremented", ((n, n + 1) for n in range(5)))
    enabled = _compare(board, "enabled", "enable", 1)
    full = _compare(board, "full", "count", high)
    ticking = _compare(board, "ticking", "phase", int(_Phase.STEP))
    move = _gate(board, "And", "move", ticking, _compare(board, "carry", "step", 1))
    reset = _gate(board, "Not", "reset", enabled)
    wrap = _gate(board, "And", "wrap", move, full)
    load = _gate(board, "Or", "load", reset, wrap)
    _gate(board, "If", "value", low, load)
    _gate(board, "If", "value", "incremented", _gate(board, "And", "inc", enabled,
          _gate(board, "And", "inc_here", move, _gate(board, "Not", "space", full))))
    _gate(board, "If", "value", "count", _gate(board, "And", "hold", enabled,
          _gate(board, "Not", "no_step", move)))
    board.outputs = {"value": count, "full": status}
    return board


def _carry(statuses, steps, full):
    board = Module({f"full{q}": ch for q, ch in enumerate(statuses)})
    # q3 是 product 的最内层。只在所有右侧列达到上界时向左进位。
    carry = _gate(board, "If", "step3", 1, 1)
    for q in reversed(range(4)):
        board.outputs[carry] = steps[q]
        carry = _gate(board, "And", f"carry{q}", f"full{q}", carry)
    board.outputs[carry] = full
    return board


def _nonempty(counts, output):
    board = Module({f"count{q}": ch for q, ch in enumerate(counts)})
    filled = tuple(_compare(board, f"filled{q}", f"count{q}", 0, "Aw==") for q in range(4))
    board.outputs[_any(board, "nonempty", filled)] = output
    return board


def _control(enable, advance, phase, full, elapsed, nonempty, ready, exhausted, available):
    inputs = {"enable": enable, "phase": phase, "elapsed": elapsed}
    if available:
        inputs.update(advance=advance, full=full, nonempty=nonempty)
    board = Module(inputs)

    def match(name, value):
        return _compare(board, name, "phase", int(value))

    def both(name, left, right):
        return _gate(board, "And", name, left, right)

    def neg(name, signal):
        return _gate(board, "Not", name, signal)

    def select(value, signal):
        _gate(board, "If", "next", int(value), signal)

    enabled = _compare(board, "enabled", "enable", 1)
    settled = _compare(board, "settled", "elapsed", int(_Phase.SETTLE))
    waiting = match("settle", _Phase.SETTLE)
    pick = both("pick", waiting, settled)
    holding = match("ready", _Phase.READY)
    done = match("exhausted", _Phase.EXHAUSTED)
    if available:
        ack = _compare(board, "ack", "advance", 1)
        empty = neg("empty", "nonempty")
        arm = both("arm", "nonempty", neg("ack_low", ack))
        first = both("first", pick, arm)
        skip = both("skip", pick, empty)
        request = both("request", holding, ack)
        move = _gate(board, "Or", "move", skip, request)
        select(_Phase.STEP, both("step", enabled, both("next_item", move, neg("more", "full"))))
        finish = _gate(board, "Or", "finish", done, both("at_end", move, "full"))
        keep = both("keep", holding, "ack_low")
        visible = _gate(board, "Or", "visible", first, keep)
        select(_Phase.READY, both("show", enabled, visible))
        wait = both("wait", waiting, neg("stay", _gate(board, "Or", "leave", visible, move)))
    else:
        finish = _gate(board, "Or", "finish", done, pick)
        wait = both("wait", waiting, neg("stay", pick))
    select(_Phase.EXHAUSTED, both("end", enabled, finish))
    settle = _any(board, "settle_next", (neg("disabled", enabled), wait, match("step_done", _Phase.STEP)))
    select(_Phase.SETTLE, settle)
    board.outputs = {"next": phase, both("published", holding, enabled): ready,
                     both("depleted", done, enabled): exhausted}
    return board


def _row(counts, output, cells):
    board = Module({f"count{q}": counts[q] for q, _, _ in cells})
    labels = [EMPTY] * 4
    for q, rank, _ in cells:
        keep = _compare(board, f"keep{q}", f"count{q}", rank, "Ag==")
        _gate(board, "Not", f"drop{q}", keep)

    def select(index, mask):
        if index == len(cells):
            return Shape((tuple(labels),)) if mask else None
        q, _, label = cells[index]
        drop = select(index + 1, mask)
        labels[q] = label
        keep = select(index + 1, mask | (1 << q))
        labels[q] = EMPTY
        result = f"row{index}_{mask}"
        if drop is not None:
            _gate(board, "If", result, drop, f"drop{q}")
        return _gate(board, "If", result, keep, f"keep{q}")

    result = select(0, 0)
    if result is None:
        result = _gate(board, "If", "empty", None, 1)
    board.outputs = {result: output}
    return board


def build(target: Shape, limits=(5, 5, 5, 5), channel_base: int = _BASE) -> tuple[dict, dict]:
    """固定目标标签及前置上界，原生运行时逐个递增四列计数。"""
    target = Rules().parse(target.to_key())
    if len(limits) != 4 or any(type(limit) is not int or not 0 <= limit <= 5 for limit in limits):
        raise ValueError("需要四个 0～5 的非空格数上界")
    if not 1 <= channel_base <= (1 << 31) - 100:
        raise ValueError("首频道必须给后续 99 个频道留出空间")
    columns, lower, upper = _prefixes(target, limits)
    channels = iter(range(channel_base, channel_base + 100))
    enable, advance, ready, exhausted = (next(channels) for _ in range(4))
    rows = tuple(next(channels) for _ in range(5))
    counts = tuple(next(channels) for _ in range(4))
    phase, full, nonempty = (next(channels) for _ in range(3))
    statuses = tuple(next(channels) for _ in range(4))
    steps = tuple(next(channels) for _ in range(4))
    timers, elapsed, _ = _wait_timer(phase, tuple(next(channels) for _ in range(5)), _SETTLE_STEPS, _SETTLE_STEPS)
    available = all(low <= high for low, high in zip(lower, upper, strict=True))
    slots = {(z, q): (q, rank, label) for q, column in enumerate(columns)
             for rank, (z, label) in enumerate(column, 1)}
    modules = [
        _control(enable, advance, phase, full, elapsed, nonempty, ready, exhausted, available),
        _carry(statuses, steps, full), _nonempty(counts, nonempty), *timers,
        *(_count(enable, phase, step, count, status, low, high)
          for step, count, status, low, high in zip(steps, counts, statuses, lower, upper, strict=True)),
        *(_row(counts, output, [slots[z, q] for q in range(4) if (z, q) in slots]) for z, output in enumerate(rows)),
    ]
    entries = []
    for i, module in enumerate(modules):
        entry, = module.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 5), "Y": 3 * (i // 5)})
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    senders = [ch for _, transmitter, ch, _ in _radio_ports(wiring) if transmitter]
    receivers = {ch for _, transmitter, ch, _ in _radio_ports(wiring) if not transmitter}
    if (len(senders) != len(set(senders)) or receivers - set(senders) != ({enable, advance} if available else {enable})
            or set(senders) != set(range(ready, channel_base + 29))):
        raise ValueError("原生走线频道与四列枚举计划不符")
    return document, {
        "target": target.to_key(), "limits": limits, "lower": lower, "upper": upper,
        "inputs": {"enable": enable, "advance": advance},
        "outputs": {"ready": ready, "exhausted": exhausted, "rows": rows, "counts": counts},
        "channels": {"reserved_range": [channel_base, channel_base + 99], "phase": phase},
        "timing": {"radio_signal_ticks": _RADIO, "settle_signal_ticks": _SETTLE_STEPS * _RADIO,
                   "reset_hold_signal_ticks": _SETTLE_STEPS * _RADIO},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按目标重导 S 前态四列枚举器")
    parser.add_argument("target", help="原图短代码")
    parser.add_argument("--limits", type=int, nargs=4, default=(5, 5, 5, 5), metavar="COUNT",
                        help="按 q0～q3 给出非空格数上界，默认各列 5")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(Rules().parse(args.target), tuple(args.limits), args.channel_base), args.output)
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
