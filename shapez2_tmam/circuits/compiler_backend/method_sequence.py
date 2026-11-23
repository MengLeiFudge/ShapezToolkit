"""串行调用子方法，并将完成确认绑定到发起调用的阶段。"""

import argparse
from collections import Counter
from pathlib import Path

from ...mari.blueprint import _kind
from ...mari.signals import decode_constant

from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .confirmed_call import build as build_confirmed_call
from .module_caller import _RADIO_TICKS, _WAIT_RADIX, _check_channel, _compare, _gate, _local_wiring, _wait_timer
from .prefix_scan_wiring import _append, _native_wiring, _report


_PHASE, _KIND = 1701690, 1701691
_ENABLE, _SETTLED, _CONFIRMED = 1701695, 1701696, 1701697
_NEXT, _DONE = 1701698, 1701699
_DEFAULT_BASE = 1702070
_DEFAULT_METHODS = tuple((kind, 1702050 + 2 * kind, 1702051 + 2 * kind, 256, 160)
                         for kind in range(1, 6))


def _dispatch(request, opcode, address, methods):
    board = Module({"phase": _PHASE, "kind": _KIND, "request": request})
    board.outputs[_gate(board, "If", "address", "phase", 1)] = address
    matching = _compare(board, "matching", "phase", "request")
    present = _compare(board, "present", "request", 0, "Ag==")
    active = _gate(board, "And", "active", matching, present)
    skip = _compare(board, "skip", "kind", 0)
    board.outputs[_gate(board, "If", "opcode", 1, _gate(board, "Not", "needs_call", skip))] = opcode
    for kind, attempt in methods:
        selected = _compare(board, f"kind_{kind}", "kind", kind)
        launch = _gate(board, "And", f"launch_{kind}", selected, active)
        board.outputs[_gate(board, "If", f"attempt_{kind}", "request", launch)] = attempt
    return board


def _method(attempt, started, reset, sampled, run, done, ack):
    board = Module({"attempt": attempt, "started": started, "reset": reset, "sampled": sampled,
                    "done": done, "enable": _ENABLE})
    present = _compare(board, "present", "attempt", 0, "Ag==")
    valid = _gate(board, "And", "valid", present, _compare(board, "enabled", "enable", 1))
    live = _compare(board, "live", "started", "attempt")
    running = _gate(board, "And", "run", valid, live)
    reset_elapsed = _compare(board, "reset_elapsed", "reset", "attempt")
    cleared = _compare(board, "cleared", "done", 0)
    ready = _gate(board, "And", "ready", reset_elapsed, cleared)
    start = _gate(board, "And", "start", ready, valid)
    remember = _gate(board, "Or", "remember", start, running)
    board.outputs[_gate(board, "If", "started_out", "attempt", remember)] = started
    board.outputs[running] = run
    elapsed = _compare(board, "elapsed", "sampled", "attempt")
    finished = _compare(board, "finished", "done", 1)
    accepted = _gate(board, "And", "accepted", running, _gate(board, "And", "complete", elapsed, finished))
    board.outputs[_gate(board, "If", "ack", "attempt", accepted)] = ack
    return board


def _collect(channels, ack):
    board = Module({f"ack{i}": channel for i, channel in enumerate(channels)})
    for name in board.inputs:
        _gate(board, "If", "ack", name, 1)
    board.outputs = {"ack": ack}
    return board


