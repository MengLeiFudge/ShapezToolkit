"""递归网格的原目标标签路由与原生加工结果比较部件。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Literal, constant
from .corner_program import CornerProgram
from .decoder_circuit import decode
from .synthesis.physics import Rules
from .tag_palette import TagPalette, same_grid


def build_tagged_goal(channel_base: int = 1_127_000) -> tuple[Circuit, dict]:
    """编译标签查表与比较网表，不执行候选、加工指令或目标。"""
    reserve = 16_384
    if not 1 <= channel_base < (1 << 24) - reserve:
        raise ValueError("频道基址需要保留后续16384个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    original = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    actual = circuit.add("ControlledSignalReceiver", Literal(channel_base + 22))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 23))
    tags = tuple(tuple(circuit.add("ControlledSignalReceiver", Literal(channel_base + 2 + 4 * z + q))
                       for z in range(5)) for q in range(4))
    one = circuit.add("ConstantSignal", config=constant(1))
    program = CornerProgram(circuit)
    root = decode(circuit, original, one, Rules(4))
    grid = TagPalette(program, root).grid(tags)
    observed = decode(circuit, actual, one, Rules(4))
    valid = program.and_(enable, root.valid, grid.valid)
    matches = program.and_(valid, same_grid(program, observed, grid))
    published = tuple(tuple({name: circuit.add("LogicGateIf", getattr(grid.columns[q][z], name), valid)
                             for name in ("npc", "occupied", "pin", "crystal", "color")}
                            for q in range(4)) for z in range(5))
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("原目标标签网格超出其保留频道范围")
    return circuit, {
        "component": "original_tag_goal_grid", "quadrants": 4, "height": 5,
        "inputs": {"original_target": channel_base, "actual_result": channel_base + 22,
                   "enable": channel_base + 23,
                   "tags_bottom_to_top": [[channel_base + 2 + 4 * z + q for q in range(4)] for z in range(5)]},
        "outputs": {"valid": channels[valid], "matches": channels[matches],
                    "cells_bottom_to_top": [[{name: channels[value] for name, value in cell.items()}
                                             for cell in row] for row in published]},
        "tag_encoding": "0空、1辅助Cu、2P、3辅助红C；4+4*z+q引用原目标(z,q)格。原目标空格编号无效。",
        "cell_encoding": "npc是q0无C片段，C仅用P占位；crystal/color供真实后续结晶指令，不是免费C原料。",
        "gate_platforms": len(circuit.gates), "reserved_channels": [channel_base, channel_base + reserve - 1],
        "settling": circuit.settling_bound(),
        "protocol": "组合通路，无完成脉冲。原目标、20份ID、actual和enable均保持settling给出的时间再读。",
        "scope": "供递归控制器使用的材料/标签路由及完整结果比较；不判可制作性，不制造原生候选图形。空actual不匹配。",
        "proof": "4q5l/tagged-goal-grid.md；pin-column-circuit.md的固定标签表归纳。",
        "verification": "逐输入端口、别名及实际建筑占地静态编译；未运行目标、测试、指令或游戏",
    }


def main() -> int:
    """只生成生产电路和频道文档。"""
    parser = argparse.ArgumentParser(description="生成原目标标签网格路由与原生结果比较电路")
    parser.add_argument("--channel-base", type=int, default=1_127_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_tagged_goal(args.channel_base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"原目标标签网格已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
