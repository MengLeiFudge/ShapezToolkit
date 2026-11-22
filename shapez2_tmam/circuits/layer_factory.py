"""按配方地址串接带火车进料的工段、六槽直通带和目标过滤出口。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .freight_stage import add_machine_dyes, freight_stage
from .layer_controller import RUN
from .scaffold_controller import build as layer_control
from .production_line import TARGET, check_jump, product_exit
from .production_stage import build_stage
from .slot_streams import SLOT_ROWS, SlotStreams


def slot_bridge():
    lane = SlotStreams()
    for row in SLOT_ROWS:
        lane.put('BeltPortReceiver',-18,row,config='AA==')
        lane.straight(-17,37,row)
        lane.put('BeltPortSender',37,row,config='KAAAAAA=')
    return lane.finish()


def layer_factory():
    islands = []
    bridge = slot_bridge()
    previous = None
    for index in range(10):
        needs_base = index in (0,1,3,5,7)
        stage_doc = freight_stage(index, machine_dyes=False, stream=True) if needs_base else build_stage(index, stream=True)
        stage = stage_doc['BP']['Entries']
        if index == 9:
            add_machine_dyes(stage)
        for obj in stage:
            obj['X'] = obj.get('X',0) + 18*index
        take, receive = stage[:2]
        if previous is not None:
            for x in range(previous['X']+3,take['X'],3):
                relay = dict(bridge,X=x)
                for row in SLOT_ROWS:
                    check_jump(previous,relay,row,0)
                islands.append(relay)
                previous = relay
            for row in SLOT_ROWS:
                check_jump(previous,take,row,0)
        islands.extend(stage)
        previous = receive
    outlet = product_exit()
    outlet['X'] = previous['X']+3
    for row in SLOT_ROWS:
        check_jump(previous,outlet,row,0)
    islands.append(outlet)
    for obj in layer_control()['BP']['Entries']:
        obj.update(Y=9)
        islands.append(obj)
    occupied = set()
    for obj in islands:
        x,y,z = (obj.get(k,0) for k in ('X','Y','Z'))
        if obj['T']=='Foundation_3x3':
            offsets = [(a,b) for a in (-1,0,1) for b in (-1,0,1)]
        elif obj['T'].startswith('Layout_TrainUnloader_'):
            offsets = [(0,0),(1,0)]
        else:
            offsets = [(0,0)]
        for a,b in offsets:
            tile = x+a,y+b,z
            if tile in occupied:
                raise ValueError(f'串接工段的区块相交 {tile}')
            occupied.add(tile)
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def main():
    parser=argparse.ArgumentParser(description='生成逐层堆叠及可选末次结晶的混合货运生产线')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    doc=layer_factory()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    islands=doc['BP']['Entries']
    report={'target':1_600_000,'run':RUN,'product_filter':TARGET,'coverage':'逐层骨架直接还原目标，或该骨架经一次单色结晶还原目标',
            'stage_count':10,'program_lengths':[9,10],'product_outlet':{'platform':[168,0,0],'east':31,'level':0},
            'shape_train_heads':[[18*i-12,-17] for i in (0,1,3,5,7)],'fluid_train_heads':[[153,3]],
            'islands':len(islands),'foundations':sum(obj['T']=='Foundation_3x3' for obj in islands)}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
