"""重导双半形调度、尾料读取和配方写入电路。"""

import argparse
from pathlib import Path

from ..mari.signals import decode_constant
from .compiler_backend import _write_blueprint
from .compiler_backend.fields import compile_fields
from .compiler_backend.module_caller import _RADIO_TRANSMITTER, _local_wiring
from .compiler_backend.pair_packet_bus import attach_writer, build
from .compiler_backend.prefix_scan_wiring import _append, _native_wiring, _report
from .compiler_frontend import FrontendError, compile_field_methods


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


def _packets():
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
        {"row": 1701720, "load": 1701721, "has_lower": 1701722, "lower": 1701692, "upper": 1701694}, append,
        {"opcode": "append_packet_active", "destination": "append_packet_active", "a": "append_packet_stack",
         "b": "append_packet_stack", "base": "append_packet_load"},
    )


def _steps():
    for part, output in (("low", 1701738), ("high", 1701739)):
        yield f"packet-successor-{part}", _one("packet_cursor", f"packet_successor_{part}", "successor",
                                              {"step": 1701710}, output)
    controls = {"enable": 1701741, "settled": 1701742, "has_packet": 1701743, "confirmed": 1701744}
    yield "packet-cursor", _one("packet_cursor", "packet_next_step", "next",
                                {"step": 1701710, "successor_low": 1701738, "successor_high": 1701739,
                                 "terminal": 1701746, **controls}, 1701745)
    yield "packet-done", _one("packet_cursor", "packet_done", "done",
                              {"step": 1701710, "selector": 1701740, "release_stage": 1701660, "enable": 1701741},
                              1701746)
    append = {"level": 1701749, "load": 1701721, "has_lower": 1701722}
    yield "append-step-input", _compile("packet_cursor", {name: f"append_step_{name}" for name in append},
                                        {"step": 1701710, "initial_lower": 1701693, "appended": 1701747}, append)
    yield "append-step-presence", _one("packet_cursor", "append_next_presence", "appended",
                                       {"step": 1701710, "selector": 1701740, "row": 1701720, "appended": 1701747,
                                        **controls}, 1701748)
    yield "tail-row-mask", _one("tail_input", "tail_mask_at", "mask", {"mask": 1701196, "level": 1701749}, 1701728)
    yield "tail-row-original", _one("dense_input", "dense_input_row", "original",
                                    {**{f"row{i}": 1701200 + i for i in range(5)}, "level": 1701749}, 1701729)
    yield "tail-row", _one("paired_tail", "_tail_layer", "row", {"row": 1701729, "mask": 1701728}, 1701720)


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


def export(circuits: Path, output_dir: Path) -> dict:
    parts = dict((*_jobs(), *_packets(), *_steps()))
    releases = tuple(circuits / "角备料" / name for name in
                     ("corner-handoff-word", "corner-release-word", "corner-release-packet"))
    dense = tuple(circuits / name for name in ("dense-column-packet", "dense-column-input", "dense-column-advance-phase",
                                              "dense-column-advance-level", "dense-confirmed-call"))
    reports = {"dense": _report(dense[0]), "release": _report(releases[-1]),
               "join": parts["pair-join-packet"][1], "append": parts["append-packet"][1]}
    document, bus = build(reports, 1701740, 1701750)
    report = attach_writer(document, bus, settle_ticks=6400, update_ticks=1600)
    for name, (part, interface) in parts.items():
        _write_blueprint(part, interface, output_dir / f"{name}.spz2bp")
        _append(document, part["BP"]["Entries"])
    for path in (*releases, *dense, circuits / "mask-paired-tail"):
        _append(document, _native_wiring(path.with_suffix(".spz2bp")).platforms)
    wiring = _local_wiring(document["BP"])
    senders = _public_transmitters(wiring)
    result = {**report, "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
              "global_transmitters": len(senders), "parts": tuple(parts),
              "top_level": {"kind": 1701691, "control_phase": 1701690, "control_next": 1701698,
                            "control_done": 1701699, "current_column": 1700873,
                            "append_level": 1701749, "release_stage": 1701660}}
    _write_blueprint(document, result, output_dir / "pair-writer.spz2bp")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="从 Python 方法生成双半形调度和配方写入分册")
    parser.add_argument("--circuits", required=True, type=Path, help="双半形基础电路目录")
    parser.add_argument("--output-dir", required=True, type=Path, help="蓝图和接口表的输出目录")
    args = parser.parse_args()
    try:
        result = export(args.circuits, args.output_dir)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output_dir / 'pair-writer.spz2bp'}，共 {result['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
