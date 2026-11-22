"""按原层号访问目标格。跨方法往返一次剥一层，空层不会被当成下一层。"""

import argparse
import json
from pathlib import Path

from .circuit import Literal, encode_document
from .local_module import Module


def row_step():
    step = Module({"remaining": 1_600_040, "z": 1_600_041})
    step.gate("VirtualUnstacker", ("remaining",), ("lower", "top"))
    # 同色结晶副本填满内部和底部空层，不改变高度。只在副本上测高。
    step.gate("VirtualCrystalGenerator", ("remaining", Literal("color:r")), ("dense",))
    current = "dense"
    for i in range(5):
        lower = f"below{i}"
        step.gate("VirtualUnstacker", (current,), (lower, None))
        step.gate("LogicGateCompare", (lower, None), (f"end{i}",), "AQ==")
        step.gate("LogicGateCompare", (current, None), (f"live{i}",), "Bg==")
        step.gate("LogicGateAnd", (f"end{i}", f"live{i}"), (f"at{i}",))
        step.gate("LogicGateIf", (i, f"at{i}"), ("height_index",))
        current = lower
    step.gate("LogicGateCompare", ("height_index", "z"), ("found",), "AQ==")
    step.gate("LogicGateCompare", ("height_index", "z"), ("higher",), "Aw==")
    # 高于所求层时返回未处理的下半。已到达/已越过时返回原物，使结果持续有效。
    step.gate("LogicGateNot", ("higher",), ("stop",))
    step.gate("LogicGateIf", ("remaining", "stop"), ("next",))
    step.gate("LogicGateIf", ("lower", "higher"), ("next",))
    step.gate("LogicGateIf", ("top", "found"), ("answer",))
    step.outputs = {"next": 1_600_042, "answer": 1_600_043}
    return step


def main() -> int:
    parser = argparse.ArgumentParser(description="生成按原层号和象限号读取目标格的电路")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    step = row_step()
    driver = Module({"target": 1_600_044, "q": 1_600_045, "run": 1_600_046,
                     "next": step.outputs["next"], "answer": step.outputs["answer"]})
    driver.gate("LogicGateNot", ("run",), ("reset",))
    driver.gate("LogicGateIf", ("target", "reset"), ("remaining",))
    driver.gate("LogicGateIf", ("next", "run"), ("remaining",))
    for q in range(4):
        rotated = "answer" if not q else f"rot{q}"
        if q:
            previous = "answer" if q == 1 else f"rot{q-1}"
            driver.gate("VirtualRotatorCCW", (previous,), (rotated,))
        driver.gate("LogicGateCompare", ("q", q), (f"at{q}",), "AQ==")
        driver.gate("LogicGateIf", (rotated, f"at{q}"), ("aligned",))
    driver.gate("VirtualAnalyzer", ("aligned",), ("part", "color"))
    driver.outputs = {"remaining": step.inputs["remaining"], "part": 1_600_047, "color": 1_600_048}
    doc = step.layout()
    upper = driver.layout()["BP"]["Entries"][0]
    upper["Z"] = 1
    doc["BP"]["Entries"].append(upper)
    report = {"component": "cell_at", "inputs": {"target": driver.inputs["target"], "z": step.inputs["z"],
              "q": driver.inputs["q"], "run": driver.inputs["run"]},
              "outputs": {"part": driver.outputs["part"], "color": driver.outputs["color"]},
              "call_channels": {"remaining": step.inputs["remaining"], **step.outputs},
              "protocol": "z=0…4，q=0…3。目标和坐标固定，run=0 保持128信号tick，再令run=1并保持160tick。空格返回两个空信号，非空格返回去色的q0单格和原颜色。",
              "timing_conditions": "整件批量导入或重载，固定接线、独占频道、Hybrid/AlwaysHighUPS常速连续推进。",
              "platforms": 2, "island_layers": 2, "internal_global_devices_per_method": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(doc) + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
