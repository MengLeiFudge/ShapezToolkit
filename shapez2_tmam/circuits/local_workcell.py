"""六槽物品指令共用的原生虚拟加工单元。状态、寻址和实物移动属于调用方。"""

import argparse
import json
from pathlib import Path

from .circuit import encode_document
from .local_module import Module


def build_workcell():
    module = Module({"opcode": 1_600_050, "a": 1_600_051, "b": 1_600_052, "color": 1_600_053})
    module.gate("VirtualRotator", ("a",), ("cw",))
    module.gate("VirtualRotator", ("cw",), ("half",))
    module.gate("VirtualRotatorCCW", ("a",), ("ccw",))
    module.gate("VirtualHalfCutter", ("a",), ("front",))
    module.gate("VirtualHalfCutter", ("half",), ("opposite",))
    module.gate("VirtualRotator", ("opposite",), ("quarter",))
    module.gate("VirtualRotator", ("quarter",), ("back",))
    module.gate("VirtualPinPusher", ("a",), ("pushed",))
    module.gate("VirtualStacker", ("a", "b"), ("stacked",))
    module.gate("VirtualHalvesSwapper", ("a", "b"), ("swap0", "swap1"))
    module.gate("VirtualCrystalGenerator", ("a", "color"), ("filled",))
    names = ("cw", "ccw", "half", "front", "back", "pushed", "stacked", "swap0", "swap1", "filled")
    for opcode, result in enumerate(names, start=1):
        active = f"use{opcode}"
        module.gate("LogicGateCompare", ("opcode", opcode), (active,), "AQ==")
        module.gate("LogicGateIf", (result, active), ("result",))
    module.outputs = {"result": 1_600_054}
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="编译四象限五层虚拟加工单元")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module = build_workcell()
    doc = module.layout()
    report = {"component": "workcell", "inputs": module.inputs, "outputs": module.outputs,
              "opcodes": ["1 顺转", "2 逆转", "3 半周转", "4 前半", "5 后半", "6 顶针", "7 下a上b堆叠",
                          "8 取a前半与b后半", "9 取b前半与a后半", "10 按color结晶"],
              "protocol": "输入原生图形，结晶颜色限可供给的七色。空产物返回空信号。固定输入后保持64信号tick再读结果。",
              "timing_conditions": "整件批量导入或重载，固定接线、独占频道、Hybrid/AlwaysHighUPS常速连续推进。",
              "platforms": 1, "building_entries": len(doc["BP"]["Entries"][0]["B"]["Entries"]),
              "internal_global_devices": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc) + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
