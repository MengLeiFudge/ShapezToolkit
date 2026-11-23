"""让同一配方主控先做虚拟验收，再向实体工段提交。"""

import argparse
from pathlib import Path

from ...mari.signals import decode_constant
from ...synthesis.physics import Rules
from ..circuit import Literal, constant
from ..circuit_packing import stack_platforms
from ..factory_assembly.changeover import LOADED
from ..factory_assembly.interface import OPERATOR_INPUTS, ORDER_INPUTS, WRITE_STATUS
from ..factory_assembly.mixed_sample import ORDERS
from ..factory_assembly.recipe import MAX_STAGES
from ..factory_assembly.submit_bridge import CANDIDATE_ADDRESS, CANDIDATE_FIELDS
from ..factory_assembly.submit_bridge import build as build_submit
from ..local_module import Module
from ..stage_writer import WRITE_RESET
from . import _write_blueprint
from .auto_prefix_scan import _radio_ports
from .confirmed_call import _register
from .method_sequence import _DONE, _ENABLE, _radio_channels
from .module_caller import _RADIO_TICKS, _compare, _gate, _local_wiring, _wait_timer
from .prefix_scan_wiring import _append, _native_wiring
from .virtual_recipe_replay import build as build_replay


_BATCH, _FEED_REQUEST, _PHASE, _FAULT, _FINISHED = range(1702850, 1702855)
_METHOD_RUN, _VIRTUAL_RUN, _VIRTUAL_MODE, _PHYSICAL_MODE = range(1702855, 1702859)
_BUS_ADDRESS, _BUS_REQUEST, _BUS_ACK, _BUS_RESET, _BUS_RUN = range(1702860, 1702865)
_TARGET, _LIVE, _VERIFY, _FACTORY_READY, _CAPTURE = range(1702865, 1702870)
_SAVED_LENGTH, _SAVED_RESULT, _SAVED_ACCEPTED, _LAST_SAMPLE = range(1702870, 1702874)
_NEXT_PHASE, _SUBMIT_RESET = 1702874, 1702875
_TIMER = tuple(range(1702880, 1702884))
_RESET_TICKS = 192
_RESET_STEPS = _RESET_TICKS // _RADIO_TICKS + 2
_HANDOFF_STEPS = 18
_HOLD_TICKS = 384
_FACTORY_RUN = OPERATOR_INPUTS["run"]
_INPUT_TARGET = ORDER_INPUTS["target"]
_WRITER_INPUTS = {_ENABLE: _METHOD_RUN, _FACTORY_RUN: _BUS_RUN, WRITE_RESET: _BUS_RESET,
                  WRITE_STATUS["address"]: _BUS_ADDRESS, WRITE_STATUS["request"]: _BUS_REQUEST,
                  WRITE_STATUS["ack"]: _BUS_ACK}


def _freeze_target() -> Module:
    board = Module({"target": _INPUT_TARGET, "saved": _TARGET, "batch": _BATCH})
    armed = _compare(board, "armed", "batch", 1)
    empty = _compare(board, "empty", "saved", None)
    retain = _gate(board, "Not", "occupied", empty)
    _gate(board, "If", "latched", "target", _gate(board, "And", "capture", armed, empty))
    _gate(board, "If", "latched", "saved", _gate(board, "And", "retain", armed, retain))
    same = _compare(board, "same", "target", "saved")
    matched = _gate(board, "And", "matched", same, retain)
    board.outputs = {"latched": _TARGET, _gate(board, "And", "live", armed, matched): _LIVE}
    return board


def _verify(replay: dict) -> Module:
    board = Module({"finished": replay["finished"], "accepted": replay["accepted"], "result": replay["result"],
                    "length": replay["length"], "fault": replay["fault"], "target": _TARGET})
    finished = _compare(board, "complete", "finished", 1)
    same = _compare(board, "same", "result", "target")
    wrote = _compare(board, "wrote", "length", 0, "Aw==")
    accepted = _compare(board, "accepted_flag", "accepted", 1)
    passed = _gate(board, "And", "passed", accepted, _gate(board, "And", "shape_ok", same, wrote))
    failed = _gate(board, "And", "failed", finished, _gate(board, "Not", "no_pass", passed))
    _gate(board, "If", "verified", 1, _gate(board, "And", "pass_result", finished, passed))
    _gate(board, "If", "verified", 2, _gate(board, "Or", "fail_result", failed, "fault"))
    board.outputs = {"verified": _VERIFY}
    return board


def _factory_ready() -> Module:
    board = Module({"clean": OPERATOR_INPUTS["clean_confirmed"], "loaded": LOADED, "reset": WRITE_RESET})
    cleared = _compare(board, "cleared", "clean", 1)
    resetting = _compare(board, "resetting", "reset", 1)
    empty = _compare(board, "empty", "loaded", 0)
    board.outputs = {_gate(board, "And", "ready", cleared, _gate(board, "And", "reset_ok", resetting, empty)):
                     _FACTORY_READY}
    return board


