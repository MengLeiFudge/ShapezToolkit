"""共享无线节拍与本地导线寄存器组成的自主拆层器。"""

from collections import Counter

from ...mari.blueprint import Wiring, _kind
from ..circuit import Circuit, Literal, Ref, constant
from ..decoder_circuit import height_flags
from ..foundations import TILE_SIZE, foundation_tiles, platform_interior
from ._layout import _EdgeLinks, _layout_platform
from .ported_assembly import _index
from .ported_layout import Notch, _Netlist, _build_netlist

# 五位计数器每 12 刻递增，低两位提供每相四个计数。第六位在第一圈结束后置位。
_PHASE_TICKS = 48
CLOCK_CHANNEL = 1_709_500
_BITS = ('p0', 'p1', 'p2', 'armed')
_Y = (8, 9, 10, 11)


def _clock(channel):
    if not 1 <= channel <= (1 << 24) - 6:
        raise ValueError('主时钟需六个连续频道')
    circuit = Circuit()
    enable = circuit.add('ConstantSignal', config=constant(1))
    read = tuple(circuit.add('ControlledSignalReceiver', Literal(channel + i)) for i in range(6))
    carry = Literal(1)
    writes = []
    for bit in read[:5]:
        toggled = circuit.add('LogicGateXOr', bit, carry)
        writes.append(circuit.add('LogicGateAnd', toggled, enable))
        carry = circuit.add('LogicGateAnd', carry, bit)
    armed = circuit.add('LogicGateOr', read[5], carry)
    writes.append(circuit.add('LogicGateAnd', armed, enable))
    channels = circuit.channel_map()
    outputs = dict(zip(range(channel, channel + 6), writes, strict=True))
    ports = _EdgeLinks({channels[enable]: (27, 0)}, {channels[v]: (y + 17, 0) for v, y in zip(read[2:], _Y, strict=True)})
    placed = _layout_platform(circuit, channels, set(range(1, len(circuit.gates))), outputs, ports)
    wiring = Wiring({'$type': 'Island', 'Entries': [placed.entry]})
    for (index, port), expected in placed.expected.items():
        if tuple(sorted(wiring._direct_sources(index, port))) != expected:
            raise ValueError(f'时钟原生端口 {index}/{port} 失配')
    transmit = dict(zip(_BITS, (wiring.entries[i][1] for i in placed.senders.values()), strict=True))
    return placed.entry, wiring.entries[next(iter(placed.receivers.values()))][1], transmit


def _scanner(foundation):
    circuit = Circuit()
    inputs = {name: circuit.add('ConstantSignal', config=constant(i))
              for i, name in enumerate(('target', *_BITS, 'a_saved', 'b_saved', 'a_input', 'b_input'))}
    armed = inputs['armed']
    p0, p1, p2 = (inputs[name] for name in _BITS[:3])

    def neg(x):
        return circuit.add('LogicGateNot', x)

    def and_(a, b):
        return circuit.add('LogicGateAnd', a, b)

    def or_(a, b):
        return circuit.add('LogicGateOr', a, b)

    n0, n1, n2 = map(neg, (p0, p1, p2))
    seed = neg(armed)
    different = circuit.add('LogicGateXOr', p0, p1)
    a_hold = or_(and_(seed, or_(p1, p2)), and_(armed, or_(n2, p1)))
    a_load = and_(and_(armed, p2), different)
    b_hold = and_(armed, or_(p2, neg(different)))
    b_load = and_(and_(armed, n2), p1)
    a = circuit.add('LogicGateIf', inputs['target'], seed)
    circuit.aliases.append((a, circuit.add('LogicGateIf', inputs['a_saved'], a_hold),
                            circuit.add('LogicGateIf', inputs['a_input'], a_load)))
    split = circuit.add('VirtualUnstacker', a)
    b = circuit.add('LogicGateIf', inputs['b_input'], b_load)
    circuit.aliases.append((b, circuit.add('LogicGateIf', inputs['b_saved'], b_hold)))
    present = circuit.add('LogicGateCompare', a, Literal(None), config='Bg==')
    sample = and_(and_(armed, and_(and_(n0, n1), n2)), present)
    empty_b = circuit.add('LogicGateCompare', b, Literal(None), config='AQ==')
    done = and_(armed, and_(neg(present), empty_b))
    outputs = {'remaining': a, 'sample': sample, 'done': done,
               'staged': b, 'lower': split, 'next': b, 'prior': a}
    model = _Netlist.from_circuit(circuit, inputs, outputs,
                                feedback={'a_saved': 'prior', 'b_saved': 'staged', 'a_input': 'next', 'b_input': 'lower'})
    # 时钟到扫描均走同一条板缝，各端口朝西接入。
    left = min(x for x, _ in platform_interior(foundation)) - 1
    pins = {name: Notch(left, y, 0, 'W') for name, y in zip(_BITS, _Y, strict=True)}
    east = max(x for x, _ in platform_interior(foundation)) + 1
    outputs = {name: Notch(east, y, 0, 'E') for name, y in (('remaining', 10), ('sample', 9))}
    return _build_netlist(model, platform=(foundation, 0), input_ports=pins, output_ports=outputs)


