"""把基础单层的一个角译为备料线订单，四条角料线分时调用同一方法。"""

import argparse
import json
from pathlib import Path

from ..synthesis.physics import Rules
from .circuit import encode_document
from .local_module import Module


def quarter_order():
    module = Module({"row": 1_600_010, "quadrant": 1_600_011})
    for q in range(4):
        name = f"at{q}"
        module.gate("LogicGateCompare", ("quadrant", q), (name,), "AQ==")
        rotated = "row" if q == 0 else f"turn{q}"
        if q:
            previous = "row" if q == 1 else f"turn{q-1}"
            module.gate("VirtualRotatorCCW", (previous,), (rotated,))
        module.gate("LogicGateIf", (rotated, name), ("aligned",))
    module.gate("VirtualAnalyzer", ("aligned",), ("part", "color"))
    rules = Rules(4)
    for kind in "CRSW":
        module.gate("LogicGateCompare", ("part", rules.parse(kind + "u------")), (kind,), "AQ==")
        module.gate("LogicGateIf", (rules.parse((kind + "u") * 4), kind), ("stock",))
    # 针与空角均可领取任一无色整片。两种空角占位方向由所在工道决定。
    module.gate("LogicGateCompare", ("aligned", None), ("has_order",), "Bg==")
    module.gate("LogicGateCompare", ("part", None), ("vacant",), "AQ==")
    module.gate("LogicGateAnd", ("has_order", "vacant"), ("empty",))
    module.gate("LogicGateCompare", ("part", rules.parse("P-------")), ("pin",), "AQ==")
    module.outputs = {"stock": 1_600_012, "color": 1_600_013, "empty": 1_600_014, "pin": 1_600_015}
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="生成基础单层订单译码电路")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module = quarter_order()
    doc = module.layout()
    report = {"component": "quarter_order", "inputs": module.inputs, "outputs": module.outputs,
              "input_contract": "row 为空信号时停止领料。有效订单为非空无晶体单层，quadrant 为 0 至 3。",
              "return_contract": "普通角返回整片无色 stock 及目标 color；针或空角按 pin、empty 领任一牺牲整片。",
              "platforms": 1, "building_entries": len(doc["BP"]["Entries"][0]["B"]["Entries"]),
              "internal_global_devices": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc) + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
