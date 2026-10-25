"""四象限五层完整尾部的五帧DFS：共用制造ROM，成功后才重放并发布指令。"""

import argparse
import json
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .circuit import Circuit, Gate, Literal, Ref
from .clocked_state import ClockedState
from .corner_program import CornerProgram, half_body
from .decoder_circuit import decode
from .half_circuit import MaterialCell, column_admissible, half_stable
from .pin_source_circuit import pin_source
from .prefix_search import PrefixSearch
from .program_controller import RECORD_FIELDS, _rom
from .recipe_processor import _read, recipe_step
from .sequential_circuit import timing_contract
from .synthesis.physics import Rules
from .tag_palette import TagPalette, TaggedGrid, same_grid


class Phase(IntEnum):
    """一份共享控制状态；挂起父帧只保存目标和游标。"""

    ENTRY = 0
    PREFIX = 1
    PREFIX_NEXT = 2
    LEAF = 3
    SOURCE = 4
    LEAF_CHECK = 5
    SOURCE_NEXT = 6
    RETURN = 7
    FAIL = 8
    PARENT_CHECK = 9
    DONE = 10
    REPLAY_LEAF = 11
    REPLAY_LEAF_CHECK = 12
    REPLAY_PARENT = 13
    REPLAY_PARENT_CHECK = 14


@dataclass(frozen=True)
class Frame:
    """固定标签目标、S前缀、四列来源槽及第五层；没有全量候选存储。"""

    goal: tuple[tuple[Ref, ...], ...]
    prefix: tuple[Ref, ...]
    slots: tuple[tuple[Ref, ...], ...]
    top: tuple[tuple[Ref, ...], ...]
    pin_search: Ref


def _equals(program: CornerProgram, bits: tuple[Ref, ...], value: int) -> Ref:
    return program.and_(*(bit if value & (1 << k) else program.not_(bit) for k, bit in enumerate(bits)))


def _value(program: CornerProgram, bits: tuple[Ref, ...], limit: int) -> Ref:
    circuit = program.circuit
    branches = tuple(circuit.add("LogicGateIf", Literal(value), _equals(program, bits, value))
                     for value in range(limit))
    circuit.aliases.append(branches)
    return branches[0]


def _increment(program: CornerProgram, bits: tuple[Ref, ...], advance: Ref, modulus: int) -> tuple[tuple[Ref, ...], Ref]:
    """布尔二进制加一，非二幂模数在末码归零；返回传到下一位的进位。"""
    wrap = program.and_(advance, _equals(program, bits, modulus - 1))
    values = tuple(program.circuit.add("LogicGateXOr", bit, program.and_(advance, *bits[:k]))
                   for k, bit in enumerate(bits))
    if modulus != 1 << len(bits):
        values = tuple(program.pick(wrap, program.zero, value) for value in values)
    return values, wrap


