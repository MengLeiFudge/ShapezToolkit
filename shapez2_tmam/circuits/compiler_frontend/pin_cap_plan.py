"""为单次顶针层搜索枚举合法顶盖族与成员。"""

import argparse
from enum import IntEnum
from pathlib import Path

from ...mari.blueprint import Wiring
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from .pin_candidate_closure import _radio_ports, _rewire
from .pin_candidate_row import _in_phases, _RADIO, _read_blueprint, _read_report
from .s_predecessor_scan import _Phase as _ScanPhase, _carry, _count


_BASE = 1703740
_WINDOW = 100
_SETTLE_STEPS = 136
_ASSETS = Path(__file__).resolve().parents[2] / "blueprints" / "验收" / "电路" / "顶针逆推"


class _Phase(IntEnum):
    RESET = 0
    MEMBER_STEP = _ScanPhase.STEP
    FAMILY = 3
    IMAGE_CLEAR = 4
    IMAGE = 5
    TEMPLATE = 6
    DESCENT_CLEAR = 7
    DESCENT = 8
    MEMBER_WAIT = 9
    MEMBER = 10
    MASK_STEP = 11
    END = 12


def _transition(board, source, target, suffix, *conditions):
    allowed = _compare(board, f"phase_{suffix}", "phase", int(source))
    for i, condition in enumerate(conditions):
        allowed = _gate(board, "And", f"allow_{suffix}_{i}", allowed, condition)
    _gate(board, "If", "jump", int(target), allowed)


def _active(enable, frozen, active):
    board = Module({"enable": enable, "tuple_ready": frozen})
    enabled = _compare(board, "enabled", "enable", 1)
    settled = _compare(board, "frozen", "tuple_ready", 1)
    board.outputs = {_gate(board, "And", "active", enabled, settled): active}
    return board


def _phase(active, phase, decisions):
    board = Module({"active": active, "phase": phase, **{f"jump{i}": ch for i, ch in enumerate(decisions)}})
    for i in range(len(decisions)):
        _gate(board, "If", "requested", f"jump{i}", 1)
    hold = _compare(board, "hold", "requested", None)
    _gate(board, "If", "next", "phase", _gate(board, "And", "keep_phase", "active", hold))
    jump = _gate(board, "Not", "jump", hold)
    _gate(board, "If", "next", "requested", _gate(board, "And", "update", "active", jump))
    _gate(board, "If", "next", int(_Phase.RESET), _gate(board, "Not", "reset", "active"))
    board.outputs = {"next": phase}
    return board


def _step_pulses(phase, stamp, mask_step, member_step):
    board = Module({"phase": phase, "stamp": stamp})
    _gate(board, "If", "seen", "phase", 1)
    edge = _compare(board, "fresh", "phase", "stamp", "Bg==")
    for state, channel in ((_Phase.MASK_STEP, mask_step), (_Phase.MEMBER_STEP, member_step)):
        suffix = str(int(state))
        stepping = _compare(board, f"step{suffix}", "phase", int(state))
        pulse = _gate(board, "And", f"pulse{suffix}", edge, stepping)
        board.outputs[_gate(board, "If", f"phase{suffix}", int(state), pulse)] = channel
    board.outputs["seen"] = stamp
    return board


def _mask(active, phase, mask):
    board = Module({"active": active, "phase": phase, "mask": mask})
    board.lookup("mask", "decremented", ((n, n - 1) for n in range(16)))
    reset = _gate(board, "Not", "reset", "active")
    step = _compare(board, "step", "phase", int(_Phase.MASK_STEP))
    _gate(board, "If", "next", 15, reset)
    _gate(board, "If", "next", "decremented", _gate(board, "And", "move", "active", step))
    _gate(board, "If", "next", "mask", _gate(board, "And", "hold", "active", _gate(board, "Not", "stay", step)))
    board.outputs = {"next": mask}
    return board


