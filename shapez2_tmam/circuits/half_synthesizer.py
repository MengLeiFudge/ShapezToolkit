"""标准四象限半形的自动制造程序：判据、指令ROM、六槽回放和目标核对。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Literal, constant
from .corner_program import half_program
from .decoder_circuit import decode
from .half_circuit import classify_half
from .program_controller import execute_program
from ..synthesis.physics import Rules


def build_half_synthesizer(channel_base: int = 1_028_000) -> tuple[Circuit, dict]:
    """闭环前静态测量完整组合步，再让PC和物品状态共用同一时钟。"""
    reserve = 32_768
    if not 1 <= channel_base < (1 << 24) - reserve:
        raise ValueError("频道基址需要保留后续32768个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    one = circuit.add("ConstantSignal", config=constant(1))
    null = circuit.add("ConstantSignal", config=constant(None))
    decoded = decode(circuit, target, one, Rules(4))
    flags = classify_half(circuit, target, decoded)
    program = half_program(circuit, decoded)
    control = execute_program(circuit, target, enable, decoded.valid, flags.solved, flags.unsolvable,
                              flags.unknown, program, one, null)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("自动半形构造超出其保留频道范围")
    return circuit, {
        "component": "automatic_standard_half_synthesizer", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": control["outputs"],
        "statuses": {"0": "程序运行中", "1": "可制作，指令流已回放并与完整目标相同",
                     "2": "标准半形违反完整局部判据，不可制作", "3": "非标准半形或cu供料未界定",
                     "4": "内部程序或回放失配，不构成不可制作结论", "null": "无效输入、停机或窗口之外"},
        "gate_platforms": len(circuit.gates),
        "program_rom_rows": control["program_rom_rows"], "program_counter_bits": control["program_counter_bits"],
        "item_registers": 6, "step_max_gate_depth": control["step_max_gate_depth"],
        "initial_max_gate_depth": control["initial_max_gate_depth"],
        "reserved_channels": [channel_base, channel_base + reserve - 1], "timing": control["timing"],
        "input_protocol": "target保持不变，enable=0完成完整复位后改为1。首周期只初始化；读取新目标前重新复位。",
        "output_protocol": "每个window上升后等48信号tick，在窗口内只读一次。sample为真接收本条指令，再处理同窗done/status；条件假指令行不发布sample。",
        "termination": f"通过判据的目标：初始化一周期后遍历{len(program)}条条件ROM行，最多{len(program) + 1}周期；其他有效目标首窗口给范围或否定结论。",
        "resource_bound": "六物品槽、二进制PC及确认/结束状态、一份包快照；ROM共用地址前缀和相同字段。不存完整半形目录。",
        "scope": "q0/q1标准半形的自动判据和完整制造流；尚不是任意全图四象限TMAM，其他朝向须由上层旋转。",
        "proof": "4q5l/automatic-half.md；角构造依据corner-synthesis.md，消费式回放依据recipe-registers.md。",
        "verification": "组合步DAG深度、端口与实际占地静态编译；未执行目标、指令循环、测试、反馈模拟或游戏",
    }


def main() -> int:
    """编译自动半形生产蓝图，不执行任何目标求解或程序回放。"""
    parser = argparse.ArgumentParser(description="生成标准四象限半形的自动制造流电路")
    parser.add_argument("--channel-base", type=int, default=1_028_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_half_synthesizer(args.channel_base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"自动半形构造已编译：{args.output}；{report['gate_platforms']} 块平台，{report['program_rom_rows']} 条ROM行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
