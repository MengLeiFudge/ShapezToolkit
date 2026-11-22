"""用两个存储板的实际回读推进一笔写入。调用者保持地址和六字段直到应答。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .local_module import Module
from .stage_memory import READBACK, WRITE_BUS


WRITE_REQUEST = 1_640_011
WRITE_RESET = 1_640_012
WRITE_ACK = 1_640_013
WRITE_READY = 1_640_014


def writer():
    m = Module({'request': WRITE_REQUEST, 'reset': WRITE_RESET,
                'operands': READBACK[0], 'materials': READBACK[1]})
    m.gate('LogicGateNot', ('reset',), ('enabled',))
    m.gate('LogicGateAnd', ('request','enabled'), ('active',))
    m.gate('LogicGateNot', ('active',), ('idle',))
    for i, code in enumerate((2,3,1)):
        for bank in ('operands','materials'):
            m.gate('LogicGateCompare', (bank,code), (f'{bank}{i}',), 'AQ==')
        m.gate('LogicGateAnd', (f'operands{i}',f'materials{i}'), (f'both{i}',))
        previous = 'active' if i==0 else f'seen{i-1}'
        m.gate('LogicGateAnd', (previous,f'both{i}'), (f'hit{i}',))
        m.gate('LogicGateOr', (f'hit{i}',f'seen{i}'), (f'keep{i}',))
        m.gate('LogicGateAnd', (f'keep{i}','active'), (f'seen{i}',))
    m.gate('LogicGateNot', ('seen0',), ('first',))
    m.gate('LogicGateNot', ('seen1',), ('before_hold',))
    m.gate('LogicGateAnd', ('active','first'), ('write',))
    m.gate('LogicGateAnd', ('seen0','before_hold'), ('overlap',))
    for value, select in ((1,'write'),(2,'overlap'),(0,'seen1'),(3,'reset')):
        m.gate('LogicGateIf', (value,select), ('phase',))
    m.gate('LogicGateAnd', ('idle','enabled'), ('standby',))
    m.gate('LogicGateIf', (4,'standby'), ('phase',))
    for bank in ('operands','materials'):
        m.gate('LogicGateCompare',(bank,None),(bank+'_idle',),'AQ==')
    m.gate('LogicGateAnd', ('operands_idle','materials_idle'), ('quiet',))
    m.gate('LogicGateOr', ('seen0','seen1'), ('early',))
    m.gate('LogicGateOr', ('early','seen2'), ('busy',))
    m.gate('LogicGateNot', ('busy',), ('released',))
    m.gate('LogicGateAnd', ('standby','released'), ('armed',))
    m.gate('LogicGateAnd', ('armed','quiet'), ('ready',))
    m.outputs = {'phase': WRITE_BUS['phase'], 'seen2': WRITE_ACK, 'ready': WRITE_READY}
    return m


def main():
    parser = argparse.ArgumentParser(description='生成以两组回读确认的工段配方写入器')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    m=writer()
    doc=m.layout()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    report={'inputs':m.inputs,'outputs':m.outputs,'payload':{k:v for k,v in WRITE_BUS.items() if k!='phase'},
            'phases':{'3':'全线清空','4':'空闲，保持数据','1':'替换旧值','2':'写入并保持','0':'撤去写入，核对保持值'},
            'protocol':'初始化时 request=0 并复位。解除复位后等待 ready=1。稳定提供地址和六字段，再置 request=1。ack=1 后撤去 request。下一笔须等 ready=1。'}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