def _lane(q, mask, permitted, pin, valid, limit):
    board = Module({"mask": mask, "permitted": permitted, "pin": pin})
    board.lookup("mask", "bit", ((n, (n >> q) & 1) for n in range(16)))
    free = _gate(board, "Not", "free", "bit")
    _gate(board, "Or", "valid", free, "permitted")
    _gate(board, "If", "limit", 0, "bit")
    with_pin = _gate(board, "And", "with_pin", free, "pin")
    without_pin = _gate(board, "And", "without_pin", free, _gate(board, "Not", "no_pin", "pin"))
    _gate(board, "If", "limit", 2, with_pin)
    _gate(board, "If", "limit", 1, without_pin)
    board.outputs = {"valid": valid, "limit": limit}
    return board


def _all_lanes(lanes, output):
    board = Module({f"valid{q}": ch for q, ch in enumerate(lanes)})
    pair0 = _gate(board, "And", "pair0", "valid0", "valid1")
    pair1 = _gate(board, "And", "pair1", "valid2", "valid3")
    board.outputs = {_gate(board, "And", "all", pair0, pair1): output}
    return board


def _family(phase, mask, legal, elapsed, plan, reject, output):
    board = Module({"phase": phase, "mask": mask, "legal": legal, "elapsed": elapsed, "plan": plan, "reject": reject})
    idle = _compare(board, "reject_idle", "reject", None)
    zero = _compare(board, "reject_zero", "reject", 0)
    clean = _gate(board, "Or", "clean", idle, zero)
    requested = _gate(board, "And", "requested", clean, _compare(board, "plan_live", "plan", 1))
    settled = _compare(board, "settled", "elapsed", int(_Phase.FAMILY))
    inspect = _gate(board, "And", "inspect", settled, requested)
    end = _compare(board, "end", "mask", -1)
    more = _compare(board, "more", "mask", 0, "Ag==")
    _transition(board, _Phase.RESET, _Phase.FAMILY, "start")
    _transition(board, _Phase.FAMILY, _Phase.END, "end", inspect, end)
    _transition(board, _Phase.FAMILY, _Phase.IMAGE_CLEAR, "legal", inspect, more, "legal")
    _transition(board, _Phase.FAMILY, _Phase.MASK_STEP, "illegal", inspect, more,
                _gate(board, "Not", "illegal", "legal"))
    _transition(board, _Phase.MASK_STEP, _Phase.FAMILY, "advance")
    board.outputs = {"jump": output}
    return board


def _filter(phase, filter_ready, filter_ok, output):
    board = Module({"phase": phase, "ready": filter_ready, "ok": filter_ok})
    clear = _gate(board, "Or", "clear", _compare(board, "zero", "ready", 0),
                  _compare(board, "empty", "ready", None))
    answered = _compare(board, "answered", "ready", 1)
    yes = _gate(board, "And", "yes", answered, _compare(board, "pass", "ok", 1))
    no = _gate(board, "And", "no", answered, _compare(board, "fail", "ok", 0))
    _transition(board, _Phase.IMAGE_CLEAR, _Phase.IMAGE, "ask_image", clear)
    _transition(board, _Phase.DESCENT_CLEAR, _Phase.DESCENT, "ask_descent", clear)
    _transition(board, _Phase.IMAGE, _Phase.TEMPLATE, "matching_image", yes)
    _transition(board, _Phase.IMAGE, _Phase.MASK_STEP, "wrong_image", no)
    _transition(board, _Phase.DESCENT, _Phase.MEMBER_WAIT, "descend", yes)
    _transition(board, _Phase.DESCENT, _Phase.MASK_STEP, "no_descent", no)
    board.outputs = {"jump": output}
    return board


def _templates(phase, reject, remaining, output):
    board = Module({"phase": phase, "reject": reject, "remaining": remaining})
    missed = _compare(board, "missed", "reject", 1)
    positive = _compare(board, "positive", "remaining", 0, "Aw==")
    bounded = _compare(board, "bounded", "remaining", 4, "BQ==")
    recurse = _gate(board, "And", "recurse", positive, bounded)
    _transition(board, _Phase.TEMPLATE, _Phase.DESCENT_CLEAR, "try_members", missed, recurse)
    _transition(board, _Phase.TEMPLATE, _Phase.MASK_STEP, "no_budget", missed,
                _compare(board, "no_budget", "remaining", 0))
    board.outputs = {"jump": output}
    return board


