"""一层顶针来源的族策略与原生调用控制。"""

import argparse
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from ...synthesis.inverse import pin_column_at, pin_families
from ...synthesis.physics import EMPTY, PIN, Rules, Shape
from ...synthesis.pin_constraints import pin_base_possible
from ...synthesis.support import in_support_class
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _any, _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from .pin_candidate_closure import _radio_ports
from .pin_candidate_row import _in_phases, _RADIO, _read_report


_BASE = 1703300
_WINDOW = 100


class Phase(IntEnum):
    TUPLE = 1
    PLAN = 2
    RESET = 3
    SEAL = 4
    CLOSURE = 5
    PROOF = 6
    REPLAY = 7
    TEMPLATE_MISSED = 8
    MEMBER_MISSED = 9
    NEXT_TUPLE = 10
    ACCEPTED = 11
    EXHAUSTED = 12
    FAULT = 13


@dataclass(frozen=True)
class Attempt:
    mask: int
    members: tuple[int, ...] | None = None

    @property
    def kind(self) -> int:
        return 1 if self.members is None else 2


def attempts(target: Shape, slots: tuple[int, ...], lowest: int, remaining_pins: int):
    """按当前四槽访问题族。模板失败或成员无证书时恢复迭代。"""
    if len(slots) != 4 or not 0 <= lowest <= 4 or not 0 <= remaining_pins <= 3:
        raise ValueError("顶针搜索需要四个槽号、最低晶层及有界尾针余量")
    rules = Rules(4, 5)
    layers = target.layers + ((EMPTY,) * 4,) * (5 - len(target.layers))
    columns = tuple(pin_column_at(column, slot) for column, slot in zip(zip(*layers), slots, strict=True))
    if any(column is None for column in columns):
        return
    lower = tuple(zip(*columns, strict=True))
    for family in pin_families(rules, target):
        if family.lower != lower:
            continue
        mask = family.top_crystals
        yield Attempt(mask)
        template = Shape((*lower, tuple("cr" if mask & (1 << q) else "Cu" for q in range(4))))
        if (not remaining_pins or not pin_base_possible(template)
                or not in_support_class(rules, template, grounded=True, optional_top=True)):
            continue
        crystal_bottom = min((z for z, row in enumerate(template.layers) if any(cell[0] == "c" for cell in row)),
                             default=5)
        if crystal_bottom == 5:
            continue
        if crystal_bottom >= lowest:
            raise ValueError("成员递归的最低晶层须严格下降")
        for member in family.members(rules):
            top = member.layers[4] if len(member.layers) == 5 else (EMPTY,) * 4
            yield Attempt(mask, tuple(0 if mask & (1 << q) or cell == EMPTY else 2 if cell == PIN else 1
                                      for q, cell in enumerate(top)))


def _case(board, current, target, name, *conditions):
    test = _compare(board, f"phase_{name}", "phase", int(current))
    for i, condition in enumerate(conditions):
        test = _gate(board, "And", f"when_{name}_{i}", test, condition)
    _gate(board, "If", "next", int(target), test)


def _choose_tuple(phase, ready, exhausted, plan_ready, output):
    board = Module({"phase": phase, "ready": ready, "exhausted": exhausted, "plan_ready": plan_ready})
    depleted = _compare(board, "depleted", "exhausted", 1)
    present = _compare(board, "present", "ready", 1)
    _case(board, Phase.TUPLE, Phase.PLAN, "tuple", present, _gate(board, "Not", "more", depleted),
          _compare(board, "plan_idle", "plan_ready", 1, "Bg=="))
    _case(board, Phase.TUPLE, Phase.EXHAUSTED, "depleted", depleted)
    _case(board, Phase.NEXT_TUPLE, Phase.TUPLE, "next_tuple", _gate(board, "Not", "absent", present))
    board.outputs = {"next": output}
    return board


