"""把并行分支与公共分发、汇聚电路分别放在相邻平台。"""

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass

from ...mari.blueprint import Wiring
from ...mari.ports import PORTS
from ..circuit import Ref
from .ported_layout import Notch, _layout

_ROTATORS = ('VirtualRotator', 'VirtualRotatorCCW')
_LEAF = 'Foundation_1x1'


@dataclass(frozen=True)
class _Cone:
    nodes: set[int]
    incoming: tuple[int, ...]
    result: int


def _cones(model):
    members = []
    distributed = set(model.inputs.values())
    pre_rotations = set()
    for node, gate in model.gates.items():
        if gate.kind in _ROTATORS and model.nets.get(gate.inputs[0]) in distributed:
            pre_rotations.add(node)
            distributed.add(model.nets[Ref(node)])
    for root in model.lane_nets:
        todo = [root]
        seen = set()
        while todo:
            net = todo.pop()
            for node in sorted(model.writers[net]):
                gate = model.gates[node]
                if node in seen or node in pre_rotations:
                    continue
                seen.add(node)
                todo.extend(model.nets[arg] for arg in gate.inputs if isinstance(arg, Ref))
        members.append(seen)
    uses = Counter(node for group in members for node in group)
    members = [{node for node in group if uses[node] == 1} for group in members]
    cones = []
    for root, group in zip(model.lane_nets, members, strict=True):
        boundary = {model.nets[a] for node in group for a in model.gates[node].inputs if isinstance(a, Ref)
                    and (not (writers := model.writers[model.nets[a]]) or not writers <= group)}
        outputs = {net for net in model.live if model.writers[net] & group
                   and (net in model.outputs.values() or set(model.readers[net]) - group)}
        split_bus = any(drivers & group and drivers - group for drivers in model.writers.values())
        if split_bus or outputs != {root} or not model.writers[root] <= group or not 1 <= len(boundary) <= 8:
            raise ValueError('并行分支需要独占一个出口及其中所有选择总线驱动')
        def order(net):
            return min(i for i in model.readers[net] if i in group), net
        cones.append(_Cone(group, tuple(sorted(boundary, key=order)), root))
    return cones


def _signature(model):
    nets: dict[int, tuple[int, int]] = {net: (-1, i) for i, net in enumerate(model.inputs.values())}
    components = []
    for i, (node, gate) in enumerate(model.gates.items()):
        outputs = tuple(nets.setdefault(model.nets[Ref(node, port)], (i, port))
                        for port in range(len(PORTS[gate.kind][0])))
        components.append((gate.kind, gate.config, outputs,
                           tuple(model.nets[arg] if isinstance(arg, Ref) else arg for arg in gate.inputs)))
    def substitute(arg):
        return nets[arg] if isinstance(arg, int) else arg
    return (tuple((kind, config, outputs, tuple(map(substitute, inputs)))
                  for kind, config, outputs, inputs in components),
            tuple(nets[net] for net in model.outputs.values()))


def _turn(entry):
    entry['X'], entry['Y'] = 19 - entry['X'], 19 - entry['Y']
    entry['R'] = (entry['R'] + 2) % 4