def _members(phase, reject, plan, elapsed, full, output):
    board = Module({"phase": phase, "reject": reject, "plan": plan, "elapsed": elapsed, "full": full})
    clear = _gate(board, "Or", "reject_clear", _compare(board, "reject_absent", "reject", None),
                  _compare(board, "reject_zero", "reject", 0))
    settled = _compare(board, "settled", "elapsed", int(_Phase.MEMBER_WAIT))
    _transition(board, _Phase.MEMBER_WAIT, _Phase.MEMBER, "publish", clear, settled,
                _compare(board, "requested", "plan", 1))
    missed = _compare(board, "missed", "reject", 2)
    _transition(board, _Phase.MEMBER, _Phase.MASK_STEP, "done", missed, "full")
    _transition(board, _Phase.MEMBER, _Phase.MEMBER_STEP, "next", missed,
                _gate(board, "Not", "more", "full"))
    _transition(board, _Phase.MEMBER_STEP, _Phase.MEMBER_WAIT, "stepped")
    board.outputs = {"jump": output}
    return board


def _publish(active, plan, phase, mask, ready, kind, mask_out, request, member_enable):
    board = Module({"active": active, "plan": plan, "phase": phase, "mask": mask})
    template = _compare(board, "template", "phase", int(_Phase.TEMPLATE))
    member = _compare(board, "member", "phase", int(_Phase.MEMBER))
    end = _compare(board, "end", "phase", int(_Phase.END))
    present = _any(board, "present", (template, member, end))
    ask = _gate(board, "And", "ask", "active", _compare(board, "plan_live", "plan", 1))
    _gate(board, "And", "ready", ask, present)
    for code, state in ((0, end), (1, template), (2, member)):
        condition = _gate(board, "And", f"kind_{code}", state, "active")
        _gate(board, "If", "kind", code, condition)
    _gate(board, "If", "mask_out", "mask", "active")
    for code, state in ((1, _Phase.IMAGE), (2, _Phase.DESCENT)):
        phase_live = _compare(board, f"query_phase{code}", "phase", int(state))
        condition = _gate(board, "And", f"query{code}", "active", phase_live)
        _gate(board, "If", "request", code, condition)
    counting = _in_phases(board, "count", tuple(map(int, (_Phase.MEMBER_WAIT, _Phase.MEMBER, _Phase.MEMBER_STEP))))
    _gate(board, "And", "count_live", "active", counting)
    board.outputs = {"ready": ready, "kind": kind, "mask_out": mask_out, "request": request,
                     "count_live": member_enable}
    return board


