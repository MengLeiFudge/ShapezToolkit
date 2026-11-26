"""从组合方法的网表直接摆放一进一出的短距有线部件。"""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from ...mari.blueprint import Wiring, _kind
from ...mari.ports import PORTS
from ..circuit import Literal, Ref, _TYPES, constant
from ..compiler_contract import Program
from ..factory_dense_layout import _Part, _candidate, _place, _route_buses
from ..factory_progressive_layout import _clear_routes, _clone, _open_tap, _tracks
from ..foundations import platform_ground, platform_interior
from ..wired_module import _Board
from ._lower import Lowering, _Value
from ._snapshot_router import _join


_FOUNDATIONS = ("Foundation_1x1", "Foundation_1x2", "Foundation_1x3", "Foundation_2x2")


def _lower(program):
    if (program.quadrants, program.height) != (4, 5):
        raise ValueError("有线布局目前使用四象限五层的原生门")
    lowering = Lowering(program)
    function = lowering.functions[program.entry]
    if len(function.inputs) != 1:
        raise ValueError("有线布局需要一个输入参数")
    (arg,) = function.inputs
    circuit = lowering.circuit
    # 参数在网表里占一个引用，在原生布局中直接成为飞线入口。
    parameter = circuit.add("ConstantSignal")
    returned = lowering.invoke(function.name, (_Value(arg.type, parameter),)).signal
    if not isinstance(returned, Ref) or returned == parameter:
        raise ValueError("有线布局需要返回计算所得的信号")
    names = circuit.channel_map()
    parts = []
    for index, gate in enumerate(circuit.gates[1:], start=1):
        entry = {"T": _TYPES.get(gate.kind, gate.kind + "InternalVariant")}
        if gate.config is not None:
            entry["C"] = gate.config
        outputs = tuple((names[Ref(index, port)], None) for port in range(len(PORTS[gate.kind][0])))
        inputs = tuple(
            (None, constant(signal.value)) if isinstance(signal, Literal) else (names[signal], None)
            for signal in gate.inputs
        )
        parts.append(_Part(index, entry, (outputs, inputs), (0, 0, 0)))
    return parts, names[parameter], names[returned]


def _put_edge(board, name, coordinate, side):
    x, y = coordinate
    sends = side == 2
    kind = "WireTransmitterSender" if sends else "WireTransmitterReceiver"
    board.entries.append({"T": kind + "InternalVariant", "X": x, "Y": y, "L": 0, "R": 0})
    x, y = x - board.origin_x, y - board.origin_y
    board.occupied.add((x, y, 0))
    board.pin(name, x, y, 0, side)


def _put_part(board, part, active, degree, remaining, last):
    tracks = _tracks(board)
    candidates = []
    pins = {net for group in part.ports for net, _ in group if net in active}
    targets = {net: tracks[net] for net in pins & tracks.keys()}
    protected = {
        net for net, sites in tracks.items() if remaining[net] > 0 and len(sites) <= 3 and _open_tap(board, net, sites)
    }
    distance = {}
    for a, b in sorted(board.ground):
        x, y = a - board.origin_x, b - board.origin_y
        for z in range(3):
            center = x, y, z
            if center in board.occupied:
                continue
            direct = None
            wire = board.traces.get(center)
            if wire:
                if len(wire) != 1:
                    continue
                net, sides = next(iter(wire.items()))
                if net not in pins or degree[net] != 2 or len(sides) != 1 or tracks[net] != {center}:
                    continue
                direct = net, next(iter(sides))
            for rotation in range(4):
                proposal = _candidate(board, part, (*center, rotation), active, direct=direct)
                if proposal is None:
                    continue
                cost = 0
                for pad, (net, _) in proposal[2].items():
                    if net not in targets:
                        continue
                    key = net, pad
                    if key not in distance:
                        u, v, w = pad
                        distance[key] = min(abs(u - p) + abs(v - q) + 4 * abs(w - r) for p, q, r in targets[net])
                    cost += distance[key]
                drift = sum(abs(a - b) for a, b in zip(center, last, strict=True))
                candidates.append(((cost, direct is None, drift, z, y, x, rotation), center, direct, proposal))
    best = None
    blocked = Counter()
    for rank, center, direct, proposal in sorted(candidates)[:12]:
        trial = _clone(board)
        if direct is not None:
            del trial.traces[center]
            trial.terminals[direct[0], center[2]].remove(center)
        _place(trial, proposal)
        pads = [(pad, net) for pad, (net, _) in proposal[2].items() if net in targets]
        pads.sort(key=lambda row: -distance[row[1], row[0]])
        for pad, net in pads:
            if pad not in targets[net] and not _join(trial, net, pad, targets[net], direct=True):
                blocked[net] += 1
                break
        else:
            fresh = _tracks(trial)
            trapped = sum(net in fresh and not _open_tap(trial, net, fresh[net]) for net in protected)
            added = len(trial.entries) - len(board.entries) + len(trial.traces) - len(board.traces)
            score = (trapped, added, rank)
            if best is None or score < best[0]:
                best = score, trial, center
    if best is not None:
        return best[1:]

    # 松开旧走线，保留已验证的器件位置，再试给新增端口腾空间。
    base = _clear_routes(board)
    for _, center, direct, proposal in sorted(candidates)[:6]:
        rebuilt = _candidate(base, part, (*center, proposal[0]["R"]), active, direct=direct)
        if rebuilt is None:
            continue
        trial = _clone(base)
        if direct is not None:
            del trial.traces[center]
            trial.terminals[direct[0], center[2]].remove(center)
        _place(trial, rebuilt)
        try:
            _route_buses(trial, prefer_short=True, direct=True)
        except ValueError:
            continue
        trial.entries = [
            entry
            for entry in trial.entries
            if not PORTS[_kind(entry)][2] or _kind(entry).startswith(("Wire1Up", "Wire2Up"))
        ]
        trial.occupied.difference_update(trial.traces)
        return trial, center
    raise ValueError(f"无法接通第 {part.index} 个器件 {part.entry['T']}，候选 {len(candidates)}，失败 {dict(blocked)}")


