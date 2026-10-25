"""四象限双半形起点：选切向，两遍调用同一角程序，保留六槽上界。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Literal, constant
from .corner_program import CornerProgram, half_body
from .decoder_circuit import DecodedCell, decode
from .half_circuit import MaterialCell, column_admissible, half_stable
from .prefix_search import PrefixSearch
from .program_controller import execute_program
from .synthesis.physics import Rules


def build_startpoint(channel_base: int = 1_061_000, *, search_prefixes: bool = False) -> tuple[Circuit, dict]:
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
    finder = None
    rows: tuple[tuple[DecodedCell | MaterialCell, ...], ...] = decoded.cells
    if search_prefixes:
        original = tuple(tuple(program.original(row[q]) for row in decoded.cells) for q in range(4))
        finder = PrefixSearch(program, original)
        rows = tuple(tuple(MaterialCell(finder.columns[q][z].occupied, finder.columns[q][z].pin,
                                        finder.columns[q][z].crystal) for q in range(4)) for z in range(5))
    partitions = []
    for start in range(2):
        halves = [half_stable(circuit, tuple(tuple(row[(start + side + q) % 4] for q in (0, 1))
                                            for row in rows)) for side in (0, 2)]
        partitions.append(program.and_(*halves))
    available = program.or_(*partitions)
    legal = program.and_(decoded.valid, program.not_(uncolored))
    solved = program.and_(legal, admissible, available)
    unsolvable = program.and_(legal, program.not_(admissible))
    unknown = program.and_(decoded.valid, program.or_(uncolored,
                          program.and_(admissible, program.not_(available))))
    extra_state = ()
    if finder is not None:
        has_crystal = program.or_(*(cell.crystal for row in decoded.cells for cell in row))
        extra_state = finder.finish(available, program.and_(legal, admissible))
        solved = finder.found
        exhausted = program.and_(legal, admissible, finder.exhausted)
        unsolvable = program.or_(unsolvable, program.and_(exhausted, program.not_(has_crystal)))
        unknown = program.and_(decoded.valid, program.or_(uncolored, program.and_(exhausted, has_crystal)))
    # 0号切向优先；格片段始终在q0，因此材料路由不改变它的颜色或标签。
    shifted = program.not_(partitions[0])
    if finder is None:
        original = tuple(tuple(program.original(row[q]) for row in decoded.cells) for q in range(4))
    source = finder.columns if finder is not None else original
    aligned = tuple(tuple(program.choose(shifted, source[(q + 1) % 4][z], source[q][z])
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
    if finder is not None:
        empty = program.cell("--")
        for z in range(5):
            active = program.and_(second_pass, program.or_(*(finder.delta[q][z] for q in range(4))))
            row = tuple(program.choose(finder.delta[q][z], original[q][z], empty) for q in range(4))
            program.emit(active, 14, destination=1, base=program.layer(row))
            program.emit(active, 7, 0, 1)
    instructions = tuple(program.instructions)
    control = execute_program(circuit, target, enable, decoded.valid, solved, unsolvable, unknown,
                              instructions, one, null, second_pass, extra_state,
                              finder.bits if finder is not None else ())
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("双半形起点构造超出其保留频道范围")
    report = {
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
    if finder is not None:
        report.update({
            "component": "automatic_startpoint_and_s_tail",
            "s_prefix_height_choices": 6 ** 4, "s_prefix_choices_with_crystals": 1080, "search_state_bits": 14,
            "s_prefix_domain": "每列只保留最高C以上的不同非空格前缀，另含无C列的空前缀；跳过空层重复。",
            "input_protocol": "target全程保持；enable=0完成timing规定复位后启用。搜索命中后冻结前态，下一完整周期才发令。",
            "resource_bound": f"一份{len(instructions)}行制造ROM、六物品槽、十二位前缀高度及found/exhausted；不存全量候选。",
            "termination": f"至多1296次前缀判据及两遍各{len(instructions)}行，加初始化共至多{1297 + 2 * len(instructions)}周期；失败不判含C目标不可制作。",
            "scope": "完整覆盖A→S，含C未命中仍需顶针尾部。无C目标在本部件有完整可制作性判据。",
            "proof": "4q5l/s-tail-circuit.md；two-half-startpoint.md；stacking-proof.md。",
        })
        report["statuses"]["1"] = "起点与S追加制造成功，已与完整目标比较"
        report["statuses"]["2"] = "违反列A，或无C目标穷尽全部S起点后不可制作"
        report["statuses"]["3"] = "需要顶针尾部搜索，或cu供料未界定"
    return circuit, report


def main() -> int:
    """编译生产蓝图，不运行目标或制造流程。"""
    parser = argparse.ArgumentParser(description="生成共用一份角程序的四象限双半形起点电路")
    parser.add_argument("--channel-base", type=int)
    parser.add_argument("--s-tail", action="store_true", help="先完整遍历S前缀，再制造起点及追加层")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    channel_base = args.channel_base if args.channel_base is not None else (1_094_000 if args.s_tail else 1_061_000)
    circuit, report = build_startpoint(channel_base, search_prefixes=args.s_tail)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"双半形起点已编译：{args.output}；{report['gate_platforms']} 块平台，{report['program_rom_rows']} 行共用程序。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
