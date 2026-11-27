"""生成尾针搜索当前节点的列判定和 S 候选的材料字。"""

import argparse
from copy import deepcopy
from pathlib import Path

from ...mari.blueprint import Wiring
from ..circuit import Circuit, Literal
from ..compiler_backend import _write_blueprint
from ..compiler_backend._layout import _assemble, _layout_platform
from ..compiler_backend.fields import compile_fields
from ..compiler_backend.method_sequence import _radio_channels
from ..compiler_backend.module_caller import _RADIO_TICKS, _any, _compare, _gate, _local_wiring, _wait_timer
from ..local_module import Module
from . import FrontendError, compile_field_methods, compile_method
from .pin_candidate_closure import _rewire
from .pin_source_words import _equal, _marker, _rotate


_BASE = 1705500
_PREFLIGHT, _ELIGIBLE = 1705330, 1705356
_TARGET_ROWS = tuple(range(1705350, 1705355))
_LIMITS = tuple(range(1703509, 1703513))
_CANDIDATE_READY = 1704802
_CANDIDATE_ROWS = tuple(range(1703513, 1703518))
_WORDS = tuple(range(1701842, 1701846))
_SYNTHESIS = Path(__file__).resolve().parents[2] / "synthesis"
_COLUMNS = ("q0", "q1", "q2", "q3")


def _layout(circuit, outputs):
    return _layout_platform(circuit, circuit.channel_map(), set(range(len(circuit.gates))), outputs)


def _clone(document, connections):
    wiring = Wiring(deepcopy(document["BP"]))
    receivers, senders = _radio_channels(wiring)
    channels = receivers.keys() | senders.keys()
    if len(wiring.platforms) != 1 or channels != set(range(1, len(connections) + 1)):
        raise ValueError("当前节点的子方法须为单平台且匹配行列频道表")
    return _rewire(wiring, dict(enumerate(connections, 1)))


def _column_kernel(source, method, parameters):
    path = _SYNTHESIS / source
    program = compile_method(path.read_text(encoding="utf-8"), method, filename=str(path))
    inputs = dict(zip(parameters, range(1, 6), strict=True))
    return compile_fields({"result": program}, input_channels=inputs, output_channels={"result": 6})


def _crystal_row(cells, output):
    board = Module(dict(zip(_COLUMNS, cells, strict=True)))
    crystals = tuple(_compare(board, f"crystal_{name}", name, 3) for name in _COLUMNS)
    board.outputs = {_any(board, "has_crystal", crystals): output}
    return board


def _has_crystal(row_flags, output):
    board = Module({f"layer{i}": channel for i, channel in enumerate(row_flags)})
    board.outputs = {_any(board, "has_crystal", tuple(board.inputs)): output}
    return board


def _all_columns(admissible, output):
    board = Module(dict(zip(_COLUMNS, admissible, strict=True)))
    result = "q0"
    for name in _COLUMNS[1:]:
        result = _gate(board, "And", f"through_{name}", result, name)
    board.outputs = {result: output}
    return board


def _eligibility(all_columns, crystal):
    board = Module({"all_a": all_columns, "has_crystal": crystal,
                    **{f"limit{i}": channel for i, channel in enumerate(_LIMITS)}})
    eligible = _gate(board, "And", "has_admissible_crystal", "all_a", "has_crystal")
    for i in range(4):
        valid = _compare(board, f"valid{i}", f"limit{i}", 0, "Ag==")
        eligible = _gate(board, "And", f"through_limit{i}", eligible, valid)
    board.outputs = {eligible: _ELIGIBLE}
    return board


def _append_boards(platforms, boards):
    for board in boards:
        platforms.extend(board.layout()["BP"]["Entries"])


