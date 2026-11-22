"""将五层列判据编成按层读取的有限状态机，一次查表同时给出四种材料的后继。"""

import argparse
import json
from itertools import product
from pathlib import Path

from ..synthesis.corners import CornerBuilder
from ..synthesis.physics import Rules
from .circuit import encode_document
from .local_module import Module


def column_table():
    alphabet = ("--", "Cu", "P-", "cr")
    states = {word: int(CornerBuilder.admissible(word)) for word in product(alphabet, repeat=5)}
    rows = [(0, 0, 0, 0), (1, 1, 1, 1)]
    for depth in reversed(range(5)):
        parents = {}
        for prefix in product(alphabet, repeat=depth):
            branches = tuple(states[prefix + (symbol,)] for symbol in alphabet)
            if branches not in rows:
                rows.append(branches)
            parents[prefix] = rows.index(branches)
        states = parents
    return rows, states[()]


def build_step():
    rows, initial = column_table()
    tags = [part + color for part in "CRSW" for color in "urgbcmyw"]
    rules = Rules(4)
    module = Module({"state": 1_600_020, "material": 1_600_021})
    pairs = [(rules.parse("--" + tags[i] + "----"), rules.parse("".join(tags[j] for j in row))) for i, row in enumerate(rows)]
    module.lookup("state", "choices", pairs)
    for q in range(4):
        name = f"at{q}"
        module.gate("LogicGateCompare", ("material", q), (name,), "AQ==")
        rotated = "choices" if q == 0 else f"rotation{q}"
        if q:
            previous = "choices" if q == 1 else f"rotation{q-1}"
            module.gate("VirtualRotatorCCW", (previous,), (rotated,))
        module.gate("LogicGateIf", (rotated, name), ("selected",))
    module.gate("VirtualHalfCutter", ("selected",), ("front",))
    module.gate("VirtualRotator", ("front",), ("shifted",))
    module.gate("VirtualHalfCutter", ("shifted",), ("next",))
    module.outputs = {"next": 1_600_022}
    return module, rows, [rules.parse("--" + tag + "----") for tag in tags[:len(rows)]], initial


def build_scan(step, rows, tags, initial):
    inputs = {"run": 1_600_030, **{f"z{z}": 1_600_031+z for z in range(5)}, "reply": step.outputs["next"]}
    scan = Module(inputs)
    scan.gate("LogicGateNot", ("run",), ("reset",))
    scan.gate("LogicGateIf", (tags[initial], "reset"), ("state",))
    scan.gate("LogicGateIf", ("reply", "run"), ("state",))
    depths = {0: 5, 1: 5}
    current = {initial}
    for z in range(5):
        for i in current - {0, 1}:
            if i in depths:
                raise ValueError("非终态对应多个原层号")
            depths[i] = z
        current = {child for i in current for child in rows[i]}
    scan.lookup("state", "level", [(tags[i], depth) for i,depth in depths.items()])
    for z in range(6):
        select = f"read{z}"
        scan.gate("LogicGateCompare", ("level", z), (select,), "AQ==")
        scan.gate("LogicGateIf", (f"z{z}" if z < 5 else 0, select), ("material",))
    for index, value in ((0, 2), (1, 1)):
        hit = f"terminal{index}"
        scan.gate("LogicGateCompare", ("state", tags[index]), (hit,), "AQ==")
        scan.gate("LogicGateIf", (value, hit), ("status",))
    scan.outputs = {**step.inputs, "status": 1_600_036}
    return scan


def main() -> int:
    parser = argparse.ArgumentParser(description="生成分时复用的五层列判据电路")
    parser.add_argument("--scan", action="store_true", help="组合上下级方法，自动读完一列")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module, rows, tags, initial = build_step()
    doc = module.layout()
    report = {"component": "column_step", "inputs": module.inputs, "outputs": module.outputs,
              "initial": tags[initial].to_key(), "accept": tags[1].to_key(), "reject": tags[0].to_key(),
              "material": {"empty": 0, "ordinary": 1, "pin": 2, "crystal": 3},
              "order": "从地面至第五层调用五次，包含原层号上的空格。每次等待稳定再锁存 next。",
              "rom_rows": len(rows), "native_gates_per_rom_row": 2, "platforms": 1,
              "building_entries": len(doc["BP"]["Entries"][0]["B"]["Entries"]), "internal_global_devices": 0}
    if args.scan:
        scan = build_scan(module, rows, tags, initial)
        upper = scan.layout()["BP"]["Entries"][0]
        upper["Z"] = 1
        doc["BP"]["Entries"].append(upper)
        report = {"component": "column_scan", "inputs": {n:c for n,c in scan.inputs.items() if n != "reply"},
                  "outputs": {"status": scan.outputs["status"]}, "material": report["material"],
                  "call_channels": {**module.inputs, **module.outputs}, "platforms": 2, "island_layers": 2,
                  "building_entries": sum(len(p["B"]["Entries"]) for p in doc["BP"]["Entries"]),
                  "internal_global_devices_per_method": 0,
                  "protocol": "run=0，保持五个原层位材料不变 128 信号 tick。随后 run=1，保持材料不变 160 tick，读取 status。1 表示通过，2 表示违反列判据。换列须重新复位。",
                  "timing_conditions": "整件批量导入或整图重载，固定接线、频道独占，Hybrid/AlwaysHighUPS 常速连续推进。"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc) + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