def _verify(island, parts, entry_net, exit_net, positions):
    wiring = Wiring(island)
    indices = {site: index for index, site in enumerate(wiring.sites)}
    placed = {part: indices[(0, *site)] for part, site in positions.items()}
    drivers = defaultdict(set, {entry_net: {(0, 0)}})
    for part in parts:
        for port, (net, _) in enumerate(part.ports[0]):
            drivers[net].add((placed[part.index], port))

    def verify(index, port, expected):
        actual = set()
        for source, output in wiring._direct_sources(index, port):
            _, entry = wiring.entries[source]
            actual.add(entry["C"] if _kind(entry) == "ConstantSignal" else (source, output))
        if actual != expected:
            raise ValueError(f"原生端口 {wiring.sites[index]}/{port} 的驱动 {actual} 与网表 {expected} 不一致")

    for part in parts:
        for port, (net, literal) in enumerate(part.ports[1]):
            verify(placed[part.index], port, drivers[net] if literal is None else {literal})
    verify(1, 0, drivers[exit_net])
    if wiring.short_ports:
        raise ValueError("两个开放的板缝端点发生意外配对")


def _layout(parts, entry, exit_, foundation: str, row: int):
    board = _Board(foundation=foundation)
    board.ground = platform_interior(foundation)
    edges = sorted(x for x, y in platform_ground(foundation) - board.ground if y == row)
    _put_edge(board, entry, (edges[0], row), 0)
    _put_edge(board, exit_, (edges[-1], row), 2)
    active = {exit_, *(net for part in parts for net, _ in part.ports[1] if net is not None)}
    degree = Counter(net for part in parts for group in part.ports for net, _ in group if net in active)
    degree.update((entry, exit_))
    last = 0, row - board.origin_y, 0
    positions = {}
    pending = list(parts)
    remaining = Counter(net for part in parts for group in part.ports for net, _ in group if net in active)
    while pending:
        tracks = _tracks(board)

        def score(part):
            nets = {net for group in part.ports for net, _ in group if net in active}
            attached = nets & tracks.keys()
            return len(attached), sum(degree[net] for net in attached), -len(nets - attached), -part.index

        failure = None
        for part in sorted(pending, key=score, reverse=True)[:4]:
            future = remaining.copy()
            future.subtract(net for group in part.ports for net, _ in group if net in active)
            try:
                board, last = _put_part(board, part, active, degree, future, last)
            except ValueError as error:
                failure = error
                continue
            x, y, z = last
            positions[part.index] = x + board.origin_x, y + board.origin_y, z
            remaining = future
            pending.remove(part)
            break
        else:
            raise ValueError(str(failure)) from failure
    island = board.finish()
    _verify(island, parts, entry, exit_, positions)
    return island


def build(program: Program) -> tuple[dict, dict]:
    parts, entry, exit_ = _lower(program)
    errors = []
    for foundation in _FOUNDATIONS:
        proposals = []
        for row in (10, 9):
            try:
                island = _layout(parts, entry, exit_, foundation, row)
            except ValueError as error:
                errors.append(f"{foundation}/{row} {error}")
                continue
            entries = island["Entries"][0]["B"]["Entries"]
            proposals.append((len(entries), island, entries[:2]))
        if proposals:
            count, island, (receiver, sender) = min(proposals, key=lambda item: item[0])
            return {"V": 1137, "BP": island}, {
                "method": program.entry,
                "foundation": foundation,
                "gate_count": len(parts),
                "building_entries": count,
                "global_radios": 0,
                "entry": {key: receiver[key] for key in ("X", "Y", "L", "R")},
                "exit": {key: sender[key] for key in ("X", "Y", "L", "R")},
            }
    raise ValueError("有线部件布局失败。" + "；".join(errors))


def main() -> int:
    from ..compiler_frontend import FrontendError, compile_method
    from . import _write_blueprint

    parser = argparse.ArgumentParser(description="从 Python 组合方法生成短距有线蓝图")
    parser.add_argument("source", type=Path)
    parser.add_argument("method")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        program = compile_method(args.source.read_text(encoding="utf-8"), args.method, filename=str(args.source))
        _write_blueprint(*build(program), args.output)
    except (OSError, FrontendError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
