"""四分五层的基础单层工道，常规原料经角料预处理后由两级交换拼装。"""

import argparse
from pathlib import Path

from .circuit import encode_document


def make_platform(section):
    entries = []
    occupied = set()

    def put(kind, x, y, z=0, rotation=0, mirror=False):
        offsets = {"HalvesSwapperDefault": ((0,0,0),(0,-1,0)),
                   "CrystalGeneratorDefault": ((0,0,0),(0,1,0),(0,0,1)),
                   "PainterDefault": ((0,0,0),(0,1,0)),
                   "MixerDefault": ((0,0,0),(1,0,0),(2,0,0),(0,-1,0),(1,-1,0)),
                   "PipeUpForward": ((0,0,0),(0,0,1)),
                   "Pipe2UpForward": ((0,0,0),(0,0,1),(0,0,2))}
        for dx, dy, dz in offsets.get(kind, ((0,0,0),)):
            tile = x+dx, y+dy, z+dz
            notch = x+dx in (-18,37) and (y+dy)%20 in (8,9,10,11)
            if tile in occupied or not (0 <= z+dz < 3 and -17 <= y+dy <= 36 and (-17 <= x+dx <= 36 or notch)):
                raise ValueError(f"单层工道占地冲突或越界 {tile}")
            occupied.add(tile)
        entry = {"T":kind+"InternalVariant"+("Mirrored" if mirror else ""), "X":x,"Y":y,"L":z,"R":rotation}
        if kind in ("FluidPortReceiver", "BeltPortReceiver", "BeltPortSender", "FluidPortSender"):
            entry["C"] = "KAAAAAA=" if kind.endswith("Sender") else "AA=="
        entries.append(entry)

    def inlet(y, z, stop, machines=None, *, pipe=False):
        put("FluidPortReceiver" if pipe else "BeltPortReceiver", -18,y,z)
        for x in range(-17,stop):
            put((machines or {}).get(x,"PipeForward" if pipe else "BeltDefaultForward"), x,y,z)

    if section == "quarters":
        # 先拼 q0/q1、q2/q3。交换机南线为操作数a，北线为b。
        for y in range(8,12):
            inlet(y,0,0)
        for y in (9,11):
            put("HalvesSwapperDefault",0,y)
            put("TrashDefault",1,y-1)
            put("RotatorOneQuadCCW",1,y)
        for x in range(2,10):
            put("BeltDefaultForward",x,11)
            if x < 6:
                put("BeltDefaultForward",x,9)
            elif x == 6:
                put("BeltDefaultLeft",x,9,mirror=True)
                put("BeltDefaultLeft",x,10,rotation=1)
            else:
                put("BeltDefaultForward",x,10)
        put("HalvesSwapperDefault",10,11)
        put("TrashDefault",11,10)
        for x in range(11,37):
            put("BeltDefaultForward",x,11)
        put("BeltPortSender",37,11)
    elif section == "palette":
        # 西侧保持混合车的 R/G/B 层序。每条管固定颜色，第一台混色器占前方三格。
        def supply(y, source, dest, stop):
            inlet(y,source,-5,pipe=True)
            if source == dest:
                put("PipeForward",-5,y,dest)
            else:
                lift = "Pipe2UpForward" if abs(source-dest) == 2 else "PipeUpForward"
                put(lift,-5,y,min(source,dest),2 if dest < source else 0)
            for x in range(-4,stop):
                put("PipeForward",x,y,dest)

        def outlet(x0,y,z):
            for x in range(x0,37):
                put("PipeForward",x,y,z)
            put("FluidPortSender",37,y,z)

        for y,z,a,b in ((-11,0,0,1),(-9,1,0,2),(9,2,1,2)):
            supply(y-1,a,z,0)
            supply(y,b,z,0)
            put("MixerDefault",0,y,z)
            outlet(3,y,z)
        supply(28,1,0,0)
        supply(29,2,0,0)
        put("MixerDefault",0,29)
        for x in range(3,8):
            put("PipeForward",x,29)
        supply(30,0,0,8)
        put("MixerDefault",8,30)
        outlet(11,30,0)
        for z in range(3):
            inlet(11,z,37,pipe=True)
            put("FluidPortSender",37,11,z)
    elif section == "paint":
        # 三层各自接一路图形和一管固定颜色，避免切色时余液串色。
        for z in range(3):
            inlet(8,z,37,{3:"PainterDefault"})
            inlet(9,z,3,pipe=True)
            put("BeltPortSender",37,8,z)
    elif section == "stock":
        # 限高五层：前五针把全圆挤出留下五层针。结晶后第六针顶碎整塔。
        inlet(8,0,37,{-7:"PinPusherDefault",-5:"PinPusherDefault",-3:"PinPusherDefault",-1:"PinPusherDefault",
                       1:"PinPusherDefault",3:"CrystalGeneratorDefault",5:"PinPusherDefault"})
        put("BeltPortSender",37,8)
        inlet(9,0,3,pipe=True)
        for z,rotation in ((1,"RotatorOneQuadCCW"),(2,"RotatorOneQuad")):
            inlet(10,z,37,{3:"CutterHalf",5:rotation})
            put("BeltPortSender",37,10,z)
    else:
        raise ValueError(f"未知单层工道 {section}")
    return {"V":1137,"BP":{"$type":"Island","BinaryVersion":1137,"Entries":[{"T":"Foundation_3x3",
            "B":{"$type":"Building","BinaryVersion":1137,"Entries":entries}}]}}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成基础单层的实体拼装与备料平台")
    parser.add_argument("section", choices=("stock", "quarters", "paint", "palette"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(make_platform(args.section))+"\n",encoding="utf-8")
    return 0
