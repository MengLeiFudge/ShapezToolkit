"""从成品槽位平台的带口追线，核对直通槽、A/B 侧路及回料目的地。"""

from ..mari.blueprint import DIRECTIONS


def transport_paths(island):
    connections = {}
    for e in island['B']['Entries']:
        kind, _, mirror = e['T'].partition('InternalVariant')
        x,y,z,r = (e[k] for k in ('X','Y','L','R'))

        def port(d, dz=0):
            return x,y,z+dz,((-d if mirror else d)+r)%4

        if kind == 'BeltFilterDefault':
            connections[port(2)] = (port(0), port(3))
        elif kind == 'Merger2To1L':
            connections[port(2)] = connections[port(3)] = (port(0),)
        elif kind.startswith('Lift'):
            dz = int(kind[4]) * (1 if 'Up' in kind else -1)
            connections[port(2)] = (port(0,dz),)
        elif kind in ('BeltDefaultForward','BeltDefaultLeft','BeltPortSender'):
            connections[port(2)] = (port(3 if kind == 'BeltDefaultLeft' else 0),)
    return connections


def trace(ports, start, exits, turns):
    at = start
    visited = set()
    while at not in visited:
        if at in exits:
            return at
        visited.add(at)
        if at not in ports:
            raise ValueError(f'槽带从 {start} 追到断口 {at}')
        choices = ports[at]
        x,y,z,d = choices[int(len(choices) == 2 and at[:3] in turns)]
        dx,dy = DIRECTIONS[d]
        at = x+dx,y+dy,z,(d+2)%4
    raise ValueError(f'槽带出现未指定的回流 {at}')


def check_slots(take, receive, rows, a_x, *, north_base=False):
    paths = transport_paths(take)
    outlets = {(37,y,0,2) for y in rows} | {(a_x,37,z,3) for z in (0,1)}
    for y in rows:
        entry = (-17,y,0,2)
        for turns,end in ((set(),(37,y,0,2)), ({(-14,y,0)},(a_x,37,0,3)), ({(8,y,0)},(a_x,37,1,3))):
            if trace(paths,entry,outlets,turns) != end:
                raise ValueError(f'槽带 {y} 未抵达 {end}')
    paths = transport_paths(receive)
    outlets = {(37,y,0,2) for y in rows}
    for y in rows:
        end = (37,y,0,2)
        if trace(paths,(-17,y,0,2),outlets,set()) != end:
            raise ValueError(f'收料台直通槽 {y} 未接回原行')
        inputs = [(x,36,0,1) for x in range(-12,-8)]
        inputs.extend([(30,-17,0,3)] if north_base else [(x,36,1,1) for x in range(8,12)])
        for start in inputs:
            if trace(paths,start,outlets,{(-4,y+1,1)}) != end:
                raise ValueError(f'收料台 {start} 未接到目的槽 {y}')
