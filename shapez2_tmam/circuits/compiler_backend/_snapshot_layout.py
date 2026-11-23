"""紧凑排列锁存单元，并为整块锁存的控制逻辑布线。"""

from collections import defaultdict
from itertools import product
from random import Random

from ...mari.blueprint import DIRECTIONS, PORTS, Wiring, _rotate
from ..circuit import constant
from ..wired_module import _Board


class _Layout:
    def __init__(self, foundation):
        self.board = _Board(foundation=foundation)
        self.drivers = defaultdict(list)
        self.inputs = {}
        self.literals = {}

    def radio(self, net, channel, x, y, rotation, *, receive):
        kind = "ControlledSignalReceiver" if receive else "ControlledSignalTransmitter"
        index = self.board.place(kind, x, y, 0, rotation, radius=1, height=3)
        dx, dy = _rotate(0, -2, rotation)
        cfg = self.board.place("ConstantSignal", x + dx, y + dy, 0, (1 + rotation) % 4, constant(channel))
        self.literals[index, 0] = ((cfg, 0),)
        if receive:
            self.drivers[net].append((index, 0))
            dx, dy = _rotate(1, 0, rotation)
            self.board.pin(net, x + dx, y + dy, 0, rotation)
        else:
            self.inputs[index, 1] = net
            dx, dy = _rotate(-1, 0, rotation)
            self.board.pin(net, x + dx, y + dy, 0, (rotation + 2) % 4)

    def gate(self, gate, x, y, z, rotation):
        kind, args, outputs, config = gate
        index = self.board.place(kind, x, y, z, rotation, config)
        for port, (net, (direction, _, _, _)) in enumerate(zip(outputs, PORTS[kind][0], strict=True)):
            self.drivers[net].append((index, port))
            self.board.pin(net, x, y, z, (direction + rotation) % 4)
        for port, (arg, (direction, _, _, _)) in enumerate(zip(args, PORTS[kind][1], strict=True)):
            side = (direction + rotation) % 4
            if isinstance(arg, str):
                self.board.pin(arg, x, y, z, side)
                self.inputs[index, port] = arg
            else:
                dx, dy = DIRECTIONS[side]
                cfg = self.board.place("ConstantSignal", x + dx, y + dy, z, (side + 2) % 4, constant(arg))
                self.literals[index, port] = ((cfg, 0),)

    def cell(self, x, y, source, stored, saved=None):
        value = f"value-{stored}"
        incoming = f"incoming-{stored}"
        saved = saved or f"saved-{stored}"
        self.radio(incoming, source, x + 1, y + 2, 0, receive=True)
        self.radio(saved, stored, x + 1, y + 6, 0, receive=True)
        self.radio(value, stored, x + 7, y + 4, 0, receive=False)
        for offset, net, level in ((0, "load", 1), (4, "retain", 2)):
            arg = incoming if offset == 0 else saved
            self.gate(("LogicGateIf", (arg, net), (value,), None), x + 4, y + 2 + offset, 0, 0)
            self.board.place(f"WireDefault{level}UpBackward", x + 4, y + offset, 0, 3, height=level + 1)
            for z in (0, level):
                self.board.pin(net, x + 4, y + offset, z, 1)
            # 每个单元的数据线接到本单元的发射器，就地验线后再摆下一个。
            self.route(arg, 0)
        self.route(value, 0)

    def route(self, net, level):
        key = net, level
        connected = {p for p, nets in self.board.traces.items()
                     if p[2] == level and len(nets) == 1 and len(nets.get(net, ())) > 1}
        if not self.board.route(net, self.board.terminals[key], connected=connected, protect_pads=True):
            raise ValueError(f"锁存板的本地线 {net} 在第 {level} 层无法接通")

    def controls(self, gates, order):
        board = self.board
        sites = tuple(product(range(2, board.width - 1, 4), range(3, board.height - 1, 4), order, range(4)))
        random = Random(1)
        for gate in gates:
            kind, args, outputs, _ = gate
            signals = (*outputs, *args)
            directions = tuple(d for ports in PORTS[kind][:2] for d, _, _, _ in ports)
            pads = {net: tuple(p for level in range(3) for p in board.terminals.get((net, level), ()))
                    for net in signals if isinstance(net, str)}
            candidates = []
            for x, y, z, rotation in sites:
                if (x, y, z) in board.occupied or (x, y, z) in board.traces:
                    continue
                score = 2 * sum((x + dx, y + dy, z) in board.occupied or (x + dx, y + dy, z) in board.traces
                                for dx, dy in product(range(-2, 3), repeat=2))
                for net, direction in zip(signals, directions, strict=True):
                    dx, dy = DIRECTIONS[(direction + rotation) % 4]
                    site = a, b, _ = x + dx, y + dy, z
                    if site in board.occupied:
                        break
                    traces = board.traces.get(site)
                    if traces and (not isinstance(net, str) or traces.keys() != {net}):
                        break
                    if isinstance(net, str) and pads[net]:
                        score += min(abs(a - u) + abs(b - v) + 6 * abs(z - l) for u, v, l in pads[net])
                else:
                    candidates.append((score + random.random() * 4, order.index(z), y, x, rotation))
            last_error = None
            for _, rank, y, x, rotation in sorted(candidates)[:40]:
                z = order[rank]
                trial = self.copy()
                try:
                    trial.gate(gate, x, y, z, rotation)
                    trial.connect(pads, z)
                except ValueError as error:
                    last_error = error
                    continue
                self.board, self.drivers = trial.board, trial.drivers
                self.inputs, self.literals = trial.inputs, trial.literals
                board = self.board
                break
            else:
                raise ValueError(f"锁存板无法放置并接通控制门 {outputs}") from last_error

    def copy(self):
        trial = _Layout(self.board.foundation)
        trial.board.entries = self.board.entries.copy()
        trial.board.occupied = self.board.occupied.copy()
        trial.board.traces.update({p: {n: v.copy() for n, v in nets.items()}
                                   for p, nets in self.board.traces.items()})
        trial.board.terminals.update({k: v.copy() for k, v in self.board.terminals.items()})
        trial.drivers.update({k: v.copy() for k, v in self.drivers.items()})
        trial.inputs = self.inputs.copy()
        trial.literals = self.literals.copy()
        return trial

    def connect(self, pads, level):
        for net, old_sites in pads.items():
            levels = {z for _, _, z in old_sites if (net not in ("load", "retain") or z > 0)}
            if levels and level not in levels:
                other = min(levels, key=lambda z: (abs(z - level), z))
                self.join_layers(net, other, level)
            else:
                self.route(net, level)

    def join_layers(self, net, old, new):
        lo, hi = sorted((old, new))
        board = self.board
        old_track = [p for p, nets in board.traces.items() if p[2] == old and net in nets and len(nets) == 1]
        new_pads = board.terminals[net, new]
        candidates = []
        for x, y in product(range(1, board.width - 1), range(1, board.height - 1)):
            if any((x, y, z) in board.occupied or (x, y, z) in board.traces for z in range(lo, hi + 1)):
                continue
            for direction, (dx, dy) in enumerate(DIRECTIONS):
                a, b = x + dx, y + dy
                if any((a, b, z) in board.occupied or board.traces.get((a, b, z), {}).keys() - {net}
                       for z in (lo, hi)):
                    continue
                distance = sum(min(abs(a - u) + abs(b - v) for u, v, _ in sites)
                               for sites in (old_track, new_pads))
                candidates.append((distance, y, x, direction))
        for _, y, x, direction in sorted(candidates)[:24]:
            trial = self.copy()
            try:
                trial.board.place(f"WireDefault{hi - lo}UpBackward", x, y, lo, (direction + 2) % 4,
                                  height=hi - lo + 1)
                for level in (old, new):
                    trial.board.pin(net, x, y, level, direction)
                    trial.route(net, level)
            except ValueError:
                continue
            self.board = trial.board
            return
        raise ValueError(f"锁存板的本地线 {net} 无法从第 {old} 层接到第 {new} 层")

    def finish(self):
        board = self.board
        blueprint = board.finish()
        wiring = Wiring(blueprint)
        expected = {**self.literals, **{pin: tuple(sorted(self.drivers[net])) for pin, net in self.inputs.items()}}
        for pin, sources in expected.items():
            if not sources or wiring.sources(*pin) != sources:
                raise ValueError(f"锁存板输入 {pin} 的实际驱动 {wiring.sources(*pin)}，预期 {sources}")
        return blueprint["Entries"][0]


