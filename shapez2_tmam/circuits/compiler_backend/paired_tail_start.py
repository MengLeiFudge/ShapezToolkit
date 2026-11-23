"""等闭包掩码和半形拼接稳定后启动五轮尾料回放。"""

import argparse
import json
from pathlib import Path

from ..circuit_packing import stack_platforms
from ..local_module import Module
from . import _write_blueprint
from .module_caller import _RADIO_TICKS, _WAIT_RADIX, _check_channel, _compare, _gate, _local_wiring, _wait_timer


def _report(root: Path, name: str) -> dict:
    return json.loads((root / f"{name}.json").read_text(encoding="utf-8-sig"))


def _delay(phase: int, wait: int) -> tuple[list[Module], int, int]:
    steps = (wait + _RADIO_TICKS - 1) // _RADIO_TICKS
    if not 1 <= steps <= _WAIT_RADIX ** 2:
        raise ValueError("尾料启动等待超出计数器范围")
    width = steps if steps <= 3 else 5 if steps > _WAIT_RADIX else 4
    last = phase + width
    boards, ready, _ = _wait_timer(phase, tuple(range(phase + 1, last + 1)), steps, 1)
    return boards, ready, last


def build(root: Path, halves_ready: int, channel_base: int) -> tuple[dict, dict]:
    closure = _report(root, "paired-prefix-scan")
    upstream = _report(root, "read-four-columns")
    replay = _report(root, "replay-paired-tail")
    mask = _report(root, "mask-paired-tail")
    join = _report(root, "join-oriented-halves")
    enable = upstream["inputs"]["enable"]["channel"]
    closed = closure["outputs"]["done"]["channel"]
    run = replay["inputs"]["run"]["channel"]
    heights = {closure["outputs"][f"result_h{i}"]["channel"] for i in range(4)}
    if ({port["channel"] for port in mask["inputs"].values()} != heights
            or mask["outputs"]["mask"]["channel"] != replay["inputs"]["initial_mask"]["channel"]
            or join["outputs"]["lower"]["channel"] != replay["inputs"]["initial_replay"]["channel"]):
        raise ValueError("闭包、尾料掩码、半形拼接与尾料回放的端口不匹配")
    reset = replay["timing"]["reset_hold_signal_ticks"]
    mask_wait = mask["settling"]["hold_signal_ticks"]
    join_wait = join["settling"]["hold_signal_ticks"]
    mask_phase = channel_base
    mask_timer, mask_ready, last = _delay(mask_phase, mask_wait + reset)
    join_phase = last + 1
    join_timer, join_ready, last = _delay(join_phase, join_wait + reset)

    public = {enable, closed, halves_ready, run}
    for ch in (*public, channel_base, last):
        _check_channel(ch)
    reserved = range(channel_base, last + 1)
    occupied = [range(r["reserved_channels"][0], r["reserved_channels"][1] + 1)
                for r in (closure, upstream, replay)]
    occupied.extend(r["reserved_channels"] for r in (mask, join))
    if (len(public) != 4 or any(ch in public or any(ch in channels for channels in occupied) for ch in reserved)
            or any(halves_ready in channels for channels in occupied)):
        raise ValueError("尾料启动板的专用频道或半形就绪频道与现有模块重叠")

    phase = Module({"enable": enable, "closed": closed, "halves_ready": halves_ready})
    enabled = _compare(phase, "enabled", "enable", 1)
    for name, ch in (("closed", mask_phase), ("halves_ready", join_phase)):
        received = _compare(phase, f"{name}_one", name, 1)
        phase.outputs[_gate(phase, "And", f"{name}_phase", received, enabled)] = ch

    start = Module({"enable": enable, "mask_phase": mask_phase, "mask_ready": mask_ready,
                    "join_phase": join_phase, "join_ready": join_ready})
    waits = []
    for name in ("mask", "join"):
        elapsed = _compare(start, f"{name}_elapsed", f"{name}_ready", 1)
        waits.append(_gate(start, "And", f"{name}_stable", f"{name}_phase", elapsed))
    both_ready = _gate(start, "And", "both_ready", *waits)
    enabled = _compare(start, "enabled", "enable", 1)
    start.outputs[_gate(start, "And", "run", both_ready, enabled)] = run

    platforms = [module.layout()["BP"]["Entries"][0] for module in (phase, *mask_timer, *join_timer, start)]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    wiring = _local_wiring(document["BP"])
    report = {
        "inputs": {"enable": enable, "closure_done": closed, "halves_ready": halves_ready},
        "outputs": {"replay_run": run},
        "replay_inputs": {name: port["channel"] for name, port in replay["inputs"].items() if name != "run"},
        "replay_outputs": {name: port["channel"] for name, port in replay["outputs"].items()},
        "reserved_channels": [channel_base, last],
        "timing": {
            "channel_signal_ticks": _RADIO_TICKS,
            "mask_hold_signal_ticks": mask_wait,
            "join_hold_signal_ticks": join_wait,
            "replay_reset_hold_signal_ticks": reset,
            "closure_wait_signal_ticks": ((mask_wait + reset + _RADIO_TICKS - 1) // _RADIO_TICKS) * _RADIO_TICKS,
            "halves_wait_signal_ticks": ((join_wait + reset + _RADIO_TICKS - 1) // _RADIO_TICKS) * _RADIO_TICKS,
            "enable_to_run_low_signal_ticks": _RADIO_TICKS,
            "replay_start_to_sample_signal_ticks": replay["timing"]["start_to_sample_signal_ticks"],
        },
        "platforms": len(wiring.platforms),
        "building_entries": len(wiring.entries),
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出双半形尾料回放的双完工启动板")
    parser.add_argument("--circuits", required=True, type=Path, help="双半形电路的接口表目录")
    parser.add_argument("--halves-ready", required=True, type=int, help="主控的半形就绪频道")
    parser.add_argument("--channel-base", required=True, type=int, help="启动板的首个专用频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.circuits, args.halves_ready, args.channel_base)
        _write_blueprint(document, report, args.output)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