def _sequence(reset_at: int, finish_at: int) -> tuple[Module, Module]:
    board = Module({"phase": _PHASE, "live": _LIVE, "verified": _VERIFY, "method_done": _DONE,
                    "reset_at": reset_at, "finish_at": finish_at, "ready": _FACTORY_READY, "loaded": LOADED})
    boot, virtual, reset, physical, drain = tuple(_compare(board, f"phase{i}", "phase", i) for i in range(5))
    passed = _compare(board, "passed", "verified", 1)
    failed = _compare(board, "failed", "verified", 2)
    done = _compare(board, "method_done_flag", "method_done", 1)
    method_reset = _compare(board, "method_reset", "method_done", 0)
    reset_elapsed = _compare(board, "reset_elapsed", "reset_at", 2)
    drains_done = _compare(board, "drains_done", "finish_at", 4)
    ready = _gate(board, "And", "ready_when_reset", "ready", method_reset)
    restart = _gate(board, "And", "restart", ready, reset_elapsed)
    checked = _gate(board, "And", "checked", drain, drains_done)
    loaded = _compare(board, "loaded_flag", "loaded", 1)
    transitions = ((1, boot, "live"), (2, virtual, passed), (3, reset, restart), (4, physical, done),
                   (5, checked, loaded), (6, virtual, failed),
                   (6, checked, _gate(board, "Not", "not_loaded", loaded)))
    for i, (stage, before, condition) in enumerate(transitions):
        _gate(board, "If", "step", stage, _gate(board, "And", f"transition{i}", before, condition))
    board.outputs = {"step": _NEXT_PHASE}

    state = Module({"batch": _BATCH, "state": _PHASE, "step": _NEXT_PHASE, "live": _LIVE})
    enabled = _compare(state, "enabled", "batch", 1)
    running = _compare(state, "running", "state", 0, "Aw==")
    lost = _gate(state, "And", "lost", running, _gate(state, "Not", "target_gone", "live"))
    valid_step = _compare(state, "step_present", "step", None, "Bg==")
    okay = _gate(state, "Not", "okay", lost)
    _gate(state, "If", "next", "step", _gate(state, "And", "step_ok", okay, valid_step))
    hold = _gate(state, "And", "hold", okay, _gate(state, "Not", "no_step", valid_step))
    _gate(state, "If", "next", "state", hold)
    _gate(state, "If", "next", 6, lost)
    _gate(state, "If", "out", "next", enabled)
    _gate(state, "If", "out", 0, _gate(state, "Not", "reset", enabled))
    state.outputs = {"out": _PHASE}
    return board, state


def _modes() -> tuple[Module, Module]:
    board = Module({"phase": _PHASE, "live": _LIVE})
    virtual, reset, physical = (_compare(board, name, "phase", i) for i, name in
                                ((1, "virtual"), (2, "resetting"), (3, "physical")))
    writing = _gate(board, "Or", "working", virtual, physical)
    verifying = _gate(board, "Or", "verifying", virtual, reset)
    board.outputs = {_gate(board, "And", "method", writing, "live"): _METHOD_RUN,
                     _gate(board, "And", "replay", verifying, "live"): _VIRTUAL_RUN,
                     _gate(board, "And", "virtual_port", virtual, "live"): _VIRTUAL_MODE,
                     _gate(board, "And", "physical_port", physical, "live"): _PHYSICAL_MODE}

    factory = Module({"phase": _PHASE, "live": _LIVE, "feed": _FEED_REQUEST, "loaded": LOADED})
    finished = _compare(factory, "finished", "phase", 5)
    fault = _compare(factory, "fault", "phase", 6)
    at_factory = _gate(factory, "And", "factory_stage", _compare(factory, "after_reset", "phase", 3, "Ag=="),
                       _compare(factory, "before_error", "phase", 5, "BQ=="))
    run = _gate(factory, "And", "factory_run", at_factory, "live")
    complete = _gate(factory, "And", "complete", finished, "live")
    feed = _gate(factory, "And", "feed_granted", complete, _gate(factory, "And", "feed_loaded", "feed", "loaded"))
    factory.outputs = {run: _FACTORY_RUN, feed: OPERATOR_INPUTS["enable_feed"], complete: _FINISHED, fault: _FAULT}
    return board, factory


def _metadata() -> Module:
    board = Module({"run": _FACTORY_RUN, "length": _SAVED_LENGTH, "result": _SAVED_RESULT,
                    "accepted": _SAVED_ACCEPTED})
    for name in ("length", "result", "accepted"):
        key = "replay_result" if name == "result" else name
        board.outputs[_gate(board, "If", f"publish_{name}", name, "run")] = ORDER_INPUTS[key]
    return board


