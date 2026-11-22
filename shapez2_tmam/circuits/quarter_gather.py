"""四个角料台依次把出料插入固定带位，最后一个汇集台向东送入两级交换机。"""

from .slot_stream_ports import trace, transport_paths
from .slot_streams import SlotStreams


QUADRANTS = (2, 3, 1, 0)


def gather(slot):
    if slot not in range(4):
        raise ValueError('汇集带位须为 0 至 3')
    lane = SlotStreams()
    # 先接最东侧的带位，后续从西侧插入新料时不穿越已接通的带。
    x = 11-slot
    for xx in range(x+1,12):
        lane.put('BeltPortReceiver',xx,-18,rotation=1,config='AA==')
        for y in range(-17,37):
            lane.put('BeltDefaultForward',xx,y,rotation=1)
        lane.put('BeltPortSender',xx,37,rotation=1,config='KAAAAAA=')
    lane.put('BeltPortReceiver',-18,30,config='AA==')
    lane.straight(-17,x,30)
    lane.put('BeltDefaultLeft',x,30,mirrored=True)
    for y in range(31,37):
        lane.put('BeltDefaultForward',x,y,rotation=1)
    lane.put('BeltPortSender',x,37,rotation=1,config='KAAAAAA=')
    island = lane.finish()
    paths = transport_paths(island)
    ends = {(xx,37,0,3) for xx in range(x,12)}
    for xx in range(x,12):
        start = (-17,30,0,2) if xx == x else (xx,-17,0,3)
        if trace(paths,start,ends,set()) != (xx,37,0,3):
            raise ValueError('角料接到了其他带位')
    return island


def turn_to_assembly():
    lane = SlotStreams()
    for i in range(4):
        x,y = 11-i,8+i
        lane.put('BeltPortReceiver',x,-18,rotation=1,config='AA==')
        for yy in range(-17,y):
            lane.put('BeltDefaultForward',x,yy,rotation=1)
        lane.put('BeltDefaultLeft',x,y,rotation=1)
        lane.straight(x+1,37,y)
        lane.put('BeltPortSender',37,y,config='KAAAAAA=')
    island = lane.finish()
    paths = transport_paths(island)
    ends = {(37,y,0,2) for y in range(8,12)}
    for i,q in enumerate(QUADRANTS):
        if trace(paths,(11-i,-17,0,3),ends,set()) != (37,8+i,0,2):
            raise ValueError(f'q{q} 未送到拼装行 {8+i}')
    return island
