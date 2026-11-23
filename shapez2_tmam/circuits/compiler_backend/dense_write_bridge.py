"""将紧柱六字段调用接到实体工道的提交桥与回读。"""

import argparse
import json
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..factory_assembly.interface import FIELDS, OPERATOR_INPUTS, ORDER_INPUTS, WRITE_STATUS
from ..factory_assembly.submit_bridge import CANDIDATE_ADDRESS, CANDIDATE_FIELDS
from ..local_module import Module
from ..stage_writer import WRITE_RESET
from . import _write_blueprint
from .module_caller import _check_channel, _compare, _gate, _local_wiring


def _address_ports(enable, caller_address, caller_request, eligible):
    board = Module({"enable": enable, "public": WRITE_STATUS["address"], "request": caller_request})
    enabled = _compare(board, "enabled", "enable", 1)
    live = _compare(board, "live", "public", 0, "Ag==")
    addressed = _gate(board, "And", "addressed", enabled, live)
    matched = _compare(board, "matched", "public", "request")
    publish = _gate(board, "And", "publish", addressed, matched)
    board.outputs[_gate(board, "If", "address_out", "public", addressed)] = caller_address
    board.outputs[_gate(board, "If", "eligible", "request", publish)] = eligible
    return board


def _enable(enable):
    board = Module({"run": OPERATOR_INPUTS["run"], "reset": WRITE_RESET})
    running = _compare(board, "running", "run", 1)
    released = _compare(board, "released", "reset", 0)
    board.outputs[_gate(board, "And", "enable", running, released)] = enable
    return board


def _fields(fields, eligible, *, publish_address):
    board = Module({**fields, "eligible": eligible})
    active = _compare(board, "active", "eligible", None, "Bg==")
    for name in fields:
        board.outputs[_gate(board, "If", name + "_out", name, active)] = CANDIDATE_FIELDS[name]
    if publish_address:
        board.outputs[_gate(board, "If", "stamp", "eligible", active)] = CANDIDATE_ADDRESS
    return board


def _ack_inputs(enable, caller_request):
    return {"enable": enable, "public": WRITE_STATUS["address"], "request": caller_request,
            "writing": WRITE_STATUS["request"], "ack": WRITE_STATUS["ack"]}


def _writing_request(board):
    live = _compare(board, "live", "request", 0, "Ag==")
    matched = _compare(board, "matched", "public", "request")
    writing = _compare(board, "active_writer", "writing", 1)
    addressed = _gate(board, "And", "addressed", live, matched)
    return _gate(board, "And", "writing_request", addressed, writing)


def _arm(enable, caller_request, armed):
    board = Module({**_ack_inputs(enable, caller_request), "armed": armed})
    writing = _writing_request(board)
    ack_low = _compare(board, "ack_low", "ack", 0)
    observed = _gate(board, "And", "observed", writing, ack_low)
    keep = _compare(board, "keep", "armed", "request")
    ready = _gate(board, "Or", "ready", observed, keep)
    valid = _gate(board, "And", "valid", ready, "enable")
    board.outputs[_gate(board, "If", "armed_out", "request", valid)] = armed
    return board


def _ack_address(enable, caller_request, caller_ack, armed):
    board = Module({**_ack_inputs(enable, caller_request), "armed": armed, "stored": caller_ack})
    writing = _writing_request(board)
    ack_high = _compare(board, "ack_high", "ack", 1)
    armed_for_request = _compare(board, "armed_for_request", "armed", "request")
    capture = _gate(board, "And", "capture", writing, _gate(board, "And", "confirmed", ack_high, armed_for_request))
    # 工道换到下一地址后，调用器仍需收到已确认的旧地址。
    keep = _compare(board, "keep", "stored", "request")
    ready = _gate(board, "Or", "ready", capture, keep)
    valid = _gate(board, "And", "valid", ready, "enable")
    board.outputs[_gate(board, "If", "ack_address", "request", valid)] = caller_ack
    return board


def build(caller: dict, packet: dict, channel_base: int) -> tuple[dict, dict]:
    inputs = caller["inputs"]
    enable, address, ack = (inputs[name] for name in ("enable", "address", "ack_address"))
    request = caller["outputs"]["request_address"]
    fields = {name: packet["outputs"][name]["channel"] for name in FIELDS}
    if fields["opcode"] != inputs["opcode"]:
        raise ValueError("配方工序与确认调用的输入频道不匹配")
    eligible, armed = range(channel_base, channel_base + 2)
    channels = [enable, address, ack, request, *fields.values(), *CANDIDATE_FIELDS.values(), CANDIDATE_ADDRESS,
                *WRITE_STATUS.values(), *OPERATOR_INPUTS.values(), *ORDER_INPUTS.values(), WRITE_RESET, eligible, armed]
    for channel in channels:
        _check_channel(channel)
    if len(channels) != len(set(channels)):
        raise ValueError("紧柱、工道和适配板的频道重叠")
    caller_start, caller_stop = caller["reserved_channels"]
    used = set(range(caller_start, caller_stop + 1)) | set(packet["reserved_channels"])
    used.update(caller["inputs"].values(), caller["outputs"].values())
    for state in caller["states"].values():
        used.update((state["current"], state["next"]))
    if {eligible, armed} & used:
        raise ValueError("适配板专用频道与确认调用或紧柱字段重叠")
    first = tuple(fields)[:3]
    modules = [_enable(enable), _address_ports(enable, address, request, eligible),
               _fields({name: fields[name] for name in first}, eligible, publish_address=True),
               _fields({name: ch for name, ch in fields.items() if name not in first}, eligible, publish_address=False),
               _arm(enable, request, armed), _ack_address(enable, request, ack, armed)]
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    wiring = _local_wiring(document["BP"])
    report = {
        "inputs": {"run": OPERATOR_INPUTS["run"], "write_reset": WRITE_RESET, "write_address": WRITE_STATUS["address"],
                   "write_request": WRITE_STATUS["request"], "write_ack": WRITE_STATUS["ack"],
                   "caller_request_address": request, "packet": fields},
        "outputs": {"caller_enable": enable, "caller_address": address, "caller_ack_address": ack,
                    "candidate_address": CANDIDATE_ADDRESS, "candidate_fields": CANDIDATE_FIELDS},
        "reserved_channels": [eligible, armed],
        "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出紧柱六字段与实体写入地址确认的适配板")
    parser.add_argument("--circuits", required=True, type=Path, help="紧柱字段及确认调用接口表所在目录")
    parser.add_argument("--channel-base", required=True, type=int, help="适配板首个专用频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        caller, packet = (json.loads((args.circuits / f"{name}.json").read_text(encoding="utf-8-sig"))
                          for name in ("dense-confirmed-call", "dense-column-packet"))
        document, report = build(caller, packet, args.channel_base)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
