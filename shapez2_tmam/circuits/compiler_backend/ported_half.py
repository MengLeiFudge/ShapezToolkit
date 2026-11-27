"""按原生半形判据逐层收窄信号，编译标准半形有线部件。"""

import argparse
from pathlib import Path
from time import perf_counter

from ...synthesis.physics import Rules
from ..circuit import Circuit, Literal, constant
from ..compiler_contract import BOOL, INT, SHAPE
from ..decoder_circuit import decode_row
from ..half_circuit import _combine
from . import _write_blueprint
from ._lower import Lowering, _Value
from .ported_assembly import _PhysicalModule, _assemble
from .ported_layout import _Netlist
from .ported_read_five import split_rows


_PREFIX = ('occupied', 'prefix_pin', 'crystal', 'last_ordinary')
_MIDDLE = (*_PREFIX, 'outside_pin', 'gap', 'admissible', 'special')
_STATE = (_PREFIX, _MIDDLE, _MIDDLE, ('occupied', 'last_ordinary', 'outside_pin', 'gap', 'admissible', 'special'),
          ('admissible',))
_LEVEL = {'last_ordinary': 1, 'outside_pin': 1, 'gap': 1,
          'special': 2, 'admissible': 2, 'outside': 2, 'uncolored': 2}


def _ports(circuit, kinds):
    return {name: circuit.add('ConstantSignal', config=constant(i)) for i, name in enumerate(kinds)}


def _part(circuit, inputs, outputs, types, kinds, foundation):
    return _PhysicalModule(_Netlist.from_circuit(circuit, inputs, outputs), types, kinds, (foundation, 0), rotate=True)


def _raw(programs, *, turn_second=False):
    circuit = Circuit()
    types = {'target': SHAPE}
    inputs = _ports(circuit, types)
    target = inputs['target']
    outputs = {}
    for key, program in programs.items():
        lowering = Lowering(program)
        lowering.circuit = circuit
        ref = lowering.invoke(program.entry, (_Value(SHAPE, target),)).signal
        if isinstance(ref, Literal):
            raise ValueError('原色拆层编译为常量')
        outputs[key] = ref
    row = outputs.pop('row', target)
    outputs.update(q0=row, q1=circuit.add('VirtualRotatorCCW', row) if turn_second else row)
    return _part(circuit, inputs, outputs, types, dict.fromkeys(outputs, SHAPE), 'Foundation_1x1')


def _column_checks(circuit, cell, previous, z):
    def gate(op, *args):
        return circuit.add('LogicGate' + op, *args)

    occupied, pin, crystal = cell.occupied, cell.pin, cell.crystal
    ordinary = gate('And', occupied, gate('Not', gate('Or', pin, crystal)))
    if z == 0:
        return dict(occupied=occupied, prefix_pin=pin, crystal=crystal, last_ordinary=ordinary)

    p = previous
    below_empty = gate('Not', p['occupied'])
    if z == 1:
        failure = gate('And', below_empty, gate('Or', pin, crystal))
        permitted = gate('Not', failure)
        outside_pin = gate('And', pin, gate('Not', p['prefix_pin']))
        gap = gate('And', p['crystal'], gate('Not', occupied))
        special = gate('And', p['crystal'], ordinary)
    else:
        # A：检查悬空针、针前缀、晶体最近支撑和两晶之间的空格。
        floating_pin = gate('And', pin, below_empty)
        forbidden_gap = p['gap'] if z < 4 else gate('And', p['gap'], gate('Not', p['special']))
        no_support = gate('Not', gate('Or', p['occupied'], p['last_ordinary']))
        forbidden = gate('Or', p['outside_pin'], gate('Or', forbidden_gap, no_support))
        failure = gate('Or', floating_pin, gate('And', crystal, forbidden))
        permitted = gate('And', p['admissible'], gate('Not', failure))
        if z == 4:
            return {'admissible': permitted}
        outside_pin = gate('Or', p['outside_pin'], gate('And', pin, gate('Not', p['prefix_pin'])))
        gap = gate('Or', p['gap'], gate('And', p['crystal'], gate('Not', occupied)))
        if z == 2:
            special = gate('And', p['special'], gate('Or', ordinary, gate('Not', occupied)))
        else:
            third_empty = gate('And', below_empty, ordinary)
            fourth_empty = gate('And', p['occupied'], gate('Not', occupied))
            special = gate('And', p['special'], gate('Or', third_empty, fourth_empty))
    return dict(occupied=occupied, prefix_pin=gate('And', p['prefix_pin'], pin), crystal=gate('Or', p['crystal'], crystal),
                last_ordinary=gate('Or', ordinary, gate('And', gate('Not', occupied), p['last_ordinary'])),
                outside_pin=outside_pin, gap=gap, admissible=permitted, special=special)


