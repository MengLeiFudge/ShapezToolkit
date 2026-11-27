"""按 Shapez 2 1.2.0-rc3 的信号批更新规则回放原生接线。"""

from base64 import b64decode
from collections import defaultdict
from functools import cache
from graphlib import TopologicalSorter
from random import Random

from ...mari.blueprint import Wiring, _kind
from ...mari.ports import OPERATIONS, PORTS
from ...mari.signals import Signal, decode_constant, merge, operate
from .ported_assembly import _index

_BATCH_MAX = 4
_RADIO_DELAY = 3 * _BATCH_MAX
_Node = tuple[str, tuple[tuple[tuple[int, int], ...], ...], Signal, int]


def _strong_components(dependencies):
    """按依赖图的两个深搜方向求强连通分量。"""
    reverse = dict((i, []) for i in dependencies)
    for node, parents in dependencies.items():
        for parent in parents:
            reverse[parent].append(node)
    visited = set()
    finished = []
    for root in dependencies:
        if root in visited:
            continue
        stack = [(root, iter(dependencies[root]))]
        visited.add(root)
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                finished.append(node)
                stack.pop()
            elif child not in visited:
                visited.add(child)
                stack.append((child, iter(dependencies[child])))
    visited.clear()
    groups = []
    for root in reversed(finished):
        if root in visited:
            continue
        stack = [root]
        visited.add(root)
        group = []
        while stack:
            node = stack.pop()
            group.append(node)
            for child in reverse[node]:
                if child not in visited:
                    visited.add(child)
                    stack.append(child)
        groups.append(tuple(sorted(group)))
    return groups


def _most_backward(group, dependencies):
    """选最长逆序的排列。逐项假定哪一个节点最后更新，记忆化求精确值。"""
    if len(group) == 1:
        return group
    if len(group) > 16:
        raise ValueError('精确逆序压力回放支持最多 16 节点的反馈分量')
    readers = [sum(1 << j for j, target in enumerate(group) if node in dependencies[target]) for node in group]

    @cache
    def best(mask):
        if not mask:
            return 0, ()
        candidates = []
        for i, node in enumerate(group):
            bit = 1 << i
            if mask & bit:
                prior = mask ^ bit
                score, order = best(prior)
                candidates.append((score + (prior & readers[i]).bit_count(), (*order, node)))
        return max(candidates)

    return best((1 << len(group)) - 1)[1]


