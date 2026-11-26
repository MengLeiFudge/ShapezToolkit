"""从 Python 组合方法直接生成带有线接口的一进一出直通条带。"""

import argparse
from pathlib import Path

from ...mari.blueprint import Wiring, _kind
from ...mari.ports import PORTS
from ..circuit import Gate, Ref, _TYPES
from ..compiler_contract import Program
from ..compiler_frontend import FrontendError, compile_method
from ..foundations import FOUNDATION_CHUNKS, platform_ground, platform_interior
from . import _write_blueprint
from ._lower import Lowering, _Value


# 同一条带从西向东。每个端口的朝向和距离在最终蓝图回查。
_WEST = ((2, 0, 0, 0),)
_EAST = ((0, 0, 0, 0),)
_ROW = 9
_FOUNDATIONS = ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3")


def _strip_gates(program: Program) -> tuple[Gate, ...]:
    if (program.quadrants, program.height) != (4, 5):
        raise ValueError("直通条带目前使用四象限五层的原生门")
    lowering = Lowering(program)
    method = lowering.functions[program.entry]
    if len(method.inputs) != 1:
        raise ValueError("直通条带需要一个输入参数")
    (arg,) = method.inputs
    # 这个引用仅用于降低阶段标识参数，在生成实体前由有线入口代替。
    param = lowering.circuit.add("ConstantSignal")
    value = lowering.invoke(method.name, (_Value(arg.type, param),)).signal
    chain = []
    gates = lowering.circuit.gates
    while isinstance(value, Ref) and value != param:
        gate = gates[value.node]
        if value.port != 0 or len(gate.inputs) != 1 or PORTS[gate.kind][:2] != (_EAST, _WEST):
            raise ValueError(f"{gate.kind} 超出直通条带支持的西入东出单格门范围")
        chain.append(gate)
        (value,) = gate.inputs
    if value != param or not chain:
        raise ValueError("直通条带需要从输入到输出的非空串联组合链")
    return tuple(reversed(chain))


def _span(start: int, stop: int) -> tuple[tuple[int, str], ...]:
    """在两端已经确定的直线上，逐格比较导线和同板短距跳线。"""
    best: dict[int, tuple[tuple[int, str], ...]] = {stop: ()}
    for x in range(stop - 1, start - 1, -1):
        candidates = [((x, "WireDefaultForwardInternalVariant"), *best[x + 1])]
        for gap in range(2, 6):
            if x + gap + 1 <= stop:
                candidates.append(
                    (
                        (x, "WireTransmitterSenderInternalVariant"),
                        (x + gap, "WireTransmitterReceiverInternalVariant"),
                        *best[x + gap + 1],
                    )
                )
        best[x] = min(candidates, key=len)
    return best[start]


def _render(gates: tuple[Gate, ...], foundation: str, left: int) -> tuple[dict, dict]:
    interior = platform_interior(foundation)
    notches = platform_ground(foundation) - interior
    edges = sorted(x for x, y in notches if y == _ROW)
    west, east = edges[0], edges[-1]
    rows: list[tuple[int, str, str | None]] = [(west, "WireTransmitterReceiverInternalVariant", None)]
    rows.extend((x, kind, None) for x, kind in _span(west + 1, left))
    rows.extend(
        (left + i, _TYPES.get(gate.kind, gate.kind + "InternalVariant"), gate.config) for i, gate in enumerate(gates)
    )
    rows.extend((x, kind, None) for x, kind in _span(left + len(gates), east))
    rows.append((east, "WireTransmitterSenderInternalVariant", None))
    entries = [
        {"T": kind, "X": x, "Y": _ROW, "L": 0, "R": 0, **({"C": cfg} if cfg is not None else {})}
        for x, kind, cfg in rows
    ]
    if any((x, _ROW) not in interior for x, _, _ in rows[1:-1]):
        raise ValueError("直通条带越出平台内部")
    board = {
        "T": foundation,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "B": {"$type": "Building", "BinaryVersion": 1137, "Entries": entries},
    }
    island = {"$type": "Island", "BinaryVersion": 1137, "Entries": [board]}
    wiring = Wiring(island)
    expected_pairs = {i + 1: i for i in range(1, len(entries) - 1) if _kind(entries[i]) == "WireTransmitterSender"}
    if wiring.short_ports != expected_pairs:
        raise ValueError("短距端口存在意外配对")
    gate_positions = range(left, left + len(gates))
    drivers = [0, *(i for i, entry in enumerate(entries) if entry["X"] in gate_positions)]
    destinations = [*drivers[1:], len(entries) - 1]
    for source, destination in zip(drivers, destinations, strict=True):
        actual = tuple(wiring._direct_sources(destination, 0))
        while len(actual) == 1 and actual[0][0] in expected_pairs:
            actual = tuple(wiring._direct_sources(expected_pairs[actual[0][0]], 0))
        if actual != ((source, 0),):
            raise ValueError(f"原生端口 {wiring.sites[destination]} 没有接到条带上一步")

    def port(x):
        return {"X": x, "Y": _ROW, "L": 0, "R": 0}

    return {"V": 1137, "BP": island}, {
        "entry": port(west),
        "exit": port(east),
        "island_tiles": FOUNDATION_CHUNKS[foundation][0],
        "gate_count": len(gates),
        "local_flywires": len(expected_pairs),
        "building_entries": len(entries),
        "global_radios": 0,
    }


def build(program: Program) -> tuple[dict, dict]:
    """按岛格数和建筑数选择直接生成的条带。"""
    gates = _strip_gates(program)
    last_error = None
    for foundation in _FOUNDATIONS:
        interior = sorted(x for x, y in platform_interior(foundation) if y == _ROW)
        layouts = []
        for left in range(interior[0], interior[-1] - len(gates) + 2):
            try:
                layouts.append(_render(gates, foundation, left))
            except ValueError as error:
                # 同向短距端点可能竞争同一接收器，换一个起点。
                last_error = error
        if layouts:
            document, report = min(layouts, key=lambda pair: pair[1]["building_entries"])
            return document, {"method": program.entry, **report}
    if last_error is not None:
        raise ValueError(f"没有满足端口约束的直通条带：{last_error}") from last_error
    raise ValueError("串联组合链超出直通条带的单板容量")


def main() -> int:
    parser = argparse.ArgumentParser(description="直接从 Python 串联组合方法生成短距有线条带")
    parser.add_argument("source", type=Path, help="Python 源码文件")
    parser.add_argument("method", help="单输入串联组合方法")
    parser.add_argument("--output", type=Path, required=True, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        source = args.source.read_text(encoding="utf-8")
        program = compile_method(source, args.method, filename=str(args.source))
        _write_blueprint(*build(program), args.output)
    except (OSError, FrontendError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