def _choose_plan(phase, ready, kind, elapsed, cleared, output):
    board = Module({"phase": phase, "ready": ready, "kind": kind, "elapsed": elapsed, "cleared": cleared})
    received = _compare(board, "received", "ready", 1)
    template = _compare(board, "template", "kind", 1)
    member = _compare(board, "member", "kind", 2)
    attempt = _gate(board, "Or", "attempt", template, member)
    tail = _compare(board, "end_tuple", "kind", 0)
    bad = _gate(board, "Not", "bad_kind", _gate(board, "Or", "known", tail, attempt))
    _case(board, Phase.PLAN, Phase.RESET, "setup", received, attempt)
    _case(board, Phase.PLAN, Phase.NEXT_TUPLE, "complete_tuple", received, tail)
    _case(board, Phase.PLAN, Phase.FAULT, "bad_plan", received, bad)
    reset = _compare(board, "waited", "elapsed", int(Phase.RESET))
    _case(board, Phase.RESET, Phase.SEAL, "read", reset, "cleared")
    pending = _gate(board, "Not", "released", received)
    _case(board, Phase.TEMPLATE_MISSED, Phase.PLAN, "resume_template", pending)
    _case(board, Phase.MEMBER_MISSED, Phase.PLAN, "resume_member", pending)
    board.outputs = {"next": output}
    return board


def _choose_closure(phase, kind, ready, valid, chosen, exhausted, output):
    board = Module({"phase": phase, "kind": kind, "ready": ready, "valid": valid,
                    "chosen": chosen, "exhausted": exhausted})
    done = _compare(board, "sealed", "ready", 1)
    ok = _compare(board, "legal", "valid", 1)
    _case(board, Phase.SEAL, Phase.FAULT, "invalid", done, _gate(board, "Not", "invalid", ok))
    _case(board, Phase.SEAL, Phase.CLOSURE, "closure", done, ok, _compare(board, "template", "kind", 1))
    _case(board, Phase.SEAL, Phase.PROOF, "member", done, ok, _compare(board, "member", "kind", 2))
    missed = _compare(board, "missed", "exhausted", 1)
    success = _gate(board, "And", "success", _compare(board, "closed", "chosen", 1),
                    _gate(board, "Not", "has_cut", missed))
    _case(board, Phase.CLOSURE, Phase.PROOF, "certificate", success)
    _case(board, Phase.CLOSURE, Phase.TEMPLATE_MISSED, "no_cut", missed)
    board.outputs = {"next": output}
    return board


def _choose_proof(phase, kind, proof_done, proof_ok, replay_done, replay_ok, output):
    board = Module({"phase": phase, "kind": kind, "proof_done": proof_done, "proof_ok": proof_ok,
                    "replay_done": replay_done, "replay_ok": replay_ok})
    proof = _compare(board, "proved", "proof_done", 1)
    proof_yes = _compare(board, "has_proof", "proof_ok", 1)
    proof_no = _compare(board, "missing_proof", "proof_ok", 0)
    miss = _gate(board, "And", "miss", proof_no, _compare(board, "member", "kind", 2))
    _case(board, Phase.PROOF, Phase.REPLAY, "replay", proof, proof_yes)
    _case(board, Phase.PROOF, Phase.MEMBER_MISSED, "next_member", proof, miss)
    reported = _gate(board, "Or", "reported", proof_yes, miss)
    _case(board, Phase.PROOF, Phase.FAULT, "lost_proof", proof, _gate(board, "Not", "fault", reported))
    replay = _compare(board, "replayed", "replay_done", 1)
    match = _compare(board, "matched", "replay_ok", 1)
    _case(board, Phase.REPLAY, Phase.ACCEPTED, "accept", replay, match)
    _case(board, Phase.REPLAY, Phase.FAULT, "mismatch", replay, _gate(board, "Not", "wrong", match))
    board.outputs = {"next": output}
    return board


def _phase(enable, phase, ready, decisions):
    board = Module({"enable": enable, "phase": phase, "ready": ready,
                    **{f"jump{i}": ch for i, ch in enumerate(decisions)}})
    for i in range(len(decisions)):
        _gate(board, "If", "jump", f"jump{i}", 1)
    protected = _in_phases(board, "protect", (int(Phase.PLAN), int(Phase.RESET), int(Phase.SEAL),
                                             int(Phase.CLOSURE), int(Phase.PROOF), int(Phase.REPLAY),
                                             int(Phase.TEMPLATE_MISSED), int(Phase.MEMBER_MISSED), int(Phase.ACCEPTED)))
    lost = _gate(board, "And", "lost", protected, _compare(board, "lost_ready", "ready", 1, "Bg=="))
    enabled = _compare(board, "enabled", "enable", 1)
    live = _gate(board, "And", "live", enabled, _gate(board, "Not", "has_tuple", lost))
    stalled = _compare(board, "stalled", "jump", None)
    _gate(board, "If", "next", "jump", _gate(board, "And", "moving", live, _gate(board, "Not", "move", stalled)))
    _gate(board, "If", "next", "phase", _gate(board, "And", "staying", live, stalled))
    _gate(board, "If", "next", int(Phase.FAULT), _gate(board, "And", "lost_tuple", enabled, lost))
    _gate(board, "If", "next", int(Phase.TUPLE), _gate(board, "Not", "reset", enabled))
    board.outputs = {"next": phase}
    return board


