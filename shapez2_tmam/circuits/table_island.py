"""三层只读表。每行共用查找键和返回线，所有表项在同一次调用中并行比较。"""

from ..mari.blueprint import DIRECTIONS, Wiring
from .circuit import constant
from .wired_module import _Board


def _table(pairs, key_channel, result_channel):
    pairs = tuple(pairs)
    if not 1 <= len(pairs) <= 351 or len({key for key, _ in pairs}) != len(pairs):
        raise ValueError('只读平台需要 1 到 351 个不同的键')
    board = _Board()
    checks = {}

    def wire(net, x, y, a, b, z):
        if (x,y) == (a,b):
            return
        dx,dy = (a>x)-(a<x),(b>y)-(b<y)
        direction = DIRECTIONS.index((dx,dy))
        while (x,y) != (a,b):
            board.traces[x,y,z].setdefault(net,set()).add(direction)
            x,y = x+dx,y+dy
            board.traces[x,y,z].setdefault(net,set()).add((direction+2)%4)

    taps = {('key',0):[], ('value',0):[]}
    def short(kind,x,z):
        board.entries.append({'T':'WireTransmitter'+kind+'InternalVariant','X':x-17,'Y':31,'L':z})
        board.occupied.add((x,48,z))
        return len(board.entries)-1

    rx = tx = None
    if key_channel is not None:
        rx = board.place('ControlledSignalReceiver',1,50,0,radius=1,height=3)
        cfg = board.place('ConstantSignal',1,48,0,1,constant(key_channel))
        checks[rx,0] = ((cfg,0),)
        taps['key',0].append(50)
        wire('key',2,50,3,50,0)
    else:
        short('Receiver',-1,0)
        wire('key',-1,48,3,48,0)
        taps['key',0].append(48)
        short('Receiver',-1,1)
        wire('value',-1,48,48,48,1)
        taps['value',1] = [48]
    if result_channel is not None:
        tx = board.place('ControlledSignalTransmitter',51,50,0,radius=1,height=3)
        cfg = board.place('ConstantSignal',51,48,0,1,constant(result_channel))
        checks[tx,0] = ((cfg,0),)
        taps['value',0].append(50)
        wire('value',48,50,50,50,0)
    else:
        short('Sender',54,0)
        wire('key',3,48,54,48,0)
        taps['key',0].append(48)
        short('Sender',54,1)
        wire('value',48,48,54,48,1)
        taps.setdefault(('value',1),[]).append(48)
    outputs = []
    for start in range(0,len(pairs),13):
        z,r = divmod(start//13,9)
        row = pairs[start:start+13]
        y = 5 + 5*r
        taps.setdefault(('key',z),[]).append(y+2)
        taps.setdefault(('value',z),[]).append(y-2)
        wire('key',3,y+2,7+3*(len(row)-1),y+2,z)
        wire('value',8,y-2,48,y-2,z)
        for i,(key,value) in enumerate(row):
            x = 7+3*i
            match = board.place('LogicGateCompare',x,y,z,config='AQ==')
            select = board.place('LogicGateIf',x+1,y,z,3)
            want = board.place('ConstantSignal',x,y-1,z,1,constant(key))
            data = board.place('ConstantSignal',x+1,y+1,z,3,constant(value))
            checks[match,0] = ((want,0),)
            checks[match,1] = 'key'
            checks[select,0] = ((data,0),)
            checks[select,1] = ((match,0),)
            outputs.append((select,0))
            wire('key',x,y+2,x,y,z)
            wire('value',x+1,y,x+1,y-2,z)
    for net,x in (('key',3),('value',48)):
        levels = sorted(z for n,z in taps if n==net)
        for z in levels[1:]:
            y,rotation = (0,3) if z==1 else (53,1)
            board.place('WireDefault1UpBackward',x,y,z-1,rotation,height=2)
            taps[net,z-1].append(y)
            taps[net,z].append(y)
        for z in levels:
            rows = taps[net,z]
            wire(net,x,min(rows),x,max(rows),z)
    # 导线记录含相邻建筑的端格，实际建筑本身已经提供端口。
    for site in board.occupied:
        board.traces.pop(site,None)
    if tx is not None:
        checks[tx,1] = 'value'
    return board.finish()['Entries'][0],checks,outputs,rx


def table_strip(pairs, key_channel, result_channel):
    pairs = tuple(pairs)
    if not pairs or len({k for k,_ in pairs}) != len(pairs):
        raise ValueError('查表键须唯一且至少有一条记录')
    islands, checks, outputs = [], {}, []
    count = 0
    for start in range(0,len(pairs),351):
        island, local, matches, receiver = _table(pairs[start:start+351],
            key_channel if not start else None, result_channel if start+351>=len(pairs) else None)
        island['X'] = 3*len(islands)
        islands.append(island)
        for (i,p),sources in local.items():
            checks[count+i,p] = sources if isinstance(sources,str) else tuple((count+j,k) for j,k in sources)
        outputs.extend((count+i,p) for i,p in matches)
        if receiver is not None:
            key = ((count+receiver,0),)
        count += len(island['B']['Entries'])
    wiring = Wiring({'Entries':islands})
    buses = {'key':key, 'value':tuple(outputs)}
    for pin,sources in checks.items():
        expected = buses[sources] if isinstance(sources,str) else sources
        if wiring.sources(*pin) != expected:
            raise ValueError(f'只读表端口 {pin} 接线与表项不符')
    return islands


def table_island(pairs, key_channel, result_channel):
    island, = table_strip(pairs,key_channel,result_channel)
    return island
