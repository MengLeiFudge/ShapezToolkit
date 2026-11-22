"""由一条整片带、固定颜色管路和角料订单生成拼装用的实物。"""

from .slot_streams import SlotStreams
from .work_lane import A_X, COLORS, OUT_X


def prepare_quarter(channel, quadrant):
    if quadrant not in range(4):
        raise ValueError('角料象限需在 0 至 3 之间')
    lane = SlotStreams(channel)
    lane.receiver = lane.station(channel, -8, 34)
    for x in range(-15, -9):
        lane.put('WireDefaultForward', x, 34)
    lane.put('WireDefaultLeft', -16, 34, rotation=1)
    # 整片先在一层绕到选择带北端，再降至底层，不穿过底层选机电路。
    lane.put('BeltPortReceiver', -18, 9, config='AA==')
    lane.put('Lift1UpForward', -17, 9)
    lane.put('BeltDefaultLeft', -16, 9, 1)
    for yy in range(-14, 9):
        lane.put('BeltDefaultForward', -16, yy, 1, 3)
    lane.put('BeltDefaultLeft', -16, -15, 1, 3, mirrored=True)
    lane.put('Lift1DownForward', -15, -15, 1)
    lane.straight(-14, A_X, -15)
    lane.put('BeltDefaultLeft', A_X, -15, mirrored=True)
    keys = [(0, 'color:u'), (3, 1), (6, 2)] + [(12+3*i, 'color:'+c) for i,c in enumerate(COLORS)]
    rows = dict(keys)
    for y in range(-14, 31):
        if y not in rows:
            lane.put('BeltDefaultForward', A_X, y, rotation=1)
            continue
        lane.selector(y, 0, rows[y])
        machines = {}
        if y == 3:
            machines = {2:'CutterHalf', 4:'RotatorOneQuadCCW' if quadrant < 2 else 'RotatorOneQuad'}
        elif y == 6:
            machines = {x:'PinPusherDefault' for x in (-7,-5,-3,-1,1,12)}
            machines[10] = 'CrystalGeneratorDefault'
        elif y >= 12:
            machines[10] = 'PainterDefault'
        for x in range(A_X+1,OUT_X):
            lane.put(machines.get(x,'BeltDefaultForward'),x,y)
        if y == 0:
            lane.put('BeltDefaultLeft',OUT_X,y,mirrored=True)
        elif y == 30:
            lane.put('Merger2To1L',OUT_X,y)
        else:
            lane.put('Merger2To1L',OUT_X,y,rotation=1,mirrored=True)
    for y in range(1,30):
        if y not in rows:
            lane.put('BeltDefaultForward',OUT_X,y,rotation=1)
    lane.straight(OUT_X+1,37,30)
    lane.put('BeltPortSender',37,30,config='KAAAAAA=')
    for yy in range(1,34):
        kind = 'WireDefaultJunction' if yy-1 in rows else 'WireDefaultForward'
        if yy == 1:
            lane.put('WireDefaultLeft',-16,yy,rotation=2)
        else:
            lane.put(kind,-16,yy,rotation=0 if yy-1 in rows else 1)
    lane.dyes()
    # 制针结晶机单独接入一管牺牲染料。
    lane.put('FluidPortReceiver',-18,11,1,config='AA==')
    lane.straight(-17,4,11,1,pipe=True)
    lane.put('PipeLeft',4,11,1)
    for yy in range(8,11):
        lane.put('PipeForward',4,yy,1,3)
    lane.put('PipeLeft',4,7,1,3,mirrored=True)
    lane.put('PipeUpForward',5,7,rotation=2)
    lane.straight(6,10,7,pipe=True)
    return lane.finish()
