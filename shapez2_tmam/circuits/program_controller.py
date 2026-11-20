"""有限制造程序的共用时序控制：条件ROM、六槽回放、快照及可选双遍调用。"""

from collections.abc import Callable
from dataclasses import dataclass, replace

from .circuit import Circuit, Gate, Literal, Ref, constant
from .corner_program import CornerProgram, Instruction
from .half_circuit import _combine
from .recipe_processor import PACKET_FIELDS, recipe_step
from .sequential_circuit import clock, latch, select, timing_contract


RECORD_FIELDS = PACKET_FIELDS[:-1]


def active_rows(program: CornerProgram, boundaries: tuple[int, ...]) -> tuple[tuple[Instruction, ...], tuple[Ref | None, ...]]:
    """把嵌套前向分支合入行条件；保留可达调用边界，供直接有效行后继使用。"""
    instructions = tuple(program.instructions)
    protected = {*boundaries, len(instructions) - 1}
    if any(not 0 <= index < len(instructions) or instructions[index].branch is not None for index in protected):
        raise ValueError("制造程序的调用边界必须指向普通指令行")
    scopes: list[tuple[int, Ref]] = []
    normalized = []
    visits: list[Ref | None] = []
    for index, instruction in enumerate(instructions):
        while scopes and index == scopes[-1][0]:
            scopes.pop()
        outer = program.and_(*(guard for _, guard in scopes))
        if instruction.branch is not None:
            end = instruction.skip_to
            if end is None or not index < end < len(instructions) or scopes and end > scopes[-1][0]:
                raise ValueError("有效行后继需要正确嵌套的前向宏跳转")
            scopes.append((end, instruction.branch))
            normalized.append(instruction)
            visits.append(None)
        else:
            if instruction.skip_to is not None:
                raise ValueError("有效行后继应读取尚未附加普通行跳转的制造程序")
            condition = program.and_(outer, instruction.condition)
            normalized.append(replace(instruction, condition=condition))
            visits.append(outer if index in protected else condition)
    return tuple(normalized), tuple(visits)


def _rom_fields(circuit: Circuit, program: tuple[Instruction, ...], addresses: list[Ref],
                zero: Ref, null: Ref) -> tuple[dict[str, Ref], list[Ref]]:
    """按地址共用同值字段；普通行是否执行另由condition决定。"""
    chosen = [circuit.add("LogicGateAnd", address, instruction.condition) if instruction.branch is None else zero
              for address, instruction in zip(addresses, program)]
    fields = {}
    for name in ("opcode", "a", "b", "destination", "base", "color"):
        groups: dict[int | Ref | Literal, list[Ref]] = {}
        for instruction, enabled in zip(program, addresses):
            if instruction.branch is not None:
                continue
            value = getattr(instruction, name)
            if isinstance(value, Literal) and value.value is None:
                continue
            groups.setdefault(value, []).append(enabled)
        branches = []
        for value, conditions in groups.items():
            enabled = _combine(circuit, "LogicGateOr", conditions)
            source = Literal(value) if isinstance(value, int) else value
            branches.append(circuit.add("LogicGateIf", source, enabled))
        if branches:
            circuit.aliases.append(tuple(branches))
            fields[name] = branches[0]
        else:
            fields[name] = null
    return fields, chosen


