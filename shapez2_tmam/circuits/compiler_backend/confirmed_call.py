"""按稳定时间和地址确认复用组合状态更新板。"""

import argparse
import json
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .module_caller import _RADIO_TICKS, _WAIT_RADIX, _any, _check_channel, _compare, _gate, _local_wiring, _wait_timer


def _on(board: Module, signal: str) -> str:
    return _compare(board, f"{signal}_on", signal, 1)


def _choose(enable, stage, stable, packet, finished, address, action, held):
    board = Module({"enable": enable, "stage": stage, "stable": stable, "packet": packet,
                    "finished": finished, "address": address, "held": held})
    enabled = _on(board, "enable")
    settling = _compare(board, "settling", "stage", 0)
    elapsed = _compare(board, "elapsed", "stable", 0)
    ready = _gate(board, "And", "ready", settling, elapsed)
    open_ = _gate(board, "And", "open", enabled, _gate(board, "Not", "unfinished", _on(board, "finished")))
    choose = _gate(board, "And", "choose", ready, open_)
    packet_on = _on(board, "packet")
    valid_address = _compare(board, "valid_address", "address", 0, "Ag==")
    issue = _gate(board, "And", "issue", choose, _gate(board, "And", "addressed", packet_on, valid_address))
    skip = _gate(board, "And", "skip", choose, _compare(board, "empty", "packet", 0))
    _gate(board, "If", "action", 1, issue)
    _gate(board, "If", "action", 2, skip)
    _gate(board, "If", "address_out", "address", issue)
    keep = _gate(board, "And", "keep", enabled, _gate(board, "Not", "not_issuing", issue))
    _gate(board, "If", "address_out", "held", keep)
    board.outputs = {"action": action, "address_out": held}
    return board


def _sequence(enable, stage, action, update_ready, ack, held):
    board = Module({"enable": enable, "stage": stage, "action": action, "elapsed": update_ready,
                    "ack": ack, "held": held})
    # 0 稳定输入，1 等旧确认撤销，6 发送并等匹配确认。2/3 计算，4/5 提交。
    phases = tuple(_compare(board, f"stage{i}", "stage", i) for i in range(7))
    enabled = _on(board, "enable")
    _gate(board, "If", "next", 0, _compare(board, "initial", "stage", -1))
    _gate(board, "If", "next", "action", _gate(board, "And", "chosen", phases[0], "action"))
    matched = _compare(board, "matched", "ack", "held")
    accepting = _gate(board, "And", "accepting", phases[1], _gate(board, "Not", "ack_cleared", matched))
    _gate(board, "If", "next", 6, accepting)
    _gate(board, "If", "next", 3, _gate(board, "And", "confirmed", phases[6], matched))
    elapsed = _compare(board, "update_stable", "elapsed", "stage")
    for phase in (2, 3):
        _gate(board, "If", "next", phase + 2, _gate(board, "And", f"ready{phase}", phases[phase], elapsed))
    _gate(board, "If", "next", 0, _gate(board, "Or", "committing", phases[4], phases[5]))
    change = _compare(board, "change", "next", None, "Bg==")
    _gate(board, "If", "stage_out", "next", _gate(board, "And", "advance", enabled, change))
    _gate(board, "If", "stage_out", "stage", _gate(board, "And", "keep", enabled,
                                                   _gate(board, "Not", "keep_current", change)))
    _gate(board, "If", "stage_out", -1, _gate(board, "Not", "disabled", enabled))
    board.outputs = {"stage_out": stage}
    return board


def _protocol(enable, stage, held, settled, confirmed, commit, request):
    board = Module({"enable": enable, "stage": stage, "held": held})
    enabled = _on(board, "enable")
    update = _compare(board, "update", "stage", 2, "Ag==")
    issuing = _compare(board, "issuing", "stage", 6)
    computing = _gate(board, "And", "computing", update, _gate(board, "Not", "not_issuing", issuing))
    board.outputs[_gate(board, "And", "settled", enabled, computing)] = settled
    sent = tuple(_compare(board, f"sent{i}", "stage", i) for i in (3, 5))
    board.outputs[_gate(board, "And", "confirmed", enabled, _any(board, "sent", sent))] = confirmed
    ready = tuple(_compare(board, f"commit{i}", "stage", i) for i in (4, 5))
    board.outputs[_gate(board, "And", "commit", enabled, _any(board, "load", ready))] = commit
    board.outputs[_gate(board, "If", "request", "held", _gate(board, "And", "send", enabled, issuing))] = request
    return board


def _register(enable, commit, target, next_value, initial):
    board = Module({"enable": enable, "commit": commit, "value": target, "next": next_value})
    enabled = _on(board, "enable")
    _gate(board, "If", "value_out", initial, _gate(board, "Not", "reset", enabled))
    _gate(board, "If", "value_out", "next", _gate(board, "And", "load", enabled, "commit"))
    _gate(board, "If", "value_out", "value", _gate(board, "And", "keep", enabled,
                                                   _gate(board, "Not", "no_commit", "commit")))
    board.outputs = {"value_out": target}
    return board


def _packet_flag(opcode, valid):
    board = Module({"opcode": opcode})
    board.outputs[_compare(board, "has_packet", "opcode", None, "Bg==")] = valid
    return board


