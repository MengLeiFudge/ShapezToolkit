"""用二维材料表选择角配方，按地址读取各条消费式指令。"""

import argparse
import json
from pathlib import Path

from ..synthesis.physics import Rules
from .angle_binding import COLOR, FIELDS, ORDER, header_reader, lookup_label, material_order
from .angle_rom import LABELS, angle_program
from .circuit import encode_document
from .goal_column import WORD
from .local_module import Module
from .table_island import table_strip


ENTRY, ADDRESS, RECORD, NEXT, HEADER, BASE, DYE = range(1_655_042,1_655_049)
DIGITS = 'urgbcmyw'


def pc_code(index):
    if not 0 <= index < 8**4:
        raise ValueError('角程序地址超出四角八色编码')
    return ''.join('C'+DIGITS[index >> (3*q) & 7] for q in range(4))


def build():
    rules = Rules(4)
    entry, nodes = angle_program(rules)
    heads = [(word,rules.parse(pc_code(pc))) for word,pc in entry.items()]
    records = []
    for pc,(opcode,a,b,dest,base,color,following) in enumerate(nodes,1):
        header = ''.join('CR'[i//8]+DIGITS[i%8] for i in (opcode,a,b,dest))
        dye = (('R'+color[-1]) if color and color[-1]!='r' else 'Cr' if color else 'Cu')+'------'
        data = rules.parse(':'.join((pc_code(following),header,base or 'SuSuSuSu',dye)))
        records.append((rules.parse(pc_code(pc)),data))
    islands = table_strip(heads,WORD,ENTRY)
    banks = table_strip(records,ADDRESS,RECORD)
    for island in banks:
        island.update(Z=1)
    m = Module({'record':RECORD})
    m.gate('VirtualUnstacker', ('record',), ('below_dye','dye'))
    m.gate('VirtualUnstacker', ('below_dye',), ('below_base','base'))
    m.gate('VirtualUnstacker', ('below_base',), ('next','header'))
    m.outputs = {'next':NEXT, 'header':HEADER, 'base':BASE, 'dye':DYE}
    unpack = m.layout()['BP']['Entries'][0]
    unpack['X'] = 3*len(islands)
    controls = [unpack]
    templates = {base for _,_,_,_,base,_,_ in nodes if base is not None}
    methods = (lookup_label(BASE,DYE,LABELS), material_order(BASE,DYE,templates),
               header_reader(HEADER,DIGITS,(0,)),header_reader(HEADER,DIGITS,(1,2,3)))
    for method in methods:
        board = method.layout()['BP']['Entries'][0]
        board['X'] = unpack['X']+3*len(controls)
        controls.append(board)
    doc = {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':[*islands,*banks,*controls]}}
    return doc, len(heads), len(records)


def main():
    parser = argparse.ArgumentParser(description='生成带原层标签的四象限五层单角制造程序')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    doc,columns,states = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    report = {'column_word':WORD,'first_address':ENTRY,'read_address':ADDRESS,'next_address':NEXT,
              'header':HEADER,'base_template':BASE,'dye_template':DYE,'end':pc_code(0),
              'packet':dict(zip(('opcode','a','b','destination','base','color'),(*FIELDS,ORDER,COLOR))),
              'columns':columns,'program_states':states,'platforms':len(doc['BP']['Entries']),
              'orientation':'主角 q0，助手 q3。使用槽 0 至 3。首地址由五层材料字查出。',
              'fields':'header 的四角依次编码操作号、a、b、目标槽。Cu/Cr/Cg/Cb/Cc/Cm/Cy/Cw 编码 0～7，换 R 编码 8～15。',
              'binding':'订单中 Rg/Rb/Rc/Rm/Ry 引用该列底到顶的普通格。染料模板的同种标记引用对应原层晶体色，Cr 指固定红染料。只在指令 14 取基础料，只在指令 10 取染料。'}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