def _column(q, z, foundation, *, turned=False):
    circuit = Circuit()
    types = {'row': SHAPE}
    scope = ('uncolored', 'outside') if q == 0 else ('uncolored',)
    if z:
        types.update(dict.fromkeys((*_STATE[z - 1], *scope), BOOL))
    inputs = _ports(circuit, types)
    row = inputs['row']
    cell = decode_row(circuit, row, Rules(4))[0 if turned else q]
    checks = _column_checks(circuit, cell, inputs, z)
    values = {name: checks[name] for name in _STATE[z]}
    color = circuit.add('LogicGateCompare', cell.color, Literal('color:u'), config='AQ==')
    flags = {'uncolored': circuit.add('LogicGateAnd', cell.crystal, color)}
    if q == 0:
        cut = circuit.add('VirtualHalfCutter', row)
        # 单层全触地，标准半形经过空切仍等于原行。
        flags['outside'] = circuit.add('LogicGateCompare', cut, row, config='Bg==')
    values.update({name: circuit.add('LogicGateOr', signal, inputs[name]) if z else signal
                   for name, signal in flags.items()})
    return _part(circuit, inputs, values, types, dict.fromkeys(values, BOOL), foundation)


def _classify():
    circuit = Circuit()
    types = {'target': SHAPE, **dict.fromkeys(('enable', 'a0', 'a1', 'u0', 'u1', 'outside'), BOOL)}
    inputs = _ports(circuit, types)
    target, enable, a0, a1, u0, u1, outside = inputs.values()
    cut = circuit.add('VirtualHalfCutter', target)
    stable = circuit.add('LogicGateCompare', cut, target, config='AQ==')
    present = circuit.add('LogicGateCompare', target, Literal(None), config='Bg==')
    valid = circuit.add('LogicGateAnd', enable, present)
    standard = circuit.add('LogicGateNot', circuit.add('LogicGateAnd', outside, enable))
    admissible = circuit.add('LogicGateOr', circuit.add('LogicGateNot', enable), circuit.add('LogicGateAnd', a0, a1))
    outside_scope = _combine(circuit, 'LogicGateOr', [outside, u0, u1])
    in_scope = circuit.add('LogicGateAnd', valid, circuit.add('LogicGateNot', outside_scope))
    predicate = circuit.add('LogicGateAnd', stable, admissible)
    solved = circuit.add('LogicGateAnd', in_scope, predicate)
    unsolvable = circuit.add('LogicGateAnd', in_scope, circuit.add('LogicGateNot', predicate))
    unknown = circuit.add('LogicGateAnd', valid, outside_scope)
    status = tuple(circuit.add('LogicGateIf', Literal(i), flag)
                   for i, flag in enumerate((solved, unsolvable, unknown), 1))
    circuit.aliases.append(status)
    outputs = {'status': status[0], 'solvable': solved, 'unsolvable': unsolvable, 'unknown': unknown,
               'standard_half': standard, 'stable': stable, 'columns_admissible': admissible, 'original': target}
    kinds = {**dict.fromkeys(outputs, BOOL), 'status': INT, 'original': SHAPE}
    return _part(circuit, inputs, outputs, types, kinds, 'Foundation_1x3')


def build():
    stages, _, _ = split_rows()
    modules = {'verdict': _classify()}
    placements = {'verdict': (-1, 0, 1)}
    original = (('verdict', 'original'), ('raw4', 'target'))
    links = [original]
    for z in reversed(range(5)):
        x = 4 - z
        name = f'raw{z}'
        # 第一层拆行板同时转向第二列，省掉判断板里的一段入线。
        modules[name] = _raw(stages[f'layer{z}'].programs if z else {}, turn_second=z == 1)
        placements[name] = (x, 0, 0)
        if z < 4:
            links.append(((f'raw{z+1}', 'remaining' if z else 'bottom'), (name, 'target')))
        for q in (0, 1):
            stage = f'c{q}z{z}'
            tall = z in (1, 2, 3)
            foundation = 'Foundation_1x2' if tall else 'Foundation_1x1'
            placements[stage] = (x, 1 if q else -1 - tall, int(tall))
            if q == 1 and z == 3:
                foundation = 'Foundation_L3'
                placements[stage] = (x, 2, 2)
            modules[stage] = _column(q, z, foundation, turned=q == 1 and z == 1)
            links.append(((name, f'q{q}'), (stage, 'row')))
            if z:
                fields = tuple(name for name in modules[stage].inputs if name != 'row')
                links.extend(((f'c{q}z{z-1}', field), (stage, field)) for field in fields)
    links.extend(((f'c{q}z4', field), ('verdict', f'{dest}{q}')) for q in (0, 1)
                 for field, dest in (('admissible', 'a'), ('uncolored', 'u')))
    links.append((('c0z4', 'outside'), ('verdict', 'outside')))
    levels = {name: {port: (_LEVEL.get(port, 0) + (2 if name == 'c1z1' else 0)) % 3
                     for port in module.inputs} for name, module in modules.items()}
    blueprint, report = _assemble(modules, tuple(links), feedback=(original,), placements=placements,
                                  port_levels=levels)
    report.pop('feedback')
    report['inputs'] = {key.split('.')[1]: value for key, value in report['inputs'].items()}
    report['outputs'] = {key.split('.')[1]: value for key, value in report['outputs'].items()}
    return blueprint, report


def main():
    parser = argparse.ArgumentParser(description='从标准半形判据导出窄接口有线蓝图')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    start = perf_counter()
    blueprint, report = build()
    report['layout_seconds'] = round(perf_counter() - start, 4)
    _write_blueprint(blueprint, report, args.output)


if __name__ == '__main__':
    main()
