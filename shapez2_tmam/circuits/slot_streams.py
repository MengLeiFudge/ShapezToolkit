"""六槽连续物品流。取料台分出两个操作数，收料台在目标槽合并加工或领料产物。"""

from .circuit import constant
from .work_lane import WorkLane, A_X
from ..mari.blueprint import Wiring


SLOT_ROWS = (-12, -9, 8, 11, 28, 31)
FIRST, SECOND, DEST = 1_600_061, 1_600_062, 1_600_063


class SlotStreams(WorkLane):
    def station(self, channel, x, y, r=2):
        rx = self.put("ControlledSignalReceiver",x,y,rotation=r)
        dy = 2 if r == 2 else -2
        cfg = self.put("ConstantSignalDefault",x,y+dy,rotation=3 if r == 2 else 1,config=constant(channel))
        self.pins.append((rx,0,cfg))
        return rx

    def finish(self):
        island = {"T":"Foundation_3x3", "B":{"$type":"Building","BinaryVersion":1137,"Entries":self.electrical}}
        wiring = Wiring({"Entries":[island]})
        for sink, port, source in self.pins:
            if wiring.sources(sink,port) != ((source,0),):
                raise ValueError(f'槽地址未接通 {self.electrical[sink]}')
        island["B"]["Entries"] = self.entries
        return island

    def select(self, offset=0):
        lift_columns = (-14, 8)
        for side,x in enumerate(lift_columns):
            level = side+1
            rx = self.station((FIRST,SECOND)[side]+offset,x+1,-16)
            self.put("WireDefaultForward",x-1,-16,rotation=0)
            self.put("WireDefault1UpForward",x-2,-16,rotation=2)
            self.put("WireDefaultLeft",x-3,-16,1,2)
            for y in range(-15,33):
                if y in [s+1 for s in SLOT_ROWS]:
                    kind,r = ("Left",1) if y == 32 else ("Junction",0)
                else:
                    kind,r = "Forward",1
                self.put("WireDefault"+kind,x-3,y,1,r)
            for slot,y in enumerate(SLOT_ROWS):
                filt = self.put("BeltFilterDefault",x,y)
                comp = self.put("LogicGateCompare",x,y+1,rotation=3,config="Bg==")
                val = self.put("ConstantSignalDefault",x+1,y+1,rotation=2,config=constant(slot))
                self.put("WireDefaultForward",x-1,y+1)
                self.put("WireDefault1UpForward",x-2,y+1,rotation=2)
                self.pins.extend(((filt,0,comp),(comp,0,rx),(comp,1,val)))
                self.put("BeltDefaultLeft",x,y-1,rotation=3,mirrored=True)
                self.put(f"Lift{level}UpForward",x+1,y-1)
                if slot == 0:
                    self.put("BeltDefaultLeft",x+2,y-1,level,mirrored=True)
                else:
                    self.put("Merger2To1L",x+2,y-1,level,1,mirrored=True)
            rows = {s-1 for s in SLOT_ROWS}
            for y in range(min(rows),32):
                if y not in rows:
                    self.put("BeltDefaultForward",x+2,y,level,1)
        for y in SLOT_ROWS:
            self.put("BeltPortReceiver",-18,y,config="AA==")
            self.straight(-17,lift_columns[0],y)
            self.straight(lift_columns[0]+1,lift_columns[1],y)
            self.straight(lift_columns[1]+1,37,y)
            self.put("BeltPortSender",37,y,config="KAAAAAA=")
        # 二层的 B 横移到 A 正上方，两路分别降一层送南侧同排口。
        self.put("BeltDefaultLeft",10,32,2,1,mirrored=True)
        for x in range(A_X+1,10):
            self.put("BeltDefaultForward",x,32,2,2)
        self.put("BeltDefaultLeft",A_X,32,2,2)
        for level,drop in ((1,34),(2,35)):
            for y in range(32 if level == 1 else 33,37):
                if y == drop:
                    self.put("Lift1DownForward",A_X,y,level,1)
                else:
                    self.put("BeltDefaultForward",A_X,y,level-int(y > drop),1)
            self.put("BeltPortSender",A_X,37,level-1,1,config="KAAAAAA=")
        return self.finish()

    def receive(self, offset=0, *, north_base=False):
        rx = self.station(DEST+offset,-13,-15,r=0)
        self.put("WireDefault1UpForward",-11,-15)
        self.put("WireDefaultLeft",-10,-15,1,mirrored=True)
        x = -4
        for y in range(-14,32):
            if y == 31:
                self.put("WireDefaultLeft",-10,y,1,1)
            elif y in SLOT_ROWS:
                self.put("WireDefaultJunction",-10,y,1)
            elif y < 31:
                self.put("WireDefaultForward",-10,y,1,1)
        for slot,y in enumerate(SLOT_ROWS):
            # 材料返回缓冲由南向北走，地址匹配时向东分出。
            filt = self.put("BeltFilterDefault",x,y+1,1,3,mirrored=True)
            comp = self.put("LogicGateCompare",x-1,y+1,1,0,config="Bg==")
            val = self.put("ConstantSignalDefault",x-1,y+2,1,3,config=constant(slot))
            self.put("WireDefaultLeft",x-1,y,1,mirrored=True)
            for xx in range(-9,x-1):
                self.put("WireDefaultForward",xx,y,1)
            self.pins.extend(((filt,0,comp),(comp,0,rx),(comp,1,val)))
            self.straight(x+1,14,y+1,1)
            self.put("Lift1DownForward",14,y+1,1)
            self.put("BeltDefaultForward",15,y+1)
            self.put("BeltDefaultLeft",16,y+1)
            self.put("BeltPortReceiver",-18,y,config="AA==")
            self.straight(-17,16,y)
            self.put("Merger2To1L",16,y,mirrored=True)
            self.straight(17,37,y)
            self.put("BeltPortSender",37,y,config="KAAAAAA=")
        for y in range(min(SLOT_ROWS)+1,34):
            if y-1 not in SLOT_ROWS:
                self.put("BeltDefaultForward",x,y,1,3)
        # 加工回带与基础层领料各用一个南侧入口组，接收四种带序。
        for first,z in (((-12,0),) if north_base else ((-12,0),(8,1))):
            for xx in range(first,first+4):
                self.put("BeltPortReceiver",xx,37,z,3,config="AA==")
                self.put("BeltDefaultForward",xx,36,z,3)
                self.put("BeltDefaultLeft" if xx == first else "Merger2To1L",xx,35,z,
                         3 if xx == first else 0,mirrored=True)
            if z == 0:
                self.straight(first+4,x,35)
                self.put("Lift1UpForward",x,35)
                self.put("BeltDefaultLeft",x+1,35,1)
                self.put("Merger2To1L",x+1,34,1,2)
            else:
                self.put("BeltDefaultLeft",12,35,1)
                self.put("BeltDefaultLeft",12,34,1,3)
                for xx in range(x+2,12):
                    self.put("BeltDefaultForward",xx,34,1,2)
        if north_base:
            self.put('BeltPortReceiver',30,-18,rotation=1,config='AA==')
            self.put('Lift1UpForward',30,-17,rotation=1)
            for yy in range(-16,34):
                self.put('BeltDefaultForward',30,yy,1,1)
            self.put('BeltDefaultLeft',30,34,1,1,mirrored=True)
            for xx in range(x+2,30):
                self.put('BeltDefaultForward',xx,34,1,2)
        self.put("BeltDefaultLeft",x,34,1,2,mirrored=True)
        return self.finish()
