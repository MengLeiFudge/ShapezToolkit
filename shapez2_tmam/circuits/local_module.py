"""本地组合模块的建筑生成。每根信号线有自己的纵向走线列，同层横线用线桥相交。"""

from collections import defaultdict

from ..mari.blueprint import DIRECTIONS, Wiring
from ..mari.ports import PORTS
from .circuit import Literal, constant


class Module:
    def __init__(self, inputs):
        self.inputs = inputs
        self.gates = []
        self.outputs = {}
        self.rom = None

    def lookup(self, address, result, pairs):
        pairs = tuple(pairs)
        if self.rom or not 1 <= len(pairs) <= 26 or len({key for key, _ in pairs}) != len(pairs):
            raise ValueError("单板可放一张键唯一、至多26行的只读表")
        self.rom = address, result, pairs

    def gate(self, kind, args, nets, config=None):
        if (len(args), len(nets)) != (len(PORTS[kind][1]), len(PORTS[kind][0])):
            raise ValueError(f"端口数不符 {kind}")
        self.gates.append((kind, args, nets, config))

    def layout(self):
        cells = {}
        entries = []
        paths = defaultdict(lambda: defaultdict(set))
        taps = defaultdict(lambda: defaultdict(list))
        drivers = defaultdict(list)
        expected = {}
        literals = {}
        nets = dict.fromkeys(n for _, args, _, _ in self.gates for n in args if isinstance(n, str))
        nets.update(dict.fromkeys(self.outputs))
        if self.rom:
            nets.update(dict.fromkeys(self.rom[:2]))
        tracks = {n: i for i, n in enumerate(nets, 4)}
        if self.rom:
            # 查表键和四路结果在表边缘上下串联，各行不横穿整个平台。
            data = [n for n in nets if n not in self.rom[:2]]
            if len(data) > 42:
                raise ValueError("查表板的其余信号超过42根纵线")
            tracks = {n: i for i, n in enumerate(data, 4)}
            tracks.update(zip(self.rom[:2], (46, 47)))
        if len(tracks) > 44:
            raise ValueError(f"单板需要 {len(tracks)} 根纵向线，可用44根")

        def put(kind, x, y, z, r=0, config=None, radius=0, height=1):
            index = len(entries)
            for a in range(x-radius, x+radius+1):
                for b in range(y-radius, y+radius+1):
                    for l in range(z, z+height):
                        if (a, b, l) in cells or not (0 <= a < 54 and 0 <= b < 54 and 0 <= l < 3):
                            raise ValueError(f"建筑越界或重叠 {kind}@{(a,b,l)}")
                        cells[a, b, l] = index
            entry = {"T": kind + "InternalVariant", "X": x - 17, "Y": y - 17, "L": z, "R": r}
            if config is not None:
                entry["C"] = config
            entries.append(entry)
            return index

        def line(n, z, *points):
            for (x,y), (a,b) in zip(points, points[1:]):
                if (x,y) == (a,b):
                    continue
                dx, dy = (a>x)-(a<x), (b>y)-(b<y)
                d = DIRECTIONS.index((dx,dy))
                while (x,y) != (a,b):
                    paths[x,y,z][n].add(d)
                    x,y = x+dx,y+dy
                    paths[x,y,z][n].add((d+2)%4)

        count = len(self.inputs) + len(self.outputs)
        if count > 10:
            raise ValueError("单板的公开接口最多十个")
        for i,(net,channel) in enumerate((*self.inputs.items(), *self.outputs.items())):
            rx = i < len(self.inputs)
            y = 2 + i * 5
            index = put("ControlledSignalReceiver" if rx else "ControlledSignalTransmitter", 51,y,0,
                        2 if rx else 0,radius=1,height=3)
            cfg = put("ConstantSignalDefault",51,y+(2 if rx else -2),0,3 if rx else 1,constant(channel))
            literals[index,0] = ((cfg,0),)
            if rx:
                drivers[net].append((index,0))
            else:
                expected[index,1] = net
            line(net,0,(50,y),(tracks[net],y))
            taps[net][0].append(y)

        # 同一个门的三个方向各占一横行。第一层的门避开右侧接口的横线。
        reserved = {0: 2 + (count-1)*5, 1: -1, 2: -1}
        if self.rom:
            address, result, pairs = self.rom
            for i, (key, value) in enumerate(pairs):
                z, slot = divmod(i, 13)
                z += 1
                y = 3 + 4 * slot
                match = put("LogicGateCompare",48,y,z,config="AQ==")
                select = put("LogicGateIf",49,y,z,3)
                key_gate = put("ConstantSignalDefault",48,y-1,z,1,constant(key))
                value_gate = put("ConstantSignalDefault",49,y+1,z,3,constant(value))
                literals[match,0] = ((key_gate,0),)
                expected[match,1] = address
                literals[select,0] = ((value_gate,0),)
                literals[select,1] = ((match,0),)
                drivers[result].append((select,0))
                line(address,z,(48,y),(48,y+1),(tracks[address],y+1))
                line(result,z,(49,y),(49,y-2),(tracks[result],y-2))
                taps[address][z].append(y+1)
                taps[result][z].append(y-2)
                # 门阵列位于左侧。查表边缘水平线只占 x≥46。
                reserved[z] = -1
        sites = [(y,z) for z in (0,1,2) for y in range(2,52,3) if y-1 > reserved[z]]
        if len(self.gates) > len(sites):
            raise ValueError(f"单板需要 {len(self.gates)} 个门位，可用 {len(sites)} 个")
        for (kind,args,outs,config),(y,z) in zip(self.gates,sites):
            typ = kind + ("Default" if kind.startswith("Virtual") and kind != "VirtualRotatorCCW" else "")
            index = put(typ,2,y,z,config=config)
            for category, signals in enumerate((outs,args)):
                for port,(net, (d,px,py,pz)) in enumerate(zip(signals,PORTS[kind][category])):
                    if (px,py,pz) != (0,0,0):
                        raise ValueError(f"该门需要专用多格布局 {kind}")
                    if category and not isinstance(net,str):
                        dx,dy = DIRECTIONS[d]
                        src = put("ConstantSignalDefault",2+dx,y+dy,z,(d+2)%4,constant(net.value if isinstance(net, Literal) else net))
                        literals[index,port] = ((src,0),)
                        continue
                    if category:
                        expected[index,port] = net
                    else:
                        drivers[net].append((index,port))
                    if net not in tracks:
                        continue
                    row = y + (0,1,1,-1)[d]
                    lead = ((), ((2,row),), ((1,y),(1,row)), ((2,row),))[d]
                    line(net,z,(2,y),*lead,(tracks[net],row))
                    taps[net][z].append(row)

        for n, levels in taps.items():
            x = tracks[n]
            zs = sorted(levels)
            for k,(lo,hi) in enumerate(zip(zs,zs[1:])):
                y,r = (0,3) if k==0 else (53,1)
                put(f"WireDefault{hi-lo}UpBackward",x,y,lo,r,height=hi-lo+1)
                levels[lo].append(y)
                levels[hi].append(y)
            for z,rows in levels.items():
                line(n,z,(x,min(rows)),(x,max(rows)))

        patterns = {frozenset((d+r)%4 for d in ds):(kind,r) for kind,ds in
                    (("Forward",(0,2)),("Left",(2,3)),("Junction",(0,1,3)),("Cross",(0,1,2,3))) for r in range(4)}
        for site, signals in paths.items():
            if site in cells:
                continue
            ds = list(map(frozenset,signals.values()))
            if len(ds)==2 and set(ds)=={frozenset((0,2)),frozenset((1,3))}:
                kind,r = "Bridge",0
            elif len(ds)==1 and ds[0] in patterns:
                kind,r = patterns[ds[0]]
            elif len(ds)==1 and len(ds[0])==1:
                continue
            else:
                raise ValueError(f"本地走线重叠 {site} {signals}")
            put("WireDefault"+kind,*site,r)
        bp = {"$type":"Island","BinaryVersion":1137,"Entries":[{"T":"Foundation_3x3","B":{
              "$type":"Building","BinaryVersion":1137,"Entries":entries}}]}
        wiring = Wiring(bp)
        for pin,sources in {**literals, **{pin:tuple(sorted(drivers[n])) for pin,n in expected.items()}}.items():
            if not sources or wiring.sources(*pin) != sources:
                raise ValueError(f"输入 {pin} 期望 {sources}，接到 {wiring.sources(*pin)}")
        return {"V":1137,"BP":bp}