def _writer_ports(replay: dict) -> tuple[Module, Module, Module]:
    address = Module({"virtual": _VIRTUAL_MODE, "physical": _PHYSICAL_MODE, "virtual_ack": replay["ack"],
                      "virtual_next": replay["next_address"], "factory_address": WRITE_STATUS["address"]})
    ack_present = _compare(address, "virtual_done", "virtual_ack", None, "Bg==")
    pending = _gate(address, "Not", "use_next", ack_present)
    _gate(address, "If", "address", "virtual_ack", _gate(address, "And", "keep_ack", "virtual", ack_present))
    _gate(address, "If", "address", "virtual_next", _gate(address, "And", "take_next", "virtual", pending))
    _gate(address, "If", "address", "factory_address", "physical")
    address.outputs = {"address": _BUS_ADDRESS}

    flags = Module({"virtual": _VIRTUAL_MODE, "physical": _PHYSICAL_MODE, "virtual_ack": replay["ack"],
                    "address": _BUS_ADDRESS, "candidate": CANDIDATE_ADDRESS,
                    "factory_request": WRITE_STATUS["request"], "factory_ack": WRITE_STATUS["ack"]})
    stamped = _compare(flags, "present", "candidate", None, "Bg==")
    matching = _compare(flags, "same_address", "candidate", "address")
    virtual_request = _gate(flags, "And", "virtual_request", "virtual", _gate(flags, "And", "issued", stamped, matching))
    compare_ack = _compare(flags, "matching_ack", "virtual_ack", "address")
    virtual_ack = _gate(flags, "And", "virtual_confirmed", virtual_request, compare_ack)
    for name, flag, output in (("request", virtual_request, _BUS_REQUEST), ("ack", virtual_ack, _BUS_ACK)):
        entity = _gate(flags, "And", f"physical_{name}", "physical", f"factory_{name}")
        flags.outputs[_gate(flags, "Or", name, flag, entity)] = output

    enable = Module({"virtual": _VIRTUAL_MODE, "physical": _PHYSICAL_MODE, "factory_reset": WRITE_RESET})
    okay = _compare(enable, "open", "factory_reset", 0)
    entity = _gate(enable, "And", "factory_ready", "physical", okay)
    active = _gate(enable, "Or", "active", "virtual", entity)
    enable.outputs = {active: _BUS_RUN, _gate(enable, "Not", "reset", active): _BUS_RESET,
                      _gate(enable, "Not", "submit_reset", entity): _SUBMIT_RESET}
    return address, flags, enable


def _sample() -> tuple[list[Module], dict]:
    target, packets = ORDERS[0]
    rules = Rules(4, 5)
    last = len(packets) - 1
    status = Module({"ack": _BUS_ACK, "address": _BUS_ADDRESS, "last": _LAST_SAMPLE, "run": _METHOD_RUN})
    active = _gate(status, "And", "capture", "run", "ack")
    keep = _gate(status, "And", "keep", "run", _gate(status, "Not", "await", "ack"))
    _gate(status, "If", "last_out", "address", active)
    _gate(status, "If", "last_out", "last", keep)
    done = _compare(status, "done", "last", last)
    status.outputs = {"last_out": _LAST_SAMPLE, _gate(status, "And", "finished", done, "run"): _DONE}
    modules = [status]
    groups = (tuple(CANDIDATE_FIELDS)[:3], tuple(CANDIDATE_FIELDS)[3:])
    for group in groups:
        board = Module({"address": _BUS_ADDRESS, "last": _LAST_SAMPLE, "run": _METHOD_RUN})
        fresh = _compare(board, "fresh", "address", "last", "Bg==")
        enabled = _gate(board, "And", "enabled", "run", fresh)
        for i, packet in enumerate(packets):
            active = _gate(board, "And", f"row{i}", enabled, _compare(board, f"address{i}", "address", i))
            if group is groups[0]:
                _gate(board, "If", "stamp", "address", active)
            for name in group:
                value = packet[name]
                if value is not None:
                    signal = rules.parse(value) if name == "base" else value
                    _gate(board, "If", name, Literal(signal), active)
                    board.outputs[name] = CANDIDATE_FIELDS[name]
        if group is groups[0]:
            board.outputs["stamp"] = CANDIDATE_ADDRESS
        modules.append(board)
    return modules, {"target": target, "length": len(packets), "instructions": packets}


def _rebind(wiring, assignments: dict[int, int], *, inputs_only: bool = False) -> list[dict]:
    for kind, config in _radio_ports(wiring):
        channel = decode_constant(config["C"])
        if channel in assignments and (not inputs_only or kind.startswith("ControlledSignalReceiver")):
            config["C"] = constant(assignments[channel])
    return wiring.platforms