class BatchReplay:
    """每批推进 1～4 信号刻，支持原生飞线、本地缓冲和无线历史。"""

    def __init__(self, blueprint, report, *, seed=0, adversarial=False):
        wiring = Wiring(blueprint['BP'])
        self.inputs = {name: _index(wiring, i, p) for name, (i, p) in report['inputs'].items()}
        outputs = {**report['outputs'], **report.get('observe', {})}
        paired = {sender: receiver for receiver, sender in wiring.short_ports.items()}
        self.outputs = {name: paired.get(index, index) for name, (i, p) in outputs.items()
                        for index in (_index(wiring, i, p),)}
        external = set(self.inputs.values())
        networks = {wiring._find(pin) for pins in wiring.pins.values() for pin in pins[2]}
        offset = len(wiring.entries)
        self.nodes: dict[int, _Node] = {offset + net: ('merge', (tuple(wiring.drivers[net]),), 0, 1)
                      for net in networks if wiring.drivers[net]}
        shorts = set(wiring.short_ports)

        def arguments(index):
            roots = (wiring._find(pin) for pin in wiring.pins[index][1])
            return tuple(((offset + net, 0),) if offset + net in self.nodes else tuple(wiring.drivers[net])
                         for net in roots)

        for index, (_, entry) in enumerate(wiring.entries):
            if index in external or wiring.pins[index][2] or index in paired:
                continue
            kind = _kind(entry)
            config = 0
            args = arguments(index)
            if kind == 'ConstantSignal':
                config = decode_constant(entry['C'])
                op = 'literal'
            elif kind == 'WireTransmitterReceiver':
                if index not in shorts:
                    raise ValueError(f'原生回放发现未声明的接收口 {wiring.sites[index]}')
                # 飞线一对端点由 SignalPortSystem 建成同一个模拟节点。
                args = arguments(wiring.short_ports[index])
                op = 'merge'
            elif kind == 'WireTransmitterSender':
                op = 'merge'
            elif kind in ('ControlledSignalReceiver', 'ControlledSignalTransmitter'):
                ((source, _),) = wiring._direct_sources(index, 0)
                config = decode_constant(wiring.entries[source][1]['C'])
                if not isinstance(config, int):
                    raise ValueError(f'无线频道不是整数 {wiring.sites[index]}')
                op = 'radio_rx' if kind.endswith('Receiver') else 'radio_tx'
                args = args[1:] if op == 'radio_tx' else ()
            else:
                op = OPERATIONS[kind]
                if kind == 'LogicGateCompare':
                    config = int.from_bytes(b64decode(entry['C']), 'little')
            self.nodes[index] = op, args, config, len(PORTS[kind][0]) or 1
        self.dependencies = {i: {j for arg in args for j, _ in arg if j not in external}
                             for i, (_, args, _, _) in self.nodes.items()}
        groups = _strong_components(self.dependencies)
        membership = {node: i for i, group in enumerate(groups) for node in group}
        between = {i: {membership[p] for n in group for p in self.dependencies[n] if membership[p] != i}
                   for i, group in enumerate(groups)}
        order = []
        rng = Random(seed)
        for i in TopologicalSorter(between).static_order():
            group = groups[i]
            if adversarial:
                order.extend(_most_backward(group, self.dependencies))
            else:
                order.extend(rng.sample(group, len(group)))
        self.order = tuple(order)
        self.feedback_components = tuple(group for group in groups if len(group) > 1 or group[0] in self.dependencies[group[0]])
        self.feedback_flywires = sum(n in shorts for group in self.feedback_components for n in group)
        rank = {node: i for i, node in enumerate(self.order)}
        self.backward_edges = sum(rank[p] >= rank[i] for i, parents in self.dependencies.items() for p in parents)
        self.memory: dict[int, list[tuple[Signal, ...]]] = {i: [(None,) * spec[-1]] * _BATCH_MAX for i, spec in self.nodes.items()}
        self.last_start = dict.fromkeys(self.nodes, -2 * _BATCH_MAX)
        self.radio = defaultdict(dict)
        self.tick = 0

    def batch(self, width, values):
        if not 1 <= width <= _BATCH_MAX or values.keys() != self.inputs.keys():
            raise ValueError('每批需有 1～4 个信号刻和全部公开输入')
        start = self.tick
        stop = start + width
        external = {i: values[name] for name, i in self.inputs.items()}
        memory, previous = self.memory, self.last_start
        # SignalBuffer 的逆序读取用两批起始刻之差修正槽位。
        for i in self.order:
            op, args, config, _ = self.nodes[i]
            for tick in range(start, stop):
                if op == 'literal':
                    result = (config,)
                elif op == 'radio_rx':
                    reading = tick - _RADIO_DELAY
                    stamp, value = self.radio[config].get(reading % (2 * _RADIO_DELAY), (-1, None))
                    result = (value if stamp == reading else None,)
                else:
                    def read(src, port):
                        if src in external:
                            return external[src]
                        age = start - previous[src]
                        return None if age > _BATCH_MAX else memory[src][(tick - age) % _BATCH_MAX][port]

                    signals = tuple(merge(read(src, port) for src, port in arg) for arg in args)
                    if op == 'radio_tx':
                        radio = self.radio[config]
                        address = tick % (2 * _RADIO_DELAY)
                        stamp, value = radio.get(address, (-1, None))
                        radio[address] = (tick, merge((value, signals[0])) if stamp == tick else signals[0])
                        continue
                    result = signals if op == 'merge' else operate(op, signals, config if isinstance(config, int) else 0)
                memory[i][tick % _BATCH_MAX] = result
            previous[i] = start
        self.tick = stop
        return [{name: external[idx] if idx in external else memory[idx][tick % _BATCH_MAX][0]
                 for name, idx in self.outputs.items()} for tick in range(start, stop)]