def compact_snapshot(fields, control, height, column):
    # 单元的尺寸由三个收发器及两根换层线决定。上侧和右侧留给控制接口。
    layout = _Layout("Foundation_2x3")
    for i, (source, stored) in enumerate(fields):
        row, col = divmod(i, 5)
        saved = f"height{i - 2}" if 2 <= i < 6 else None
        layout.cell(col * 9, 8 + row * 8, source, stored, saved)
    for i, (receive, net, channel) in enumerate(
            [(True, net, channel) for net, channel in control.inputs.items()]
            + [(False, net, channel) for net, channel in control.outputs.items()]):
        layout.radio(net, channel, 2 + 5 * i, 2, 1 if receive else 3, receive=receive)
    layout.radio("column", column, 47, 10, 2, receive=True)
    layout.radio("current_height", height.outputs["current_height"], 47, 15, 0, receive=False)
    for net, level in (("load", 1), ("retain", 2)):
        gate, = (gate for gate in control.gates if gate[2] == (net,))
        layout.controls((gate,), (level,))
    gates = tuple(gate for gate in reversed(control.gates) if gate[2] not in (("load",), ("retain",)))
    layout.controls((*gates, *height.gates), (1, 2))
    return layout.finish()


def compact_batch(batch):
    layout = _Layout("Foundation_1x1")
    for (net, channel), y in zip(batch.inputs.items(), (3, 8), strict=True):
        layout.radio(net, channel, 2, y, 0, receive=True)
    layout.radio("start", batch.outputs["start"], 11, 6, 0, receive=False)
    layout.controls(batch.gates, (0,))
    return layout.finish()
