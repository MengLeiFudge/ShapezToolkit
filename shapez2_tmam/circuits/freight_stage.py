"""四角备料的混合列车，从车头起每三节依次装三种整片、风车和三原色。"""

import argparse
import json
from pathlib import Path

from .assembled_stage import assembled_stage
from .circuit import encode_document
from .production_line import check_jump
from .slot_streams import SlotStreams
from .stock_selector import SOURCES, route_dyes
from .wagon_intake import intake


CARS = (('Shapes', ('C','R','S')), ('Shapes', ('W',None,None)), ('Fluids', ('r','g','b')))


def depot():
    islands = [{'T':'Layout_TrainProducer_Red','R':3}, {'T':'Rail_Forward','Y':-2,'R':3,'S':'AQAAAAA='}]
    for n,(kind,_) in enumerate(CARS*4,1):
        wagon = 'Layout_TrainFluidWagonExtension' if kind=='Fluids' else 'Layout_TrainShapeWagonExtension'
        islands.append({'T':wagon,'Y':n,'R':3})
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def approach_tracks(*, machine_dyes=True, corner_stock=True):
    tracks = []

    def rail(x, y, direction, kind='Forward'):
        tracks.append({'T':'Rail_'+kind,'X':x,'Y':y,'R':direction,'S':'AQAAAAA='})

    for y in range(-18,-4):
        rail(-13,y,1)
    rail(-13,-4,1,'LeftTurn')
    rail(-12,-4,0,'LeftTurn')
    rail(-12,-18,3)
    if not corner_stock:
        tracks.clear()
    if not machine_dyes:
        return tracks
    rail(-9,2,3,'LeftTurn')
    rail(-10,2,2,'LeftTurn')
    for y in range(3,8):
        rail(-10,y,1)
    for y in range(5,8):
        rail(-9,y,3)
    return tracks


def freight_stage(index, *, machine_dyes=True, stream=False):
    doc = assembled_stage(index, stream=stream)
    islands = doc['BP']['Entries']
    selectors = {(obj['X'],obj['Y']):obj for obj in islands if obj.get('X') == -6 and obj.get('Z',0)==0}
    station_x = -12
    islands.append({'T':'Layout_TrainWaitStation','X':station_x,'Y':-17,'R':3})
    for i in range(4):
        y = -15+3*i
        receiver = selectors[-6,y]
        feed = intake()
        feed.update(X=-9,Y=y)
        for row,level in SOURCES:
            check_jump(feed,receiver,row,0,level)
        for level in (1,2):
            for row in range(28,32):
                check_jump(feed,receiver,row,0,level,fluid=True)
        islands.append(feed)
        for j,(kind,_) in enumerate(CARS):
            station = {'T':'Layout_TrainUnloader_'+kind+'_Flipped','X':station_x,'Y':y+j-1,'R':3}
            islands.append(station)
    if not machine_dyes:
        islands.extend(approach_tracks(machine_dyes=False))
        return doc
    islands.extend(approach_tracks(machine_dyes=False))
    add_machine_dyes(islands)
    return doc


def add_machine_dyes(islands):
    feed = intake(dyes_only=True)
    feed.update(X=-6,Y=3)
    lane = SlotStreams()
    route_dyes(lane)
    adapter = lane.finish()
    adapter.update(X=-3,Y=3)
    for level in (1,2):
        for row in range(28,32):
            check_jump(feed,adapter,row,0,level,fluid=True)
    for row in (-12,-11,-10,-9,8,9,10):
        check_jump(adapter,islands[2],row,0,2,fluid=True)
    islands.extend((feed,adapter,{'T':'Layout_TrainWaitStation','X':-9,'Y':3,'R':3},
                    {'T':'Layout_TrainUnloader_Fluids_Flipped','X':-9,'Y':4,'R':3}))
    islands.extend(approach_tracks(corner_stock=False))


def main():
    parser = argparse.ArgumentParser(description='生成四角供料混编列车和收货工段')
    parser.add_argument('role',choices=('stage','depot'))
    parser.add_argument('--index',type=int,default=0)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    doc = depot() if args.role=='depot' else freight_stage(args.index)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+'\n',encoding='utf-8')
    report = {'cars':[{'wagon':i,'type':kind,'layers_bottom_to_top':layers} for i,(kind,layers) in enumerate(CARS*4,1)],
              'train_head':'north','stage':args.index if args.role=='stage' else None,
              'islands':len(doc['BP']['Entries'])}
    args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
