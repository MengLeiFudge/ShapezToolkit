"""重导双半形调度、尾料读取和配方写入电路。"""

import argparse
from pathlib import Path

from ..mari.signals import decode_constant
from .circuit import constant
from .compile_corner_jobs import export as export_corner_jobs
from .compiler_backend import _write_blueprint
from .compiler_backend.confirmed_call import build as build_confirmed_call
from .compiler_backend.fields import compile_fields
from .compiler_backend.module_caller import _RADIO_TRANSMITTER, _local_wiring
from .compiler_backend.pair_packet_bus import attach_writer, build
from .compiler_backend.prefix_scan_wiring import _append, _native_wiring, _report
from .compiler_frontend import FrontendError, compile_field_methods
from .compiler_frontend.pin_candidate_closure import _radio_ports


_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "synthesis"


def _compile(source, fields, inputs, outputs, publish=None):
    programs, conditions = compile_field_methods(_SOURCE_ROOT / f"{source}.py", fields, publish_when=publish)
    return compile_fields(programs, input_channels=inputs, output_channels=outputs, publish_when=conditions)


def _one(source, method, name, inputs, output):
    return _compile(source, {name: method}, inputs, {name: output})


def _jobs():
    inputs = {"phase": 1701690, **{f"h{i}": 1700766 + i for i in range(4)}, "alternate": 1700871}
    for name, fields in (("pair-job", {"kind": 1701691, "column": 1700873, "destination": 1701692}),
                         ("pair-job-inputs", {"left": 1701693, "right": 1701694})):
        yield name, _compile("pair_jobs", {field: f"pair_job_{field}" for field in fields}, inputs, fields)
    yield "pair-job-cursor", _compile(
        "pair_jobs", {"next": "pair_job_next", "done": "pair_job_done"},
        {"phase": 1701690, "enable": 1701695, "settled": 1701696, "kind": 1701691, "confirmed": 1701697},
        {"next": 1701698, "done": 1701699},
    )


def _packets(append_lower, append_upper):
    yield "pair-join-word", _one("pair_join_packet", "pair_join_word", "word",
                                 {"kind": 1701691, "step": 1701710, "left": 1701693, "right": 1701694}, 1701711)
    join = {"opcode": 1701712, "a": 1701713, "b": 1701714, "destination": 1701715}
    yield "pair-join-packet", _compile(
        "pair_join_packet", {name: f"pair_join_{name}" for name in join},
        {"word": 1701711, "left": 1701693, "right": 1701694, "destination": 1701692}, join,
        {name: "pair_join_two_inputs" if name == "b" else "pair_join_active" for name in join},
    )
    append = {"opcode": 1701723, "a": 1701724, "b": 1701725, "destination": 1701726, "base": 1701727}
    yield "append-packet", _compile(
        "append_packet", {name: f"append_packet_{name}" for name in append},
        {"row": 1701720, "load": 1701721, "has_lower": 1701722, "lower": append_lower, "upper": append_upper}, append,
        {"opcode": "append_packet_active", "destination": "append_packet_active", "a": "append_packet_stack",
         "b": "append_packet_stack", "base": "append_packet_load"},
    )


def _steps(tail_row, append_initial, corner_inputs, optional_top):
    for part, output in (("low", 1701738), ("high", 1701739)):
        yield f"packet-successor-{part}", _one("packet_cursor", f"packet_successor_{part}", "successor",
                                              {"step": 1701710}, output)
    controls = {"enable": 1701741, "settled": 1701742, "has_packet": 1701743, "confirmed": 1701744}
    yield "packet-cursor", _one("packet_cursor", "packet_next_step", "next",
                                {"step": 1701710, "successor_low": 1701738, "successor_high": 1701739,
                                 "terminal": 1701746, **controls}, 1701745)
    done_file, done = ("corner_release_steps", "corner_packet_done") if corner_inputs else ("packet_cursor", "packet_done")
    yield "packet-done", _one(done_file, done, "done",
                              {"step": 1701710, "selector": 1701740, "release_stage": 1701660, "enable": 1701741},
                              1701746)
    append = {"level": 1701749, "load": 1701721, "has_lower": 1701722}
    yield "append-step-input", _compile("packet_cursor", {name: f"append_step_{name}" for name in append},
                                        {"step": 1701710, "initial_lower": append_initial, "appended": 1701747}, append)
    yield "append-step-presence", _one("packet_cursor", "append_next_presence", "appended",
                                       {"step": 1701710, "selector": 1701740, "row": 1701720, "appended": 1701747,
                                        **controls}, 1701748)
    yield "tail-row-mask", _one("tail_input", "tail_mask_at", "mask", {"mask": 1701196, "level": 1701749}, 1701728)
    yield "tail-row-original", _one("dense_input", "dense_input_row", "original",
                                    {**{f"row{i}": 1701200 + i for i in range(5)}, "level": 1701749}, 1701729)
    source = 1701729
    if corner_inputs:
        source = 1702665
        yield "tail-source-row", _one("tail_input", "tail_source_row", "row",
                                      {"row": 1701729, "level": 1701749, "optional_top": optional_top}, source)
    yield "tail-row", _one("paired_tail", "_tail_layer", "row", {"row": source, "mask": 1701728}, tail_row)


