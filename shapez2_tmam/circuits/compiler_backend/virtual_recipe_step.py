"""计算六槽工道的一笔虚拟操作及提交后的六个槽。"""

import argparse
from pathlib import Path

from ...synthesis.physics import Rules, Shape
from ..circuit import Circuit, Literal, Ref
from ..factory_assembly.recipe import BASE, BINARY, CRYSTAL, OPCODES, _base_shape, _process, _slot
from ..half_circuit import _combine
from ..operation_core import physical_results
from ..recipe_processor import _address, _base_valid, _read
from ..slot_streams import SLOT_ROWS
from ..work_lane import COLORS
from . import _write_blueprint
from ._layout import layout
from .method_sequence import _radio_channels
from .module_caller import _local_wiring
from .prefix_scan_wiring import _append


_RULES = Rules(4, 5)
_SLOT_NAMES = tuple(f"slot{i}" for i in range(len(SLOT_ROWS)))
_FIELDS = ("opcode", "a", "b", "destination", "base", "color")
_COLOR_SIGNALS = tuple(f"color:{color}" for color in COLORS)
_INPUTS = dict(zip((*_FIELDS, *_SLOT_NAMES), range(1702700, 1702712), strict=True))
_OUTPUTS = dict(zip((*_SLOT_NAMES, "valid"), range(1702712, 1702719), strict=True))
_A, _B, _DEST, _RESULT = range(1702720, 1702724)


def step(slots: tuple[Shape | None, ...], opcode: int | None, a: int | None, b: int | None,
         destination: int | None, base: Shape | str | None, color: str | None) -> tuple[tuple[Shape | None, ...], bool]:
    """以同一份旧槽状态执行单笔指令，返回下一状态和是否成功。"""
    if len(slots) != len(_SLOT_NAMES):
        raise ValueError(f"回放需要 {len(_SLOT_NAMES)} 个旧槽，收到 {len(slots)} 个")
    if type(opcode) is not int or opcode not in OPCODES:
        return slots, False
    try:
        dest = _slot(destination)
        sources = () if opcode == BASE else (_slot(a),)
        if opcode in BINARY:
            sources += (_slot(b),)
            if sources[0] == sources[1]:
                return slots, False
        if slots[dest] is not None and dest not in sources:
            return slots, False
        if opcode == BASE:
            result = _base_shape(_RULES, base.to_key() if isinstance(base, Shape) else base)
        else:
            operands = tuple(slots[index] for index in sources)
            if any(value is None for value in operands):
                return slots, False
            if opcode == CRYSTAL and color not in _COLOR_SIGNALS:
                return slots, False
            dye = color[-1] if opcode == CRYSTAL and color is not None else None
            result, _ = _process(_RULES, opcode, operands, dye)
    except ValueError:
        return slots, False
    if result is None:
        return slots, False
    return tuple(result if index == dest else None if index in sources else value
                 for index, value in enumerate(slots)), True


def _receive(circuit: Circuit, channel: int) -> Ref:
    return circuit.add("ControlledSignalReceiver", Literal(channel))


def _eq(circuit: Circuit, first, second) -> Ref:
    return circuit.add("LogicGateCompare", first, second, config="AQ==")


def _slot_reader(address: str, output: int) -> tuple[dict, int]:
    circuit = Circuit()
    slots = tuple(_receive(circuit, _INPUTS[name]) for name in _SLOT_NAMES)
    picks = _address(circuit, _receive(circuit, _INPUTS[address]))
    return layout(circuit, {output: _read(circuit, slots, picks)})


def _operation() -> tuple[dict, int]:
    circuit = Circuit()
    opcode, base, color = (_receive(circuit, _INPUTS[name]) for name in ("opcode", "base", "color"))
    first, second = (_receive(circuit, channel) for channel in (_A, _B))
    values = physical_results(circuit, first, second, color, 4)
    base_ok = _base_valid(circuit, base, 4)
    colors = _combine(circuit, "LogicGateOr", [_eq(circuit, color, Literal(value)) for value in _COLOR_SIGNALS])
    results = []
    for code in OPCODES:
        selected = _eq(circuit, opcode, Literal(code))
        if code == BASE:
            selected = circuit.add("LogicGateAnd", selected, base_ok)
        elif code == CRYSTAL:
            selected = circuit.add("LogicGateAnd", selected, colors)
        results.append(circuit.add("LogicGateIf", base if code == BASE else values[code], selected))
    circuit.aliases.append(tuple(results))
    return layout(circuit, {_RESULT: results[0]})


