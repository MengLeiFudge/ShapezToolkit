"""生成完整五层原色读列蓝图。"""

import argparse
from dataclasses import replace
import json
from pathlib import Path
from time import perf_counter

from ...mari.shapes import Shape
from ...mari.signals import Signal, describe
from ...synthesis import shape_methods
from ...synthesis.physics import Rules
from ..compiler_contract import Block, Reference, Return
from ..compiler_frontend import compile_field_methods
from . import _write_blueprint
from .ported_assembly import Module, Simulation, assemble
from .ported_layout import Notch
from .prefix_scan_wiring import _native_island

_SOURCE = Path(shape_methods.__file__)
_CORNERS = ('read_labeled_corner', 'read_labeled_corner_q1', 'read_labeled_corner_q2', 'read_labeled_corner_q3')


def five_rows(*, with_prefix=False):
    """拆出五行，读原色并可同时选择前缀中的 q0 原料。"""
    reader, _ = compile_field_methods(_SOURCE, {f'q{q}': name for q, name in enumerate(_CORNERS)})
    read = Module(reader, ('Foundation_1x2', 0), input_side='W', rotate=True,
                  outputs={'q0': Notch(37, 8, 0, 'E')} if with_prefix else {})
    modules = {}
    links = []
    for z in reversed(range(1, 5)):
        fields = {'row': 'original_row_4' if z == 4 else f'read_bound_row{z}'}
        fields['remaining' if z > 1 else 'bottom'] = (f'remaining_after_row{z}' if z > 1
                                                       else 'read_bound_row0_after_row1')
        stage, _ = compile_field_methods(_SOURCE, fields)
        modules[f'layer{z}'] = Module(stage, ('Foundation_1x1', 0))
        modules[f'row{z}'] = read
        links.append(((f'layer{z}', 'row'), (f'row{z}', 'row')))
        if z > 1:
            links.append(((f'layer{z}', 'remaining'), (f'layer{z - 1}', 'target')))
    # 最底读板可从长边进线，收起拆层链末端突出的一岛格。
    modules['row0'] = read if with_prefix else replace(read, input_side=None)
    links.append((('layer1', 'bottom'), ('row0', 'row')))
    if with_prefix:
        choose, _ = compile_field_methods(_SOURCE, {'prefix': 'select_prefix_cell'})
        selected = choose['prefix']
        fn = next(fn for fn in selected.functions if fn.name == selected.entry)
        origin = replace(fn, name='cell_signal', locals=(), max_block_visits=1,
                         blocks=(Block('entry', (), Return(Reference('cell'))),))
        module = Module({'prefix': selected, 'q0': replace(selected, functions=(origin,), entry=origin.name)},
                        ('Foundation_1x1', 0), input_side='W', rotate=True,
                        inputs={'row_height': Notch(10, 2, 0, 'N'), 'prefix_height': Notch(10, 17, 0, 'S')})
        for z in range(5):
            modules[f'prefix{z}'] = module
            links.append(((f'row{z}', 'q0'), (f'prefix{z}', 'cell')))
    through = tuple(source for source, (_, arg) in links if with_prefix and arg == 'row')
    return assemble(modules, tuple(links), through=through)


def audit(blueprint, report, codes):
    simulation = Simulation.from_assembly(blueprint, report)
    cases = []
    with_prefix = 'prefix0.prefix' in report['outputs']
    for case, code in enumerate(codes):
        target = None if code is None else Rules().parse(code)
        inputs: dict[str, Signal] = {'layer4.target': None if code is None else Shape.from_key(code)}
        expected = {}
        for z in range(5):
            row = getattr(shape_methods, f'original_row_{z}')(target)
            for q, method in enumerate(_CORNERS):
                cell = getattr(shape_methods, method)(row)
                name = f'prefix{z}.q0' if with_prefix and q == 0 else f'row{z}.q{q}'
                expected[name] = None if cell is None else cell.to_key()
            if with_prefix:
                bound = (case + 2 * z) % 6
                inputs[f'prefix{z}.row_height'] = z + 1
                inputs[f'prefix{z}.prefix_height'] = bound
                expected[f'prefix{z}.prefix'] = expected[f'prefix{z}.q0'] if z + 1 <= bound else None
        result = {name: describe(value) for name, value in simulation.run(inputs).items()}
        if result != expected:
            raise ValueError(f'五层原色回放失配：{code}，得到 {result}，预期 {expected}')
        observed_inputs = {name: describe(value) for name, value in inputs.items()}
        cases.append({'input': code, 'inputs': observed_inputs, 'outputs': result})
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description='生成五层原色读列的短距飞线总装')
    parser.add_argument('--output', required=True, type=Path, help='原生蓝图输出路径')
    parser.add_argument('--with-prefix', action='store_true', help='共用多路走廊并为每行输出 q0 前缀原料')
    parser.add_argument('--check-targets', type=Path, help='JSON 短代码数组，写盘后回放并输出对照表')
    args = parser.parse_args()
    try:
        start = perf_counter()
        blueprint, report = five_rows(with_prefix=args.with_prefix)
        report['layout_seconds'] = round(perf_counter() - start, 4)
        _write_blueprint(blueprint, report, args.output)
        if args.check_targets is not None:
            codes = json.loads(args.check_targets.read_text(encoding='utf-8-sig'))
            if not isinstance(codes, list) or not codes or any(c is not None and not isinstance(c, str) for c in codes):
                raise ValueError('对照输入应为非空 JSON 数组，元素为图形短代码或 null')
            cases = audit({'BP': _native_island(args.output)}, report, codes)
            args.output.with_suffix('.audit.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n',
                                                             encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
