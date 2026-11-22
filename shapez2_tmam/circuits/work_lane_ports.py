"""按原生加工机端口追踪指令工道，检查两份操作数、副产物和七个染料入口。"""


def check_lane(entries, selections, colors):
    facing = ((1,0),(0,1),(-1,0),(0,-1))
    ports = {}
    commands = {tuple(site): key for site,key in selections.items()}
    for e in entries:
        kind, _, suffix = e['T'].partition('InternalVariant')
        x,y,z,r = (e[k] for k in ('X','Y','L','R'))
        def port(direction, dx=0, dy=0, dz=0):
            if suffix == 'Mirrored':
                dy, direction = -dy,-direction
            for _ in range(r):
                dx,dy = -dy,dx
            return (x+dx,y+dy,z+dz,(direction+r)%4)
        def connect(pin, pout, tag=None):
            if pin in ports:
                raise ValueError(f'加工机接口重叠 {pin}')
            ports[pin] = pout, tag
        left, east = port(2),port(0)
        if kind == 'BeltFilterDefault':
            connect(left,(east,port(3)),('select',commands[x,y,z]))
        elif kind == 'HalvesSwapperDefault':
            for i in (0,1):
                connect(port(2,dy=-i),(port(0),port(0,dy=-1)),('swap',i))
        elif kind == 'StackerStraight':
            for dz in (0,1):
                connect(port(2,dz=dz),east,('stack',dz))
        elif kind == 'Lift1DownForward':
            connect(left,port(0,dz=-1))
        elif kind == 'Merger2To1L':
            connect(left,east)
            connect(port(3),east)
        elif kind in ('BeltDefaultLeft','BeltDefaultForward','BeltPortSender','TrashDefault'):
            connect(left,port(3) if kind == 'BeltDefaultLeft' else east,kind if kind in ('BeltPortSender','TrashDefault') else None)
        elif kind in ('RotatorOneQuad','RotatorOneQuadCCW','RotatorHalf','CutterHalf','PinPusherDefault','CrystalGeneratorDefault'):
            connect(left,east,kind)
            if kind == 'CrystalGeneratorDefault':
                connect(port(2,dy=1),east,('dye',commands[-12,y,0]))
        elif kind.startswith('Pipe'):
            other = port(3) if kind == 'PipeLeft' else port(0,dz=2 if kind == 'Pipe2UpForward' else 0)
            connect(left,other)
            connect(other,left)

    def trace(start, key, exit_side=0):
        at = start
        seen, machines = set(), []
        while at not in seen:
            seen.add(at)
            if at not in ports:
                raise ValueError(f'{key!r} 从 {start} 在 {at} 断开')
            out, tag = ports[at]
            if isinstance(tag, tuple) and tag[0] == 'select':
                out = out[int(tag[1] == key)]
            elif isinstance(tag, tuple) and tag[0] == 'swap':
                out = out[exit_side]
                machines.append(tag)
            elif tag is not None:
                machines.append(tag)
                if tag in ('BeltPortSender','TrashDefault') or isinstance(tag,tuple) and tag[0] == 'dye':
                    return machines
            x,y,z,d = out
            dx,dy = facing[d]
            at = x+dx,y+dy,z,(d+2)%4
        raise ValueError(f'{key!r} 从 {start} 遇到输送环路')

    uni = (('RotatorOneQuad',),('RotatorOneQuadCCW',),('RotatorHalf',),('CutterHalf',),
           ('RotatorHalf','CutterHalf','RotatorHalf'),('PinPusherDefault',))
    for key in (*range(1,10), *('color:'+c for c in colors)):
        for operand in range(2 if key in (7,8,9) else 1):
            start = (-12,-17,operand,3)
            path = trace(start,key,int(key == 9))
            expected = (['CrystalGeneratorDefault'] if isinstance(key,str) else list(uni[key-1]) if key <= 6 else
                        [('stack' if key == 7 else 'swap',operand)])
            if path != expected+['BeltPortSender']:
                raise ValueError(f'{key}/{operand} 加工路径 {path}')
            if key in (8,9) and trace(start,key,int(key == 8)) != expected+['TrashDefault']:
                raise ValueError(f'{key} 的副产物出口未消纳')
    for color,y in zip(colors,(-12,-11,-10,-9,8,9,10)):
        if trace((-17,y,2,2),color) != [('dye','color:'+color)]:
            raise ValueError(f'染料 {color} 未送到同色结晶机')