def active_rom(program: CornerProgram, instructions: tuple[Instruction, ...], pc: Ref,
               visits: tuple[Ref | None, ...]) -> tuple[dict[str, Ref], Ref, Ref, Ref]:
    """整数PC及平衡优先树；下一地址为严格大于当前地址的首个可访问行。"""
    if not instructions or len(visits) != len(instructions):
        raise ValueError("有效行标志必须与非空制造ROM逐行对应")
    circuit = program.circuit
    addresses = [circuit.add("LogicGateCompare", pc, Literal(index), config="AQ==") for index in range(len(instructions))]
    fields, chosen = _rom_fields(circuit, instructions, addresses, program.zero, program.const(None))
    eligible = [(program.and_(visit, circuit.add("LogicGateCompare", pc, Literal(index), config="BA==")), Literal(index))
                for index, visit in enumerate(visits) if visit is not None]

    def first(lo: int, hi: int) -> tuple[Ref, Ref | Literal]:
        """子树返回存在标志及最小地址；不存在时地址值不参与外部选择。"""
        if hi - lo == 1:
            return eligible[lo]
        middle = (lo + hi) // 2
        left, left_value = first(lo, middle)
        right, right_value = first(middle, hi)
        # 内部组合选择只要求稳定值；时钟上界覆盖正反条件不同延迟的过渡。
        take_left = circuit.add("LogicGateIf", left_value, left)
        take_right = circuit.add("LogicGateIf", right_value, program.not_(left))
        circuit.aliases.append((take_left, take_right))
        return program.or_(left, right), take_left

    if not eligible:
        raise ValueError("有效行ROM必须至少包含一个可访问的调用边界")
    has_next, next_pc = first(0, len(eligible))
    next_pc = program.control(has_next).select(next_pc, pc)
    return fields, program.or_(*chosen), addresses[-1], next_pc


def _rom(circuit: Circuit, program: tuple[Instruction, ...], bits: tuple[Ref, ...],
         one: Ref, null: Ref) -> tuple[dict[str, Ref], Ref, Ref, list[tuple[Ref, int]]]:
    """共用分段地址译码，并把同值字段的地址合为一组。"""
    inverted = [circuit.add("LogicGateNot", bit) for bit in bits]
    segments: dict[tuple[int, int, int], Ref] = {}

    def decode_segment(lo: int, hi: int, index: int) -> Ref:
        if lo == hi:
            return one
        if hi - lo == 1:
            return bits[lo] if index & (1 << lo) else inverted[lo]
        key = (lo, hi, (index >> lo) & ((1 << (hi - lo)) - 1))
        if key not in segments:
            middle = (lo + hi) // 2
            segments[key] = circuit.add("LogicGateAnd", decode_segment(lo, middle, index), decode_segment(middle, hi, index))
        return segments[key]

    addresses = [decode_segment(0, len(bits), index) for index in range(len(program))]
    zero = circuit.add("ConstantSignal", config=constant(0))
    fields, chosen = _rom_fields(circuit, program, addresses, zero, null)
    jumps = []
    for index, (address, instruction) in enumerate(zip(addresses, program)):
        if instruction.branch is None and instruction.skip_to is None:
            continue
        if instruction.skip_to is None or not index < instruction.skip_to < len(program):
            raise ValueError("宏跳转必须指向当前控制行之后的有效指令地址")
        condition = instruction.condition if instruction.branch is None else instruction.branch
        absent = circuit.add("LogicGateNot", condition)
        jumps.append((circuit.add("LogicGateAnd", address, absent), instruction.skip_to))
    return fields, _combine(circuit, "LogicGateOr", chosen), addresses[-1], jumps


@dataclass(frozen=True)
class StateUpdate:
    """由调用者建立组合步、交给共用时钟锁存的一份状态。"""

    read: Ref
    source: Ref
    initial: int | None | Ref


