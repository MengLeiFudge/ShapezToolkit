"""四象限实体加工平台和原生货运车站。坐标采用岛内建筑格，东为输出方向。"""

import argparse
from pathlib import Path

from .circuit import encode_document


TRAIN_BOOK = {
    "shape-depot": "图形货运", "shape-loading": "图形货运", "shape-unloading": "图形货运",
    "fluid-depot": "染料货运", "fluid-loading": "染料货运", "fluid-unloading": "染料货运",
}
WORKSHOP_BOOK = {"shape-workshop-4q5l": "图形加工", "crystal-workshop-4q5l": "结晶加工",
                 "slot-bank-4q5l": "实体槽位"}


def _station(name: str) -> list[dict]:
    cargo, role = name.split("-")
    if role == "depot":
        wagon = "Layout_TrainShapeWagonExtension" if cargo == "shape" else "Layout_TrainFluidWagonExtension"
        return [{"T": "Layout_TrainProducer_Red", "R": 3}, {"T": wagon, "Y": 1, "R": 3},
                {"T": "Rail_Forward", "Y": -2, "R": 3, "S": "AQAAAAA="}]
    transfer = "Loader" if role == "loading" else "Unloader"
    material = "Shapes" if cargo == "shape" else "Fluids"
    return [{"T": f"Layout_Train{transfer}_{material}", "Y": 1, "R": 3},
            {"T": "Layout_TrainWaitStation", "R": 3},
            {"T": "Rail_Forward", "Y": -1, "R": 3, "S": "AQAAAAA="}]


def _workshop(name: str) -> list[dict]:
    entries = []
    occupied = set()
    # resources.assets 中的跨格建筑，直堆叠上层口为第二输入。
    footprints = {"StackerStraight": ((0, 0), (0, 1)), "HalvesSwapperDefault": ((0, 0), (-1, 0)),
                  "CrystalGeneratorDefault": ((0, 0), (0, 1), (1, 0))}

    def put(kind, x, y, layer):
        for dy, dz in footprints.get(kind, ((0, 0),)):
            site = x, y + dy, layer + dz
            notch = x in (-18, 37) and 8 <= (y + dy) % 20 <= 11
            if site in occupied or not (0 <= layer + dz < 3 and -17 <= y + dy <= 36 and
                                        (-17 <= x <= 36 or notch)):
                raise ValueError(f"实体加工平台占地冲突或越界 {kind} {site}")
            occupied.add(site)
        entry = {"T": kind + "InternalVariant", "X": x, "Y": y, "L": layer}
        if kind in ("BeltPortSender", "BeltPortReceiver", "FluidPortReceiver"):
            entry["C"] = "KAAAAAA=" if kind == "BeltPortSender" else "AA=="
        entries.append(entry)

    def lane(y, layer, machines, *, fluid=False, stop=37, through=()):
        for x in range(-18, stop + 1):
            if x in through:
                continue  # 相邻工道的同一台建筑在这里有真实的第二端口。
            if x == -18:
                kind = "FluidPortReceiver" if fluid else "BeltPortReceiver"
            elif x == 37:
                kind = "BeltPortSender"
            else:
                kind = machines.get(x, "PipeForward" if fluid else "BeltDefaultForward")
            put(kind, x, y, layer)

    if name == "slot-bank-4q5l":
        for slot in range(6):
            layer, row = divmod(slot, 2)
            y = (-11, 9)[row]
            lane(y, layer, {0: "BeltReaderDefault", 8: "BeltFilterDefault"})
            # 失配口朝北。镜像弯带取 R=3，使其输入朝南、输出朝东。
            put("BeltDefaultLeft", 8, y - 1, layer)
            entries[-1].update(T="BeltDefaultLeftInternalVariantMirrored", R=3)
            for x in range(9, 38):
                put("BeltPortSender" if x == 37 else "BeltDefaultForward", x, y - 1, layer)
            for x in (0, 8):
                put("WireDefaultForward", x, y + 1, layer)
                entries[-1]["R"] = 1
    elif name == "crystal-workshop-4q5l":
        lane(8, 0, {8: "CrystalGeneratorDefault", 33: "BeltReaderDefault"})
        lane(9, 0, {}, fluid=True, stop=7)
    else:
        for y, kind in zip(range(-12, -8), ("RotatorOneQuad", "RotatorOneQuadCCW", "RotatorHalf", "PinPusherDefault")):
            lane(y, 0, {8: kind})
        lane(8, 2, {8: "CutterHalf"})
        lane(9, 2, {4: "RotatorHalf", 8: "CutterHalf", 12: "RotatorHalf"})
        lane(10, 0, {8: "StackerStraight"})
        lane(10, 1, {}, stop=7)
        lane(29, 1, {8: "HalvesSwapperDefault"})
        lane(28, 1, {}, through=(8,))
    return [{"T": "Foundation_3x3", "B": {"$type": "Building", "BinaryVersion": 1137, "Entries": entries}}]


def main() -> int:
    parser = argparse.ArgumentParser(description="生成实体加工与单车厢货运蓝图")
    parser.add_argument("name", choices=(*WORKSHOP_BOOK, *TRAIN_BOOK))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    islands = _station(args.name) if args.name in TRAIN_BOOK else _workshop(args.name)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": islands}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(document) + "\n", encoding="utf-8")
    print(f"已生成 {args.output}")
    return 0