def _clear_replies(channels, output):
    board = Module({f"reply{i}": ch for i, ch in enumerate(channels)})
    replies = tuple(_compare(board, f"high{i}", name, 1) for i, name in enumerate(board.inputs))
    _gate(board, "Not", "cleared", _any(board, "previous_replies", replies))
    board.outputs = {"cleared": output}
    return board


def _run_phases(phase, enable, kind, ports):
    board = Module({"phase": phase, "enable": enable, "kind": kind})
    enabled = _compare(board, "enabled", "enable", 1)
    template = _compare(board, "template", "kind", 1)
    hold = (Phase.PROOF, Phase.REPLAY, Phase.ACCEPTED)
    schedule = {
        "plan": (Phase.PLAN, Phase.RESET, Phase.SEAL, Phase.CLOSURE, *hold),
        "advance": (Phase.NEXT_TUPLE,),
        "seal": (Phase.SEAL, Phase.CLOSURE, *hold),
        "closure": (Phase.CLOSURE, *hold),
        "proof": hold,
        "replay": (Phase.REPLAY, Phase.ACCEPTED),
    }
    for name, channel in ports.items():
        live = _in_phases(board, name, tuple(map(int, schedule[name])))
        output = _gate(board, "And", name, live, enabled)
        if name == "closure":
            output = _gate(board, "And", "run_template", output, template)
        board.outputs[output] = channel
    return board


def _status(phase, enable, outputs):
    board = Module({"phase": phase, "enable": enable})
    enabled = _compare(board, "enabled", "enable", 1)
    for name, current in (("accepted", Phase.ACCEPTED), ("exhausted", Phase.EXHAUSTED), ("fault", Phase.FAULT)):
        output = _gate(board, "And", name, enabled, _compare(board, f"is_{name}", "phase", int(current)))
        board.outputs[output] = outputs[name]
    for reason, current in enumerate((Phase.TEMPLATE_MISSED, Phase.MEMBER_MISSED), 1):
        live = _gate(board, "And", f"missed_{reason}", enabled, _compare(board, f"reason_{reason}", "phase", int(current)))
        _gate(board, "If", "reject", reason, live)
    board.outputs["reject"] = outputs["reject"]
    return board


def _copy_ports(pairs):
    board = Module({f"value{i}": source for i, (source, _) in enumerate(pairs)})
    for i, (_, destination) in enumerate(pairs):
        board.outputs[_gate(board, "If", f"copy{i}", f"value{i}", 1)] = destination
    return board


def _arguments(enable, kind, tuple_enable, seal_mode, closure_mode, optional):
    board = Module({"enable": enable, "kind": kind})
    board.outputs = {
        _compare(board, "tuple_enable", "enable", 1): tuple_enable,
        _compare(board, "seal_mode", "kind", 1): seal_mode,
        _gate(board, "If", "closure_mode", 1, 1): closure_mode,
        _gate(board, "If", "optional", 1, 1): optional,
    }
    return board


