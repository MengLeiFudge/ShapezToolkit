"""工段基础层订单到四角备料与交换拼装，原料从混合车的固定层位领用。"""

import argparse
import json
from pathlib import Path

from ..synthesis.physics import Rules
from .angle_prep import prepare_quarter
from .quarter_join import quarter_join
from .circuit import encode_document
from .local_module import Module
from .production_line import check_jump
from .quarter_gather import QUADRANTS, gather, turn_to_assembly
from .stock_selector import STOCK_CHANNEL, stock_selector


def ordering(row_channel, quadrant, stock, route):
    module = Module({'row': row_channel})
    aligned = 'row'
    for i in range(quadrant if quadrant < 3 else 1):
        turned = f'turn{i}'
        module.gate('VirtualRotatorCCW' if quadrant < 3 else 'VirtualRotator', (aligned,), (turned,))
        aligned = turned
    module.gate('VirtualAnalyzer', (aligned,), ('part', 'pigment'))
    module.gate('LogicGateCompare', ('row', None), ('active',), 'Bg==')
    module.gate('LogicGateCompare', ('part', None), ('vacant',), 'AQ==')
    module.gate('LogicGateAnd', ('active', 'vacant'), ('placeholder',))
    rules = Rules(4)
    module.gate('LogicGateCompare', ('part', rules.parse('P-------')), ('pin',), 'AQ==')
    module.gate('LogicGateOr', ('placeholder', 'pin'), ('sacrifice',))
    module.gate('LogicGateIf', (rules.parse('CuCuCuCu'), 'sacrifice'), ('stock',))
    module.gate('LogicGateIf', (1, 'placeholder'), ('route',))
    module.gate('LogicGateIf', (2, 'pin'), ('route',))
    for k in 'CRSW':
        module.gate('LogicGateCompare', ('part', rules.parse(k+'u------')), (k,), 'AQ==')
        module.gate('LogicGateIf', (rules.parse((k+'u')*4), k), ('stock',))
        module.gate('LogicGateIf', ('pigment', k), ('route',))
    module.outputs = {'stock': stock, 'route': route}
    if quadrant:
        module.gate('LogicGateCompare', ('turn0', 'row'), ('mixed',), 'Bg==')
        module.gate('LogicGateIf', ('stock', 'mixed'), ('requested',))
        module.outputs = {'requested': stock, 'route': route}
    else:
        module.gate('VirtualRotator', ('row',), ('turned',))
        module.gate('LogicGateCompare', ('row', 'turned'), ('direct',), 'AQ==')
        module.outputs['direct'] = row_channel+1
    return module.layout()['BP']['Entries'][0]


def build_layer_supply(index, *, south_output=False):
    if not 0 <= index < 971:
        raise ValueError('工段编号需要在 0 至 970 之间')
    islands = []
    order = 1_600_076 + 32*index
    last = None
    for i, q in enumerate(QUADRANTS):
        channel = STOCK_CHANNEL + 8*index + 2*q
        select = stock_selector(channel)
        process = prepare_quarter(channel+1, q)
        collect = gather(i)
        control = ordering(order, q, channel, channel+1)
        for obj,x,z in ((select,0,0),(process,3,0),(collect,6,0),(control,0,1)):
            obj.update(X=x,Y=3*i,Z=z)
            islands.append(obj)
        check_jump(select,process,9,0)
        for y in (-12,-11,-10,-9,8,9,10,11):
            check_jump(select,process,y,0,1 if y==11 else 2,fluid=True)
        check_jump(process,collect,30,0)
        if last is not None:
            for x in range(12-i,12):
                check_jump(last,collect,x,1)
        last = collect
    turn = turn_to_assembly()
    turn.update(X=6,Y=12)
    join = quarter_join(order+1, south_output=south_output)
    join.update(X=9,Y=12)
    for i in range(4):
        check_jump(last,turn,8+i,1)
        check_jump(turn,join,8+i,0)
    islands.extend((turn,join))
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def main():
    parser = argparse.ArgumentParser(description='生成指定工段的四角基础层供料线')
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    doc = build_layer_supply(args.index)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    report = {'stage':args.index,'row_channel':1_600_076+32*args.index,'quadrants_north_to_south':QUADRANTS,
              'raw_west':{'C':[-12,0],'R':[-12,1],'S':[-12,2],'W':[8,0]},
              'fluid_west':{'r':[28,2],'g':[29,2],'b':[30,2],'c':[31,2],'m':[28,1],'y':[29,1],'w':[30,1],'pin':[31,1]},
              'output':{'platform':[9,12,0],'east_y':11,'level':0},'platforms':len(doc['BP']['Entries'])}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
