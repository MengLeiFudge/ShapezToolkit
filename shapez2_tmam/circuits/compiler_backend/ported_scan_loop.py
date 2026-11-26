"""用有线主副寄存器复用一次最高层扫描。相位由外部短距口输入。"""

import argparse
from collections import deque
from graphlib import TopologicalSorter
from pathlib import Path
from random import Random

from ...mari.blueprint import Wiring
from ...mari.ports import OPERATIONS, PORTS
from ...mari.signals import Signal, merge, operate
from ..circuit import Circuit, Literal, constant
from ..compiler_contract import BOOL, INT, SHAPE
from ..scan_circuit import scan_step
from . import _write_blueprint
from .ported_assembly import _PhysicalModule, _assemble, _index, _native_graph
from .ported_layout import _Netlist

# 一个追线边最多跨出入缓冲和两段连续线，每段预留 8 信号刻。
_EDGE_AGE = 32
_PHASES = {
    'clear': (),
    'seed': ('a.seed',),
    'seed_hold': ('a.seed', 'a.hold'),
    'idle': ('a.hold', 'b.hold'),
    'b_clear': ('a.hold',),
    'b_write': ('a.hold', 'b.write'),
    'b_overlap': ('a.hold', 'b.write', 'b.hold'),
    'a_clear': ('b.hold',),
    'a_write': ('b.hold', 'a.write'),
    'a_overlap': ('b.hold', 'a.write', 'a.hold'),
}


def _inputs(circuit, types):
    return {name: circuit.add('ConstantSignal', config=constant(i)) for i, name in enumerate(types)}


def _register(seed=False):
    circuit = Circuit()
    types = {'next': SHAPE, 'saved': SHAPE, 'write': BOOL, 'hold': BOOL}
    if seed:
        types.update(target=SHAPE, seed=BOOL)
    pins = _inputs(circuit, types)
    paths = [('next', 'write'), ('saved', 'hold')]
    if seed:
        paths.append(('target', 'seed'))
    drivers = tuple(circuit.add('LogicGateIf', pins[data], pins[enable]) for data, enable in paths)
    # 重叠期两路都驱动同一个值；合并前后的值相同。
    circuit.aliases.append(drivers)
    model = _Netlist.from_circuit(circuit, pins, {'stored': drivers[0]})
    return _PhysicalModule(model, types, {'stored': SHAPE}, ('Foundation_1x1', 0))


def _scan():
    circuit = Circuit()
    types = {'target': SHAPE}
    pins = _inputs(circuit, types)
    step = scan_step(circuit, pins['target'], Literal(1))
    outputs = {'feedback': pins['target'], 'lower': step.lower, 'top': step.top, 'height': step.original_layer}
    model = _Netlist.from_circuit(circuit, pins, outputs)
    return _PhysicalModule(model, types, {'feedback': SHAPE, 'lower': SHAPE, 'top': SHAPE, 'height': INT},
                           ('Foundation_1x2', 0))


def _relay():
    circuit = Circuit()
    types = {'saved': SHAPE}
    pins = _inputs(circuit, types)
    outputs = dict.fromkeys(('return', 'next'), pins['saved'])
    model = _Netlist.from_circuit(circuit, pins, outputs)
    return _PhysicalModule(model, types, dict.fromkeys(outputs, SHAPE), ('Foundation_1x1', 0))


def build_scan_loop():
    modules = {'a': _register(seed=True), 'scan': _scan(), 'b': _register(), 'relay': _relay()}
    feedback = ((('scan', 'feedback'), ('a', 'saved')), (('relay', 'return'), ('b', 'saved')),
                (('relay', 'next'), ('a', 'next')))
    links = ((('a', 'stored'), ('scan', 'target')), (('scan', 'lower'), ('b', 'next')),
             (('b', 'stored'), ('relay', 'saved')), *feedback)
    bp, report = _assemble(modules, links, feedback=feedback)
    report['observe'] = {name: (i, report['modules'][name]['outputs']['stored']) for i, name in ((0, 'a'), (2, 'b'))}
    model = TickReplay(bp, report)
    report['timing'] = {
        'edge_age_max': _EDGE_AGE, 'acyclic_depth': model.depth, 'hold_ticks': model.hold_ticks,
        'phases': _PHASES, 'initialize': ['clear', 'seed', 'seed_hold', 'idle'],
        'step': ['b_clear', 'b_write', 'b_overlap', 'idle', 'a_clear', 'a_write', 'a_overlap', 'idle'],
        'sample': '在提交前后各自的 idle 末尾读取 scan.top 和 scan.height；height 为空表示没有下一层。',
    }
    return bp, report


