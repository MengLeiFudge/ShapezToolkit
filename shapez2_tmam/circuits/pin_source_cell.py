"""按来源层读取带序号的候选槽，把保留格映射到原目标标签。"""

import argparse
import json
from pathlib import Path

from ..synthesis.physics import Rules
from .circuit import Literal, encode_document
from .local_module import Module
from .pin_source_table import PATTERN, address, read_page


LEVEL = 1_655_010
ORDERED = tuple(range(1_655_011, 1_655_015))
FORCED, TAG, VALID = range(1_655_015, 1_655_018)


def source_cell(rules):
    inputs = {'pattern': PATTERN, 'level': LEVEL, 'forced': FORCED}
    inputs.update({f'kept{i}': channel for i, channel in enumerate(ORDERED)})
    m = Module(inputs)
    rotated = 'pattern'
    for r in range(4):
        if r:
            following = f'turn{r}'
            m.gate('VirtualRotatorCCW', (rotated,), (following,))
            rotated = following
        m.gate('LogicGateCompare', ('level', r), (f'at{r}',), 'AQ==')
        m.gate('LogicGateIf', (rotated, f'at{r}'), ('aligned',))
    m.gate('VirtualAnalyzer', ('aligned',), ('kind', 'rank'))
    for kind, code in (('empty', 'Cu'), ('retained', 'Ru'), ('crystal', 'Su')):
        m.gate('LogicGateCompare', ('kind', rules.parse(code+'------')), (kind,), 'AQ==')
    for rank, pigment in enumerate('rgby'):
        m.gate('LogicGateCompare', ('rank', Literal('color:'+pigment)), (f'rank{rank}',), 'AQ==')
        m.gate('LogicGateIf', (f'kept{rank}', f'rank{rank}'), ('original',))
    m.gate('LogicGateCompare', ('forced', None), ('free',), 'AQ==')
    m.gate('LogicGateIf', ('original', 'retained'), ('npc',))
    m.gate('LogicGateIf', ('npc', 'free'), ('tag',))
    m.gate('LogicGateAnd', ('empty', 'free'), ('vacant',))
    m.gate('LogicGateIf', (0, 'vacant'), ('tag',))
    m.gate('LogicGateAnd', ('crystal', 'free'), ('helper',))
    m.gate('LogicGateIf', (3, 'helper'), ('tag',))
    m.gate('LogicGateIf', ('forced', 'crystal'), ('tag',))
    m.gate('LogicGateCompare', ('tag', None), ('valid',), 'Bg==')
    m.outputs = {'tag': TAG, 'valid': VALID}
    return m


def main():
    parser = argparse.ArgumentParser(description='读取顶针候选的一格来源标签')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rules = Rules(4)
    decoder = address(rules)
    cell = source_cell(rules)
    doc = decoder.layout()
    table = read_page(rules, ranked=True).layout()['BP']['Entries'][0]
    table['Z'] = 1
    reader = cell.layout()['BP']['Entries'][0]
    reader['X'] = 3
    doc['BP']['Entries'].extend((table, reader))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n', encoding='utf-8')
    report = {'inputs':{**decoder.inputs, **{n:v for n,v in cell.inputs.items() if n!='pattern'}},
              'outputs':cell.outputs, 'platforms':3,
              'kept':'同一目标列去掉晶体及地面新增针后，按原层号递增提供最多四个非零格标签。空余位置送空信号。',
              'forced':'若目标 r+1 层为晶体，提供其原非零标签，否则送空信号。level 为来源层 r，0 至 3。',
              'result':'合法空格返回整数 0，辅助晶体返回 3，保留块返回原标签。无候选或与强制晶体冲突时返回空信号。valid 表示本格标签就绪。'}
    args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