def _target_part(platforms):
    source = Path(__file__).with_name("pin_landings.py")
    programs, _ = compile_field_methods(source, {name: f"target_{name}" for name in _COLUMNS})
    row, row_report = compile_fields(programs, input_channels={"row": 1},
                                     output_channels=dict(zip(_COLUMNS, range(2, 6), strict=True)))
    limits, limits_report = _column_kernel("pin_prefix.py", "pin_prefix_limit", ("ground", "z1", "z2", "z3", "z4"))
    admissible, admissible_report = _column_kernel("column_rules.py", "column_admissible", tuple(f"z{i}" for i in range(5)))
    cells = [tuple(range(_BASE + 4 * z, _BASE + 4 * z + 4)) for z in range(5)]
    row_flags = tuple(range(_BASE + 20, _BASE + 25))
    columns = tuple(range(_BASE + 25, _BASE + 29))
    has_crystal, all_columns = _BASE + 29, _BASE + 30

    for channel, layer in zip(_TARGET_ROWS, cells, strict=True):
        platforms.extend(_clone(row, (channel, *layer)))
    for layers, limit, passes in zip(zip(*cells), _LIMITS, columns, strict=True):
        platforms.extend(_clone(limits, (*layers, limit)))
        platforms.extend(_clone(admissible, (*layers, passes)))
    _append_boards(platforms, (_crystal_row(layer, flag) for layer, flag in zip(cells, row_flags, strict=True)))
    _append_boards(platforms, (_has_crystal(row_flags, has_crystal), _all_columns(columns, all_columns),
                               _eligibility(all_columns, has_crystal)))

    row_ticks = row_report["settling"]["hold_signal_ticks"]
    column_ticks = max(r["settling"]["hold_signal_ticks"] for r in (limits_report, admissible_report))
    steps = (row_ticks + column_ticks + _RADIO_TICKS - 1) // _RADIO_TICKS + 4
    timers, ready, _ = _wait_timer(_PREFLIGHT, tuple(range(_BASE + 31, _BASE + 36)), steps, steps)
    _append_boards(platforms, timers)
    return {"inputs": {"rows_bottom_to_top": _TARGET_ROWS, "preflight": _PREFLIGHT},
            "outputs": {"limits_q0_to_q3": _LIMITS, "column_a_q0_to_q3": columns, "all_columns_a": all_columns,
                        "has_lowest_crystal": has_crystal, "eligible": _ELIGIBLE, "prepared": ready},
            "timing": {"preflight_hold_signal_ticks": steps * _RADIO_TICKS,
                       "preflight_rearm_signal_ticks": 4 * _RADIO_TICKS}}


def _word_column(column, output):
    circuit = Circuit()
    markers = [
        _marker(circuit, _rotate(circuit, circuit.add("ControlledSignalReceiver", Literal(channel)), column))
        for channel in _CANDIDATE_ROWS
    ]
    word, *upper = markers
    for marker in upper:
        word = circuit.add("VirtualStacker", word, marker)
    ready = circuit.add("ControlledSignalReceiver", Literal(_CANDIDATE_READY))
    result = circuit.add("LogicGateIf", word, _equal(circuit, ready, 1))
    return _layout(circuit, {output: result})


def _candidate_part(platforms):
    document, depth = _assemble([_word_column(q, channel) for q, channel in enumerate(_WORDS)])
    platforms.extend(document["BP"]["Entries"])
    return {"inputs": {"rows_bottom_to_top": _CANDIDATE_ROWS, "s_ready": _CANDIDATE_READY},
            "outputs": {"words_q0_to_q3": _WORDS}, "consumer_start": 1705333,
            "timing": {"candidate_hold_signal_ticks": 64 * (depth + 2), "withdraw_signal_ticks": 2 * _RADIO_TICKS}}


def build(part: str = "both") -> tuple[dict, dict]:
    platforms, parts = [], {}
    if part in ("target", "both"):
        parts["target"] = _target_part(platforms)
    if part in ("candidate", "both"):
        parts["candidate"] = _candidate_part(platforms)
    if not parts:
        raise ValueError("导出部分须为 target、candidate 或 both")
    placed = [{**board, "X": 3 * i, "Y": 0, "L": 0} for i, board in enumerate(platforms)]
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": placed}}
    wiring = _local_wiring(document["BP"])
    received, sent = _radio_channels(wiring)
    expected_inputs, expected_outputs = set(), set()
    for interface in parts.values():
        for ports, channels in ((interface["inputs"], expected_inputs), (interface["outputs"], expected_outputs)):
            for channel in ports.values():
                channels.update(channel if isinstance(channel, tuple) else (channel,))
    if (any(count != 1 for count in sent.values()) or received.keys() - sent.keys() != expected_inputs
            or not expected_outputs <= sent.keys()
            or any(not _BASE <= channel < _BASE + 200 for channel in sent.keys() - expected_outputs)):
        raise ValueError("当前节点蓝图的收发频道与接口表不符")
    return document, {"parts": parts, "private_range": [_BASE, _BASE + 199],
                      "platforms": len(wiring.platforms), "building_entries": len(wiring.entries)}


def main() -> int:
    parser = argparse.ArgumentParser(description="导出尾针搜索的当前节点判定和候选材料字")
    parser.add_argument("--part", choices=("both", "target", "candidate"), default="both", help="选择导出部分")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(args.part), args.output)
    except FrontendError as error:
        parser.error(f"{error.filename}:{error.lineno}:{error.offset} {error.msg}")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
