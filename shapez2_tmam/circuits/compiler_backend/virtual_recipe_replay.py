"""按候选地址提交虚拟六槽状态，并在整单结束时验收成品。"""

import argparse
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..factory_assembly.interface import ORDER_INPUTS
from ..factory_assembly.recipe import MAX_STAGES
from ..factory_assembly.submit_bridge import CANDIDATE_ADDRESS, CANDIDATE_FIELDS
from ..local_module import Module
from . import _write_blueprint
from .confirmed_call import _register
from .method_sequence import _DONE, _ENABLE, _radio_channels
from .module_caller import _RADIO_TICKS, _compare, _gate, _local_wiring, _wait_timer
from .prefix_scan_wiring import _append
from .virtual_recipe_step import _INPUTS, _OUTPUTS, _SLOT_NAMES
from .virtual_recipe_step import build as build_step


_ACK, _LENGTH, _FINISHED, _ACCEPTED, _RESULT, _FAULT, _NEXT_ADDRESS = range(1702740, 1702747)
_PHASE, _CLASS, _LAST, _COMMIT, _OTHER_EMPTY, _NEXT_LENGTH = range(1702750, 1702756)
_TIMER_CHANNELS = tuple(range(1702760, 1702765))
_ROM_BASE, _GROUP_BASE = 1702790, 1702830
_RESET_TICKS = 96
_DRAIN_STEPS = 8
_TARGET = ORDER_INPUTS["target"]


def _classify(max_packets: int) -> Module:
    board = Module({"address": CANDIDATE_ADDRESS, "length": _LENGTH, "last": _LAST})
    present = _compare(board, "present", "address", None, "Bg==")
    expected = _compare(board, "expected", "address", "length")
    capacity = _compare(board, "capacity", "length", max_packets, "BA==")
    new = _gate(board, "And", "new", expected, capacity)
    duplicate = _compare(board, "duplicate", "address", "last")
    admitted = _gate(board, "Or", "admitted", new, duplicate)
    wrong = _gate(board, "And", "wrong", present, _gate(board, "Not", "not_admitted", admitted))
    _gate(board, "If", "class", 1, new)
    _gate(board, "If", "class", 2, wrong)
    board.outputs = {"class": _CLASS}
    return board


def _sequence(read_at: int, drain_at: int) -> Module:
    board = Module({"enable": _ENABLE, "phase": _PHASE, "class": _CLASS, "done": _DONE,
                    "read_at": read_at, "drain_at": drain_at, "valid": _OUTPUTS["valid"]})
    enabled = _compare(board, "enabled", "enable", 1)
    idle = _compare(board, "idle", "phase", 0)
    running = _compare(board, "running", "phase", 1)
    commit = _compare(board, "commit", "phase", 2)
    draining = _compare(board, "draining", "phase", 3)
    drained = _gate(board, "And", "drained", draining, _compare(board, "drain_ready", "drain_at", 3))
    finished = _compare(board, "finished", "done", 1)
    allowed = _gate(board, "And", "allowed", idle, _gate(board, "Not", "open", finished))
    request = _compare(board, "request", "class", 1)
    error = _compare(board, "error", "class", 2)
    stable = _compare(board, "stable", "read_at", 1)
    sampled = _gate(board, "And", "sampled", running, stable)
    ready = _gate(board, "And", "ready", request, _compare(board, "valid_input", "valid", 1))
    _gate(board, "If", "next", 1, _gate(board, "And", "start", allowed, request))
    _gate(board, "If", "next", 2, _gate(board, "And", "accept", sampled, ready))
    _gate(board, "If", "next", 3, commit)
    invalid = _gate(board, "And", "invalid", sampled, _gate(board, "Not", "not_ready", ready))
    refused = _gate(board, "And", "refused", allowed, error)
    _gate(board, "If", "next", 4, _gate(board, "Or", "fail", invalid, refused))
    _gate(board, "If", "next", 5, _gate(board, "And", "finish", idle, finished))
    needs_idle = _compare(board, "reset_phase", "phase", -1)
    _gate(board, "If", "next", 0, _gate(board, "Or", "go_idle", drained, needs_idle))
    changed = _compare(board, "changed", "next", None, "Bg==")
    _gate(board, "If", "chosen", "next", 1)
    _gate(board, "If", "chosen", "phase", _gate(board, "Not", "unchanged", changed))
    _gate(board, "If", "state", "chosen", enabled)
    _gate(board, "If", "state", -1, _gate(board, "Not", "reset", enabled))
    board.outputs = {"state": _PHASE}
    return board


