"""直接从十个材料整数判断标准半形，不生成候选原生图形信号。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Literal
from .half_circuit import MaterialCell, _combine, column_admissible, half_stable


def build_material_half(channel_base: int = 1_016_000) -> tuple[Circuit, dict]:
    """为完整逆推的格位寄存器提供半形充要判据。"""
    if not 1 <= channel_base < (1 << 24) - 2048:
        raise ValueError("频道基址需要为实例保留后续2048个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    rows = []
    allowed = []
    for z in range(5):
        row = []
        for q in (0, 1):
            source = circuit.add("ControlledSignalReceiver", Literal(channel_base + 2 * z + q))
            kinds = [circuit.add("LogicGateCompare", source, Literal(kind), config="AQ==") for kind in range(4)]
            occupied = _combine(circuit, "LogicGateOr", kinds[1:])
            allowed.append(_combine(circuit, "LogicGateOr", kinds))
            row.append(MaterialCell(occupied, kinds[2], kinds[3]))
        rows.append(tuple(row))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 10))
    nonempty = _combine(circuit, "LogicGateOr", [cell.occupied for row in rows for cell in row])
    valid = _combine(circuit, "LogicGateAnd", [enable, nonempty, *allowed])
    stable = half_stable(circuit, tuple(rows))
    admissible = _combine(circuit, "LogicGateAnd", [
        column_admissible(circuit, tuple(row[q] for row in rows)) for q in (0, 1)])
    predicate = circuit.add("LogicGateAnd", stable, admissible)
    solved = circuit.add("LogicGateAnd", valid, predicate)
    failed = circuit.add("LogicGateNot", predicate)
    unsolvable = circuit.add("LogicGateAnd", valid, failed)
    statuses = (circuit.add("LogicGateIf", Literal(1), solved),
                circuit.add("LogicGateIf", Literal(2), unsolvable))
    circuit.aliases.append(statuses)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 2047:
        raise ValueError("材料半形判据超出其保留频道范围")
    return circuit, {
        "component": "material_half_classifier", "quadrants": 4, "height": 5,
        "inputs": {"cells_bottom_to_top": [[channel_base + 2 * z + q for q in (0, 1)] for z in range(5)],
                   "enable": channel_base + 10},
        "outputs": {"valid": channels[valid], "status": channels[statuses[0]],
                    "solvable": channels[solved], "unsolvable": channels[unsolvable],
                    "stable": channels[stable], "columns_admissible": channels[admissible]},
        "encoding": {"0": "empty", "1": "ordinary", "2": "pin", "3": "crystal"},
        "gate_platforms": len(circuit.gates),
        "reserved_channels": [channel_base, channel_base + 2047],
        "scope": "q0/q1标准半形的材料结构；其他两列为空。普通种类及合法颜色在制造证书中回填，晶体3须对应rgbcmyw供料，cu供料由调用者另行排除。",
        "statuses": {"1": "solved", "2": "unsolvable", "null": "停用、全空或某格不是0～3整数"},
        "proof": "4q5l/half-row-stability.md、4q5l/corner-synthesis.md；两列A且稳定为充要条件。",
        "recipe": "仅判断候选材料格；角配方流和完整全图逆推控制尚未包含。",
        "timing": "组合电路；valid和status不是完成脉冲，整组输入保持不少于settling.hold_signal_ticks。",
        "settling": circuit.settling_bound(),
        "verification": "静态端口、实际占地与几何网络核对；未运行目标、门级模拟或游戏",
    }


def main() -> int:
    """编译生产判据及频道表，不运行任何目标判定。"""
    parser = argparse.ArgumentParser(description="生成直接读取材料格的四象限五层半形判据")
    parser.add_argument("--channel-base", type=int, default=1_016_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_material_half(args.channel_base)
    encoded = circuit.encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"材料半形判据已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
