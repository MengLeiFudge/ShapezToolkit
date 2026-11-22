"""五层逐层制造方法。拆出的上料通过托底堆叠识别晶体，成功时直接返回配方的五个单层。"""

import argparse
import json
from pathlib import Path

from ..synthesis.physics import Rules
from .circuit import constant, encode_document
from .local_module import Module


def layer_recipe():
    module = Module({"target": 1_600_000})
    rows = []
    checks = []
    lower = "target"
    support = Rules(4).parse("CuCuCuCu")
    for z in range(5):
        row, rest = f"row{z}", f"rest{z}"
        module.gate("VirtualUnstacker", (lower,), (rest, row))
        raised, stripped, clean = f"raised{z}", f"stripped{z}", f"clean{z}"
        module.gate("VirtualStacker", (support, row), (raised,))
        module.gate("VirtualUnstacker", (raised,), (None, stripped))
        module.gate("LogicGateCompare", (stripped, row), (clean,), "AQ==")
        lower = rest
        rows.append(row)
        checks.append(clean)
    for i, (a, b) in enumerate(((0, 1), (2, 3), (5, 6), (7, 4))):
        name = f"all{5+i}"
        module.gate("LogicGateAnd", (checks[a], checks[b]), (name,))
        checks.append(name)
    acc = rows[-1]
    for i, row in enumerate(reversed(rows[:-1])):
        empty, result = f"empty{i}", f"assembled{i}"
        module.gate("LogicGateCompare", (acc, None), (empty,), "AQ==")
        module.gate("LogicGateIf", (row, empty), (result,))
        module.gate("VirtualStacker", (acc, row), (result,))
        acc = result
    module.gate("LogicGateCompare", (acc, "target"), ("matches",), "AQ==")
    module.outputs = {checks[-1]: 1_600_001, "matches": 1_600_002,
                      **{row: 1_600_003 + z for z, row in enumerate(rows)}}
    return module, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="生成四象限五层逐层制造配方方法")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module, rows = layer_recipe()
    doc = module.layout()
    entries = doc['BP']['Entries'][0]['B']['Entries']
    report = {"component": "layer_recipe", "inputs": module.inputs,
              "outputs": {"crystal_free": module.outputs["all8"], "matches": module.outputs["matches"],
                          "base_top_to_bottom": [module.outputs[row] for row in rows]},
              "input_contract": "非空四象限图形，高度上限5。保持输入至组合电路稳定。",
              "return_contract": "crystal_free与matches均为真时，从最下方非空base开始逆序取料、堆叠。crystal_free真且matches假表示不可制作。crystal_free假交由含晶体求解。",
              "building_entries": len(entries), "platforms": 1, "building_layers": sorted({e["L"] for e in entries}),
              "global_receivers": len(module.inputs), "global_transmitters": len(module.outputs), "internal_global_devices": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc) + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