def execute_program(circuit: Circuit, target: Ref, enable: Ref, valid: Ref,
                    solved: Ref, unsolvable: Ref, unknown: Ref,
                    program: tuple[Instruction, ...], one: Ref, null: Ref,
                    second_pass: Ref | None = None, extra_state: tuple[StateUpdate, ...] = (),
                    precomputed_state: tuple[Ref, ...] = (), result_test: Callable[[Ref], Ref] | None = None) -> dict:
    """单遍程序，或以second_pass切换数据源的两遍共享程序；不执行目标。"""
    if not program:
        raise ValueError("制造程序至少需要一行")
    width = max(1, (len(program) - 1).bit_length())
    initial: tuple[int | None | Ref, ...] = (None,) * 6 + (0,) * (width + 5)
    reads = tuple(circuit.add("LogicGateIf", value if isinstance(value, Ref) else Literal(value), Literal(1))
                  for value in initial)
    pc = reads[8:8 + width]
    finished, failed, started = reads[8 + width:]
    if second_pass is not None:
        reads += (second_pass,)
        initial += (0,)
    ready_index = None
    checked = None
    if result_test is not None:
        ready_index = len(reads)
        reads += (circuit.add("LogicGateIf", Literal(0), Literal(1)),)
        initial += (0,)
        checked = result_test(reads[0])
    if len({state.read for state in extra_state}) != len(extra_state) or any(
            state.read in reads for state in extra_state):
        raise ValueError("调用者状态入口必须独立，且不能与程序状态重复")
    reads += tuple(state.read for state in extra_state)
    initial += tuple(state.initial for state in extra_state)
    if any(read not in {state.read for state in extra_state} for read in precomputed_state):
        raise ValueError("制造前冻结的状态必须属于调用者状态")
    halted = circuit.add("LogicGateOr", finished, failed)
    machine = _combine(circuit, "LogicGateAnd", [enable, solved, started,
                                               circuit.add("LogicGateNot", halted)])
    packet, selected, last, jumps = _rom(circuit, program, pc, one, null)
    packet["enable"] = circuit.add("LogicGateAnd", machine, selected)
    packet["request"] = circuit.add("LogicGateNot", reads[6])
    next_items = recipe_step(circuit, reads[:6], reads[6], reads[7], packet)
    bad_status = circuit.add("LogicGateCompare", next_items[7], Literal(2), config="AQ==")
    error = circuit.add("LogicGateAnd", packet["enable"], bad_status)
    advance = circuit.add("LogicGateAnd", machine, circuit.add("LogicGateNot", error))
    carry = advance
    next_pc = []
    for bit in pc:
        next_pc.append(circuit.add("LogicGateXOr", bit, carry))
        carry = circuit.add("LogicGateAnd", bit, carry)
    if jumps:
        jump_selected = _combine(circuit, "LogicGateOr", [event for event, _ in jumps])
        take_jump = circuit.add("LogicGateAnd", advance, jump_selected)
        zero = circuit.add("ConstantSignal", config=constant(0))
        for index, value in enumerate(next_pc):
            choices = [event for event, destination in jumps if destination & (1 << index)]
            target_bit = _combine(circuit, "LogicGateOr", choices) if choices else zero
            next_pc[index] = select(circuit, take_jump, target_bit, value)
    end = circuit.add("LogicGateAnd", last, advance)
    if second_pass is not None:
        repeat = circuit.add("LogicGateAnd", end, circuit.add("LogicGateNot", second_pass))
        next_pc = [select(circuit, repeat, Literal(0), bit) for bit in next_pc]
        end = circuit.add("LogicGateAnd", end, second_pass)
    next_finished = circuit.add("LogicGateOr", finished, end)
    next_failed = circuit.add("LogicGateOr", failed, error)
    next_state = (*next_items, *next_pc, next_finished, next_failed, Literal(1))
    if second_pass is not None:
        next_state += (circuit.add("LogicGateOr", second_pass, repeat),)
    if result_test is not None:
        next_state += (finished,)
    next_state += tuple(state.source for state in extra_state)
    accepted = circuit.add("LogicGateAnd", packet["enable"], circuit.add("LogicGateNot", error))
    record_data = tuple(packet[name] for name in RECORD_FIELDS) + (accepted,)
    # 固定目标在复位期间预计算；首周期只设置started。
    full_depth = circuit.settling_bound()["max_gate_depth"]
    dynamic = tuple(read for read in reads if read not in precomputed_state)
    depth = circuit.changing_depth(dynamic)
    phase_steps = max(8, (depth + 7) // 3)
    precompute_depth = search_depth = 0
    if precomputed_state:
        # 调用者须保证：计数冻结一整周期后才放开发令；对应通路有7P。
        search_depth = circuit.changing_depth(reads, tuple(state.source for state in extra_state))
        precompute_depth = circuit.changing_depth(reads)
        phase_steps = max(phase_steps, (search_depth + 7) // 3, (precompute_depth + 10) // 7)
    timing = clock(circuit, enable, phase_steps=phase_steps)
    timing = replace(timing, reset_ticks=max(timing.reset_ticks, 12 * full_depth + 256))
    reset = circuit.add("LogicGateNot", enable)
    master_load = circuit.add("LogicGateOr", timing.phases[0], reset)
    slave_load = circuit.add("LogicGateOr", timing.phases[2], reset)
    states = []
    for read, source, value in zip(reads, next_state, initial):
        initial_value = value if isinstance(value, Ref) else Literal(value)
        data = select(circuit, enable, source, initial_value)
        master = latch(circuit, data, master_load)
        slave_data = select(circuit, enable, master, initial_value)
        slave = latch(circuit, slave_data, slave_load)
        states.append(slave)
        circuit.gates[read.node] = Gate("LogicGateIf", (slave, Literal(1)))
    captured = []
    for index, source in enumerate(record_data):
        value = 0 if index == len(record_data) - 1 else None
        data = select(circuit, enable, source, Literal(value))
        master = latch(circuit, data, master_load)
        slave_data = select(circuit, enable, master, Literal(value))
        captured.append(latch(circuit, slave_data, slave_load))
    final_finished, final_failed, final_started = states[8 + width:11 + width]
    running = circuit.add("LogicGateAnd", enable, final_started)
    window = circuit.add("LogicGateAnd", timing.phases[3], running)
    matches = checked if checked is not None else circuit.add("LogicGateCompare", states[0], target, config="AQ==")
    ready = final_finished if ready_index is None else states[ready_index]
    success = circuit.add("LogicGateAnd", ready, matches)
    mismatch = circuit.add("LogicGateAnd", ready, circuit.add("LogicGateNot", matches))
    internal_error = circuit.add("LogicGateOr", final_failed, mismatch)
    terminal = _combine(circuit, "LogicGateOr", [success, internal_error, unsolvable, unknown])
    done = circuit.add("LogicGateAnd", window, terminal)
    sample = circuit.add("LogicGateAnd", window, captured[-1])
    records = [circuit.add("LogicGateIf", value, sample) for value in captured[:-1]]
    statuses = []
    conditions = (circuit.add("LogicGateNot", terminal), success, unsolvable, unknown, internal_error)
    for code, condition in enumerate(conditions):
        enabled = circuit.add("LogicGateAnd", window, condition)
        enabled = circuit.add("LogicGateAnd", enabled, valid)
        statuses.append(circuit.add("LogicGateIf", Literal(code), enabled))
    circuit.aliases.append(tuple(statuses))
    output = circuit.add("LogicGateIf", states[0], circuit.add("LogicGateAnd", window, success))
    channels = circuit.channel_map()
    report = {
        "outputs": {"window": channels[window], "sample": channels[sample], "done": channels[done],
                    "status": channels[statuses[0]], "result": channels[output],
                    "instruction": {name: channels[value] for name, value in zip(RECORD_FIELDS, records)}},
        "program_rom_rows": len(program), "program_counter_bits": width,
        "item_registers": 6, "step_max_gate_depth": depth, "initial_max_gate_depth": full_depth,
        "timing": timing_contract(timing),
    }
    if precomputed_state:
        report.update({"search_max_gate_depth": search_depth,
                       "precompute_max_gate_depth": precompute_depth, "precompute_handoff_phases": 7})
    if result_test is not None:
        report["verification_wait_cycles"] = 1
    return report
