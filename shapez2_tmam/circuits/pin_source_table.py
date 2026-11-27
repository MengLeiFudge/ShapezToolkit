"""用五层图形常量存储顶针逆推的一列来源槽，按原层位返回四格材料控制字。"""

import argparse
import json
from pathlib import Path

from ..synthesis.physics import Rules
from ..synthesis.pin_patterns import SOURCE_PATTERNS
from .circuit import encode_document
from .local_module import Module


GROUND, COUNT, SLOT, PATTERN = range(1_655_000, 1_655_004)
KEY, OFFSET = 1_655_004, 1_655_005
BUCKET_TAGS = ('Cu','Cr','Cg','Cb','Cy','Cm','Cc','Cw','Ru','Rr')
PAGE_TAGS = ('Su','Sr','Sg','Sb')


def pages(rules, *, ranked=False):
    pairs = []
    for occupied, buckets in enumerate(SOURCE_PATTERNS):
        for count, patterns in enumerate(buckets):
            bucket = BUCKET_TAGS[5*occupied+count]*4
            for start in range(0,len(patterns),5):
                key = rules.parse(bucket+':'+PAGE_TAGS[start//5]*4)
                rows = []
                for keep, crystals in patterns[start:start+5]:
                    ranks = iter(('Rr','Rg','Rb','Ry') if ranked else ('Ru',)*4)
                    rows.append(''.join(next(ranks) if keep & 1<<r else 'Su' if crystals & 1<<r else 'Cu' for r in range(4)))
                value = rules.parse(':'.join(reversed(rows)))
                for offset,(keep,crystals) in enumerate(patterns[start:start+5]):
                    row = value.layers[-1-offset]
                    if (sum(1<<r for r,c in enumerate(row) if c[0]=='R'),sum(1<<r for r,c in enumerate(row) if c=='Su')) != (keep,crystals):
                        raise ValueError('来源槽的倒序层位与 Python 控制字不符')
                pairs.append((key,value))
    return pairs


def address(rules):
    m = Module({'ground':GROUND,'count':COUNT,'slot':SLOT})
    # 先将层内地址和页号打包在同一行。分析器读取 q0 的部件和颜色。
    # 四种部件编码页号，五种颜色编码页内位置。
    m.lookup('slot','packed',[(s,rules.parse('CRSW'[s//5]+'urgby'[s%5]+'------')) for s in range(20)])
    m.gate('VirtualAnalyzer',('packed',),('shape','offset'))
    for i,k in enumerate('CRSW'):
        m.gate('LogicGateCompare',('shape',rules.parse(k+'u------')),(f'page{i}',),'AQ==')
        m.gate('LogicGateIf',(rules.parse(PAGE_TAGS[i]*4),f'page{i}'),('top',))
    for n in range(5):
        m.gate('LogicGateCompare',('count',n),(f'n{n}',),'AQ==')
        for g in range(2):
            m.gate('LogicGateIf',(rules.parse(BUCKET_TAGS[g*5+n]*4),f'n{n}'),(f'ground{g}',))
    for g in range(2):
        m.gate('LogicGateCompare',('ground',g),(f'g{g}',),'AQ==')
        m.gate('LogicGateIf',(f'ground{g}',f'g{g}'),('bottom',))
    m.gate('VirtualStacker',('bottom','top'),('key',))
    m.outputs={'key':KEY,'offset':OFFSET}
    return m


def read_page(rules, *, ranked=False):
    from .circuit import Literal
    m=Module({'key':KEY,'offset':OFFSET})
    m.lookup('key','page',pages(rules, ranked=ranked))
    current='page'
    for i,c in enumerate('urgby'):
        lower=f'lower{i}'
        m.gate('VirtualUnstacker',(current,),(lower,f'row{i}'))
        m.gate('LogicGateCompare',('offset',Literal('color:'+c)),(f'at{i}',),'AQ==')
        m.gate('LogicGateIf',(f'row{i}',f'at{i}'),('pattern',))
        current=lower
    m.outputs={'pattern':PATTERN}
    return m


def main():
    parser=argparse.ArgumentParser(description='生成四列时序共用的五层顶针来源表')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    rules=Rules(4)
    decoder=address(rules)
    doc=decoder.layout()
    upper=read_page(rules).layout()['BP']['Entries'][0]
    upper['Z']=1
    doc['BP']['Entries'].append(upper)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    report={'inputs':decoder.inputs,'output':PATTERN,'ground':'目标底格为针取整数 1，否则取 0',
            'count':'去掉底部新增针后保留的普通格和针的总数','slot':'0 至 19',
            'pattern':'q0 至 q3 依次表示前态从地面至第四层。Cu 为空，Ru 为保留的普通格或针，Su 为晶体。桶外槽返回空信号。',
            'bucket_lengths':[[len(b) for b in group] for group in SOURCE_PATTERNS],
            'pages':len(pages(rules)),'platforms':2}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