def _guard() -> tuple[dict, int]:
    circuit = Circuit()
    opcode, a, b, dest = (_receive(circuit, _INPUTS[name]) for name in ("opcode", "a", "b", "destination"))
    first, second, current, result = (_receive(circuit, channel) for channel in (_A, _B, _DEST, _RESULT))
    is_base = _eq(circuit, opcode, Literal(BASE))
    binary = _combine(circuit, "LogicGateOr", [_eq(circuit, opcode, Literal(code)) for code in BINARY])
    not_base = circuit.add("LogicGateNot", is_base)
    not_binary = circuit.add("LogicGateNot", binary)
    first_empty = _eq(circuit, first, Literal(None))
    second_empty = _eq(circuit, second, Literal(None))
    first_ok = circuit.add("LogicGateOr", is_base, circuit.add("LogicGateNot", first_empty))
    second_ok = circuit.add("LogicGateOr", not_binary, circuit.add("LogicGateNot", second_empty))
    same_source = _eq(circuit, a, b)
    distinct = circuit.add("LogicGateOr", not_binary, circuit.add("LogicGateNot", same_source))
    reuse_a = circuit.add("LogicGateAnd", not_base, _eq(circuit, dest, a))
    reuse_b = circuit.add("LogicGateAnd", binary, _eq(circuit, dest, b))
    available = _combine(circuit, "LogicGateOr", [_eq(circuit, current, Literal(None)), reuse_a, reuse_b])
    address_ok = _combine(circuit, "LogicGateOr", _address(circuit, dest))
    nonempty = circuit.add("LogicGateNot", _eq(circuit, result, Literal(None)))
    valid = _combine(circuit, "LogicGateAnd", [first_ok, second_ok, distinct, available, address_ok, nonempty])
    return layout(circuit, {_OUTPUTS["valid"]: valid})


def _commit(indices: range) -> tuple[dict, int]:
    circuit = Circuit()
    opcode, a, b, dest = (_receive(circuit, _INPUTS[name]) for name in ("opcode", "a", "b", "destination"))
    result, valid = (_receive(circuit, channel) for channel in (_RESULT, _OUTPUTS["valid"]))
    unary_or_binary = circuit.add("LogicGateNot", _eq(circuit, opcode, Literal(BASE)))
    binary = _combine(circuit, "LogicGateOr", [_eq(circuit, opcode, Literal(code)) for code in BINARY])
    outputs = {}
    for index in indices:
        name = _SLOT_NAMES[index]
        previous = _receive(circuit, _INPUTS[name])
        slot = Literal(index)
        consume_a = circuit.add("LogicGateAnd", unary_or_binary, _eq(circuit, a, slot))
        consume_b = circuit.add("LogicGateAnd", binary, _eq(circuit, b, slot))
        writes_here = _eq(circuit, dest, slot)
        touched = _combine(circuit, "LogicGateOr", [consume_a, consume_b, writes_here])
        changed = circuit.add("LogicGateAnd", valid, touched)
        keep = circuit.add("LogicGateIf", previous, circuit.add("LogicGateNot", changed))
        write = circuit.add("LogicGateIf", result, circuit.add("LogicGateAnd", valid, writes_here))
        circuit.aliases.append((keep, write))
        outputs[_OUTPUTS[name]] = keep
    return layout(circuit, outputs)


def build() -> tuple[dict, dict]:
    readers = tuple(_slot_reader(name, channel) for name, channel in (("a", _A), ("b", _B), ("destination", _DEST)))
    operation, guard = _operation(), _guard()
    commits = (_commit(range(3)), _commit(range(3, 6)))
    document = readers[0][0]
    for part, _ in (*readers[1:], operation, guard, *commits):
        _append(document, part["BP"]["Entries"])
    wiring = _local_wiring(document["BP"])
    receive, send = _radio_channels(wiring)
    if (receive.keys() - send.keys() != set(_INPUTS.values())
            or send.keys() != {*_OUTPUTS.values(), _A, _B, _DEST, _RESULT}
            or any(count != 1 for count in send.values())):
        raise ValueError("单步蓝图的发射频道或外部输入与接口不符")
    depth = max(depth for _, depth in readers) + operation[1] + guard[1] + max(depth for _, depth in commits)
    report = {"inputs": _INPUTS, "outputs": _OUTPUTS, "reserved_channels": [1702700, 1702731],
              "quadrants": 4, "height": 5, "opcodes": list(OPCODES), "schedule": "combination",
              "settling": {"hold_signal_ticks": 64 * (depth + 8), "max_gate_depth": depth},
              "platforms": len(wiring.platforms), "building_entries": len(wiring.entries),
              "internal_channels": [_A, _B, _DEST, _RESULT], "global_transmitters": len(send)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出虚拟六槽配方单步与接口表")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = build()
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
