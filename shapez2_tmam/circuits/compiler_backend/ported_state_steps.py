"""以有线双寄存器反复执行带类型的定步更新方法。"""

import argparse
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter

from ...mari.blueprint import Wiring, _kind
from ...synthesis.physics import Shape
from ..circuit import Circuit, Literal, constant
from ..compiler_contract import BOOL, INT, SHAPE, Program
from ..compiler_frontend import compile_field_methods
from ..foundations import TILE_SIZE, foundation_tiles, platform_interior
from . import _write_blueprint
from .ported_assembly import _index, require_public_access
from .ported_auto_scan import CLOCK_CHANNEL, _BITS, _PHASE_TICKS, _Y, _clock, _timing
from .ported_layout import Notch, _Netlist, _build_netlist
from .ported_replay import BatchReplay


_GATES = ('start', 'a_keep', 'a_load', 'b_keep', 'b_load', 'terminal', 'phase_bit')


def _register_model(fields, initial, steps=None):
    circuit = Circuit()
    inputs = {}
    feedback = {}
    outputs = {}

    def input_(name):
        src = circuit.add('ConstantSignal', config=constant(len(inputs)))
        inputs[name] = src
        return src

    def gate(op, *args):
        return circuit.add('LogicGate' + op, *args)

    def combine(*args):
        refs = tuple(gate('If', value, condition) for value, condition in args)
        circuit.aliases.append(refs)
        return refs[0]

    def bank(name, current, source, pending, controls):
        start, a_keep, a_load, b_keep, b_load, *_ = controls
        saved = input_(f'b_{name}')
        staged = input_(f'staged_{name}')
        a = combine((source, start), (current, a_keep), (staged, a_load))
        b = combine((saved, b_keep), (pending, b_load))
        feedback.update({f'a_{name}': f'a_keep_{name}', f'b_{name}': f'b_keep_{name}',
                         f'staged_{name}': f'b_load_{name}'})
        outputs.update({f'a_keep_{name}': a, f'b_keep_{name}': b, f'b_load_{name}': b})
        return a

    if steps is None:
        controls = tuple(map(input_, _GATES))
        # 终止时先冻结 A。至少等到下一相位，再打开对外发布。
        start, terminal, phase_bit = controls[0], controls[-2], controls[-1]
        done = combine((Literal(1), gate('And', terminal, phase_bit)),
                       (input_('published'), gate('Not', start)))
        feedback['published'] = 'hold_published'
        outputs.update(done=done, hold_published=done)
        for name in fields:
            current = input_(f'a_{name}')
            source = Literal(initial[name]) if name in initial else input_(f'initial_{name}')
            a = bank(name, current, source, input_(f'next_{name}'), controls)
            outputs[name] = a
            outputs[f'result_{name}'] = gate('If', a, done)
        return _Netlist.from_circuit(circuit, inputs, outputs, feedback=feedback)

    p0, p1, p2, armed = map(input_, _BITS)
    start = gate('Not', armed)
    n0, n1, n2 = (gate('Not', bit) for bit in (p0, p1, p2))
    a_old = input_('a_round')
    previous_done = input_('done_feedback')
    settled = circuit.add('LogicGateCompare', a_old, Literal(steps), config='AQ==')
    phase0 = gate('And', n0, gate('And', n1, n2))
    done = combine((Literal(1), gate('And', armed, gate('And', phase0, settled))),
                   (previous_done, armed))
    feedback['done_feedback'] = 'latched_done'
    outputs['latched_done'] = done
    run = gate('And', armed, gate('Not', done))
    different = gate('XOr', p0, p1)
    a_keep = gate('Or', done, gate('Or', gate('And', start, gate('Or', p1, p2)),
                                  gate('And', armed, gate('Or', n2, p1))))
    a_load = gate('And', gate('And', run, p2), different)
    b_keep = gate('And', run, gate('Or', p2, gate('Not', different)))
    b_load = gate('And', gate('And', run, n2), p1)
    advance = combine(*((Literal(min(i + 1, steps)), circuit.add('LogicGateCompare', a_old,
                       Literal(i), config='AQ==')) for i in range(steps + 1)))
    controls = start, a_keep, a_load, b_keep, b_load, done, p0
    bank('round', a_old, Literal(0), advance, controls)
    outputs.update(zip(_GATES, controls, strict=True))
    return _Netlist.from_circuit(circuit, inputs, outputs, feedback=feedback)


