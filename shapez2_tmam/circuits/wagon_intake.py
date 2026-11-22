"""四角供料台的车厢接口。前两节卸无色整片，第三节卸三原色。"""

from .intake_ports import check_intake
from .proportioning import _jogs
from .slot_streams import SlotStreams
from .stock_selector import SOURCES


def intake(*, dyes_only=False):
    lane = SlotStreams()
    for y,z in (() if dyes_only else SOURCES):
        lane.put('BeltPortReceiver',-18,y,z,config='AA==')
        lane.straight(-17,37,y,z)
        lane.put('BeltPortSender',37,y,z,config='KAAAAAA=')

    def horizontal(x1,x2,y,z):
        lane.straight(x1,x2,y,z,pipe=True)

    def jog(x,y,dest,z):
        down = dest > y
        lane.put('PipeLeft',x,y,z,mirrored=down)
        for yy in range(min(y,dest)+1,max(y,dest)):
            lane.put('PipeForward',x,yy,z,1)
        lane.put('PipeLeft',x,dest,z,1 if down else 3,mirrored=not down)

    # 每种原色均有四个独立车厢带位，分别接入直通口、混色口和白色的两级混色口。
    for z,dests in enumerate(((12,14,18,24),(16,19,22,25),(15,17,23,26))):
        for i,y in enumerate(dests):
            source, turn = 28+i, -16+i
            lane.put('FluidPortReceiver',-18,source,z,config='AA==')
            horizontal(-17,turn,source,z)
            jog(turn,source,y,z)
            horizontal(turn+1,-10,y,z)
            lane.put(('PipeForward','PipeUpForward','Pipe2UpForward')[z],-10,y,0,2 if z else 0)
            horizontal(-9,3 if y in (12,25,26) else 0 if y==24 else -6,y,0)
    for y in (15,17,19,23):
        lane.put('MixerDefault',-6,y)
        horizontal(-3,0 if y==23 else 3,y,0)
    lane.put('MixerDefault',0,24)
    for y,z in ((15,1),(19,1),(24,1),(25,2),(26,2)):
        lane.put('Pipe2UpForward' if z==2 else 'PipeUpForward',3,y)
    horizontal(3,6,17,0)
    jog(6,17,27,0)
    lane.put('Pipe2UpForward',7,27)
    horizontal(3,9,12,0)
    lane.put('PipeCross',9,12)
    lane.put('Pipe2UpForward',10,12)
    for y in range(13,31):
        lane.put('PipeForward',9,y,rotation=1)
    lane.put('PipeLeft',9,31,rotation=1)
    horizontal(10,32,31,0)
    lane.put('PipeUpForward',32,31)
    horizontal(33,37,31,1)
    lane.put('FluidPortSender',37,31,1,config='KAAAAAA=')
    for z,rows in ((1,(15,19,24)),(2,(12,25,26,27))):
        jogs = _jogs([(y,28+i) for i,y in enumerate(rows)],14)
        for i,y in enumerate(rows):
            turn = jogs[y]
            horizontal({12:11,27:8}.get(y,4),turn,y,z)
            jog(turn,y,28+i,z)
            horizontal(turn+1,37,28+i,z)
            lane.put('FluidPortSender',37,28+i,z,config='KAAAAAA=')
    island = lane.finish()
    check_intake(island['B']['Entries'])
    return island