def build(*, enable: int, address: int, ack: int, finished: int, opcode: int,
          settled: int, has_packet: int, confirmed: int, request: int, states: dict,
          settle_ticks: int, update_ticks: int, channel_base: int) -> tuple[dict, dict]:
    """输出同拍提交多个整数状态的控制蓝图及接线表。"""
    if not 1 <= len(states) <= 8:
        raise ValueError("需指定 1～8 个整数状态")
    for wait in (settle_ticks, update_ticks):
        if type(wait) is not int or not 1 <= wait <= (_WAIT_RADIX ** 2 - 2) * _RADIO_TICKS:
            raise ValueError("输入与下一状态的稳定期须在计数器范围内")
    public = [enable, address, ack, finished, opcode, settled, has_packet, confirmed, request]
    for value, next_value, initial in states.values():
        public.extend((value, next_value))
        if type(initial) is not int or not -(1 << 31) <= initial < 1 << 31:
            raise ValueError("状态初值须为有符号 32 位整数")
    if len(public) != len(set(public)):
        raise ValueError("公开频道须独占")
    stage, action, held, commit = range(channel_base, channel_base + 4)
    settle_steps = (settle_ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 2
    update_steps = (update_ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 1
    width = max(settle_steps, update_steps)
    timer_count = width if width <= 3 else 5 if width > _WAIT_RADIX else 4
    timer_channels = tuple(range(commit + 1, commit + 1 + timer_count))
    private = range(channel_base, timer_channels[-1] + 1)
    for ch in (*public, private.start, private.stop - 1):
        _check_channel(ch)
    if any(ch in private for ch in public):
        raise ValueError("调用器内部频道和公开频道重叠")
    timers, stable, update_ready = _wait_timer(stage, timer_channels, settle_steps, update_steps)
    modules = [_choose(enable, stage, stable, has_packet, finished, address, action, held),
               _sequence(enable, stage, action, update_ready, ack, held),
               _protocol(enable, stage, held, settled, confirmed, commit, request),
               _packet_flag(opcode, has_packet), *timers]
    modules.extend(_register(enable, commit, *state) for state in states.values())
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    wiring = _local_wiring(document["BP"])
    report = {
        "inputs": {"enable": enable, "address": address, "ack_address": ack, "done": finished, "opcode": opcode},
        "outputs": {"settled": settled, "has_packet": has_packet, "confirmed": confirmed, "request_address": request},
        "states": {name: {"current": value, "next": next_value, "initial": initial}
                   for name, (value, next_value, initial) in states.items()},
        "reserved_channels": [private.start, private.stop - 1],
        "timing": {"input_hold_signal_ticks": settle_ticks, "update_hold_signal_ticks": update_ticks,
                   "settle_phase_signal_ticks": settle_steps * _RADIO_TICKS,
                   "update_phase_signal_ticks": update_steps * _RADIO_TICKS,
                   "reset_hold_signal_ticks": 4 * _RADIO_TICKS},
        "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
    }
    return document, report


def _dense(root: Path, address: int, ack: int, request: int, base: int) -> tuple[dict, dict]:
    def report(name):
        return json.loads((root / f"dense-column-{name}.json").read_text(encoding="utf-8-sig"))

    select, packet, phase, level = (report(name) for name in ("input", "packet", "advance-phase", "advance-level"))
    controls = {name: port["channel"] for name, port in phase["inputs"].items()}
    if controls != {name: port["channel"] for name, port in level["inputs"].items()}:
        raise ValueError("紧柱的两个下一状态板须接同一组控制和旧状态")
    if (controls["phase"] != packet["inputs"]["phase"]["channel"]
            or controls["level"] != select["inputs"]["level"]["channel"]
            or any(port["channel"] != packet["inputs"][name]["channel"] for name, port in select["outputs"].items())):
        raise ValueError("紧柱选层和指令板与旧状态频道不匹配")
    settle_ticks = sum(r["settling"]["hold_signal_ticks"] for r in (select, packet))
    update_ticks = max(r["settling"]["hold_signal_ticks"] for r in (phase, level))
    states = {name: (controls[name], r["outputs"][name]["channel"], 0)
              for name, r in (("phase", phase), ("level", level))}
    return build(enable=controls["enable"], address=address, ack=ack, finished=phase["outputs"]["done"]["channel"],
                 opcode=packet["outputs"]["opcode"]["channel"], settled=controls["settled"],
                 has_packet=controls["has_packet"], confirmed=controls["confirmed"], request=request, states=states,
                 settle_ticks=settle_ticks, update_ticks=update_ticks, channel_base=base)


def main() -> int:
    parser = argparse.ArgumentParser(description="导出紧柱的稳定后地址确认控制器")
    parser.add_argument("--circuits", required=True, type=Path, help="紧柱电路的接口表目录")
    parser.add_argument("--address-channel", required=True, type=int, help="主控的待写地址频道")
    parser.add_argument("--ack-channel", required=True, type=int, help="当前写入完成后的地址回报频道")
    parser.add_argument("--request-channel", required=True, type=int, help="发布已就绪请求地址的频道")
    parser.add_argument("--channel-base", required=True, type=int, help="控制器的首个专用频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = _dense(args.circuits, args.address_channel, args.ack_channel,
                                  args.request_channel, args.channel_base)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
