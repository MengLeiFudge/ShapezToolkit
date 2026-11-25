"""把冻结顶针前态接入自动双切向前缀闭包。"""

import argparse
from collections import Counter
from pathlib import Path

from ...mari.blueprint import _kind
from ...mari.signals import decode_constant
from ..circuit import constant
from ..compiler_backend import _write_blueprint
from ..compiler_backend.module_caller import _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from .pin_candidate_row import _RADIO, _read_blueprint, _read_report
from .pin_column_loop import _place


_BASE = 1702400
_WINDOW = 230
_ROWS = tuple(range(1701200, 1701205))
_WORDS = tuple(range(1700963, 1700967))
_START = 1700930
_WORDS_READY = 1700932
_SOURCE_SENDERS = {
    1700872, 1701605, *_ROWS, *_WORDS, *range(1700898, 1700902),
    *range(1700800, 1700816), *range(1700931, 1700945),
}


def _radio_ports(wiring, *, by_entry=False):
    for i, (platform, entry) in enumerate(wiring.entries):
        kind = _kind(entry)
        if kind in ("ControlledSignalReceiver", "ControlledSignalTransmitter"):
            (source, port), = wiring.sources(i, 0)
            driver = wiring.entries[source][1]
            if _kind(driver) != "ConstantSignal" or port != 0:
                raise ValueError("无线频道须由独立常量指定")
            yield (i if by_entry else platform), kind == "ControlledSignalTransmitter", decode_constant(driver["C"]), driver


def _cut_sources(wiring, part_counts):
    sent = {}
    for platform, transmitter, channel, _ in _radio_ports(wiring):
        if transmitter:
            sent.setdefault(platform, set()).add(channel)
    removed = {platform for platform, channels in sent.items() if channels & _SOURCE_SENDERS}
    expected = 1 + sum(part_counts[name] for name in ("orient-cut", "four-column-targets", "read-four-columns"))
    removed_channels = set().union(*(sent[platform] for platform in removed))
    links_touched = any(wiring.entries[i][0] in removed for pair in wiring.short_ports.items() for i in pair)
    if len(removed) != expected or removed_channels != _SOURCE_SENDERS or links_touched:
        raise ValueError("自动前缀蓝图的原图读取板或切点与 79 板版不符")
    return removed, set().union(*(channels for platform, channels in sent.items() if platform not in removed))


def _rewire(wiring, channels, removed=()):
    for platform, _, channel, config in _radio_ports(wiring):
        if platform not in removed:
            config["C"] = constant(channels[channel])
    return [entry for i, entry in enumerate(wiring.platforms) if i not in removed]


def _enable_gate(board):
    return _gate(board, "And", "enabled", _compare(board, "requested", "enable", 1),
                 _compare(board, "sealed", "valid", 1))


def _enabled(enable, valid, output):
    board = Module({"enable": enable, "valid": valid})
    board.outputs = {_enable_gate(board): output}
    return board


def _orient_rows(alternate, rows):
    board = Module({"alternate": alternate})
    direct = _compare(board, "direct", "alternate", 0)
    rotate = _compare(board, "rotate", "alternate", 1)
    for i, (source, target) in enumerate(rows):
        signal, turned, output = f"source{i}", f"turned{i}", f"oriented{i}"
        board.inputs[signal] = source
        board.gate("VirtualRotatorCCW", (signal,), (turned,))
        _gate(board, "If", output, signal, direct)
        _gate(board, "If", output, turned, rotate)
        board.outputs[output] = target
    return board


def _words_ready(start, elapsed, output):
    board = Module({"start": start, "elapsed": elapsed})
    _gate(board, "And", "ready", _compare(board, "running", "start", 1),
          _compare(board, "settled", "elapsed", 1))
    board.outputs = {"ready": output}
    return board


def _publish(enable, valid, signals, chosen=None):
    board = Module({"enable": enable, "valid": valid})
    permit = _enable_gate(board)
    if chosen is not None:
        board.inputs["chosen"] = chosen
        permit = _gate(board, "And", "chosen_result", permit, _compare(board, "selected", "chosen", 1))
    for i, (source, output) in enumerate(signals):
        item = f"source{i}"
        board.inputs[item] = source
        gate = _gate(board, "If", f"result{i}", item, permit)
        board.outputs[gate] = output
    return board


def _links(wiring):
    def site(i):
        platform, x, y, z = wiring.sites[i]
        island = wiring.platforms[platform]
        return (island.get("X", 0), island.get("Y", 0), island.get("Z", 0), x, y, z)

    return {(site(rx), site(tx)) for rx, tx in wiring.short_ports.items()}


def _verify(document, source, data, public, used):
    wiring = _local_wiring(document["BP"])
    tx, rx = Counter(), set()
    for _, transmitter, channel, _ in _radio_ports(wiring):
        if transmitter:
            tx[channel] += 1
        else:
            rx.add(channel)
    if (any(count != 1 for count in tx.values()) or set(tx) != used or not public <= set(tx)
            or rx - tx.keys() != data or _links(wiring) != _links(source)):
        raise ValueError("候选闭包的无线频道或短距端口与接线计划不符")
    return wiring


