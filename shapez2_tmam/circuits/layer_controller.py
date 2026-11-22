"""按地址读取逐层配方，逐条写入实体工段，最后释放基础料。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .layer_packet import ROW, layer_packet, select_layer
from .layer_recipe import layer_recipe
from .local_module import Module
from .production_line import TARGET
from .stage_memory import WRITE_BUS
from .stage_writer import WRITE_ACK, WRITE_READY, WRITE_REQUEST, WRITE_RESET, writer


RUN = 1_640_030
STATE, NEXT, ROW_ADDRESS, PACKET_ADDRESS = range(1_640_031, 1_640_035)
PRODUCE = 1_640_015


def advance():
    m = Module({'state':STATE, 'tag':PACKET_ADDRESS, 'ready':WRITE_READY, 'ack':WRITE_ACK})
    # n 表示等第 n 条数据就绪。-n-1 表示已经发起写请求。9 是终态。
    m.lookup('state','successor',[(s,t) for n in range(9) for s,t in ((n,-n-1),(-n-1,n+1))])
    m.gate('LogicGateCompare', ('state','tag'), ('same',), 'AQ==')
    m.gate('LogicGateCompare', ('state',0), ('writing',), 'BA==')
    m.gate('LogicGateCompare', ('state',9), ('done',), 'AQ==')
    m.gate('LogicGateNot', ('done',), ('live',))
    m.gate('LogicGateAnd', ('same','ready'), ('prepared',))
    m.gate('LogicGateAnd', ('writing','ack'), ('stored',))
    m.gate('LogicGateOr', ('prepared','stored'), ('event',))
    m.gate('LogicGateAnd', ('live','event'), ('step',))
    m.gate('LogicGateNot', ('step',), ('waiting',))
    m.gate('LogicGateIf', ('successor','step'), ('next',))
    m.gate('LogicGateIf', ('state','waiting'), ('next',))
    m.outputs = {'next':NEXT}
    return m


def controller(recipe):
    m = Module({'run':RUN, 'next':NEXT, 'target':recipe.inputs['target'],
                'clean':recipe.outputs['all8'], 'matches':recipe.outputs['matches']})
    m.gate('LogicGateCompare', ('target',None), ('present',), 'Bg==')
    m.gate('LogicGateAnd', ('clean','matches'), ('valid',))
    m.gate('LogicGateAnd', ('present','valid'), ('accepted',))
    m.gate('LogicGateAnd', ('accepted','run'), ('active',))
    m.gate('LogicGateNot', ('active',), ('reset',))
    m.gate('LogicGateIf', (0,'reset'), ('state',))
    m.gate('LogicGateIf', ('next','active'), ('state',))
    m.gate('LogicGateCompare', ('state',0), ('request',), 'BA==')
    m.gate('LogicGateCompare', ('state',9), ('produce',), 'AQ==')
    m.lookup('state','address',[(s,n) for n in range(9) for s in (n,-n-1)])
    m.outputs={'state':STATE,'reset':WRITE_RESET,'request':WRITE_REQUEST,'produce':PRODUCE,'address':WRITE_BUS['address']}
    return m


def build():
    recipe,rows = layer_recipe()
    selector = select_layer(recipe,rows)
    selector.inputs['address'] = WRITE_BUS['address']
    selector.gate('LogicGateIf', ('address',1), ('row_tag',))
    selector.outputs['row_tag'] = ROW_ADDRESS
    packet = layer_packet()
    packet.inputs['tag'] = ROW_ADDRESS
    packet.outputs = {name:WRITE_BUS[name] for name in packet.outputs}
    packet.gate('LogicGateIf', ('tag',1), ('tag_out',))
    packet.outputs['tag_out'] = PACKET_ADDRESS
    # 逐层法没有结晶指令，色字段全程为空。成品口独占目标频道。
    target = Module({'target':recipe.inputs['target'], 'produce':PRODUCE})
    target.gate('LogicGateIf', ('target','produce'), ('filter',))
    target.gate('LogicGateNot', ('produce',), ('discard',))
    target.gate('LogicGateIf', (0,'discard'), ('filter',))
    target.outputs = {'filter':TARGET}
    islands=[]
    for i,m in enumerate((recipe,selector,packet,advance(),controller(recipe),writer(),target)):
        obj=m.layout()['BP']['Entries'][0]
        obj.update(X=3*(i//2), Z=i%2)
        islands.append(obj)
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def main():
    parser=argparse.ArgumentParser(description='生成九工段无晶体配方的自动写入控制')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    doc=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    report={'target':1_600_000,'run':RUN,'produce':PRODUCE,'stages':list(range(9)),
            'reset':'空工道启动。保持目标且 run=0 至少 256 信号 tick，然后 run=1。保持同一目标直至生产结束。',
            'coverage':'目标须为逐层法判为可解的四象限五层无晶体图形。九台均完成两组回读后释放领料。',
            'platforms':len(doc['BP']['Entries'])}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