def _bridge_ports() -> Module:
    board = Module({"enable": _ENABLE, "phase": _PHASE, "address": CANDIDATE_ADDRESS,
                    "last": _LAST, "length": _LENGTH, "commit": _COMMIT})
    enabled = _compare(board, "enabled", "enable", 1)
    idle = _compare(board, "idle", "phase", 0)
    finish = _compare(board, "finished", "phase", 5)
    idle_or_finished = _gate(board, "Or", "idle_or_finished", idle, finish)
    last = _compare(board, "known", "last", None, "Bg==")
    same = _compare(board, "duplicate", "last", "address")
    duplicate = _gate(board, "And", "repeat", same, last)
    can_ack = _gate(board, "And", "can_ack", enabled, idle_or_finished)
    ack = _gate(board, "And", "acknowledge", can_ack, duplicate)
    board.outputs[_gate(board, "If", "ack", "last", ack)] = _ACK
    fault = _compare(board, "fault", "phase", 4)
    board.outputs[_gate(board, "And", "fault_out", enabled, fault)] = _FAULT
    working = _compare(board, "working", "phase", 0, "Ag==")
    before_end = _compare(board, "before_end", "phase", 4, "BA==")
    open_ = _gate(board, "And", "active", enabled, _gate(board, "And", "open", working, before_end))
    draining = _compare(board, "draining", "phase", 3)
    committed = _gate(board, "And", "committed", draining, _gate(board, "Not", "after_commit", "commit"))
    _gate(board, "If", "next_address", "last", _gate(board, "And", "show_last", open_, committed))
    pre_commit = _gate(board, "Not", "pre_commit", committed)
    _gate(board, "If", "next_address", "length", _gate(board, "And", "show_length", open_, pre_commit))
    board.outputs["next_address"] = _NEXT_ADDRESS
    return board


def _completions(slots: dict[str, int]) -> tuple[Module, Module]:
    empties = Module({name: slots[name] for name in _SLOT_NAMES[1:]})
    flags = [_compare(empties, f"empty_{name}", name, None) for name in empties.inputs]
    empty = flags[0]
    for i, flag in enumerate(flags[1:]):
        empty = _gate(empties, "And", f"empty_group{i}", empty, flag)
    empties.outputs[empty] = _OTHER_EMPTY
    board = Module({"enable": _ENABLE, "phase": _PHASE, "length": _LENGTH, "slot0": slots["slot0"],
                    "others_empty": _OTHER_EMPTY, "target": _TARGET})
    enabled = _compare(board, "enabled", "enable", 1)
    finish = _compare(board, "at_end", "phase", 5)
    finished = _gate(board, "And", "finished", enabled, finish)
    nonempty = _compare(board, "nonempty", "slot0", None, "Bg==")
    wrote = _compare(board, "wrote", "length", 0, "Aw==")
    unique = _gate(board, "And", "unique", nonempty, "others_empty")
    product = _gate(board, "And", "product", unique, wrote)
    publish = _gate(board, "And", "publish", finished, product)
    matches = _compare(board, "matches", "target", "slot0")
    board.outputs = {finished: _FINISHED, _gate(board, "And", "accepted", matches, publish): _ACCEPTED,
                     _gate(board, "If", "result", "slot0", publish): _RESULT}
    return empties, board


def _relay(inputs: dict[str, int], output: int) -> Module:
    board = Module(inputs)
    for name in inputs:
        _gate(board, "If", "value", name, 1)
    board.outputs = {"value": output}
    return board