def build_solver(channel_base: int = 1_211_000) -> tuple[Circuit, dict]:
    """静态编译完整四象限控制；不运行搜索、目标、制造或反馈模拟。"""
    reserve = 65_536
    if not 1 <= channel_base < (1 << 24) - reserve:
        raise ValueError("频道基址需要保留后续65536个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    target = circuit.add("ControlledSignalReceiver", Literal(channel_base))
    enable = circuit.add("ControlledSignalReceiver", Literal(channel_base + 1))
    program = CornerProgram(circuit)
    bank = ClockedState(program)
    decoded = decode(circuit, target, program.one, Rules(4))
    palette = TagPalette(program, decoded)
    root_tags = tuple(tuple(program.pick(decoded.cells[z][q].occupied, program.const(4 + 4 * z + q), program.zero)
                            for z in range(5)) for q in range(4))
    frames = tuple(Frame(
        tuple(tuple(bank.add(root_tags[q][z] if i == 0 else 0) for z in range(5)) for q in range(4)),
        tuple(bank.add() for _ in range(12)),
        tuple(tuple(bank.add() for _ in range(5)) for _ in range(4)),
        tuple(tuple(bank.add() for _ in range(2)) for _ in range(4)), bank.add()) for i in range(5))
    phase = bank.add(int(Phase.ENTRY))
    depth = bank.add()
    leaf_depth = bank.add()
    result = bank.add(None)
    status = bank.add()
    modes = {value: circuit.add("LogicGateCompare", phase, Literal(int(value)), config="AQ==") for value in Phase}
    levels = [circuit.add("LogicGateCompare", depth, Literal(i), config="AQ==") for i in range(5)]
    root = levels[0]

    def active(values: tuple[Ref, ...]) -> Ref:
        return _read(circuit, values, levels)

    tags = tuple(tuple(active(tuple(frame.goal[q][z] for frame in frames)) for z in range(5)) for q in range(4))
    prefix = tuple(active(tuple(frame.prefix[k] for frame in frames)) for k in range(12))
    slots = tuple(tuple(active(tuple(frame.slots[q][k] for frame in frames)) for k in range(5)) for q in range(4))
    top = tuple(tuple(active(tuple(frame.top[q][k] for frame in frames)) for k in range(2)) for q in range(4))
    pin_search = active(tuple(frame.pin_search for frame in frames))
    grid = palette.grid(tags)
    original = grid.columns
    nonempty = program.or_(*(cell.occupied for column in original for cell in column))
    geometry = tuple(tuple(MaterialCell(cell.occupied, cell.pin, cell.crystal) for cell in column) for column in original)
    admissible = program.and_(*(column_admissible(circuit, column) for column in geometry))
    uncolored = program.or_(*(program.and_(cell.crystal, circuit.add(
        "LogicGateCompare", cell.color, Literal("color:u"), config="AQ==")) for row in decoded.cells for cell in row))
    in_scope = program.and_(decoded.valid, program.not_(uncolored))
    has_crystal = program.or_(*(cell.crystal for column in original for cell in column))
    ground_crystal = program.or_(*(column[0].crystal for column in original))
    pin_allowed = program.and_(has_crystal, program.not_(ground_crystal), program.not_(levels[4]))

    finder = PrefixSearch(program, original)
    for read, source in zip(finder.bits, prefix):
        circuit.gates[read.node] = Gate("LogicGateIf", (source, Literal(1)))
    # 此处found/exhausted保持常0；复用finish的单步游标计算，由帧控制是否写回。
    prefix_step = finder.finish(program.zero, program.one)
    next_prefix = tuple(state.source for state in prefix_step[:12])
    last_prefix = prefix_step[-1].source
    pushed = TaggedGrid(finder.columns, grid.valid)
    partitions = []
    for start in range(2):
        halves = [half_stable(circuit, tuple(tuple(MaterialCell(
            finder.columns[(start + side + q) % 4][z].occupied,
            finder.columns[(start + side + q) % 4][z].pin,
            finder.columns[(start + side + q) % 4][z].crystal) for q in (0, 1)) for z in range(5))) for side in (0, 2)]
        partitions.append(program.and_(*halves))
    available = program.or_(*partitions)
    materials = tuple(tuple(program.pick(cell.occupied, program.pick(cell.pin, program.const(2),
                                       program.pick(cell.crystal, program.const(3), program.one)), program.zero)
                            for cell in column) for column in finder.columns)
    pushed_tags = tuple(tuple(program.pick(finder.delta[q][z], program.zero, tags[q][z])
                              for z in range(5)) for q in range(4))
    candidate = pin_source(program, materials, pushed_tags,
                           tuple(_value(program, bits, 20) for bits in slots),
                           tuple(_value(program, bits, 4) for bits in top), program.one)

    items = tuple(bank.add(None) for _ in range(6))
    ack, item_status = bank.add(), bank.add()
    second_pass = bank.add()
    shifted = program.not_(partitions[0])
    aligned = tuple(tuple(program.choose(shifted, finder.columns[(q + 1) % 4][z], finder.columns[q][z])
                          for z in range(5)) for q in range(4))
    flipped = program.not_(program.or_(*(cell.occupied for column in aligned[:2] for cell in column)))
    take_back = circuit.add("LogicGateXOr", flipped, second_pass)
    columns = tuple(tuple(program.choose(take_back, aligned[q + 2][z], aligned[q][z]) for z in range(5)) for q in (0, 1))
    present = program.or_(*half_body(program, columns))
    program.emit(present, 4, 0)
    program.rotate(0, 2, program.not_(second_pass), destination=5)
    with_second = program.and_(second_pass, present)
    program.join(0, 5, 0, with_second)
    program.rotate(0, 2, with_second)
    program.rotate(5, 2, program.and_(second_pass, program.not_(present)), destination=0)
    program.rotate(0, 2, program.and_(second_pass, flipped))
    program.rotate(0, 1, program.and_(second_pass, shifted))
    empty = program.cell("--")
    delta_present = tuple(program.or_(*(finder.delta[q][z] for q in range(4))) for z in range(5))
    layers = tuple(program.layer(tuple(program.choose(finder.delta[q][z], original[q][z], empty)
                                      for q in range(4))) for z in range(5))
    for exists, layer in zip(delta_present, layers):
        selected = program.and_(second_pass, exists)
        program.emit(selected, 14, destination=1, base=layer)
        program.emit(selected, 7, 0, 1)
    macro_last = len(program.instructions) - 1
    parent_start = len(program.instructions)
    program.emit(program.one, 6, 0)
    for exists, layer in zip(delta_present, layers):
        program.emit(exists, 14, destination=1, base=layer)
        program.emit(exists, 7, 0, 1)
    instructions = tuple(program.instructions)
    width = (len(instructions) - 1).bit_length()
    pc = tuple(bank.add() for _ in range(width))
    packet, selected, last, jumps = _rom(circuit, instructions, pc, program.one, program.const(None))
    cpu_running = program.or_(modes[Phase.LEAF], modes[Phase.REPLAY_LEAF], modes[Phase.REPLAY_PARENT])
    replay = program.or_(modes[Phase.REPLAY_LEAF], modes[Phase.REPLAY_PARENT])
    packet["enable"] = program.and_(enable, cpu_running, selected)
    packet["request"] = program.not_(ack)
    next_items = recipe_step(circuit, items, ack, item_status, packet)
    error = program.and_(packet["enable"], circuit.add("LogicGateCompare", next_items[7], Literal(2), config="AQ=="))
    advance = program.and_(cpu_running, program.not_(error))
    next_pc = [circuit.add("LogicGateXOr", bit, program.and_(advance, *pc[:k])) for k, bit in enumerate(pc)]
    if jumps:
        jump_selected = program.or_(*(event for event, _ in jumps))
        take_jump = program.and_(advance, jump_selected)
        next_pc = [program.pick(take_jump, program.or_(*(event for event, destination in jumps if destination & (1 << k))), value)
                   for k, value in enumerate(next_pc)]
    end_macro = program.and_(advance, _equals(program, pc, macro_last))
    repeat = program.and_(end_macro, program.not_(second_pass))
    next_pc = [program.pick(repeat, program.zero, bit) for bit in next_pc]
    macro_done = program.and_(end_macro, second_pass)
    parent_done = program.and_(advance, last)
    for read, source in zip((*items, ack, item_status), next_items):
        bank.put(read, source)
    for read, source in zip(pc, next_pc):
        bank.put(read, source)
    bank.put(second_pass, program.or_(second_pass, repeat))

    cpu_matches = same_grid(program, decode(circuit, items[0], program.one, Rules(4)), grid)
    pinned = circuit.add("VirtualPinPusher", result)
    pin_matches = same_grid(program, decode(circuit, pinned, program.one, Rules(4)), pushed)
    completed = pinned
    for exists, layer in zip(delta_present, layers):
        stacked = circuit.add("VirtualStacker", completed, layer)
        completed = program.pick(exists, stacked, completed)
    completed_matches = same_grid(program, decode(circuit, completed, program.one, Rules(4)), grid)

    entry = modes[Phase.ENTRY]
    valid_goal = program.and_(grid.valid, nonempty)
    enter = program.and_(entry, in_scope, valid_goal, admissible)
    entry_fail = program.and_(entry, in_scope, valid_goal, program.not_(admissible))
    bad_goal = program.and_(entry, in_scope, program.not_(valid_goal))
    start_leaf = program.and_(modes[Phase.PREFIX], program.not_(pin_search), finder.appendable, available)
    start_source = program.and_(modes[Phase.PREFIX], pin_search, finder.appendable, pin_allowed)
    skip_prefix = program.and_(modes[Phase.PREFIX], program.or_(program.not_(finder.appendable),
                              program.and_(program.not_(pin_search), program.not_(available)),
                              program.and_(pin_search, program.not_(pin_allowed))))
    move_prefix = program.and_(modes[Phase.PREFIX_NEXT], program.not_(last_prefix))
    prefix_scan_finished = program.and_(modes[Phase.PREFIX_NEXT], last_prefix)
    begin_pin_search = program.and_(prefix_scan_finished, program.not_(pin_search), pin_allowed)
    prefixes_finished = program.and_(prefix_scan_finished, program.or_(pin_search, program.not_(pin_allowed)))
    descend = program.and_(modes[Phase.SOURCE], candidate.valid)
    skip_source = program.and_(modes[Phase.SOURCE], program.not_(candidate.valid))
    leaf_checked = program.and_(modes[Phase.LEAF_CHECK], cpu_matches)
    search_return = modes[Phase.RETURN]
    search_pop = program.and_(search_return, program.not_(root))
    root_solved = program.and_(search_return, root)
    fail_pop = program.and_(modes[Phase.FAIL], program.not_(root))
    root_failed = program.and_(modes[Phase.FAIL], root)
    parent_checked = program.and_(modes[Phase.PARENT_CHECK], pin_matches, completed_matches)
    parent_reject = program.and_(modes[Phase.PARENT_CHECK], program.not_(pin_matches))
    replay_check = program.or_(modes[Phase.REPLAY_LEAF_CHECK], modes[Phase.REPLAY_PARENT_CHECK])
    original_matches = circuit.add("LogicGateCompare", items[0], target, config="AQ==")
    replay_ok = program.and_(replay_check, cpu_matches, program.or_(program.not_(root), original_matches))
    replay_up = program.and_(replay_ok, program.not_(root))
    replay_finished = program.and_(replay_ok, root)
    outside = program.and_(entry, root, decoded.valid, uncolored)
    invalid = program.and_(entry, root, program.not_(decoded.valid))
    internal = program.or_(error, bad_goal,
        program.and_(modes[Phase.LEAF_CHECK], program.not_(cpu_matches)),
        program.and_(modes[Phase.PARENT_CHECK], pin_matches, program.not_(completed_matches)),
        program.and_(replay_check, program.not_(program.and_(cpu_matches,
                     program.or_(program.not_(root), original_matches)))))

    # 最快位是四个顶格，随后是四列的二十进制槽；到末码才换S前缀。
    carry = modes[Phase.SOURCE_NEXT]
    next_top = []
    for bits in top:
        values, carry = _increment(program, bits, carry, 4)
        next_top.append(values)
    next_slots = []
    for bits in slots:
        values, carry = _increment(program, bits, carry, 20)
        next_slots.append(values)
    sources_finished = carry
    depth_choices: list[tuple[Ref, Ref | int | None]] = []
    for i, frame in enumerate(frames):
        selected_frame = levels[i]
        initialize = program.and_(program.or_(enter, begin_pin_search), selected_frame)
        bank.put(frame.pin_search, 0, program.and_(enter, selected_frame))
        bank.put(frame.pin_search, 1, program.and_(begin_pin_search, selected_frame))
        next_s = program.and_(move_prefix, selected_frame)
        reset_source = program.and_(start_source, selected_frame)
        next_d = program.and_(modes[Phase.SOURCE_NEXT], selected_frame)
        for k, read in enumerate(frame.prefix):
            bank.put(read, finder.initial[k], initialize)
            bank.put(read, next_prefix[k], next_s)
        for old, new in zip((*frame.top, *frame.slots), (*next_top, *next_slots)):
            for read, value in zip(old, new):
                bank.put(read, value, next_d)
                bank.put(read, 0, reset_source)
        if i < 4:
            pushing = program.and_(descend, selected_frame)
            for q in range(4):
                for z in range(5):
                    bank.put(frames[i + 1].goal[q][z], candidate.tags[q][z], pushing)
            depth_choices.append((pushing, i + 1))
        if i:
            popping = program.and_(selected_frame, program.or_(search_pop, fail_pop, replay_up))
            depth_choices.append((popping, i - 1))
    depth_choices.append((root_solved, leaf_depth))
    bank.put_exclusive(depth, tuple(depth_choices))
    bank.put(leaf_depth, depth, leaf_checked)
    bank.put(result, items[0], leaf_checked)
    bank.put(result, completed, parent_checked)

    # 只有重放成功路径时才发布；搜索期间的六槽结果只是信号证书。
    accepted = program.and_(packet["enable"], program.not_(error), replay)
    record = tuple(bank.add(None) for _ in RECORD_FIELDS)
    record_valid = bank.add()
    for read, name in zip(record, RECORD_FIELDS):
        bank.put(read, packet[name])
    bank.put(record_valid, accepted)
    reset_cpu = program.or_(start_leaf, root_solved)
    for read in items:
        bank.put(read, None, reset_cpu)
    bank.put(ack, 0, reset_cpu)
    bank.put(item_status, 0, reset_cpu)
    bank.put(second_pass, 0, reset_cpu)
    for k, read in enumerate(pc):
        bank.put(read, 0, reset_cpu)
        bank.put(read, int(bool(parent_start & (1 << k))), replay_up)

    transitions = (
        (enter, Phase.PREFIX), (entry_fail, Phase.FAIL),
        (start_leaf, Phase.LEAF), (start_source, Phase.SOURCE), (skip_prefix, Phase.PREFIX_NEXT),
        (move_prefix, Phase.PREFIX), (begin_pin_search, Phase.PREFIX), (prefixes_finished, Phase.FAIL),
        (descend, Phase.ENTRY), (skip_source, Phase.SOURCE_NEXT),
        (program.and_(modes[Phase.SOURCE_NEXT], program.not_(sources_finished)), Phase.SOURCE),
        (sources_finished, Phase.PREFIX_NEXT),
        (program.and_(modes[Phase.LEAF], macro_done), Phase.LEAF_CHECK),
        (leaf_checked, Phase.RETURN), (search_pop, Phase.PARENT_CHECK), (root_solved, Phase.REPLAY_LEAF),
        (fail_pop, Phase.SOURCE_NEXT), (parent_reject, Phase.SOURCE_NEXT), (parent_checked, Phase.RETURN),
        (program.and_(modes[Phase.REPLAY_LEAF], macro_done), Phase.REPLAY_LEAF_CHECK),
        (program.and_(modes[Phase.REPLAY_PARENT], parent_done), Phase.REPLAY_PARENT_CHECK),
        (replay_up, Phase.REPLAY_PARENT),
        (program.or_(root_failed, replay_finished, outside, invalid, internal), Phase.DONE),
    )
    bank.put_exclusive(phase, tuple((condition, int(destination)) for condition, destination in transitions))
    bank.put(status, 2, root_failed)
    bank.put(status, 1, replay_finished)
    bank.put(status, 3, outside)
    bank.put(status, 4, internal)
    timing, state_report = bank.close(enable)
    window = program.and_(timing.phases[3], enable)
    sample = program.and_(window, record_valid)
    done = program.and_(window, modes[Phase.DONE], decoded.valid)
    instruction_outputs = tuple(circuit.add("LogicGateIf", value, sample) for value in record)
    status_output = circuit.add("LogicGateIf", status, program.and_(window, decoded.valid))
    output = circuit.add("LogicGateIf", items[0], program.and_(done,
        circuit.add("LogicGateCompare", status, Literal(1), config="AQ==")))
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("完整四象限控制超出其保留频道范围")
    return circuit, {
        "component": "complete_four_quadrant_tail_solver", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": {"window": channels[window], "sample": channels[sample], "done": channels[done],
                    "status": channels[status_output], "result": channels[output],
                    "instruction": {name: channels[value] for name, value in zip(RECORD_FIELDS, instruction_outputs)}},
        "gate_platforms": len(circuit.gates), "reserved_channels": [channel_base, channel_base + reserve - 1],
        **state_report, "timing": timing_contract(timing),
        "search_frames": 5, "item_registers": 6, "program_rom_rows": len(instructions),
        "leaf_program_rows": macro_last + 1, "parent_tail_rows": len(instructions) - parent_start,
        "statuses": {"0": "搜索或成功路径重放中", "1": "已输出完整制造流程，原生回放等于原目标",
                     "2": "穷尽全部有界尾部后不可制作", "3": "cu晶体供料未界定", "4": "内部状态或回放失配，不能判不可制作",
                     "null": "输入无效、关闭或窗口之外"},
        "input_protocol": "target全程保持；enable=0持续timing规定的完整复位时间，再启用并保持到done。忽略启动的不完整阶段3。",
        "output_protocol": "每个完整window上升后等96信号tick，窗口内读一次；sample为真收instruction，随后处理done/status。搜索期间不发布指令，无背压。",
        "resource_bound": "五帧各20目标ID、12前缀位、20来源槽位、8顶盖位和1遍次位；共享一份制造ROM及六槽。成功参数留帧，重放一次，不保存数百条指令。",
        "termination": "最低C每次下降至少一层，递归至多四边；每帧至多1296个S前缀，每前缀至多20^4×4^4个来源地址。完整穷尽才返回2。",
        "scope": "在既定基础单层及合法晶体供料模型内完整四象限五层尾部搜索；规模和最坏等待仍需压缩，未通过游戏实用性能验收。",
        "proof": "4q5l/full-tail-circuit.md；tail-solver.md；pin-patterns.md；s-tail-circuit.md；clocked-control.md。",
        "verification": "仅静态源代码推导、DAG、端口和实际占地生产编译；未执行目标、搜索、指令、反馈模拟、测试或游戏",
    }


def main() -> int:
    """仅编译生产蓝图及接口，不执行求解。"""
    parser = argparse.ArgumentParser(description="生成五帧递归及成功路径重放的完整四象限尾部电路")
    parser.add_argument("--channel-base", type=int, default=1_211_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_solver(args.channel_base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完整四象限尾部电路已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
