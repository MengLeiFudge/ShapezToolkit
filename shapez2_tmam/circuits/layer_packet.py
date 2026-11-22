"""把逐层解的五个单层编成制作工段可读取的九个指令字。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .layer_recipe import layer_recipe
from .local_module import Module


ADDRESS = 1_640_020
ROW, LOWER, STACK = range(1_640_021, 1_640_024)
PACKET = {name: 1_640_024 + i for i,name in enumerate(('opcode','a','b','destination','base'))}


def select_layer(recipe, rows):
    m = Module({'address': ADDRESS, **{r:recipe.outputs[r] for r in rows}})
    # 第零台发最底层。后面每对工段分别领一个单层、堆叠到已有产物上。
    for i in range(9):
        m.gate('LogicGateCompare', ('address',i), (f'at{i}',), 'AQ==')
    m.gate('LogicGateIf', (rows[4],'at0'), ('row',))
    for i in range(1,5):
        base, stack = f'at{2*i-1}',f'at{2*i}'
        row = 4-i
        m.gate('LogicGateOr', (base,stack), (f'pair{i}',))
        m.gate('LogicGateIf', (rows[row],f'pair{i}'), ('row',))
        m.gate('LogicGateIf', (rows[row+1],f'pair{i}'), ('lower',))
        m.gate('LogicGateIf', (1,stack), ('stack',))
    m.outputs = {'row':ROW,'lower':LOWER,'stack':STACK}
    return m


def layer_packet():
    m = Module({'row':ROW,'lower':LOWER,'stack':STACK})
    m.gate('LogicGateCompare', ('row',None), ('occupied',), 'Bg==')
    m.gate('LogicGateCompare', ('lower',None), ('have_lower',), 'Bg==')
    m.gate('LogicGateNot', ('stack',), ('base_stage',))
    m.gate('LogicGateAnd', ('base_stage','occupied'), ('order',))
    m.gate('LogicGateAnd', ('occupied','have_lower'), ('pair',))
    m.gate('LogicGateAnd', ('stack','pair'), ('join',))
    m.gate('LogicGateIf', (14,'order'), ('opcode',))
    m.gate('LogicGateIf', (7,'join'), ('opcode',))
    m.gate('LogicGateIf', ('row','order'), ('base',))
    m.gate('LogicGateIf', ('have_lower','order'), ('destination',))
    m.gate('LogicGateIf', (0,'join'), ('destination',))
    m.gate('LogicGateIf', (0,'join'), ('a',))
    m.gate('LogicGateIf', (1,'join'), ('b',))
    m.outputs = PACKET.copy()
    return m


def main():
    parser = argparse.ArgumentParser(description='生成无晶体逐层配方的工段指令读取口')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    recipe,rows = layer_recipe()
    doc=recipe.layout()
    select=select_layer(recipe,rows).layout()['BP']['Entries'][0]
    select['Z']=1
    packet=layer_packet().layout()['BP']['Entries'][0]
    packet['X']=3
    doc['BP']['Entries'].extend((select,packet))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    report={'target':recipe.inputs['target'],'address':ADDRESS,'packet':PACKET,
            'crystal_free':recipe.outputs['all8'],'matches':recipe.outputs['matches'],
            'use':'仅在目标非空且 crystal_free 和 matches 均为 1 时，依次读取地址 0 至 8。空操作保持旁路。最后的活物在槽 0。'}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