def _readout():
    circuit = Circuit()
    inputs = {n: circuit.add('ConstantSignal', config=constant(i)) for i, n in enumerate(('remaining', 'sample'))}
    target, sample = inputs.values()
    split = circuit.add('VirtualUnstacker', target)
    top = circuit.add('LogicGateIf', Ref(split.node, 1), sample)
    flags = height_flags(circuit, target, sample)
    heights = tuple(circuit.add('LogicGateIf', Literal(i), flag) for i, flag in enumerate(flags, 1))
    circuit.aliases.append(heights)
    model = _Netlist.from_circuit(circuit, inputs, {'top': top, 'original_layer': heights[0], 'sample': sample})
    ports = {name: Notch(2, y, 0, 'W') for name, y in (('remaining', 10), ('sample', 9))}
    return _build_netlist(model, platform=('Foundation_1x2', 0), input_ports=ports, output_ports=None)


def build_clock(channel=CLOCK_CHANNEL):
    board, enable, phases = _clock(channel)
    report = {
        'inputs': {'enable': (0, enable)},
        'outputs': {name: (0, port) for name, port in phases.items()},
        'timing': _timing(channel),
    }
    return {'V': 1137, 'BP': {'$type': 'Island', 'Entries': [board]}}, report


def _timing(channel):
    return {
        'phase_ticks': _PHASE_TICKS, 'cycle_ticks': 8 * _PHASE_TICKS, 'clock_feedback_ticks': 12,
        'reset_hold_ticks': 96, 'startup_ticks': 384, 'clock_channels': tuple(range(channel, channel + 6)),
    }


def build_autonomous(channel=CLOCK_CHANNEL):
    clock, enable, clock_out = _clock(channel)
    for kind in ('Foundation_2x2', 'Foundation_2x3', 'Foundation_3x3'):
        try:
            document, scanner = _scanner(kind)
        except ValueError as error:
            last = error
        else:
            break
    else:
        raise ValueError(f'自主扫描器布线失败：{last}') from last
    part = document['BP']['Entries'][0]
    part['X'] = 2 - min(x for x, _ in platform_interior(kind)) // TILE_SIZE
    readout, reader = _readout()
    label = readout['BP']['Entries'][0]
    right = max(x for x, _ in platform_interior(kind)) // TILE_SIZE
    label['X'] = part['X'] + right + 1
    island = dict(document['BP'], Entries=[clock, part, label])
    wiring = Wiring(island)
    expected = {_index(wiring, 1, scanner['inputs'][name]): _index(wiring, 0, clock_out[name]) for name in _BITS}
    expected.update({_index(wiring, 2, reader['inputs'][name]): _index(wiring, 1, scanner['outputs'][name])
                     for name in ('remaining', 'sample')})
    actual = {dst: src for dst, src in wiring.short_ports.items() if wiring.sites[dst][0] != wiring.sites[src][0]}
    if actual != expected:
        raise ValueError(f'时钟板缝配对失配：{actual} ≠ {expected}')
    counts = Counter(_kind(entry) for _, entry in wiring.entries)
    report = {
        'inputs': {'target': (1, scanner['inputs']['target']), 'enable': (0, enable)},
        'outputs': {**{name: (2, p) for name, p in reader['outputs'].items()}, 'done': (1, scanner['outputs']['done'])},
        'observe': {'remaining': (1, scanner['outputs']['remaining'])},
        'island_tiles': 11 + len(foundation_tiles(kind)), 'building_entries': len(wiring.entries),
        'cross_flywires': len(actual), 'global_receivers': counts['ControlledSignalReceiver'],
        'global_transmitters': counts['ControlledSignalTransmitter'], 'state_global_devices': 0,
        'timing': _timing(channel),
    }
    return {'V': 1137, 'BP': island}, report
