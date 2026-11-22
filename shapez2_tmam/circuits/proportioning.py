"""三组单料的层位换装。每个西侧四带口对应一种货，每节出站车厢有三种货。"""

import argparse
from pathlib import Path

from .circuit import encode_document


def _jogs(pairs, start):
    # 同一建筑层保持行序。向南移的先移动最南一条，向北移的先移动最北一条。
    moves = sorted((a, b) for a, b in pairs if b < a)
    moves.extend(sorted(((a, b) for a, b in pairs if b > a), reverse=True))
    return {a: start + i for i, (a, _) in enumerate(moves)}


def _check_lanes(entries):
    # 按成品建筑的实际方向和升降口追线，不使用布置时记录的中间点。
    paths = {}
    outlets = {}
    for e in entries:
        kind = e["T"].partition("InternalVariant")[0]
        x, y, z, rotation = (e[k] for k in ("X", "Y", "L", "R"))
        if kind.endswith("Sender"):
            outlets[x,y,z,2] = (y,z)
            continue
        if kind.endswith("Receiver"):
            continue
        incoming, outgoing = 2, 0
        iz = oz = z
        if kind.endswith("Left"):
            outgoing = 1 if e["T"].endswith("Mirrored") else 3
        elif kind.startswith("Lift"):
            oz += int(kind[4]) * (-1 if "Down" in kind else 1)
        elif kind.startswith("Pipe") and "Up" in kind:
            oz += 2 if kind.startswith("Pipe2") else 1
            if rotation == 2:
                incoming, outgoing, iz, oz = outgoing, incoming, oz, iz
        incoming = (incoming + rotation) % 4
        outgoing = (outgoing + rotation) % 4
        dx, dy = ((1,0),(0,1),(-1,0),(0,-1))[outgoing]
        key = x,y,iz,incoming
        if key in paths:
            raise ValueError(f"重复的运输入口 {key}")
        paths[key] = (x+dx,y+dy,oz,(outgoing+2)%4)
    for i in range(3):
        for j in range(3):
            for lane in range(4):
                start_y = -12 + 20*i + lane
                at = (-17,start_y,j,2)
                while at in paths:
                    at = paths.pop(at)
                if outlets.pop(at, None) != (-12+20*j+lane,i):
                    raise ValueError(f"输入 {(start_y,j)} 未独立抵达预期车厢层位，末端 {at}")
    if paths or outlets:
        raise ValueError("配料台有未接入的带、管或出口")


def _platform(fluid):
    entries = []
    occupied = set()

    def put(kind, x, y, level, turns=0, *, top=None, config=None, mirrored=False):
        for z in range(min(level, top), max(level, top) + 1) if top is not None else (level,):
            pos = x, y, z
            notch = x in (-18, 37) and 8 <= y % 20 <= 11
            if pos in occupied or not (0 <= z < 3 and -17 <= y <= 36 and (-17 <= x <= 36 or notch)):
                raise ValueError(f"换装线相交或超出平台 {pos}")
            occupied.add(pos)
        entry = {"T": kind + "InternalVariant" + ("Mirrored" if mirrored else ""),
                 "X": x, "Y": y, "L": level, "R": turns}
        if config is not None:
            entry["C"] = config
        entries.append(entry)

    straight = "PipeForward" if fluid else "BeltDefaultForward"
    elbow = "PipeLeft" if fluid else "BeltDefaultLeft"
    port = "FluidPort" if fluid else "BeltPort"

    def run(x1, x2, y, dest, level, turn_x):
        for x in range(x1, x2):
            if x == turn_x:
                down = dest > y
                step = 1 if down else -1
                put(elbow, x, y, level, mirrored=down)
                for row in range(y + step, dest, step):
                    put(straight, x, row, level, 1 if down else 3)
                put(elbow, x, dest, level, 1 if down else 3, mirrored=not down)
                y = dest
            else:
                put(straight, x, y, level)
        if y != dest:
            raise ValueError("换装工道未抵达指定行")

    paths = [(i, j, -12 + 20 * i + k, -12 + 12 * i + 4 * j + k, -12 + 20 * j + k)
             for i in range(3) for j in range(3) for k in range(4)]
    first = [_jogs([(s, m) for _, j, s, m, _ in paths if j == z], -16) for z in range(3)]
    second = [_jogs([(m, t) for i, _, _, m, t in paths if i == z], 13) for z in range(3)]
    for i, j, source, middle, target in paths:
        put(port + "Receiver", -18, source, j, config="AA==")
        run(-17, 8, source, middle, j, first[j].get(source))
        if i == j:
            put(straight, 8, middle, i)
        elif fluid:
            # 换层管是双向接头，降层时旋转半周，锚点仍在较低层。
            put("Pipe" + ("2" if abs(i-j) == 2 else "") + "UpForward", 8, middle,
                min(i, j), 2 if i < j else 0, top=max(i, j))
        else:
            put(f"Lift{abs(i-j)}{'Up' if i > j else 'Down'}Forward", 8, middle, j, top=i)
        run(9, 37, middle, target, i, second[i].get(middle))
        put(port + "Sender", 37, target, i, config="KAAAAAA=")
    _check_lanes(entries)
    return {"T": "Foundation_3x3", "B": {"$type": "Building", "BinaryVersion": 1137, "Entries": entries}}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成混合三车厢的配料、编组与卸货蓝图")
    parser.add_argument("cargo", choices=("shapes", "fluids"))
    parser.add_argument("role", choices=("load", "depot", "unload"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fluid = args.cargo == "fluids"
    if args.role == "depot":
        wagon = "Layout_TrainFluidWagonExtension" if fluid else "Layout_TrainShapeWagonExtension"
        islands = [{"T": "Layout_TrainProducer_Red", "R": 3},
                   *({"T": wagon, "R": 3, "Y": y} for y in (1, 2, 3)),
                   {"T": "Rail_Forward", "Y": -2, "R": 3, "S": "AQAAAAA="}]
    else:
        loading = args.role == "load"
        kind = "Layout_Train" + ("Loader_" if loading else "Unloader_") + args.cargo.capitalize()
        if not loading:
            kind += "_Flipped"  # 车头朝北，制作层位于卸货站东侧。
        x = 3 if loading else 0
        islands = ([_platform(fluid)] if loading else []) + [
            {"T": "Layout_TrainWaitStation", "X": x, "Y": -2, "R": 3},
            *({"T": kind, "X": x, "Y": y, "R": 3} for y in (-1, 0, 1))]
    doc = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": islands}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc) + "\n", encoding="utf-8")
    return 0
