"""六槽工段串接和单带成品出口。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .production_stage import build_stage
from .slot_stream_ports import trace, transport_paths
from .slot_streams import SLOT_ROWS, SlotStreams
from .stage_memory import WRITE_BUS, READBACK

TARGET = 1_640_010


def product_exit():
    lane = SlotStreams()
    # 制造树结束时仅剩一份活物。六槽先合并再用一台过滤器检查整件图形。
    for i, y in enumerate(SLOT_ROWS):
        lane.put('BeltPortReceiver', -18, y, config='AA==')
        lane.straight(-17, 0, y)
        if i == 0:
            lane.put('BeltDefaultLeft', 0, y, mirrored=True)
        elif i == len(SLOT_ROWS) - 1:
            lane.put('Merger2To1L', 0, y)
        else:
            lane.put('Merger2To1L', 0, y, rotation=1, mirrored=True)
        if i + 1 < len(SLOT_ROWS):
            for yy in range(y + 1, SLOT_ROWS[i + 1]):
                lane.put('BeltDefaultForward', 0, yy, rotation=1)
    y = SLOT_ROWS[-1]
    lane.straight(1, 12, y)
    filt = lane.put('BeltFilterDefault', 12, y)
    lane.put('TrashDefault', 12, y - 1, rotation=3)
    rx = lane.station(TARGET, 15, y+3)
    lane.put('WireDefaultForward', 13, y+3)
    lane.put('WireDefaultLeft', 12, y+3, rotation=1)
    for yy in (y+1, y+2):
        lane.put('WireDefaultForward', 12, yy, rotation=1)
    lane.pins.append((filt, 0, rx))
    lane.straight(13, 37, y)
    lane.put('BeltPortSender', 37, y, config='KAAAAAA=')
    island = lane.finish()
    paths = transport_paths(island)
    ends = {(37,y,0,2), (12,y-1,0,1)}
    for row in SLOT_ROWS:
        for mismatch, end in ((False,(37,y,0,2)), (True,(12,y-1,0,1))):
            turns = {(12,y,0)} if mismatch else set()
            if trace(paths,(-17,row,0,2),ends,turns) != end:
                raise ValueError(f'成品出口槽行 {row} 选路错误')
    return island


def check_jump(sender, receiver, local, direction, level=0, *, fluid=False):
    def port(island, kind, x, y):
        matches = [e for e in island['B']['Entries'] if e['T'] == kind+'InternalVariant' and
                   (e['X'],e['Y'],e['L'],e['R']) == (x,y,level,direction)]
        if len(matches) != 1:
            raise ValueError(f'缺少唯一的跨台带口 {kind} {(x,y,level,direction)}')
        return (20*island.get('X',0)+x, 20*island.get('Y',0)+y, island.get('Z',0))
    ends = ((37,local),(-18,local)) if direction == 0 else ((local,37),(local,-18))
    prefix = 'FluidPort' if fluid else 'BeltPort'
    x,y,z = port(sender,prefix+'Sender',*ends[0])
    a,b,c = port(receiver,prefix+'Receiver',*ends[1])
    if (a-x,b-y,c-z) != ((5,0,0) if direction == 0 else (0,5,0)):
        raise ValueError('跨台带口超出五格或层位不同')


def assemble(start, count, terminal=True):
    if not 0 <= start < start+count <= 971:
        raise ValueError('流水线地址须落在 0 至 970 之间，且至少包含一个工段')
    islands = []
    previous = None
    for i in range(count):
        stage = build_stage(start+i)['BP']['Entries']
        for island in stage:
            island['X'] = island.get('X',0) + 6*i
        take, receive, work = stage[:3]
        for y in SLOT_ROWS:
            check_jump(take,receive,y,0)
            if previous is not None:
                check_jump(previous,take,y,0)
        for level in (0,1):
            check_jump(take,work,-12,1,level)
        islands.extend(stage)
        previous = receive
    if terminal:
        end = product_exit()
        end['X'] = 6*count
        for y in SLOT_ROWS:
            check_jump(previous,end,y,0)
        islands.append(end)
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def main():
    parser = argparse.ArgumentParser(description='按连续地址装配六槽流水线区段和单带成品口')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int, required=True)
    parser.add_argument('--open-end', action='store_true', help='保留六槽出口供下一册接入')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    doc = assemble(args.start,args.count,not args.open_end)
    report = {'first_stage':args.start,'last_stage':args.start+args.count-1,'stages':args.count,
              'write_bus':WRITE_BUS,'readback':READBACK,'product_filter_channel':None if args.open_end else TARGET,
              'islands':len(doc['BP']['Entries'])}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