def build(layer: dict, columns: dict, cap: dict, channel_base: int = _BASE) -> tuple[dict, dict]:
    """对接单层顶针搜索和冻结四列，生成独立的顶盖参数板。"""
    li, lo = layer["inputs"], layer["outputs"]
    ci, co = columns["inputs"], columns["outputs"]
    enable, frozen, plan, reject = li["enable"], co["ready"], lo["plan"], lo["reject"]
    out_ready, out_kind, out_mask = (li[name] for name in ("plan_ready", "kind", "mask"))
    digits = tuple(li["members"])
    cap_outputs = (out_ready, out_kind, out_mask, *digits)
    lane_inputs = tuple((ci[f"q{q}"], *(lane[f"material_{z}"] for z in range(4)))
                        for q, lane in enumerate(co["columns"]))
    channels = range(channel_base, channel_base + _WINDOW)
    external = {enable, frozen, plan, reject, *(ch for lane in lane_inputs for ch in lane)}
    if (len(digits) != 4 or len(lane_inputs) != 4 or len(set(cap_outputs)) != 7 or len(external) != 24
            or layer["columns"]["ready"] != frozen or external.intersection(cap_outputs)
            or channels[0] < 1 or channels[-1] >= 1 << 24 or (external | set(cap_outputs)).intersection(channels)):
        raise ValueError("单层搜索、四列候选和参数板频道不兼容")
    private = iter(channels)

    def take(n):
        return tuple(next(private) for _ in range(n))

    remaining, filter_ready, filter_ok, request = take(4)
    active, phase, mask, legal, full, member_enable = take(6)
    decisions = take(4)
    qualified, limits, count_full, steps = (take(4) for _ in range(4))
    timers, elapsed, _ = _wait_timer(phase, take(5), _SETTLE_STEPS, _SETTLE_STEPS)
    permitted, pin, max_cap = (take(4) for _ in range(3))
    stamp, mask_step, member_step = take(3)
    modules = [_active(enable, frozen, active), _phase(active, phase, decisions), _mask(active, mask_step, mask),
               _step_pulses(phase, stamp, mask_step, member_step),
               _family(phase, mask, legal, elapsed, plan, reject, decisions[0]),
               _filter(phase, filter_ready, filter_ok, decisions[1]),
               _templates(phase, reject, remaining, decisions[2]),
               _members(phase, reject, plan, elapsed, full, decisions[3]),
               _publish(active, plan, phase, mask, out_ready, out_kind, out_mask, request, member_enable),
               _all_lanes(qualified, legal), _carry(count_full, steps, full), *timers]
    for q in range(4):
        modules.append(_lane(q, mask, permitted[q], pin[q], qualified[q], limits[q]))
        count = _count(member_enable, member_step, steps[q], digits[q], count_full[q], 0, "limit")
        count.inputs["limit"] = limits[q]
        modules.append(count)
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    fields = ("word", "z0", "z1", "z2", "z3")
    inputs = tuple(cap["inputs"][field]["channel"] for field in fields)
    outputs = tuple(cap["outputs"][field]["channel"] for field in ("crystal_allowed", "pin_allowed", "max_cap"))
    for q, sources in enumerate(lane_inputs):
        asset = _read_blueprint(_ASSETS / "pin-cap-column.spz2bp")
        mapping = dict(zip((*inputs, *outputs), (*sources, permitted[q], pin[q], max_cap[q]), strict=True))
        platforms.extend(_rewire(Wiring(asset["BP"]), mapping))
    entries = [{**board, "X": 3 * (i % 6), "Y": 3 * (i // 6)} for i, board in enumerate(platforms)]
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    senders = [ch for _, tx, ch, _ in _radio_ports(wiring) if tx]
    receivers = {ch for _, tx, ch, _ in _radio_ports(wiring) if not tx}
    external.update((remaining, filter_ready, filter_ok))
    if (len(senders) != len(set(senders)) or set(senders).intersection(external) or receivers - set(senders) != external
            or set(senders) - set(channels) != set(cap_outputs)):
        raise ValueError("顶盖参数板的原生收发频道与接口表不符")
    return document, {
        "inputs": {"enable": enable, "tuple_ready": frozen, "plan": plan, "reject": reject,
                   "remaining_pins": remaining, "filter_ready": filter_ready, "filter_ok": filter_ok,
                   "columns": [{"word": word, "materials": materials} for word, *materials in lane_inputs]},
        "outputs": {"plan_ready": out_ready, "kind": out_kind, "mask": out_mask, "members": digits,
                    "filter_request": request, "crystal_allowed": permitted},
        "channels": {"reserved_range": [channels[0], channels[-1]], "phase": phase},
        "timing": {"channel_signal_ticks": _RADIO, "settle_signal_ticks": _SETTLE_STEPS * _RADIO,
                   "tuple_reset_signal_ticks": 48},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出单层顶针搜索的顶盖族与成员遍历板")
    parser.add_argument("layer", type=Path, help="单次顶针层控制 JSON")
    parser.add_argument("columns", type=Path, help="冻结四列候选 JSON")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="私有首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        cap = _read_report(_ASSETS / "pin-cap-column.json")
        _write_blueprint(*build(_read_report(args.layer), _read_report(args.columns), cap, args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