def build_partition(model):
    """把两个或四个独立分支接到同一块分发汇聚板。"""
    cones = _cones(model)
    hub_inputs, hub_outputs = model.inputs.copy(), model.outputs.copy()
    hub_in_ports = {}
    hub_out_ports = {}
    shape = []
    links = []
    leaf_reports = []
    cache = {}
    width = len(cones) // 2
    foundation = 'Foundation_1x1' if width == 1 else 'Foundation_1x2'
    for lane, cone in enumerate(cones):
        name = f'lane{lane}'
        side_n = lane < width
        loc_x = lane % width
        hub_y, hub_side = (2, 'N') if side_n else (17, 'S')
        offset = 20 * loc_x
        def facing_hub(x):
            return offset + (x if side_n else 19 - x)
        leaf_in = {}
        nets = {}
        for i, net in enumerate(cone.incoming):
            u, v = f'i{i}', f'{name}.i{i}'
            # 最中间的凹口留输出，输入从左到右分层排列。
            x, level = (8, 9, 11)[i // 3], i % 3
            leaf_in[u] = Notch(x, 17, level, 'S')
            hub_out_ports[v] = Notch(facing_hub(x), hub_y, level, hub_side)
            nets[u] = net
            hub_outputs[v] = net
            links.append(((0, v), (lane + 1, u)))
        leaf_out = {'result': Notch(10, 17, 0, 'S')}
        hub_inputs[name] = cone.result
        hub_in_ports[name] = Notch(facing_hub(10), hub_y, 0, hub_side)
        links.append(((lane + 1, 'result'), (0, name)))
        leaf = model.slice(cone.nodes, nets, {'result': cone.result})
        key = _signature(leaf)
        if key not in cache:
            last = None
            for center in ((7, 0), (9, 0), (5, 0), (6, 1), (8, 2)):
                try:
                    cache[key] = _layout(leaf, leaf.units(), _LEAF, 0, 2, (center,), leaf_in, leaf_out)
                    break
                except ValueError as error:
                    last = error
            else:
                raise ValueError(f'分支 {lane} 布线失败：{last}')
        bp, report = deepcopy(cache[key])
        if not side_n:
            entry = bp['BP']['Entries'][0]
            for item in entry['B']['Entries']:
                _turn(item)
            for direction in ('inputs', 'outputs'):
                for port in report[direction].values():
                    _turn(port)
            for group in report['replicated_units'] + report['direct_macros'] + report['tapped_macros']:
                for i, (x, y, z) in enumerate(group):
                    group[i] = 19 - x, 19 - y, z
            for link in report['flywire_crossings']:
                for key in ('sender', 'receiver'):
                    x, y, z = link[key]
                    link[key] = 19 - x, 19 - y, z
                link['obstacles'] = [(19 - x, 19 - y, z) for x, y, z in link['obstacles']]
        shape.append(dict(bp['BP']['Entries'][0], X=loc_x, Y=-1 if side_n else 1, Z=0))
        leaf_reports.append(report)
    hub_nodes = model.gates.keys() - set().union(*(cone.nodes for cone in cones))
    hub = model.slice(hub_nodes, hub_inputs, hub_outputs)
    centers = tuple((7, 0) if name not in hub_out_ports else
                    (3 if hub_out_ports[name].side == 'N' else 10, hub_out_ports[name].level)
                    for name in hub_outputs)
    for stride in (2, 3, 1):
        try:
            bp, report = _layout(hub, hub.units(), foundation, 0, stride, centers, hub_in_ports, hub_out_ports)
            break
        except ValueError as error:
            last = error
    else:
        raise ValueError(f'汇聚板布线失败：{last}')
    parts = [report, *leaf_reports]
    entries = [bp['BP']['Entries'][0], *shape]
    island = dict(bp['BP'], Entries=entries)
    wiring = Wiring(island)

    def index(board, direction, name):
        port = parts[board][direction][name]
        return wiring.lookup[board, port['X'], port['Y'], port['L']]

    targets = {index(b, 'inputs', i): index(a, 'outputs', o) for (a, o), (b, i) in links}
    actual = {rx: tx for rx, tx in wiring.short_ports.items() if wiring.sites[rx][0] != wiring.sites[tx][0]}
    if actual != targets:
        raise ValueError('四分支的板缝配对与网表不一致')
    return dict(bp, BP=island), {
        'methods': model.methods, 'modules': dict(enumerate(parts)), 'building_entries': len(wiring.entries),
        'global_radios': 0, 'cross_flywires': len(actual), 'logic_gates': len(model.gates),
        'selection_buses': sum(len(w) > 1 for w in model.writers.values()),
        'island_tiles': sum(p['island_tiles'] for p in parts),
        'unique_layouts': len(cache) + 1,
        'ripups': report['ripups'] + sum(r['ripups'] for _, r in cache.values()),
        'ripup_attempts': report['ripup_attempts'] + sum(r['ripup_attempts'] for _, r in cache.values()),
        'inputs': {name: (0, report['inputs'][name]) for name in model.inputs},
        'outputs': {name: (0, report['outputs'][name]) for name in model.outputs},
    }