def build(columns: dict, seal: dict, closure: dict, channel_base: int = _BASE) -> tuple[dict, dict]:
    ci, co = columns["inputs"], columns["outputs"]
    si, so = seal["inputs"], seal["outputs"]
    ai, ao = closure["inputs"], closure["outputs"]
    reads = {co["ready"], co["exhausted"], so["ready"], so["valid"], ao["chosen"], ao["exhausted"]}
    writes = {ci["enable"], ci["advance"], si["enable"], si["mode"], si["crystal_mask"], *si["members"],
              ai["enable"], ai["mode"], ai["optional_top"]}
    window = range(channel_base, channel_base + _WINDOW)
    if (len(reads) != 6 or len(writes) != 12 or reads & writes
            or not 1 <= window[0] <= window[-1] < 1 << 24 or (reads | writes).intersection(window)
            or si["candidate_ready"] != co["ready"] or ai["valid"] != so["valid"]
            or ai["source_rows_bottom_to_top"] != so["rows_bottom_to_top"]):
        raise ValueError("四列、封存和闭包的接口与顶针一层搜索不符")
    channels = iter(window)
    inputs = {name: next(channels) for name in ("enable", "plan_ready", "kind", "mask", "proof_done", "proof_ok",
                                                "replay_done", "replay_ok")}
    members = tuple(next(channels) for _ in range(4))
    outputs = {name: next(channels) for name in ("plan", "reject", "proof", "replay", "accepted", "exhausted", "fault")}
    phase, cleared = (next(channels) for _ in range(2))
    decisions = tuple(next(channels) for _ in range(4))
    timer_channels = tuple(next(channels) for _ in range(5))
    reset_ticks = max(seal["timing"]["reset_hold_signal_ticks"], closure["timing"]["mode_reset_hold_signal_ticks"])
    steps = (reset_ticks + _RADIO - 1) // _RADIO + 2
    timers, elapsed, _ = _wait_timer(phase, timer_channels, steps, 1)
    pairs = tuple(zip((inputs["mask"], *members), (si["crystal_mask"], *si["members"]), strict=True))
    modules = [
        _choose_tuple(phase, co["ready"], co["exhausted"], inputs["plan_ready"], decisions[0]),
        _choose_plan(phase, inputs["plan_ready"], inputs["kind"], elapsed, cleared, decisions[1]),
        _choose_closure(phase, inputs["kind"], so["ready"], so["valid"], ao["chosen"], ao["exhausted"], decisions[2]),
        _choose_proof(phase, inputs["kind"], *(inputs[key] for key in ("proof_done", "proof_ok", "replay_done", "replay_ok")), decisions[3]),
        _phase(inputs["enable"], phase, co["ready"], decisions),
        _clear_replies((so["ready"], ao["chosen"], ao["exhausted"], inputs["proof_done"], inputs["replay_done"]), cleared),
        *_routing(phase, inputs, outputs, ci, si, ai),
        _status(phase, inputs["enable"], outputs),
        _arguments(inputs["enable"], inputs["kind"], ci["enable"], si["mode"], ai["mode"], ai["optional_top"]),
        _copy_ports(pairs),
        *timers,
    ]
    entries = []
    for i, module in enumerate(modules):
        entry, = module.layout()["BP"]["Entries"]
        entries.append({**entry, "X": 3 * (i % 6), "Y": 3 * (i // 6)})
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    wiring = _local_wiring(document["BP"])
    senders = [ch for _, transmitter, ch, _ in _radio_ports(wiring) if transmitter]
    receivers = {ch for _, transmitter, ch, _ in _radio_ports(wiring) if not transmitter}
    external = {*inputs.values(), *members, *reads}
    if (len(senders) != len(set(senders)) or set(senders) - set(window) != writes
            or receivers - set(senders) != external):
        raise ValueError("顶针一层搜索的原生频道与计划不符")
    return document, {
        "inputs": {**inputs, "members": members}, "outputs": outputs,
        "columns": {"enable": ci["enable"], "advance": ci["advance"], "ready": co["ready"], "exhausted": co["exhausted"]},
        "seal": {"inputs": si, "outputs": so}, "closure": {"inputs": ai, "outputs": ao},
        "channels": {"reserved_range": [window[0], window[-1]], "phase": phase},
        "timing": {"channel_signal_ticks": _RADIO, "attempt_reset_signal_ticks": steps * _RADIO},
        "platforms": len(entries), "building_entries": len(wiring.entries),
    }


def _routing(phase, inputs, outputs, columns, seal, closure):
    ports = {**outputs, "advance": columns["advance"], "seal": seal["enable"], "closure": closure["enable"]}
    groups = (("plan", "advance", "seal"), ("closure", "proof", "replay"))
    return tuple(_run_phases(phase, inputs["enable"], inputs["kind"], {name: ports[name] for name in group})
                 for group in groups)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出单次顶针层内的候选调用控制")
    parser.add_argument("columns", type=Path, help="四列枚举 JSON")
    parser.add_argument("seal", type=Path, help="五层封存 JSON")
    parser.add_argument("closure", type=Path, help="双来源闭包 JSON")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="调用控制的首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        reports = [_read_report(path) for path in (args.columns, args.seal, args.closure)]
        _write_blueprint(*build(*reports, args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
