"""把封存的五层原色行读成两种切向共用的四份材料字。"""

import argparse
from pathlib import Path

from ...synthesis.shape_methods import shape_literal
from ..circuit import Circuit, Literal, Ref
from ..compiler_backend import _write_blueprint
from ..compiler_backend._layout import _assemble, _layout_platform
from .pin_candidate_row import _read_report


_BASE = 1702340
_ROTATIONS = ((), ("VirtualRotatorCCW",), ("VirtualRotatorCCW", "VirtualRotatorCCW"), ("VirtualRotator",))


def _equal(circuit, signal, value):
    return circuit.add("LogicGateCompare", signal, Literal(value), config="AQ==")


def _select(circuit, choices):
    branches = tuple(circuit.add("LogicGateIf", value, condition) for value, condition in choices)
    circuit.aliases.append(branches)
    return branches[0]


def _marker(circuit: Circuit, cell: Ref) -> Ref:
    part = circuit.add("VirtualAnalyzer", cell)
    empty = _equal(circuit, part, None)
    pin = _equal(circuit, part, shape_literal("P-------"))
    crystal = _equal(circuit, part, shape_literal("cu------"))
    special = circuit.add("LogicGateOr", pin, crystal)
    ordinary = circuit.add("LogicGateNot", circuit.add("LogicGateOr", empty, special))
    return _select(circuit, ((Literal(shape_literal(code)), flag) for code, flag in (
        ("Cu------", empty), ("Su------", pin), ("Wu------", crystal), ("Ru------", ordinary),
    )))


def _rotate(circuit, row, column):
    for kind in _ROTATIONS[column]:
        row = circuit.add(kind, row)
    return row


def _column(rows, valid, alternate, column, output):
    circuit = Circuit()
    sealed = circuit.add("ControlledSignalReceiver", Literal(valid))
    orientation = circuit.add("ControlledSignalReceiver", Literal(alternate))
    direct = _equal(circuit, orientation, 0)
    rotated = _equal(circuit, orientation, 1)
    valid_cut = circuit.add("LogicGateOr", direct, rotated)
    publish = circuit.add("LogicGateAnd", _equal(circuit, sealed, 1), valid_cut)
    markers = []
    for channel in rows:
        row = circuit.add("ControlledSignalReceiver", Literal(channel))
        cell = _select(circuit, ((_rotate(circuit, row, column), direct),
                                 (_rotate(circuit, row, (column + 1) % 4), rotated)))
        markers.append(_marker(circuit, cell))
    word, *upper = markers
    # 四种标记都是普通块，每层在同一象限，因此堆叠不会吞掉空层标记。
    for marker in upper:
        word = circuit.add("VirtualStacker", word, marker)
    result = circuit.add("LogicGateIf", word, publish)
    live = set(range(len(circuit.gates)))
    return _layout_platform(circuit, circuit.channel_map(), live, {output: result})


def build(sealed: dict, channel_base: int = _BASE) -> tuple[dict, dict]:
    source = sealed["outputs"]
    rows = tuple(source["rows_bottom_to_top"])
    valid = source["valid"]
    first, last = sealed["channels"]["private_range"]
    alternate, *words = range(channel_base, channel_base + 5)
    channels = (*rows, valid, alternate, *words)
    if (len(rows) != 5 or len(set(channels)) != len(channels)
            or any(type(channel) is not int or not 1 <= channel < 1 << 24 for channel in channels)
            or any(first <= channel <= last for channel in (alternate, *words))):
        raise ValueError("需要五个封存行频道，且切向与材料字频道须合法独占")
    platforms = [_column(rows, valid, alternate, q, output) for q, output in enumerate(words)]
    document, depth = _assemble(platforms)
    return document, {
        "inputs": {"rows_bottom_to_top": rows, "valid": valid, "alternate": alternate},
        "outputs": {f"q{q}": channel for q, channel in enumerate(words)},
        "cut_order": {"0": [0, 1, 2, 3], "1": [1, 2, 3, 0]},
        "reserved_channels": [alternate, *words],
        "settling": {"max_gate_depth": depth, "hold_signal_ticks": 64 * (depth + 2)},
        "platforms": len(platforms),
        "building_entries": sum(len(platform.entry["B"]["Entries"]) for platform in platforms),
        "global_receivers": 7 * len(platforms),
        "global_transmitters": len(words),
        "internal_global_devices": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出冻结顶针候选五层原色行的四列材料字")
    parser.add_argument("sealed", type=Path, help="五层封存的 JSON 频道表")
    parser.add_argument("--channel-base", type=int, default=_BASE, help="切向及四份材料字的首频道")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        _write_blueprint(*build(_read_report(args.sealed), args.channel_base), args.output)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