class TickReplay:
    """从原生接线回放缓冲传播；时序边可以取历史槽中的不同年龄。"""

    def __init__(self, bp, report, profile='mixed'):
        wiring = Wiring(bp['BP'])
        self.inputs = {name: _index(wiring, i, p) for name, (i, p) in report['inputs'].items()}
        self.outputs = {name: _index(wiring, i, p)
                        for name, (i, p) in {**report['outputs'], **report['observe']}.items()}
        self.cut = {_index(wiring, i, p) for i, p in report['feedback']}
        gates = _native_graph(wiring, self.inputs, self.outputs)
        external = set(self.inputs.values())
        parents = {i: {src for arg in args for src, _ in arg if src not in external and i not in self.cut}
                   for i, (_, _, args) in gates.items()}
        depth: dict[int, int] = {}
        self.gates = []
        for i in TopologicalSorter(parents).static_order():
            depth[i] = 1 + max((depth[src] for src in parents[i]), default=0)
            kind, config, args = gates[i]
            self.gates.append((i, kind, config, args))
        self.depth = max(depth.values())
        self.hold_ticks = (2 * self.depth + 4) * _EDGE_AGE
        self.history: dict[int, deque[tuple[Signal, ...]]] = {}
        for i in external | gates.keys():
            width = 1 if i in external else len(PORTS[gates[i][0]][0]) or 1
            self.history[i] = deque([(None,) * width] * (_EDGE_AGE + 1), maxlen=_EDGE_AGE + 1)
        if profile not in ('fast', 'slow', 'mixed'):
            raise ValueError(f'未知延迟配置：{profile}')
        self.profile = profile
        self.memo: dict[int, tuple[tuple[Signal, ...], tuple[Signal, ...]]] = {}
        self.rng = Random(0)
        self.tick = 0

    def step(self, values):
        if values.keys() != self.inputs.keys():
            raise ValueError('逐刻回放需要全部输入')
        current: dict[int, tuple[Signal, ...]] = {idx: (values[name],) for name, idx in self.inputs.items()}
        mixed = self.profile == 'mixed'
        slow = self.profile == 'slow'
        for i, kind, config, args in self.gates:
            if kind == 'ConstantSignal':
                current[i] = (config,)
                continue
            def read(src, port):
                low = int(src not in current)
                age = self.rng.randint(low, _EDGE_AGE) if mixed else _EDGE_AGE if slow else low
                return self.history[src][age - 1][port] if age else current[src][port]
            signals = tuple(merge(read(src, port) for src, port in arg) for arg in args)
            cached = self.memo.get(i)
            if cached is not None and signals == cached[0]:
                current[i] = cached[1]
            else:
                current[i] = signals if kind.startswith('WireTransmitter') else operate(OPERATIONS[kind], signals, config)
                self.memo[i] = (signals, current[i])
        for i, value in current.items():
            self.history[i].appendleft(value)
        self.tick += 1
        return {name: current[i][0] for name, i in self.outputs.items()}


def main():
    from time import perf_counter

    from .ported_auto_scan import CLOCK_CHANNEL, build_autonomous, build_clock

    parser = argparse.ArgumentParser(description='导出自主有线循环扫描器')
    parser.add_argument('--output', type=Path, required=True, help='原生蓝图输出路径')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--external-phases', action='store_true', help='导出旧的外部相位驱动样件')
    mode.add_argument('--clock-only', action='store_true', help='单独导出可供多路扫描共用的主时钟')
    parser.add_argument('--clock-channel', type=int, default=CLOCK_CHANNEL, help='主时钟第一条私有频道')
    args = parser.parse_args()
    try:
        start = perf_counter()
        if args.external_phases:
            bp, report = build_scan_loop()
        elif args.clock_only:
            bp, report = build_clock(args.clock_channel)
        else:
            bp, report = build_autonomous(args.clock_channel)
        report['layout_seconds'] = round(perf_counter() - start, 4)
        _write_blueprint(bp, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