def _args(programs, steps):
    if not 1 <= len(programs) <= 6 or type(steps) is not int or not 1 <= steps <= 16:
        raise ValueError('定步迭代支持 1～6 个状态字段和 1～16 轮')
    reserved = ('a_keep_', 'b_keep_', 'b_load_', 'result_')
    if any(not name.isidentifier() or name in ('round', 'done', 'hold_published') or name.startswith(reserved)
           for name in programs):
        raise ValueError('状态字段须为有效标识符，且与控制和结果端口区分')
    methods = {name: next(f for f in prog.functions if f.name == prog.entry) for name, prog in programs.items()}
    args = next(iter(methods.values())).inputs
    types = {arg.name: arg.type for arg in args}
    if (types.keys() != methods.keys() or any(f.inputs != args or f.result != types[name] for name, f in methods.items())
            or any(kind not in (SHAPE, BOOL, INT) for kind in types.values())):
        raise ValueError('更新方法须读取同名同类型的整组旧状态，并返回本字段类型')
    return types


def _build(programs, steps, initial, clock_channel, state_kind, worker_kind, control_kind='Foundation_3x3'):
    types = _args(programs, steps)
    if initial.keys() - types.keys():
        raise ValueError('指定了未知的初值字段')
    for name, value in initial.items():
        kind = types[name]
        if kind == SHAPE:
            valid = isinstance(value, Shape) or value is None
        elif kind == BOOL:
            valid = isinstance(value, int) and value in (0, 1)
        else:
            valid = isinstance(value, int) and -(1 << 31) <= value < 1 << 31
        if not valid:
            raise ValueError(f'{name} 的初值类型与更新方法不同')
    worker = _Netlist(programs)
    state = _register_model(types, initial)
    control = _register_model((), {}, steps)
    state_area = platform_interior(state_kind)
    right, south = max(x for x, _ in state_area) + 1, max(y for _, y in state_area) + 1
    left, north = min(x for x, _ in state_area) - 1, min(y for _, y in state_area) - 1
    width = 1 + right // TILE_SIZE
    seam_ports = ((y, z) for z in range(3) for y in (10, 9, 11, 8, 30, 29, 31, 28))
    phase_ports = ((y, z) for z in range(3) for y in (9, 10, 11, 8, 29, 30, 31, 28))
    state_in, state_out, worker_in, worker_out, control_out = {}, {}, {}, {}, {}
    for name in _GATES:
        y, z = (8, 2) if name == 'phase_bit' else next(phase_ports)
        state_in[name] = Notch(left, y, z, 'W')
        control_out[name] = Notch(37, y, z, 'E')
    for name in types:
        y, z = next(seam_ports)
        state_out[name] = Notch(right, y, z, 'E')
        worker_in[name] = Notch(2, y, z, 'W')
    for name in types:
        y, z = next(seam_ports)
        state_in[f'next_{name}'] = Notch(right, y, z, 'E')
        worker_out[name] = Notch(2, y, z, 'W')
    for i, name in enumerate(('done', *(f'result_{name}' for name in types))):
        x = left // TILE_SIZE * TILE_SIZE + 10 + 20 * (i // 3)
        state_out[name] = Notch(x, south, i % 3, 'S')
    for i, name in enumerate(name for name in types if name not in initial):
        state_in[f'initial_{name}'] = Notch(left // TILE_SIZE * TILE_SIZE + 10 + 20 * (i // 3), north, i % 3, 'N')
    control_left = min(x for x, _ in platform_interior(control_kind)) - 1
    control_in = {name: Notch(control_left, y, 0, 'W') for name, y in zip(_BITS, _Y, strict=True)}
    control_bp, cr = _build_netlist(control, platform=(control_kind, 0), input_ports=control_in, output_ports=control_out)
    state_bp, sr = _build_netlist(state, platform=(state_kind, 0), input_ports=state_in, output_ports=state_out)
    worker_bp, wr = _build_netlist(worker, platform=(worker_kind, 0), input_ports=worker_in, output_ports=worker_out)
    worker_ports = {side: {name: (0, port) for name, port in wr[side].items()} for side in ('inputs', 'outputs')}
    graph = BatchReplay(worker_bp, worker_ports)
    if graph.feedback_components:
        raise ValueError('单步方法板须为组合逻辑')
    depths = {}
    for node in graph.order:
        depths[node] = 1 + max((depths[p] for p in graph.dependencies[node]), default=0)
    worker_depth = max(depths[node] for node in graph.outputs.values())
    # A 写入到下一轮 B 保持有六相，其中两相留给状态门控、板缝和写回历史。
    if 8 * worker_depth > 4 * _PHASE_TICKS:
        raise ValueError(f'单步最长原生传播链为 {worker_depth} 个节点，超出四相计算窗口')
    control_x = left // TILE_SIZE - 2
    boards = [state_bp['BP']['Entries'][0], dict(worker_bp['BP']['Entries'][0], X=width),
              dict(control_bp['BP']['Entries'][0], X=control_x)]
    report_in = {name: (0, port) for name, port in sr['inputs'].items() if name.startswith('initial_')}
    phases = {}
    if clock_channel is None:
        report_in.update({name: (2, port) for name, port in cr['inputs'].items()})
    else:
        clock, enable, phases = _clock(clock_channel)
        boards.append(dict(clock, X=control_x + control_left // TILE_SIZE - 2))
        report_in['enable'] = (3, enable)
    island = dict(state_bp['BP'], Entries=boards)
    wiring = Wiring(island)
    expected = {_index(wiring, 1, wr['inputs'][name]): _index(wiring, 0, sr['outputs'][name]) for name in types}
    expected.update({_index(wiring, 0, sr['inputs'][f'next_{name}']): _index(wiring, 1, wr['outputs'][name])
                     for name in types})
    expected.update({_index(wiring, 0, sr['inputs'][name]): _index(wiring, 2, cr['outputs'][name]) for name in _GATES})
    if clock_channel is not None:
        expected.update({_index(wiring, 2, cr['inputs'][name]): _index(wiring, 3, port) for name, port in phases.items()})
    cross = {dst: src for dst, src in wiring.short_ports.items() if wiring.sites[dst][0] != wiring.sites[src][0]}
    if cross != expected:
        raise ValueError(f'时序板缝失配：预期 {len(expected)}，实际 {len(cross)}')
    if any(board != 3 and _kind(entry).startswith('ControlledSignal') for board, entry in wiring.entries):
        raise ValueError('状态板或计算板存在全局收发器')
    outputs = {name: (0, sr['outputs'][name]) for name in ('done', *(f'result_{k}' for k in types))}
    observed = {f'state_{name}': (0, sr['outputs'][name]) for name in types}
    report = {'inputs': report_in, 'outputs': outputs, 'observe': observed, 'steps': steps,
              'component': 'wired_state_steps', 'public_access': require_public_access(wiring),
              'island_tiles': sum(len(foundation_tiles(p['T'])) for p in boards),
              'building_entries': len(wiring.entries), 'cross_flywires': len(cross),
              'timing': {'phase_ticks': _PHASE_TICKS, 'cycle_ticks': 8 * _PHASE_TICKS, 'reset_hold_ticks': 96}}
    if clock_channel is not None:
        report['timing'] = _timing(clock_channel)
    report['timing']['worker_dependency_nodes'] = worker_depth
    return {'V': 1137, 'BP': island}, report


def compile_state_steps(programs: Mapping[str, Program], steps: int, *, initial: Mapping[str, int | Shape | None] | None = None,
                        clock_channel: int | None = None):
    """同名更新方法读取同一份旧状态。给出频道基址时内置共享时钟，否则接四路板缝相位。"""
    initial = {} if initial is None else initial
    start = perf_counter()
    bp, report = _build(programs, steps, initial, clock_channel, 'Foundation_2x3', 'Foundation_2x2')
    report['layout_seconds'] = round(perf_counter() - start, 4)
    return bp, report


def main():
    parser = argparse.ArgumentParser(description='将同签名 Python 方法编译成多字段有线定步迭代')
    parser.add_argument('source', type=Path)
    parser.add_argument('--field', required=True, action='append', metavar='字段=方法')
    parser.add_argument('--steps', required=True, type=int)
    parser.add_argument('--clock', nargs='?', type=int, const=CLOCK_CHANNEL)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        fields = dict(item.split('=', 1) for item in args.field)
        if len(fields) != len(args.field):
            raise ValueError('状态字段须唯一')
        programs, _ = compile_field_methods(args.source, fields)
        bp, report = compile_state_steps(programs, args.steps, clock_channel=args.clock)
        _write_blueprint(bp, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
