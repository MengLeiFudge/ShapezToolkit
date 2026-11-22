"""单料车和混合车并行停靠，本站只填指定车厢的一个层位。"""

import argparse
from pathlib import Path

from .circuit import encode_document
from .freight_stage import CARS
from .slot_streams import SlotStreams


def transfer(cargo):
    car,kind,level = next((i,kind,layers.index(cargo)) for i,(kind,layers) in enumerate(CARS) if cargo in layers)
    fluid = kind=='Fluids'
    board = SlotStreams()
    row = -12+20*car
    for y in range(row,row+4):
        prefix = 'FluidPort' if fluid else 'BeltPort'
        board.put(prefix+'Receiver',-18,y,config='AA==')
        board.straight(-17,0,y,pipe=fluid)
        lift = ('PipeForward','PipeUpForward','Pipe2UpForward') if fluid else ('BeltDefaultForward','Lift1UpForward','Lift2UpForward')
        board.put(lift[level],0,y)
        board.straight(1,37,y,level,pipe=fluid)
        board.put(prefix+'Sender',37,y,level,config='KAAAAAA=')
    return board.finish(),car,kind


def loading(cargo):
    template,car,kind = transfer(cargo)
    islands = [{'T':'Layout_TrainWaitStation','X':3,'Y':-2,'R':3}]
    unloads = {3*i+car-1 for i in range(4)}
    for y in range(-2,11):
        if y in unloads:
            entry = {'T':'Layout_TrainUnloader_'+kind+'_Flipped'}
        elif y+1 in unloads:
            entry = {'T':'Layout_TrainWaitStation'}
        else:
            entry = {'T':'Rail_Forward','S':'AQAAAAA='}
        islands.append(dict(entry,X=-3,Y=y,R=3))
    for i in range(4):
        islands.append(dict(template,Y=3*i))
        for j in range(3):
            # 停站规则从第一节开始扫描，遇普通铁轨即终止。空闲车位须为对应车种的占位站。
            spacer = 'Shape' if CARS[j][0]=='Shapes' else 'Fluid'
            station = 'Layout_TrainLoader_'+kind if j==car else 'Layout_TrainSpacerStraight'+spacer
            islands.append({'T':station,'X':3,'Y':3*i+j-1,'R':3})
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}


def main():
    parser = argparse.ArgumentParser(description='给混编车的四个同类层位填入同种原料')
    parser.add_argument('cargo',choices=tuple('CRSWrgb'))
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(loading(args.cargo))+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
