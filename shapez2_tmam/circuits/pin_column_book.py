"""按一列目标的五种层位输入，紧凑读取逐列筛选后的顶针来源。"""

import argparse
import json
from itertools import product
from pathlib import Path

from ..synthesis.inverse import pin_column_at
from ..synthesis.physics import EMPTY, PIN, Rules
from .circuit import Literal, encode_document
from .goal_column import QUADRANT, RUN, WORD, advance_column, orient, read_height, result
from .local_module import Module
from .table_island import table_island


MATERIALS = (EMPTY, 'Cu', PIN, 'cr')
TOKENS = dict(zip(MATERIALS, 'CRSW'))
PIGMENTS = 'rgbyw'
KEY, PAGE, OFFSET, PATTERN, ORDINAL = range(1_655_020, 1_655_025)
TARGET = 1_600_000


def source_pages(rules):
    pages = []
    for target in product(MATERIALS, repeat=5):
        rows = []
        for slot in range(20):
            column = pin_column_at(target, slot)
            if column is None:
                continue
            kept = iter(z for z,c in enumerate(target) if c not in (EMPTY,'cr') and (z or c!=PIN))
            row = []
            for r,cell in enumerate(column):
                if cell == EMPTY:
                    row.append('Cu')
                elif cell != 'cr':
                    row.append('R'+PIGMENTS[next(kept)])
                elif target[r+1] == 'cr':
                    row.append('R'+PIGMENTS[r+1])
                else:
                    row.append('Su')
            rows.append(''.join(row))
        for start in range(0,len(rows),5):
            key = ':'.join(TOKENS[c]+(PIGMENTS[start//5] if z==4 else 'u')+'------' for z,c in enumerate(target))
            pages.append((rules.parse(key),rules.parse(':'.join(reversed(rows[start:start+5])))))
    return pages


def page_address(rules):
    m = Module({'ordinal': ORDINAL, 'column': WORD})
    m.lookup('ordinal','entry',[(i,rules.parse('CRSW'[i//5]+'urgby'[i%5]+'------')) for i in range(20)])
    m.gate('VirtualAnalyzer', ('entry',), ('group','offset'))
    for n,k in enumerate('CRSW'):
        m.gate('LogicGateCompare', ('group',rules.parse(k+'u------')), (f'group{n}',), 'AQ==')
        m.gate('LogicGateIf', (Literal('color:'+PIGMENTS[n]),f'group{n}'), ('page_color',))
    m.gate('VirtualPainter', ('column','page_color'), ('key',))
    m.outputs = {'key':KEY,'offset':OFFSET}
    return m


def page_row():
    m = Module({'page':PAGE, 'offset':OFFSET})
    current = 'page'
    for n,c in enumerate('urgby'):
        lower, top = f'lower{n}', f'top{n}'
        m.gate('VirtualUnstacker', (current,), (lower,top))
        m.gate('LogicGateCompare', ('offset',Literal('color:'+c)), (f'at{n}',), 'AQ==')
        m.gate('LogicGateIf', (top,f'at{n}'), ('pattern',))
        current = lower
    m.outputs = {'pattern':PATTERN}
    return m


def build():
    rules = Rules(4)
    pages = source_pages(rules)
    doc = orient(TARGET).layout()
    islands = doc['BP']['Entries']
    for m in (read_height(), advance_column(rules), result(), page_address(rules)):
        islands.append(m.layout()['BP']['Entries'][0])
    islands.extend((table_island(pages,KEY,PAGE),page_row().layout()['BP']['Entries'][0]))
    for i,island in enumerate(islands):
        island.update(X=3*(i//2),Z=i%2)
    return doc,len(pages)


def main():
    parser = argparse.ArgumentParser(description='生成五层顶针逆推的单列紧凑候选表')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    doc, count = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n', encoding='utf-8')
    report = {'target':TARGET, 'quadrant':QUADRANT, 'run':RUN, 'ordinal': ORDINAL, 'pattern': PATTERN, 'column_word':WORD,
              'material_tokens': {k:v+'u------' for k,v in TOKENS.items()}, 'pages':count,
              'platforms':len(doc['BP']['Entries']), 'table_global_receivers':1,'table_global_transmitters':1,
              'input':'保持非空四象限目标和象限 0～3。run=0 复位至少 128 信号 tick，再置 1。固定接线常速下等 256 信号 tick 后从序号 0 开始读取。每次改变序号等待 64 tick，首次返回空信号时本列枚举结束。',
              'output':'四象限依次编码前态的底层至第四层。Cu 为空，Su 为辅助红晶体，R 的颜色 r/g/b/y/w 指向目标的第 1/2/3/4/5 层，复制该格的原始标签。',
              'scope':'按 pin_column_at 筛过的本列前四层。后续还需跨列约束、第五层、顶破及制造证明。'}
    args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