def build(baseline: Path, word_reader: Path, channel_base: int = _BASE) -> tuple[dict, dict]:
    report = _read_report(baseline.with_suffix(".json"))
    words = _read_report(word_reader.with_suffix(".json"))
    source = _local_wiring(_read_blueprint(baseline)["BP"])
    word_circuit = _local_wiring(_read_blueprint(word_reader)["BP"])
    if len(source.platforms) != report["platforms"] or report["platforms"] != 79:
        raise ValueError("需要 79 板自动双切向闭包及同名频道表")
    input_rows = tuple(words["inputs"]["rows_bottom_to_top"])
    valid = words["inputs"]["valid"]
    source_words = tuple(words["outputs"][f"q{q}"] for q in range(4))
    window = range(channel_base, channel_base + _WINDOW)
    occupied = {channel for wiring in (source, word_circuit) for _, _, channel, _ in _radio_ports(wiring)}
    if (len(input_rows) != 5 or len({*input_rows, valid}) != 6 or len(set(source_words)) != 4
            or not 1 <= window[0] <= window[-1] < 1 << 24 or occupied.intersection(window)):
        raise ValueError("候选闭包频道须合法、独占并保留五层和四列")
    removed, kept_senders = _cut_sources(source, report["part_platforms"])
    original_inputs, original_outputs = report["inputs"], report["outputs"]
    private_channels = kept_senders | {*_ROWS, *_WORDS, _WORDS_READY, original_inputs["enable"]}
    if len(private_channels) > _WINDOW - 32:
        raise ValueError("候选闭包的私有频道窗口不足")
    mapped = dict(zip(sorted(private_channels), window[32:]))
    enable, optional, column, chosen, exhausted, alternate, height = window[:7]
    heights, rows = tuple(window[7:11]), tuple(window[11:16])
    mapped.update({original_inputs["optional_top"]: optional, original_inputs["column"]: column})
    trial = mapped[original_outputs["alternate"]]
    selected = mapped[original_outputs["chosen"]]
    active = mapped[original_inputs["enable"]]
    start = mapped[_START]
    target_sends = {**dict(zip(source_words, (mapped[ch] for ch in _WORDS), strict=True)),
                    words["inputs"]["alternate"]: trial, **{ch: ch for ch in (*input_rows, valid)}}
    entries = _rewire(source, mapped, removed)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": entries}}
    _place(entries, {"BP": {"Entries": _rewire(word_circuit, target_sends)}})

    row_ports = tuple(zip(input_rows, (mapped[ch] for ch in _ROWS), strict=True))
    word_wait = words["settling"]["hold_signal_ticks"] + 3 * _RADIO
    steps = (word_wait + _RADIO - 1) // _RADIO
    timers, elapsed, _ = _wait_timer(start, tuple(window[16:21]), steps, 1)
    status_ports = tuple((mapped[original_outputs[name]], channel) for name, channel in
                         (("chosen", chosen), ("exhausted", exhausted), ("alternate", alternate)))
    heights_ports = tuple((mapped[ch], out) for ch, out in zip(original_outputs["heights"], heights, strict=True))
    height_port = ((mapped[original_outputs["height"]], height),)
    row_outputs = tuple((mapped[ch], out) for ch, out in zip(_ROWS, rows, strict=True))
    modules = [
        _enabled(enable, valid, active),
        *(_orient_rows(trial, row_ports[i:i + 3]) for i in (0, 3)),
        *timers,
        _words_ready(start, elapsed, mapped[_WORDS_READY]),
        _publish(enable, valid, status_ports[:2]),
        _publish(enable, valid, (*status_ports[2:], *height_port), selected),
        *(_publish(enable, valid, heights_ports[i:i + 2], selected) for i in (0, 2)),
        *(_publish(enable, valid, row_outputs[i:i + 2], selected) for i in (0, 2, 4)),
    ]
    added = [module.layout()["BP"]["Entries"][0] for module in modules]
    for i, entry in enumerate(added):
        entry.update(X=3 * (i % 5), Y=3 * (i // 5))
    _place(entries, {"BP": {"Entries": added}})
    data = {enable, optional, column, valid, *input_rows}
    public = {chosen, exhausted, alternate, height, *heights, *rows}
    timer_outputs = {channel for timer in timers for channel in timer.outputs.values()}
    used = {mapped[ch] for ch in private_channels} | timer_outputs | public
    after = _verify(document, source, data, public, used)
    return document, {
        "inputs": {"enable": enable, "optional_top": optional, "column": column, "valid": valid,
                   "source_rows_bottom_to_top": input_rows},
        "outputs": {"chosen": chosen, "exhausted": exhausted, "alternate": alternate, "height": height,
                    "heights": heights, "rows_bottom_to_top": rows},
        "closure": {"alternate": trial, "words": tuple(mapped[ch] for ch in _WORDS),
                    "rows_bottom_to_top": tuple(mapped[ch] for ch in _ROWS), "words_ready": mapped[_WORDS_READY],
                    "run": mapped[1700760], "done": mapped[1700765],
                    "top_item": mapped[1700770], "raw_top_item": mapped[1701574]},
        "channels": {"private_range": [window[0], window[-1]]},
        "timing": {**report["timing"], "candidate_reset_hold_signal_ticks": report["timing"]["source_reset_hold_signal_ticks"]
                   + 4 * _RADIO, "words_wait_signal_ticks": steps * _RADIO},
        "platforms": len(after.platforms), "building_entries": len(after.entries),
        "removed_source_platforms": len(removed), "short_range_links": len(after.short_ports),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="将五层原色和四列材料字接入自动前缀闭包")
    parser.add_argument("baseline", type=Path, help="79 板自动前缀闭包及同名频道表")
    parser.add_argument("word_reader", type=Path, help="四列材料字蓝图及同名频道表")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="候选前缀闭包的首频道")
    parser.add_argument("--output", required=True, type=Path, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = build(args.baseline, args.word_reader, args.channel_base)
        _write_blueprint(document, report, args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
