"""四象限双半形起点：选切向，两遍调用同一角程序，保留六槽上界。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Literal, constant
from .corner_program import CornerProgram, half_body
from .decoder_circuit import decode
from .half_circuit import column_admissible, half_stable
from .program_controller import execute_program
from .synthesis.physics import Rules


def build_startpoint(channel_base: int = 1_061_000) -> tuple[Circuit, dict]:
    """生成目标到双半形制造流；未覆盖的尾部返回unknown，不判不可制作。"""
    reserve = 32_768
    if not 1 <= channel_base < (1 << 24) - reserve:
        raise ValueError("频道基址需要保留后续32768个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    one = circuit.add("ConstantSignal", config=constant(1))
    null = circuit.add("ConstantSignal", config=constant(None))
    decoded = decode(circuit, target, one, Rules(4))
    program = CornerProgram(circuit)
    admissible = program.and_(*(column_admissible(circuit, tuple(row[q] for row in decoded.cells))
                                for q in range(4)))
    uncolored = program.or_(*(program.and_(cell.crystal, circuit.add(
        "LogicGateCompare", cell.color, Literal("color:u"), config="AQ=="))
        for row in decoded.cells for cell in row))
    partitions = []
    for start in range(2):
        halves = [half_stable(circuit, tuple(tuple(row[(start + side + q) % 4] for q in (0, 1))
                                            for row in decoded.cells)) for side in (0, 2)]
        partitions.append(program.and_(*halves))
    available = program.or_(*partitions)
    legal = program.and_(decoded.valid, program.not_(uncolored))
    solved = program.and_(legal, admissible, available)
    unsolvable = program.and_(legal, program.not_(admissible))
    unknown = program.and_(decoded.valid, program.or_(uncolored,
                          program.and_(admissible, program.not_(available))))
    # 0号切向优先；格片段始终在q0，因此材料路由不改变它的颜色或标签。
    shifted = program.not_(partitions[0])
    original = tuple(tuple(program.original(row[q]) for row in decoded.cells) for q in range(4))
    aligned = tuple(tuple(program.choose(shifted, original[(q + 1) % 4][z], original[q][z])
                          for z in range(5)) for q in range(4))
    front_present = program.or_(*(cell.occupied for column in aligned[:2] for cell in column))
    flipped = program.not_(front_present)
    second_pass = circuit.add("LogicGateIf", Literal(0), Literal(1))
    take_back = circuit.add("LogicGateXOr", flipped, second_pass)
    columns = tuple(tuple(program.choose(take_back, aligned[q + 2][z], aligned[q][z])
                          for z in range(5)) for q in (0, 1))
    present = program.or_(*half_body(program, columns))
    program.emit(present, 4, 0)
    first_pass = program.not_(second_pass)
    program.rotate(0, 2, first_pass, destination=5)
    with_second = program.and_(second_pass, present)
    program.join(0, 5, 0, with_second)
    program.rotate(0, 2, with_second)
    program.rotate(5, 2, program.and_(second_pass, program.not_(present)), destination=0)
    program.rotate(0, 2, program.and_(second_pass, flipped))
    program.rotate(0, 1, program.and_(second_pass, shifted))
    instructions = tuple(program.instructions)
    control = execute_program(circuit, target, enable, decoded.valid, solved, unsolvable, unknown,
                              instructions, one, null, second_pass)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("双半形起点构造超出其保留频道范围")
    return circuit, {
        "component": "automatic_two_half_startpoint", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        **control, "gate_platforms": len(circuit.gates), "program_passes": 2,
        "reserved_channels": [channel_base, channel_base + reserve - 1],
        "statuses": {"0": "程序运行中", "1": "双半形制造成功且与完整目标相同",
                     "2": "违反全图列A必要条件，不可制作", "3": "需要S/顶针尾部搜索，或cu供料未界定",
                     "4": "内部程序或回放失配，不构成不可制作结论", "null": "无效输入、停机或窗口之外"},
        "input_protocol": "target全程保持；enable=0完成timing规定复位后启用。首周期只初始化。",
        "output_protocol": "每个window上升后等48信号tick，窗口内读一次；sample为真先收instruction，再处理同窗done/status。无背压。",
        "termination": f"初始化一周期，再至多两遍各{len(instructions)}行，共{2 * len(instructions) + 1}周期；不在直接构造范围的有效目标首窗口返回。",
        "resource_bound": "一份半形角程序，两遍数据路由，一个遍次位；槽5保存首半形，第二半形仅使用槽0～4。",
        "scope": "精确识别两个互补稳定A半形的拼接；覆盖有界尾部定理的全部起点，但不包含S/顶针搜索，不能作为完整四象限TMAM。",
        "proof": "4q5l/two-half-startpoint.md；half-row-stability.md；automatic-half.md。",
        "verification": "静态组合DAG与逐端口占地编译；未执行目标、指令、测试、反馈模拟或游戏",
    }


def main() -> int:
    """编译生产蓝图，不运行目标或制造流程。"""
    parser = argparse.ArgumentParser(description="生成共用一份角程序的四象限双半形起点电路")
    parser.add_argument("--channel-base", type=int, default=1_061_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_startpoint(args.channel_base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"双半形起点已编译：{args.output}；{report['gate_platforms']} 块平台，{report['program_rom_rows']} 行共用程序。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
