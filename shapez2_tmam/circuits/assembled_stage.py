"""把基础层的拼装出口直接接入同地址工段，并保留六个流水槽的顺序。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .layer_supply import build_layer_supply
from .production_line import TARGET, check_jump, product_exit
from .production_stage import build_stage
from .slot_stream_ports import trace, transport_paths
from .slot_streams import SLOT_ROWS
from .stage_memory import READBACK, WRITE_BUS


def assembled_stage(index, *, terminal=False, stream=False):
    stage = build_stage(index, north_base=True, stream=stream)['BP']['Entries']
    take, receive, work = stage[:3]
    supply = build_layer_supply(index, south_output=True)['BP']['Entries']
    for island in supply:
        island['X'] -= 6
        island['Y'] -= 15
    join = supply[-1]
    check_jump(join, receive, 30, 1)
    end = (30,37,0,3)
    trace(transport_paths(join), (11,11,0,2), {end}, set())
    for row in SLOT_ROWS:
        check_jump(take,receive,row,0)
    for level in (0,1):
        check_jump(take,work,-12,1,level)
    islands = [*stage,*supply]
    if terminal:
        outlet = product_exit()
        outlet['X'] = 6
        for row in SLOT_ROWS:
            check_jump(receive,outlet,row,0)
        islands.append(outlet)
    occupied = set()
    for obj in islands:
        size = 1 if obj['T'] == 'Foundation_3x3' else 0
        for dx in range(-size,size+1):
            for dy in range(-size,size+1):
                chunk = obj.get('X',0)+dx,obj.get('Y',0)+dy,obj.get('Z',0)
                if chunk in occupied:
                    raise ValueError(f'装配后区块重叠 {chunk}')
                occupied.add(chunk)
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def main():
    parser = argparse.ArgumentParser(description='生成带四角基础料供给的指令工段')
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--terminal', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    doc = assembled_stage(args.index, terminal=args.terminal)
    islands = doc['BP']['Entries']
    foundations = [obj for obj in islands if obj['T']=='Foundation_3x3']
    report = {'stage':args.index, 'terminal':args.terminal, 'write_bus':WRITE_BUS, 'readback':READBACK,
              'base_transfer':{'from':[3,-3],'to':[3,0],'x':30,'level':0,'direction':'south'},
              'stock_inputs':[[-6,-15+3*i] for i in range(4)],'machine_fluids':[0,3],
              'target_filter':TARGET if args.terminal else None, 'foundation_3x3':len(foundations),
              'space_belts':len(islands)-len(foundations),'buildings':sum(len(obj['B']['Entries']) for obj in foundations)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
