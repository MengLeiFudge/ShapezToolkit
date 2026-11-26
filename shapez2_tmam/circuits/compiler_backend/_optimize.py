"""在布线前合并组合网表中的重复计算。"""

from graphlib import TopologicalSorter
from heapq import heapify, heappop, heappush

from ...mari.ports import PORTS
from ..circuit import Circuit, Gate, Ref


_ROTATION = {"VirtualRotator": 1, "VirtualRotatorCCW": -1}
_COMMUTATIVE = {"LogicGateAnd", "LogicGateOr", "LogicGateXOr"}
_EQUALITY_INVERSE = {"AQ==": "Bg==", "Bg==": "AQ=="}


def _gate_key(gate: Gate) -> tuple:
    if gate.kind in _COMMUTATIVE or (gate.kind == "LogicGateCompare" and gate.config in _EQUALITY_INVERSE):
        return gate.kind, gate.config, frozenset(gate.inputs)
    return gate.kind, gate.config, gate.inputs


def _fold_single_polarity(circuit: Circuit, outputs: dict[int, Ref]) -> bool:
    """先看实际出口依赖。只剩取反时，直接翻转比较器模式。"""
    channels = circuit.channel_map()
    writers: dict[int, set[int]] = {}
    for ref, channel in channels.items():
        writers.setdefault(channel, set()).add(ref.node)
    pending = [node for ref in outputs.values() for node in writers[channels[ref]]]
    live = set()
    users: dict[Ref, set[int]] = {ref: {-1} for ref in outputs.values()}
    while pending:
        node = pending.pop()
        if node in live:
            continue
        live.add(node)
        for source in circuit.gates[node].inputs:
            if isinstance(source, Ref):
                users.setdefault(source, set()).add(node)
                pending.extend(writers[channels[source]] - live)
    changed = False
    for node in sorted(live):
        gate = circuit.gates[node]
        if gate.kind != "LogicGateNot":
            continue
        source = gate.inputs[0]
        if not isinstance(source, Ref) or users.get(source) != {node}:
            continue
        compare = circuit.gates[source.node]
        if compare.kind == "LogicGateCompare" and compare.config in _EQUALITY_INVERSE:
            circuit.gates[node] = Gate(compare.kind, compare.inputs, _EQUALITY_INVERSE[compare.config])
            changed = True
    return changed


def compact(circuit: Circuit, outputs: dict[int, Ref], *, distinct: tuple[Ref, ...] = ()) -> tuple[Circuit, dict[int, Ref]]:
    """只合并同一计算或整组等价的互斥驱动，保留原生多出口索引。"""
    owners = list(range(len(circuit.gates)))
    aliases = {}
    for group in circuit.aliases:
        nodes = tuple(ref.node for ref in group)
        if any(ref.port != 0 or circuit.gates[ref.node].kind != "LogicGateIf" for ref in group):
            raise ValueError("组合门合并只接受单出口的互斥选择总线")
        aliases[nodes[0]] = nodes
        for node in nodes:
            owners[node] = nodes[0]

    groups = {i: aliases.get(i, (i,)) for i in range(len(owners)) if owners[i] == i}
    dependencies = {i: dict.fromkeys(owners[source.node] for node in nodes for source in circuit.gates[node].inputs
                                     if isinstance(source, Ref)) for i, nodes in groups.items()}
    sorter = TopologicalSorter(dependencies)
    sorter.prepare()
    ready = list(sorter.get_ready())
    heapify(ready)
    result = Circuit(circuit.channel_base)
    refs: dict[Ref, Ref] = {}
    gates: dict[tuple, Ref] = {}
    buses: dict[frozenset[Gate], Ref] = {}
    orientations: dict[Ref, tuple[Ref, int]] = {}
    rotated: dict[tuple[Ref, int], Ref] = {}
    shared_polarity = False
    while ready:
        owner = heappop(ready)
        sorter.done(owner)
        for next_owner in sorter.get_ready():
            heappush(ready, next_owner)
        nodes = groups[owner]
        mapped = [Gate(gate.kind, tuple(refs[arg] if isinstance(arg, Ref) else arg for arg in gate.inputs), gate.config)
                  for gate in (circuit.gates[node] for node in nodes)]
        if owner in aliases:
            unique = tuple(dict.fromkeys(mapped))
            key = frozenset(unique)
            if key not in buses:
                drivers = tuple(result.add(gate.kind, *gate.inputs, config=gate.config) for gate in unique)
                assert drivers
                if len(drivers) > 1:
                    result.aliases.append(drivers)
                buses[key] = next(iter(drivers))
            for node in nodes:
                refs[Ref(node)] = buses[key]
            continue

        gate, = mapped
        if gate.kind == "LogicGateCompare" and gate.config in _EQUALITY_INVERSE:
            complement = gates.get((gate.kind, _EQUALITY_INVERSE[gate.config], frozenset(gate.inputs)))
            if complement is not None:
                gate = Gate("LogicGateNot", (complement,))
                shared_polarity = True
        rotation = None
        if gate.kind in _ROTATION and isinstance(gate.inputs[0], Ref):
            source = gate.inputs[0]
            base, offset = orientations.get(source, (source, 0))
            rotation = base, (offset + _ROTATION[gate.kind]) % 4
            if rotation[1] == 0:
                refs[Ref(owner)] = base
                continue
            if rotation in rotated:
                refs[Ref(owner)] = rotated[rotation]
                continue
        key = (owner,) if Ref(owner) in distinct else _gate_key(gate)
        if key not in gates:
            gates[key] = result.add(gate.kind, *gate.inputs, config=gate.config)
        ref = gates[key]
        if rotation is not None:
            orientations[ref] = rotation
            rotated[rotation] = ref
        for port in range(len(PORTS[gate.kind][0])):
            refs[Ref(owner, port)] = Ref(ref.node, port)

    remapped_outputs = {channel: refs[ref] for channel, ref in outputs.items()}
    changed = _fold_single_polarity(result, remapped_outputs)
    if not (changed or shared_polarity) and len(result.gates) == len(circuit.gates):
        return circuit, outputs
    return result, remapped_outputs
