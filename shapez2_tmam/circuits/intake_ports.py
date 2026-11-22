"""沿实际管口核对混色机的两个入口、出料配比和车厢层位。"""

from collections import defaultdict
from fractions import Fraction

from ..mari.blueprint import DIRECTIONS


def check_intake(entries):
    ports = {}
    nodes = defaultdict(set)
    dyes = {}
    mixers = []
    outlets = {}
    for i,e in enumerate(entries):
        k,_,mirror = e['T'].partition('InternalVariant')
        x,y,z,r = (e[a] for a in ('X','Y','L','R'))

        def port(d, node, dx=0, dy=0, dz=0):
            if mirror:
                dy,d = -dy,-d
            for _ in range(r):
                dx,dy = -dy,dx
            p = (x+dx,y+dy,z+dz,(r+d)%4)
            if p in ports:
                raise ValueError(f'管口重叠 {p}')
            ports[p] = node

        if k == 'FluidPortReceiver':
            port(0,i)
            dyes[i] = tuple(Fraction(int(c==z)) for c in range(3))
        elif k == 'FluidPortSender':
            port(2,i)
            outlets[y,z] = i
        elif k == 'MixerDefault':
            port(2,(i,0))
            port(2,(i,1),dy=-1)
            port(0,i,dx=2)
            mixers.append(i)
        elif k.startswith('Pipe'):
            port(2,i)
            if k == 'PipeLeft':
                port(3,i)
            elif k == 'PipeCross':
                for d in (0,1,3):
                    port(d,i)
            elif k in ('PipeForward','PipeUpForward','Pipe2UpForward'):
                port(0,i,dz={'PipeForward':0,'PipeUpForward':1,'Pipe2UpForward':2}[k])
            else:
                raise ValueError(f'未知管件 {k}')
    for (x,y,z,d),node in ports.items():
        dx,dy = DIRECTIONS[d]
        mate = ports.get((x+dx,y+dy,z,(d+2)%4))
        if mate is not None:
            nodes[node].add(mate)
    pending = set(mixers)
    while dyes:
        colors = dict(dyes)
        todo = list(dyes)
        while todo:
            node = todo.pop()
            for mate in nodes[node]:
                if mate not in colors:
                    colors[mate] = colors[node]
                    todo.append(mate)
                elif colors[mate] != colors[node]:
                    raise ValueError('厂内原色或混色管道串通')
        ready = [i for i in pending if (i,0) in colors and (i,1) in colors]
        if not ready:
            break
        for i in ready:
            dyes[i] = tuple((a+b)/2 for a,b in zip(colors[i,0],colors[i,1]))
            pending.remove(i)
    rows = {(28,2):'rrrr',(29,2):'gggg',(30,2):'bbbb',(31,2):'ggbb',
            (28,1):'rrbb',(29,1):'rrgg',(30,1):'rrgb',(31,1):'rrrr'}
    if pending or set(outlets)!=set(rows):
        raise ValueError('原料站有失联的混色机或出口')
    for pos,components in rows.items():
        expected = tuple(Fraction(components.count(c),4) for c in 'rgb')
        if colors.get(outlets[pos]) != expected:
            raise ValueError(f'原料站出口 {pos} 未接到 {components}')
