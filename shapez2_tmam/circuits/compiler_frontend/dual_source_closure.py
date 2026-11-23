"""让原图和冻结顶针候选共用自动双切向前缀闭包。"""

import argparse
from pathlib import Path

from ..circuit import constant
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from .pin_candidate_closure import (
    _ROWS, _START, _WORDS, _WORDS_READY, _cut_sources, _orient_rows, _publish, _radio_ports, _rewire,
    _verify, _words_ready,
)
from .pin_candidate_row import _RADIO, _read_blueprint, _read_report
from .pin_column_loop import _place


_BASE = 1703000
_WINDOW = 300
_CUTS = (*_ROWS, *_WORDS, _WORDS_READY)


def _session(enable, mode, valid, state, original, sealed, active):
    board = Module({"enable": enable, "mode": mode, "valid": valid, "state": state})
    enabled = _compare(board, "enabled", "enable", 1)
    idle = _compare(board, "idle", "state", 0)
    for name, code in (("original", 0), ("sealed", 1)):
        requested = _gate(board, "And", f"request_{name}", enabled, _compare(board, f"mode_{name}", "mode", code))
        same = _compare(board, f"state_{name}", "state", code + 1)
        allowed = _gate(board, "Or", f"allow_{name}", idle, same)
        if name == "sealed":
            allowed = _gate(board, "And", "allow_candidate", allowed, _compare(board, "valid_candidate", "valid", 1))
        _gate(board, "And", name, requested, allowed)
        _gate(board, "If", "next", code + 1, name)
    live = _gate(board, "Or", "live", "original", "sealed")
    idle_or_live = _gate(board, "Or", "idle_or_live", idle, live)
    interrupted = _gate(board, "And", "interrupted", enabled, _gate(board, "Not", "stopped", idle_or_live))
    _gate(board, "If", "next", 3, interrupted)
    occupied = _gate(board, "Or", "occupied", live, interrupted)
    _gate(board, "If", "next", 0, _gate(board, "Not", "clear", occupied))
    board.outputs = {"next": state, "original": original, "sealed": sealed, live: active}
    return board


def _source_starts(start, original, sealed, original_run, sealed_run):
    board = Module({"start": start, "original": original, "sealed": sealed})
    board.outputs = {_gate(board, "And", "run_original", "start", "original"): original_run,
                     _gate(board, "And", "run_sealed", "start", "sealed"): sealed_run}
    return board


def _choose_sources(original, sealed, sources):
    board = Module({"original": original, "sealed": sealed})
    for i, (raw, candidate, output) in enumerate(sources):
        p, q, result = f"original{i}", f"sealed{i}", f"result{i}"
        board.inputs.update({p: raw, q: candidate})
        _gate(board, "If", result, p, "original")
        _gate(board, "If", result, q, "sealed")
        board.outputs[result] = output
    return board


