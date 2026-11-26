"""生成完整五层原色读列蓝图。"""

import argparse
import json
from pathlib import Path
from time import perf_counter

from ...mari.shapes import Shape
from ...mari.signals import describe
from ...synthesis import shape_methods
from ...synthesis.physics import Rules
from ..compiler_frontend import compile_field_methods
from . import _write_blueprint
from .ported_assembly import Module, Simulation, assemble
from .prefix_scan_wiring import _native_island

_SOURCE = Path(shape_methods.__file__)
_CORNERS = ('read_labeled_corner', 'read_labeled_corner_q1', 'read_labeled_corner_q2', 'read_labeled_corner_q3')


def five_rows():
    """从目标的原始五层发布 20 个带色单格，保留层位及空信号。"""
    reader, _ = compile_field_methods(_SOURCE, {f'q{q}': name for q, name in enumerate(_CORNERS)})
    modules = {}
    links = []
    for z in reversed(range(1, 5)):
        fields = {'row': 'original_row_4' if z == 4 else f'read_bound_row{z}'}
        fields['remaining' if z > 1 else 'bottom'] = (f'remaining_after_row{z}' if z > 1
                                                       else 'read_bound_row0_after_row1')
        stage, _ = compile_field_methods(_SOURCE, fields)
        modules[f'layer{z}'] = Module(stage, ('Foundation_1x1', 0))
        modules[f'row{z}'] = Module(reader, ('Foundation_1x2', 0))
        links.append(((f'layer{z}', 'row'), (f'row{z}', 'row')))
        if z > 1:
            links.append(((f'layer{z}', 'remaining'), (f'layer{z - 1}', 'target')))
    modules['row0'] = Module(reader, ('Foundation_1x2', 1))
    links.append((('layer1', 'bottom'), ('row0', 'row')))
    return assemble(modules, tuple(links))


def audit(blueprint, report, codes):
    simulation = Simulation.from_assembly(blueprint, report)
    cases = []
    for code in codes:
        target = None if code is None else Rules().parse(code)
        key = None if code is None else Shape.from_key(code)
        result = {name: describe(value) for name, value in simulation.run({'layer4.target': key}).items()}
        expected = {}
        for z in range(5):
            row = getattr(shape_methods, f'original_row_{z}')(target)
            for q, method in enumerate(_CORNERS):
                cell = getattr(shape_methods, method)(row)
                expected[f'row{z}.q{q}'] = None if cell is None else cell.to_key()
        if result != expected:
            raise ValueError(f'五层原色回放失配：{code}，得到 {result}，预期 {expected}')
        cases.append({'input': code, 'outputs': result})
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description='生成五层原色读列的短距飞线总装')
    parser.add_argument('--output', required=True, type=Path, help='原生蓝图输出路径')
    parser.add_argument('--check-targets', type=Path, help='JSON 短代码数组，写盘后回放并输出对照表')
    args = parser.parse_args()
    try:
        start = perf_counter()
        blueprint, report = five_rows()
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
