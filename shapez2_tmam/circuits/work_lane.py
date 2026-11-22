"""制作层的可编程加工工道。两条输入主带沿行选机，选定的产物并入同一条出带。"""

import argparse
import json
from collections import Counter
from pathlib import Path

from ..mari.blueprint import Wiring
from .circuit import constant, encode_document
from .proportioning import _jogs
from .work_lane_ports import check_lane


COLORS = "rgbcmyw"
COMMAND = 1_600_060
A_X = -12
OUT_X = 26


class WorkLane:
    def __init__(self, command=COMMAND):
        self.command = command
        self.entries = []
        self.occupied = set()
        self.selections = {}
        self.pins = []
        self.electrical = []
        self.trunks = {0: [], 1: []}

    def put(self, kind, x, y, z=0, rotation=0, *, mirrored=False, config=None):
        offsets = {"StackerStraight": ((0,0,1),), "HalvesSwapperDefault": ((0,-1,0),),
                   "CrystalGeneratorDefault": ((0,0,1),(0,1,0)), "Lift1DownForward": ((0,0,-1),),
                   "Lift1UpForward": ((0,0,1),), "Lift2UpForward": ((0,0,1),(0,0,2)),
                   "Pipe2UpForward": ((0,0,1),(0,0,2)), "WireDefault1UpBackward": ((0,0,1),),
                   "WireDefault1UpForward": ((0,0,1),)}
        offsets.update(MixerDefault=((1,0,0),(2,0,0),(0,-1,0),(1,-1,0)), PainterDefault=((0,1,0),), Lift2DownForward=((0,0,-1),(0,0,-2)),
                       PipeUpForward=((0,0,1),))
        footprint = ((0,0,0), *offsets.get(kind, ()))
        if kind == "ControlledSignalReceiver":
            footprint = [(dx,dy,dz) for dx in (-1,0,1) for dy in (-1,0,1) for dz in range(3)]
        for dx,dy,dz in footprint:
            if mirrored:
                dy = -dy
            for _ in range(rotation):
                dx,dy = -dy,dx
            xx, yy, zz = x+dx, y+dy, z+dz
            interior = -17 <= xx <= 36 and -17 <= yy <= 36
            notch = ((xx in (-18,37) and 8 <= yy%20 <= 11) or
                     (yy in (-18,37) and 8 <= xx%20 <= 11))
            if not ((interior or notch) and 0 <= zz < 3) or (xx,yy,zz) in self.occupied:
                raise ValueError(f"加工平台建筑占地冲突或越界 {kind} {(xx,yy,zz)}")
            self.occupied.add((xx,yy,zz))
        entry = {"T":kind+"InternalVariant"+("Mirrored" if mirrored else ""), "X":x,"Y":y,"L":z,"R":rotation}
        if config is not None:
            entry["C"] = config
        self.entries.append(entry)
        if kind.startswith(("LogicGate", "ControlledSignal", "ConstantSignal", "WireDefault", "BeltFilter")):
            self.electrical.append(entry)
            return len(self.electrical)-1

    def straight(self, x0, x1, y, z=0, *, pipe=False):
        for x in range(x0, x1):
            self.put("PipeForward" if pipe else "BeltDefaultForward", x,y,z)

    def selector(self, y, z, key):
        self.selections[A_X,y,z] = key
        filt = self.put("BeltFilterDefault", A_X,y,z,1)
        comp = self.put("LogicGateCompare", A_X-1,y,z,config="Bg==")
        literal = self.put("ConstantSignalDefault", A_X-1,y-1,z,1,config=constant(key))
        self.pins.extend(((filt,0,comp), (comp,0,literal), (comp,1,self.receiver)))
        # 比较器南脚取指令。匹配时比较器发 0，过滤器转向东方的机器。
        self.put("WireDefaultLeft", A_X-1,y+1,z)
        self.put("WireDefaultForward", A_X-2,y+1,z)
        self.put("WireDefaultForward", A_X-3,y+1,z)
        self.trunks[z].append(y+1)

    def inputs(self):
        self.receiver = self.put("ControlledSignalReceiver", -8,34,0,2)
        config = self.put("ConstantSignalDefault", -8,36,0,3,config=constant(self.command))
        self.pins.append((self.receiver,0,config))
        for x in range(-15,-9):
            self.put("WireDefaultForward", x,34)
        self.put("WireDefaultLeft", -16,34,0,1)  # 东、北
        for z in (0,1):
            self.put("BeltPortReceiver", A_X,-18,z,1,config="AA==")
            for y in range(-17, 31 if z == 0 else 10):
                if y in range(-15,31,3) and (z == 0 or y in (3,6,9)):
                    continue
                self.put("BeltDefaultForward", A_X,y,z,1)

    def signal_wires(self):
        self.put("WireDefault1UpBackward", -16,-17,0,3)
        for z, taps in self.trunks.items():
            end = 33 if z == 0 else max(taps)
            for y in range(-16,end+1):
                if y not in taps:
                    self.put("WireDefaultForward", -16,y,z,1)
                elif y == end and z == 1:
                    self.put("WireDefaultLeft", -16,y,z,1)
                else:
                    self.put("WireDefaultJunction", -16,y,z)

    def dyes(self):
        sources = (-12,-11,-10,-9,8,9,10)
        pairs = list(zip(sources,range(13,32,3)))
        jogs = _jogs(pairs,-17)
        for y, dest in pairs:
            turn = jogs[y]
            self.put("FluidPortReceiver",-18,y,2,config="AA==")
            self.straight(-17,turn,y,2,pipe=True)
            self.put("PipeLeft",turn,y,2,mirrored=True)
            for row in range(y+1,dest):
                self.put("PipeForward",turn,row,2,1)
            self.put("PipeLeft",turn,dest,2,1)
            self.straight(turn+1,0,dest,2,pipe=True)
            self.put("Pipe2UpForward",0,dest,0,2)
            self.straight(1,10,dest,0,pipe=True)

    def swaps(self, y, op):
        self.straight(A_X+1,1,y,1)
        self.put("BeltDefaultLeft",1,y,1)
        self.put("BeltDefaultLeft",1,y-1,1,3,mirrored=True)
        self.straight(2,5,y-1,1)
        self.put("Lift1DownForward",5,y-1,1)
        self.straight(6,10,y-1)
        self.put("HalvesSwapperDefault",10,y)
        if op == 8:
            self.put("TrashDefault",11,y-1)
        else:
            self.put("TrashDefault",11,y)
            self.straight(11,14,y-1)
            self.put("BeltDefaultLeft",14,y-1,mirrored=True)
            self.put("BeltDefaultLeft",14,y,rotation=1)

    def build(self):
        self.inputs()
        machines = ("RotatorOneQuad", "RotatorOneQuadCCW", "RotatorHalf", "CutterHalf", "CutterHalf", "PinPusherDefault")
        for i, key in enumerate((*range(1,10), *("color:"+c for c in COLORS))):
            y = -15 + 3*i
            self.selector(y,0,key)
            if key in (7,8,9):
                self.selector(y,1,key)
            start = A_X+1
            if key == 5:
                self.straight(start,6,y)
                self.put("RotatorHalf",6,y)
                start = 7
            self.straight(start,10,y)
            start = 11
            if isinstance(key,str):
                self.put("CrystalGeneratorDefault",10,y)
            elif key <= 6:
                self.put(machines[key-1],10,y)
                if key == 5:
                    self.put("RotatorHalf",11,y)
                    start = 12
            elif key == 7:
                self.straight(A_X+1,10,y,1)
                self.put("StackerStraight",10,y)
            else:
                self.swaps(y,key)
                if key == 9:
                    start = 15
            self.straight(start,OUT_X,y)
            if i == 0:
                self.put("BeltDefaultLeft",OUT_X,y,mirrored=True)
            elif i == 15:
                self.put("Merger2To1L",OUT_X,y)
            else:
                self.put("Merger2To1L",OUT_X,y,rotation=1,mirrored=True)
            if i < 15:
                for yy in (y+1,y+2):
                    self.put("BeltDefaultForward",OUT_X,yy,rotation=1)
        self.straight(OUT_X+1,37,30)
        self.put("BeltPortSender",37,30,config="KAAAAAA=")
        self.dyes()
        self.signal_wires()
        check_lane(self.entries, self.selections, COLORS)
        island = {"T":"Foundation_3x3","B":{"$type":"Building","BinaryVersion":1137,"Entries":self.electrical}}
        wiring = Wiring({"Entries":[island]})
        for sink, port, source in self.pins:
            if wiring.sources(sink,port) != ((source,0),):
                raise ValueError(f"加工工道控制接线错误 {self.electrical[sink]}，预期 {source}，实际 {wiring.sources(sink,port)}")
        island["B"]["Entries"] = self.entries
        return {"V":1137,"BP":{"$type":"Island","BinaryVersion":1137,"Entries":[island]}}


def main():
    parser = argparse.ArgumentParser(description="编译按配方自动选择加工机与回料带的实体平台")
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    lane = WorkLane()
    doc = lane.build()
    report = {"input_channel": COMMAND, "commands": "整数1至9对应旋转、半破、顶针、堆叠及交换。结晶直接发送原生颜色信号。",
              "operands_north": {"x":A_X,"a_level":0,"b_level":1}, "east_result": {"y":30,"level":0},
              "west_dyes_level_2": dict(zip(COLORS,(-12,-11,-10,-9,8,9,10))),
              "platforms":1,"buildings_per_floor":dict(Counter(e["L"] for e in lane.entries)),
              "protocol":"空工道先设置指令并保持至末件离开。仅堆叠、交换需要等量的 B 流。"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encode_document(doc)+"\n",encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0