def build(methods, *, channel_base: int, settle_ticks: int, update_ticks: int) -> tuple[dict, dict]:
    methods = tuple(sorted(methods))
    kinds = [kind for kind, _, _, _, _ in methods]
    if not 1 <= len(kinds) <= 5 or len(set(kinds)) != len(kinds) or any(kind not in range(1, 6) for kind in kinds):
        raise ValueError("需配置 1 至 5 个互不重复的 kind，编号为 1 至 5")
    public = [_PHASE, _KIND, _ENABLE, _SETTLED, _CONFIRMED, _NEXT, _DONE]
    public.extend(run for _, run, _, _, _ in methods)
    done_channels = {done for _, _, done, _, _ in methods}
    if len(public) != len(set(public)) or done_channels.intersection(public):
        raise ValueError("主控与子方法频道发生重叠")
    public.extend(sorted(done_channels))
    for channel in public:
        _check_channel(channel)

    request, ack, opcode, has_packet, address = range(channel_base, channel_base + 5)
    clock_base = channel_base + 5
    document, clock = build_confirmed_call(
        enable=_ENABLE, address=address, ack=ack, finished=_DONE, opcode=opcode,
        settled=_SETTLED, has_packet=has_packet, confirmed=_CONFIRMED, request=request,
        states={"phase": (_PHASE, _NEXT, 0)}, settle_ticks=settle_ticks, update_ticks=update_ticks,
        channel_base=clock_base,
    )
    next_channel = clock["reserved_channels"][-1] + 1

    def reserve(count):
        nonlocal next_channel
        channels = tuple(range(next_channel, next_channel + count))
        next_channel += count
        return channels

    def wait(phase, ticks):
        steps = (ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 2
        width = steps if steps <= 3 else 4 if steps <= _WAIT_RADIX else 5
        boards, ready, _ = _wait_timer(phase, reserve(width), steps, 1)
        return boards, ready, steps * _RADIO_TICKS

    dispatch, returns, modules, method_ports = [], [], [], {}
    for kind, run, done, reset_ticks, sample_ticks in methods:
        if any(type(ticks) is not int or not 1 <= ticks <= (_WAIT_RADIX ** 2 - 2) * _RADIO_TICKS
               for ticks in (reset_ticks, sample_ticks)):
            raise ValueError(f"kind {kind} 的复位和采样保持期超出计数器范围")
        attempt, started, reply = reserve(3)
        reset_boards, reset, reset_wait = wait(attempt, reset_ticks)
        sample_boards, sampled, sample_wait = wait(started, sample_ticks)
        modules.extend((*reset_boards, *sample_boards, _method(attempt, started, reset, sampled, run, done, reply)))
        dispatch.append((kind, attempt))
        returns.append(reply)
        method_ports[str(kind)] = {"run": run, "done": done, "reset_hold_signal_ticks": reset_ticks,
                                   "start_to_sample_signal_ticks": sample_ticks,
                                   "reset_timer_signal_ticks": reset_wait, "sample_timer_signal_ticks": sample_wait}

    last = next_channel - 1
    _check_channel(last)
    if any(channel_base <= ch <= last for ch in public):
        raise ValueError("公开频道进入了确认器的专用频道范围")
    modules.extend((_dispatch(request, opcode, address, dispatch), _collect(returns, ack)))
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    _append(document, platforms)
    wiring = _local_wiring(document["BP"])
    report = {
        "inputs": {"enable": _ENABLE, "kind": _KIND, "next": _NEXT, "done": _DONE},
        "outputs": {"phase": _PHASE, "settled": _SETTLED, "confirmed": _CONFIRMED},
        "methods": method_ports,
        "request_address": request, "ack_address": ack, "reserved_channels": [channel_base, last],
        "timing": {**clock["timing"], "reset_hold_signal_ticks": max(clock["timing"]["reset_hold_signal_ticks"],
                                                                    6 * _RADIO_TICKS)},
        "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
    }
    return document, report


def _radio_channels(wiring):
    receivers, senders = Counter(), Counter()
    for index, (_, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind not in ("ControlledSignalReceiver", "ControlledSignalTransmitter"):
            continue
        (source, _), = wiring.sources(index, 0)
        channel = decode_constant(wiring.entries[source][1]["C"])
        _check_channel(channel)
        (receivers if kind == "ControlledSignalReceiver" else senders)[channel] += 1
    return receivers, senders


def _attach_pair_job(document: dict, report: dict, root: Path) -> None:
    arguments = {"phase": _PHASE, "h0": 1700766, "h1": 1700767, "h2": 1700768, "h3": 1700769,
                 "alternate": 1700871}
    cursor = {"phase": _PHASE, "enable": _ENABLE, "settled": _SETTLED, "kind": _KIND, "confirmed": _CONFIRMED}
    parts = (
        ("pair-job", arguments, {"kind": _KIND, "column": 1700873, "destination": 1701692}),
        ("pair-job-inputs", arguments, {"left": 1701693, "right": 1701694}),
        ("pair-job-cursor", cursor, {"next": _NEXT, "done": _DONE}),
    )
    timings = {}
    for name, inputs, outputs in parts:
        path = root / f"{name}.spz2bp"
        interface = _report(path)
        ports = [{name: port["channel"] for name, port in interface[side].items()}
                 for side in ("inputs", "outputs")]
        wiring = _native_wiring(path)
        receivers, senders = _radio_channels(wiring)
        if ports != [inputs, outputs] or receivers.keys() != set(inputs.values()) or senders != Counter(outputs.values()):
            raise ValueError(f"{name} 的原生频道或接口表与主控接线不符")
        timings[name] = interface["settling"]["hold_signal_ticks"]
        _append(document, wiring.platforms)
    if (report["timing"]["input_hold_signal_ticks"] < max(timings["pair-job"], timings["pair-job-inputs"])
            or report["timing"]["update_hold_signal_ticks"] < timings["pair-job-cursor"]):
        raise ValueError("确认器等待时间低于主控接口表的稳定上界")

    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    duplicates = sorted(channel for channel, count in senders.items() if count > 1)
    if duplicates:
        raise ValueError(f"合装频道有重复发射器 {duplicates}")
    report["inputs"] = {"enable": _ENABLE, **{name: ch for name, ch in arguments.items() if name != "phase"}}
    for _, _, outputs in parts:
        report["outputs"].update(outputs)
    external = set(report["inputs"].values()) | {ports["done"] for ports in report["methods"].values()}
    if receivers.keys() - senders.keys() != external or senders.keys() & external:
        raise ValueError("合装的外部输入与实际收发不符")
    report["pair_job_hold_signal_ticks"] = timings
    report["platforms"], report["building_entries"] = len(wiring.platforms), len(wiring.entries)
    report["global_receivers"], report["global_transmitters"] = sum(receivers.values()), len(senders)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出串行子方法启动与阶段确认器")
    parser.add_argument("--method", action="append", type=int, nargs=5,
                        metavar=("KIND", "RUN", "DONE", "RESET_TICKS", "SAMPLE_TICKS"),
                        help="子方法编号、启停和完成频道、复位和采样保持期，可重复")
    parser.add_argument("--channel-base", type=int, default=_DEFAULT_BASE, help="确认器首个专用频道")
    parser.add_argument("--settle-ticks", type=int, default=1536, help="阶段参数的稳定时间")
    parser.add_argument("--update-ticks", type=int, default=1536, help="主控 next 的稳定时间")
    parser.add_argument("--pair-job-dir", type=Path, help="合装 pair-job、pair-job-inputs 和 pair-job-cursor 的蓝图目录")
    parser.add_argument("--output", type=Path, required=True, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.method or _DEFAULT_METHODS, channel_base=args.channel_base,
                                 settle_ticks=args.settle_ticks, update_ticks=args.update_ticks)
        if args.pair_job_dir is not None:
            _attach_pair_job(document, report, args.pair_job_dir)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