def build(*, writer: Path | None = None, caller: Path | None = None,
          corner_jobs: Path | None = None) -> tuple[dict, dict]:
    if (writer is None) != (caller is None) or (writer is None and corner_jobs is not None):
        raise ValueError("合装配方主控须同时指定 writer 和 caller")
    sample_mode = writer is None
    document, replay = build_replay(len(ORDERS[0][1]) if sample_mode else MAX_STAGES)
    replay_ports = replay["outputs"]
    _rebind(_local_wiring(document["BP"]), {_ENABLE: _VIRTUAL_RUN}, inputs_only=True)
    timers, reset_at, finish_at = _wait_timer(_PHASE, _TIMER, _RESET_STEPS, _HANDOFF_STEPS)
    capture = Module({"phase": _PHASE})
    capture.outputs = {_compare(capture, "copy", "phase", 2): _CAPTURE}
    registers = [_register(_BATCH, _CAPTURE, target, replay_ports[name], None)
                 for target, name in ((_SAVED_LENGTH, "length"), (_SAVED_RESULT, "result"),
                                      (_SAVED_ACCEPTED, "accepted"))]
    modules = [_freeze_target(), _verify(replay_ports), _factory_ready(), *_sequence(reset_at, finish_at),
               *timers, capture, *registers, *_modes(), _metadata(), *_writer_ports(replay_ports)]
    fixture = None
    if sample_mode:
        mock, fixture = _sample()
        modules.extend(mock)
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    _append(document, platforms)
    submit, _ = build_submit(_HOLD_TICKS)
    submit_platforms = _rebind(_local_wiring(submit["BP"]), {WRITE_RESET: _SUBMIT_RESET}, inputs_only=True)
    _append(document, submit_platforms)
    if not sample_mode:
        for path in (writer, caller, corner_jobs):
            if path is None:
                continue
            part = _native_wiring(path)
            receivers, senders = _radio_channels(part)
            required = set(CANDIDATE_FIELDS.values()) | {CANDIDATE_ADDRESS, _DONE}
            if path == writer and (not required <= senders.keys() or not _WRITER_INPUTS.keys() <= receivers.keys()):
                raise ValueError("writer 缺少六字段、候选、完工或写入握手频道")
            if path == caller and _ENABLE not in receivers:
                raise ValueError("caller 缺少方法运行频道")
            if senders.keys() & _WRITER_INPUTS.keys():
                raise ValueError("writer 或 caller 在复用的外部握手频道上重复发射")
            _append(document, _rebind(part, _WRITER_INPUTS, inputs_only=True))
    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    duplicate = sorted(ch for ch, count in senders.items() if count != 1)
    external = receivers.keys() - senders.keys()
    boundary = {_BATCH, _FEED_REQUEST, _INPUT_TARGET, OPERATOR_INPUTS["clean_confirmed"], LOADED, WRITE_RESET,
                WRITE_STATUS["address"], WRITE_STATUS["request"], WRITE_STATUS["ack"]}
    if duplicate or not boundary <= external or (sample_mode and external != boundary):
        raise ValueError(f"两遍合装的原生收发不匹配，重复频道 {duplicate}，外部频道 {sorted(external)}")
    report = {"inputs": {"start": _BATCH, "feed_request": _FEED_REQUEST, "target": _INPUT_TARGET},
              "outputs": {"status": _PHASE, "finished": _FINISHED, "fault": _FAULT},
              "factory": {"operator": OPERATOR_INPUTS, "status": WRITE_STATUS, "loaded": LOADED,
                          "reset": WRITE_RESET, "order": ORDER_INPUTS},
              "writer_mapping": _WRITER_INPUTS, "external_inputs": sorted(external),
              "timing": {"phase_reset_signal_ticks": _RESET_TICKS, "factory_submit_hold_signal_ticks": _HOLD_TICKS},
              "reserved_channels": [1702850, 1702899], "platforms": len(wiring.platforms),
              "building_entries": len(wiring.entries), "global_transmitters": len(senders)}
    if fixture is not None:
        report["sample"] = fixture
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出同一配方主控的虚拟验收与实体写入两遍调度")
    parser.add_argument("--writer", type=Path, help="原生配方写入主控")
    parser.add_argument("--caller", type=Path, help="配方方法确认器原生蓝图")
    parser.add_argument("--corner-jobs", type=Path, help="与配方主控合装的制角子步骤排程")
    parser.add_argument("--output", required=True, type=Path, help="原生蓝图输出路径。省略主控参数导出固定含晶样件")
    args = parser.parse_args()
    try:
        document, report = build(writer=args.writer, caller=args.caller, corner_jobs=args.corner_jobs)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
