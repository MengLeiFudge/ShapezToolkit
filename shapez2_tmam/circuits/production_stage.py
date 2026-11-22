"""将三块实体平台装成一条可串接的六槽配方工段。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .slot_stream_ports import check_slots
from .slot_streams import DEST, FIRST, SECOND, SLOT_ROWS, SlotStreams
from .local_module import Module
from .stage_memory import READBACK, WRITE_BUS, packet_memory
from .work_lane import A_X, COLORS, COMMAND, WorkLane


def instruction_decoder(offset=0):
    module = Module({'opcode':1_600_070, 'a':1_600_071, 'b':1_600_072,
                     'color':1_600_074, 'base':1_600_075})
    module.inputs = {name: channel + offset for name, channel in module.inputs.items()}
    module.inputs['produce'] = 1_640_015
    for name, value in (('base_mode',14),('crystal',10),('stack',7),('swap0',8),('swap1',9)):
        module.gate('LogicGateCompare',('opcode',value),(name,),'AQ==')
    module.gate('LogicGateCompare',('opcode',1),('positive',),'Ag==')
    module.gate('LogicGateCompare',('opcode',10),('in_range',),'BQ==')
    module.gate('LogicGateAnd',('positive','in_range'),('machine',))
    module.gate('LogicGateNot',('crystal',),('dry',))
    module.gate('LogicGateIf',('color','crystal'),('command',))
    module.gate('LogicGateIf',('opcode','dry'),('command',))
    module.gate('LogicGateIf',('a','machine'),('first',))
    module.gate('LogicGateNot',('machine',),('no_first',))
    module.gate('LogicGateIf',(-1,'no_first'),('first',))
    module.gate('LogicGateOr',('swap0','swap1'),('swap',))
    module.gate('LogicGateOr',('swap','stack'),('binary',))
    module.gate('LogicGateIf',('b','binary'),('second',))
    module.gate('LogicGateNot',('binary',),('no_second',))
    module.gate('LogicGateIf',(-1,'no_second'),('second',))
    module.outputs = {'first':FIRST,'second':SECOND,'command':COMMAND,'ordered_base':1_600_076}
    module.gate('LogicGateCompare',('produce',1),('released',),'AQ==')
    module.gate('LogicGateAnd',('released','base_mode'),('feed',))
    module.gate('LogicGateIf',('base','feed'),('ordered_base',))
    module.outputs = {name: channel + offset for name, channel in module.outputs.items()}
    return module


def build_stage(index=0, *, north_base=False, stream=False):
    if not 0 <= index < 971:
        raise ValueError('工段编号需要在 0 至 970 之间')
    offset = 32 * index
    take = SlotStreams().select(offset)
    receive = SlotStreams().receive(offset, north_base=north_base)
    check_slots(take, receive, SLOT_ROWS, A_X, north_base=north_base)
    receive['X'] = 3
    work = WorkLane(COMMAND + offset).build()['BP']['Entries'][0]
    work['Y'] = 3
    path = [{'T':'SpaceBelt_LeftTurn','X':2,'Y':4},
            *({'T':'SpaceBelt_Forward','X':2,'Y':y,'R':3} for y in (3,2))]
    decoder = instruction_decoder(offset)
    control = decoder.layout()['BP']['Entries'][0]
    control['Z'] = 1
    operands = packet_memory(index, {name: decoder.inputs[name] for name in ('opcode', 'a', 'b')}, READBACK[0], stream=stream)
    operands.update(X=3, Z=1)
    material = packet_memory(index, {'destination':DEST+offset, 'base':decoder.inputs['base'], 'color':decoder.inputs['color']}, READBACK[1], stream=stream)
    material.update(Y=3, Z=1)
    islands = [take, receive, work, control, operands, material, *path]
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def main():
    parser = argparse.ArgumentParser(description='装配可串接的六槽配方工段')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--index', type=int, default=0, help='流水线工段编号，从零开始')
    args = parser.parse_args()
    doc = build_stage(args.index)
    offset = 32 * args.index
    decoder = instruction_decoder(offset)
    report = {'component':'production_stage','index':args.index,'inputs':WRITE_BUS,
              'outputs':{'ordered_base':decoder.outputs['ordered_base'], 'operands_match':READBACK[0],
                         'materials_match':READBACK[1]},
              'call_channels':{'command':COMMAND + offset,'a':FIRST + offset,'b':SECOND + offset},
              'slots':SLOT_ROWS,'operand_order':'a 为下料或第一操作数，b 为上料或第二操作数。',
              'base_input':'领取基础层时，译码器关闭 A、B 取料并发布 ordered_base；实物经收料台南侧中口建筑层1送入。',
              'crystal_commands':['color:'+c for c in COLORS],
              'islands':len(doc['BP']['Entries']),'foundation_3x3':6,'space_belts':3}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0
