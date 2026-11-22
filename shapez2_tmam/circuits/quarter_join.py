"""三台交换机拼装四角，整片订单走 q0 直通带。"""

from .circuit import constant
from .slot_stream_ports import trace, transport_paths
from .slot_streams import SlotStreams


def quarter_join(direct_channel=None, *, south_output=False):
    lane = SlotStreams()
    for y in range(8,12):
        lane.put('BeltPortReceiver',-18,y,config='AA==')
        if y != 11 or direct_channel is None:
            lane.straight(-17,0,y)
            continue
        lane.straight(-17,-15,y)
        lane.put('BeltDefaultLeft',-15,y,mirrored=True)
        for yy in range(12,18):
            lane.put('BeltDefaultForward',-15,yy,rotation=1)
        lane.put('BeltDefaultLeft',-15,18,rotation=1)
        lane.straight(-14,-9,18)
        filt = lane.put('BeltFilterDefault',-9,18)
        rx = lane.put('ControlledSignalReceiver',-9,21,rotation=3)
        cfg = lane.put('ConstantSignalDefault',-11,21,config=constant(direct_channel))
        lane.put('WireDefaultForward',-9,19,rotation=1)
        lane.pins.extend(((rx,0,cfg),(filt,0,rx)))
        for yy in range(12,18):
            lane.put('BeltDefaultForward',-9,yy,rotation=3)
        lane.put('BeltDefaultLeft',-9,11,rotation=3,mirrored=True)
        lane.straight(-8,0,11)
        lane.straight(-8,18,18)
        lane.put('BeltDefaultLeft',18,18)
        for yy in range(12,18):
            lane.put('BeltDefaultForward',18,yy,rotation=3)
    for y in (9,11):
        lane.put('HalvesSwapperDefault',0,y)
        lane.put('TrashDefault',1,y-1)
        lane.put('RotatorOneQuadCCW',1,y)
    lane.straight(2,10,11)
    lane.straight(2,6,9)
    lane.put('BeltDefaultLeft',6,9,mirrored=True)
    lane.put('BeltDefaultLeft',6,10,rotation=1)
    lane.straight(7,10,10)
    lane.put('HalvesSwapperDefault',10,11)
    lane.put('TrashDefault',11,10)
    lane.straight(11,18,11)
    if direct_channel is None:
        lane.put('BeltDefaultForward',18,11)
    else:
        lane.put('Merger2To1L',18,11,mirrored=True)
    lane.straight(19,30 if south_output else 37,11)
    if south_output:
        lane.put('BeltDefaultLeft',30,11,mirrored=True)
        for yy in range(12,37):
            lane.put('BeltDefaultForward',30,yy,rotation=1)
        lane.put('BeltPortSender',30,37,rotation=1,config='KAAAAAA=')
        end = (30,37,0,3)
    else:
        lane.put('BeltPortSender',37,11,config='KAAAAAA=')
        end = (37,11,0,2)
    island = lane.finish()
    paths = transport_paths(island)
    trace(paths,(11,11,0,2),{end},set())
    if direct_channel is not None:
        trace(paths,(-17,11,0,2),{end},set())
        trace(paths,(-17,11,0,2),{(0,11,0,2)},{(-9,18,0)})
    return island