def _count(max_packets: int) -> list[Module]:
    modules = []
    leaves = []
    for offset in range(0, max_packets, 26):
        board = Module({"length": _LENGTH})
        channel = _ROM_BASE + len(leaves)
        board.lookup("length", "next", ((value, value + 1) for value in range(offset, min(offset + 26, max_packets))))
        board.outputs = {"next": channel}
        leaves.append(channel)
        modules.append(board)
    groups = []
    for offset in range(0, len(leaves), 8):
        channel = _GROUP_BASE + len(groups)
        modules.append(_relay({f"row{i}": leaf for i, leaf in enumerate(leaves[offset:offset + 8])}, channel))
        groups.append(channel)
    modules.append(_relay({f"group{i}": channel for i, channel in enumerate(groups)}, _NEXT_LENGTH))
    return modules


def build(max_packets: int = MAX_STAGES) -> tuple[dict, dict]:
    if type(max_packets) is not int or not 1 <= max_packets <= MAX_STAGES:
        raise ValueError(f"累计长度上限须为 1 至 {MAX_STAGES}")
    document, single = build_step()
    settle = single["settling"]["hold_signal_ticks"]
    wait_steps = (settle + _RADIO_TICKS - 1) // _RADIO_TICKS + 4
    timers, read_at, drain_at = _wait_timer(_PHASE, _TIMER_CHANNELS, wait_steps, _DRAIN_STEPS)
    signals = tuple(CANDIDATE_FIELDS)
    copy_fields = [Module({name: CANDIDATE_FIELDS[name] for name in fields})
                   for fields in (signals[:3], signals[3:])]
    for board in copy_fields:
        for name in board.inputs:
            board.outputs[_gate(board, "If", f"copy_{name}", name, 1)] = _INPUTS[name]
    slots = {name: _INPUTS[name] for name in _SLOT_NAMES}
    commit = Module({"phase": _PHASE, "enable": _ENABLE})
    selected = _compare(commit, "writing", "phase", 2)
    enabled = _compare(commit, "enabled", "enable", 1)
    commit.outputs = {_gate(commit, "And", "commit", selected, enabled): _COMMIT}
    registers = [_register(_ENABLE, _COMMIT, channel, _OUTPUTS[name], None) for name, channel in slots.items()]
    registers.extend((_register(_ENABLE, _COMMIT, _LAST, CANDIDATE_ADDRESS, None),
                      _register(_ENABLE, _COMMIT, _LENGTH, _NEXT_LENGTH, 0)))
    modules = [*copy_fields, _classify(max_packets), _sequence(read_at, drain_at), commit, _bridge_ports(),
               *registers, *_completions(slots), *_count(max_packets), *timers]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    _append(document, platforms)
    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    inputs = {**CANDIDATE_FIELDS, "address": CANDIDATE_ADDRESS, "enable": _ENABLE, "done": _DONE, "target": _TARGET}
    outputs = {"ack": _ACK, "length": _LENGTH, "finished": _FINISHED, "accepted": _ACCEPTED, "result": _RESULT,
               "fault": _FAULT, "next_address": _NEXT_ADDRESS}
    if receivers.keys() - senders.keys() != set(inputs.values()) or any(count != 1 for count in senders.values()):
        raise ValueError("整单虚拟回放的外部频道或发射器不符")
    report = {"inputs": inputs, "outputs": outputs, "maximum_length": max_packets,
              "reserved_channels": [1702700, 1702849], "timing": {"reset_hold_signal_ticks": _RESET_TICKS,
              "step_hold_signal_ticks": settle, "settle_phase_signal_ticks": wait_steps * _RADIO_TICKS,
              "commit_drain_signal_ticks": _DRAIN_STEPS * _RADIO_TICKS}, "platforms": len(wiring.platforms),
              "building_entries": len(wiring.entries), "global_transmitters": len(senders)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出整单虚拟回放、地址确认及成品核对")
    parser.add_argument("--max-packets", type=int, default=MAX_STAGES, help="订单累计长度上限")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.max_packets)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