def _baseline(wiring, split, common, original):
    for platform, _, channel, config in _radio_ports(wiring):
        channels = original if platform in split else common
        config["C"] = constant(channels[channel])
    return {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": wiring.platforms.copy()}}


def build(baseline: Path, word_reader: Path, channel_base: int = _BASE) -> tuple[dict, dict]:
    report = _read_report(baseline.with_suffix(".json"))
    words = _read_report(word_reader.with_suffix(".json"))
    source = _local_wiring(_read_blueprint(baseline)["BP"])
    word_circuit = _local_wiring(_read_blueprint(word_reader)["BP"])
    if len(source.platforms) != report["platforms"] or report["platforms"] != 79:
        raise ValueError("需要 79 板自动双切向闭包及同名频道表")
    input_rows = tuple(words["inputs"]["rows_bottom_to_top"])
    valid = words["inputs"]["valid"]
    words_out = tuple(words["outputs"][f"q{q}"] for q in range(4))
    baseline_inputs, baseline_outputs = report["inputs"], report["outputs"]
    target = baseline_inputs["target"]
    window = range(channel_base, channel_base + _WINDOW)
    occupied = {channel for wiring in (source, word_circuit) for _, _, channel, _ in _radio_ports(wiring)}
    if (len(input_rows) != 5 or len({*input_rows, valid, target}) != 7 or len(set(words_out)) != 4
            or not 1 <= window[0] <= window[-1] < 1 << 24 or occupied.intersection(window)):
        raise ValueError("双来源闭包频道须合法、独占并保留五层与四列")
    split, _ = _cut_sources(source, report["part_platforms"])
    baseline_senders = {ch for _, transmitter, ch, _ in _radio_ports(source) if transmitter}

    enable, mode, optional, column, chosen, exhausted, alternate, height = window[:8]
    heights = tuple(window[8:12])
    rows = tuple(window[12:17])
    channels = iter(window[32:])
    common = {ch: next(channels) for ch in sorted(baseline_senders)}
    state, original, sealed, active, original_start, sealed_start = (next(channels) for _ in range(6))
    original_cut = {ch: next(channels) for ch in _CUTS}
    sealed_cut = {ch: next(channels) for ch in _CUTS}
    common.update({baseline_inputs["enable"]: active, baseline_inputs["optional_top"]: optional,
                   baseline_inputs["column"]: column, target: target})
    trial, selected = (common[baseline_outputs[k]] for k in ("alternate", "chosen"))
    document = _baseline(source, split, common, {**common, **original_cut, _START: original_start})
    entries = document["BP"]["Entries"]
    candidate_ports = {**dict(zip(words_out, (sealed_cut[ch] for ch in _WORDS), strict=True)),
                       words["inputs"]["alternate"]: trial, valid: sealed, **{ch: ch for ch in input_rows}}
    _place(entries, {"BP": {"Entries": _rewire(word_circuit, candidate_ports)}})

    step_ticks = words["settling"]["hold_signal_ticks"] + 3 * _RADIO
    word_steps = (step_ticks + _RADIO - 1) // _RADIO
    timers, elapsed, _ = _wait_timer(sealed_start, tuple(window[17:22]), word_steps, 1)
    oriented = tuple(zip(input_rows, (sealed_cut[ch] for ch in _ROWS), strict=True))
    mux_ports = tuple((original_cut[ch], sealed_cut[ch], common[ch]) for ch in _CUTS)
    result_flags = tuple((common[baseline_outputs[k]], ch) for k, ch in (("chosen", chosen), ("exhausted", exhausted)))
    result_heights = ((trial, alternate), (common[baseline_outputs["height"]], height),
                      *zip((common[ch] for ch in baseline_outputs["heights"]), heights, strict=True))
    result_rows = tuple(zip((common[ch] for ch in _ROWS), rows, strict=True))
    modules = [
        _session(enable, mode, valid, state, original, sealed, active),
        _source_starts(common[_START], original, sealed, original_start, sealed_start),
        *(_orient_rows(trial, oriented[i:i + 3]) for i in (0, 3)),
        *timers,
        _words_ready(sealed_start, elapsed, sealed_cut[_WORDS_READY]),
        *(_choose_sources(original, sealed, mux_ports[i:i + 2]) for i in range(0, len(mux_ports), 2)),
        _publish(enable, active, result_flags),
        *(_publish(enable, active, result_heights[i:i + 3], selected) for i in (0, 3)),
        *(_publish(enable, active, result_rows[i:i + 3], selected) for i in (0, 3)),
    ]
    added = [module.layout()["BP"]["Entries"][0] for module in modules]
    for i, entry in enumerate(added):
        entry.update(X=3 * (i % 6), Y=3 * (i // 6))
    _place(entries, {"BP": {"Entries": added}})
    external = {enable, mode, optional, column, target, valid, *input_rows}
    public = {chosen, exhausted, alternate, height, *heights, *rows}
    existing = {common[ch] for ch in baseline_senders - set(_CUTS)}
    original_sends = set(original_cut.values())
    candidate_sends = {sealed_cut[ch] for ch in _WORDS}
    added_sends = {ch for module in modules for ch in module.outputs.values()}
    used = existing | original_sends | candidate_sends | added_sends
    after = _verify(document, source, external, public, used)
    return document, {
        "inputs": {"enable": enable, "mode": mode, "optional_top": optional, "column": column,
                   "target": target, "valid": valid, "source_rows_bottom_to_top": input_rows},
        "outputs": {"chosen": chosen, "exhausted": exhausted, "alternate": alternate, "height": height,
                    "heights": heights, "rows_bottom_to_top": rows},
        "closure": {"alternate": trial, "rows_bottom_to_top": tuple(common[ch] for ch in _ROWS),
                    "material_words": tuple(common[ch] for ch in _WORDS), "clipped_word": common[1700806],
                    "words_ready": common[_WORDS_READY],
                    "run": common[1700760], "done": common[1700765], "top_item": common[1700770],
                    "raw_top_item": common[1701574]},
        "channels": {"private_range": [window[0], window[-1]]},
        "timing": {**report["timing"], "mode_reset_hold_signal_ticks": report["timing"]["source_reset_hold_signal_ticks"]
                   + 4 * _RADIO, "sealed_words_wait_signal_ticks": word_steps * _RADIO},
        "platforms": len(after.platforms), "building_entries": len(after.entries),
        "shared_baseline_platforms": len(source.platforms) - len(split),
        "short_range_links": len(after.short_ports), "global_transmitters": len(used),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="合装原图和封存候选共用的自动前缀闭包")
    parser.add_argument("baseline", type=Path, help="79 板自动前缀闭包及同名频道表")
    parser.add_argument("word_reader", type=Path, help="四列材料字蓝图及同名频道表")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="双来源闭包的首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.baseline, args.word_reader, args.channel_base)
        _write_blueprint(document, report, args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