def _corner_inputs():
    for name, method, inputs, out in (
        ("corner-ground-pins", "corner_ground_pins", {"word": 1700806}, 1701623),
        ("corner-requires-far", "corner_requires_far",
         {"word": 1700806, "highest": 1700588, "landing": 1700578}, 1701622),
        ("append-corner-layer", "corner_append_layer", {"original": 1701620, "level": 1701749,
         "highest": 1700588, "crystal_level": 1700577, "landing": 1700578, "counterclockwise": 1700678,
         "needs_pin": 1700579}, 1702660),
    ):
        yield name, _one("corner_append_input", method, "result", inputs, out)
    yield "append-corner-feed", _one("corner_append_input", "corner_append_feed", "row",
                                      {"upper": 1702660, "level": 1701749, "crystal_level": 1700577,
                                       "mode": 1701657}, 1701621)
    yield "corner-current-label", _one("corner_inputs", "corner_label_at", "label",
                                       {**{f"row{i}": 1701200 + i for i in range(5)}, "column": 1700873,
                                        "level": 1701749, "height": 1700816}, 1701620)
    yield "corner-work-level", _one("corner_feed", "copy_level", "level", {"level": 1701465}, 1701615)
    yield "corner-dense-row", _one("corner_feed", "corner_dense_row", "row",
                                   {"main": 1701616, "far": 1701617, "role": 1701650, "level": 1701465,
                                    "highest": 1700588, "pins": 1701623, "crystal": 1700577,
                                    "landing": 1700578, "needs_pin": 1700579}, 1701401)
    yield "dispatch-append-row", _one("corner_feed", "dispatch_append_row", "row",
                                       {"tail": 1701730, "corner": 1701621, "kind": 1701691}, 1701720)
    append_slots = {"lower": 1701654, "upper": 1701655, "initial": 1701656}
    yield "dispatch-append-slots", _compile(
        "corner_feed", {name: f"dispatch_append_{name}" for name in append_slots},
        {"kind": 1701691, "lower": 1701692, "upper": 1701694, "initial": 1701693,
         "corner_lower": 1701651, "corner_upper": 1701652, "corner_initial": 1701653}, append_slots,
    )


def _corner_release():
    release = {"stage": 1701660, "step": 1701661, "counterclockwise": 1700678}
    yield "corner-release-base-word", _one("release_packet", "release_word", "word",
                                            {**release, "support": 1701663, "handoff_word": 1701672}, 1702661)
    yield "corner-transform-word", _one("corner_release_steps", "corner_transform_word", "word",
                                         {**release, "pins": 1701623}, 1702662)
    yield "corner-finish-word", _one("corner_release_steps", "corner_finish_word", "word", release, 1702663)
    yield "corner-release-word", _one("corner_release_steps", "corner_select_release_word", "word",
                                       {"stage": 1701660, "release": 1702661, "transform": 1702662,
                                        "finish": 1702663}, 1701671)
    outputs = {name: 1701666 + i for i, name in enumerate(("opcode", "a", "b", "destination", "base"))}
    methods = {name: f"corner_release_{name}" for name in outputs}
    yield "corner-release-packet", _compile(
        "corner_release_steps", methods,
        {"word": 1701671, "counterclockwise": 1700678, "main": 1701662,
         "support": 1701663, "far": 1701664, "upper": 1701665}, outputs,
        {"opcode": "corner_release_active", "a": "corner_release_uses_a", "b": "corner_release_uses_b",
         "destination": "corner_release_active", "base": "corner_release_uses_base"},
    )
    inputs = {"original": 1701612, "moved": 1701613, "ground": 1701614, "level": 1701615,
              "height": 1700816, "highest": 1700588, "crystal": 1700577, "landing": 1700578, "needs_pin": 1700579}
    for name, channel in (("main", 1701616), ("far", 1701617)):
        yield f"prepare-corner-{name}", _one("corner_inputs", f"corner_{name}_input", name, inputs, channel)


def _dense_stream():
    yield "dense-stream-input", _compile("dense_stream", {"pending": "dense_stream_color",
                                                           "assembled": "dense_stream_assembled"},
                                          {"dye": 1701640, "present": 1701642},
                                          {"pending": 1701402, "assembled": 1701403})
    controls = {"phase": 1701400, "row": 1701401, "enable": 1701461, "settled": 1701462,
                "has_packet": 1701463, "confirmed": 1701471}
    yield "dense-stream-dye", _one("dense_stream", "dense_stream_next_dye", "dye",
                                   {"dye": 1701640, "pending": 1701402, **controls}, 1701641)
    yield "dense-stream-presence", _one("dense_stream", "dense_stream_next_presence", "present",
                                        {"present": 1701642, **controls}, 1701643)
    yield "dense-stream-clock", build_confirmed_call(
        enable=1701461, address=1701480, ack=1701481, finished=1701464, opcode=1701406,
        settled=1701462, has_packet=1701463, confirmed=1701471, request=1701482,
        states={"phase": (1701400, 1701472, 0), "level": (1701465, 1701473, 0),
                "dye": (1701640, 1701641, 0), "present": (1701642, 1701643, 0)},
        settle_ticks=7800, update_ticks=2400, channel_base=1701490,
    )


