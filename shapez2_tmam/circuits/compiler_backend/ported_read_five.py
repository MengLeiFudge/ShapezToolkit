"""编译五层原色读取和逐格解码。"""

import argparse
from dataclasses import replace
import json
from pathlib import Path
from time import perf_counter

from ...mari.shapes import Shape
from ...mari.signals import describe
from ...synthesis import shape_methods
from ...synthesis.physics import Rules
from ..circuit import Circuit, constant
from ..compiler_contract import BOOL, COLOR, SHAPE
from ..decoder_circuit import decode_row
from ..compiler_frontend import compile_field_methods
from . import _write_blueprint
from .ported_assembly import Module, Simulation, _PhysicalModule, assemble
from .ported_layout import _Netlist
from .prefix_scan_wiring import _native_island

_SOURCE = Path(shape_methods.__file__)
_CORNERS = ('read_labeled_corner', 'read_labeled_corner_q1', 'read_labeled_corner_q2', 'read_labeled_corner_q3')


def split_rows(*, validity=False):
    modules, links, rows = {}, [], {}
    for z in reversed(range(1, 5)):
        fields = {'row': 'original_row_4' if z == 4 else f'read_bound_row{z}'}
        fields['remaining' if z > 1 else 'bottom'] = (f'remaining_after_row{z}' if z > 1
                                                       else 'read_bound_row0_after_row1')
        if validity and z == 4:
            fields['valid'] = 'target_present'
        stage, _ = compile_field_methods(_SOURCE, fields)
        name = f'layer{z}'
        modules[name] = Module(stage, ('Foundation_1x1', 0))
        rows[z] = (name, 'row')
        if z > 1:
            links.append(((name, 'remaining'), (f'layer{z - 1}', 'target')))
    rows[0] = ('layer1', 'bottom')
    return modules, links, rows


def five_rows():
    """拆出五层各列原色，公开二十个带色单格。"""
    reader, _ = compile_field_methods(_SOURCE, {f'q{q}': name for q, name in enumerate(_CORNERS)})
    read = Module(reader, ('Foundation_1x2', 0), input_side='W', rotate=True)
    modules, links, rows = split_rows()
    for z in reversed(range(5)):
        name = f'row{z}'
        modules[name] = read if z else replace(read, input_side=None)
        links.append((rows[z], (name, 'row')))
    return assemble(modules, tuple(links))


def _decode_fields(*, materials):
    circuit = Circuit()
    row = circuit.add('ConstantSignal', config=constant(0))
    cells = decode_row(circuit, row, Rules(4))
    fields = {'pin': BOOL, 'crystal': BOOL} if materials else {'shape': SHAPE, 'color': COLOR, 'occupied': BOOL}
    outputs = {f'q{q}.{name}': getattr(cell, name) for name in fields for q, cell in enumerate(cells)}
    types = {f'q{q}.{name}': value_type for q in range(4) for name, value_type in fields.items()}
    if not materials:
        outputs['raw'] = row
        types['raw'] = SHAPE
    model = _Netlist.from_circuit(circuit, {'row': row}, outputs)
    foundation = 'Foundation_1x1' if materials else 'Foundation_1x2'
    return _PhysicalModule(model, {'row': SHAPE}, types, (foundation, 0), rotate=True)


def five_row_decoder():
    """用原色与材料判定两条数据通路解码全部二十格。"""
    modules, links, rows = split_rows(validity=True)
    for name, module in (('color', _decode_fields(materials=False)), ('material', _decode_fields(materials=True))):
        for z in range(5):
            key = f'{name}{z}'
            modules[key] = module
            links.append((rows[z], (key, 'row')))
    return assemble(modules, tuple(links), through=(rows[0], rows[1]))

def audit(blueprint, report, codes):
    simulation = Simulation.from_assembly(blueprint, report)
    cases = []
    decoder = 'layer4.valid' in report['outputs']
    for code in codes:
        target = None if code is None else Rules().parse(code)
        inputs = {'layer4.target': None if code is None else Shape.from_key(code)}
        expected: dict[str, int | str | None] = {'layer4.valid': int(target is not None)} if decoder else {}
        for z in range(5):
            if decoder:
                parts = target.layers[z] if target is not None and z < len(target.layers) else ('--',) * 4
                expected[f'color{z}.raw'] = None if all(p == '--' for p in parts) else ''.join(parts)
                for q, part in enumerate(parts):
                    prefix = f'q{q}.'
                    expected[f'color{z}.{prefix}shape'] = (None if part == '--' else
                                                             ('P-' if part == 'P-' else part[0] + 'u') + '------')
                    expected[f'color{z}.{prefix}color'] = None if part in ('--', 'P-') else 'color:' + part[1]
                    expected[f'color{z}.{prefix}occupied'] = int(part != '--')
                    expected[f'material{z}.{prefix}pin'] = int(part == 'P-')
                    expected[f'material{z}.{prefix}crystal'] = int(part.startswith('c'))
            else:
                row = getattr(shape_methods, f'original_row_{z}')(target)
                for q, method in enumerate(_CORNERS):
                    cell = getattr(shape_methods, method)(row)
                    expected[f'row{z}.q{q}'] = None if cell is None else cell.to_key()
        result = {name: describe(value) for name, value in simulation.run(inputs).items()}
        if result != expected:
            raise ValueError(f'五层回放失配：{code}，得到 {result}，预期 {expected}')
        cases.append({'input': code, 'outputs': result})
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description='生成五层原色读列或逐格解码的短距飞线总装')
    parser.add_argument('--output', required=True, type=Path, help='原生蓝图输出路径')
    parser.add_argument('--decoder', action='store_true', help='导出二十格的形状、颜色与材料分类')
    parser.add_argument('--check-targets', type=Path, help='JSON 短代码数组，写盘后回放并输出对照表')
    args = parser.parse_args()
    try:
        start = perf_counter()
        blueprint, report = five_row_decoder() if args.decoder else five_rows()
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