def _public_transmitters(wiring):
    output = set()
    for i, (_, entry) in enumerate(wiring.entries):
        if entry["T"] != _RADIO_TRANSMITTER:
            continue
        (source, _), = wiring.sources(i, 0)
        channel = decode_constant(wiring.entries[source][1]["C"])
        if channel in output:
            raise ValueError(f"频道 {channel} 同时被两块板发布")
        output.add(channel)
    return output


def _closure_channels(closure: Path) -> dict[int, int]:
    report = _report(closure)
    ports = report["outputs"]
    return {1700873: report["inputs"]["column"], 1700871: ports["alternate"], 1700816: ports["height"],
            1700806: report["closure"]["clipped_word"],
            **dict(zip(range(1700766, 1700770), ports["heights"], strict=True)),
            **dict(zip(range(1701200, 1701205), ports["rows_bottom_to_top"], strict=True))}


def _relink(wiring, channels):
    for _, _, channel, config in _radio_ports(wiring):
        if channel in channels:
            config["C"] = constant(channels[channel])


def export(circuits: Path, output_dir: Path, *, corner_inputs: bool = False, closure: Path | None = None) -> dict:
    channels = _closure_channels(closure) if closure is not None else {}
    lower, upper, initial = (1701654, 1701655, 1701656) if corner_inputs else (1701692, 1701694, 1701693)
    optional_top = _report(closure)["inputs"]["optional_top"] if closure is not None else 1701575
    parts = dict((*_jobs(), *_packets(lower, upper),
                  *_steps(1701730 if corner_inputs else 1701720, initial, corner_inputs, optional_top)))
    releases = tuple(circuits / "角备料" / name for name in
                     ("corner-handoff-word", "corner-release-word", "corner-release-packet"))
    dense_names = ["dense-column-packet", "dense-column-advance-phase", "dense-column-advance-level"]
    if not corner_inputs:
        dense_names.insert(1, "dense-column-input")
        dense_names.append("dense-confirmed-call")
    dense = tuple(circuits / name for name in dense_names)
    if corner_inputs:
        parts.update((*_corner_inputs(), *_dense_stream(), *_corner_release()))
        releases = tuple(circuits / "角备料" / name for name in ("corner-handoff-word", "read-corner-work-label",
                                                                 "read-corner-gap-label", "read-corner-ground-label"))
        releases += (circuits / "prefix-corner-parameters",)
    release_report = (parts["corner-release-packet"][1] if corner_inputs
                      else _report(circuits / "角备料" / "corner-release-packet"))
    reports = {"dense": _report(dense[0]), "release": release_report,
               "join": parts["pair-join-packet"][1], "append": parts["append-packet"][1]}
    document, bus = build(reports, 1701740, 1701750)
    report = attach_writer(document, bus, settle_ticks=7200 if corner_inputs else 6400, update_ticks=1600)
    for name, (part, interface) in parts.items():
        _write_blueprint(part, interface, output_dir / f"{name}.spz2bp")
        _append(document, part["BP"]["Entries"])
    for path in (*releases, *dense, circuits / "mask-paired-tail"):
        _append(document, _native_wiring(path.with_suffix(".spz2bp")).platforms)
    wiring = _local_wiring(document["BP"])
    if channels:
        _relink(wiring, channels)
    senders = _public_transmitters(wiring)
    result = {**report, "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
              "global_transmitters": len(senders), "parts": tuple(parts),
              "top_level": {"kind": 1701691, "control_phase": 1701690, "control_next": 1701698,
                            "control_done": 1701699, "current_column": channels.get(1700873, 1700873),
                            "append_level": 1701749, "release_stage": 1701660}}
    _write_blueprint(document, result, output_dir / "pair-writer.spz2bp")
    if corner_inputs:
        export_corner_jobs(output_dir, _compile, _one, channels.get(1700873, 1700873))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="从 Python 方法生成双半形调度和配方写入分册")
    parser.add_argument("--circuits", required=True, type=Path, help="双半形基础电路目录")
    parser.add_argument("--output-dir", required=True, type=Path, help="蓝图和接口表的输出目录")
    parser.add_argument("--corner-inputs", action="store_true", help="接入按当前列逐层读取的角备料")
    parser.add_argument("--closure", type=Path, help="共用前缀闭包蓝图或同名 JSON 接口表")
    args = parser.parse_args()
    try:
        result = export(args.circuits, args.output_dir, corner_inputs=args.corner_inputs, closure=args.closure)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output_dir / 'pair-writer.spz2bp'}，共 {result['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
