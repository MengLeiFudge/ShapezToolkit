"""标准四象限半形的自动制造程序：判据、指令ROM、六槽回放和目标核对。"""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .circuit import Circuit, Gate, Literal, Ref, constant
from .corner_program import Instruction, half_program
from .decoder_circuit import decode
from .half_circuit import _combine, classify_half
from .recipe_processor import PACKET_FIELDS, recipe_step
from .sequential_circuit import clock, latch, select, timing_contract
from .synthesis.physics import Rules


RECORD_FIELDS = PACKET_FIELDS[:-1]


def _rom(circuit: Circuit, program: tuple[Instruction, ...], bits: tuple[Ref, ...],
         one: Ref, null: Ref) -> tuple[dict[str, Ref], Ref, Ref, list[tuple[Ref, int]]]:
    """共用地址前缀，并把同值字段的地址合为一组，压缩指令选择门。"""
    inverted = [circuit.add("LogicGateNot", bit) for bit in bits]
    prefixes: dict[tuple[int, ...], Ref] = {(): one}
    addresses = []
    for index in range(len(program)):
        prefix: tuple[int, ...] = ()
        for bit_index in reversed(range(len(bits))):
            digit = (index >> bit_index) & 1
            previous = prefix
            prefix += (digit,)
            if prefix not in prefixes:
                source = bits[bit_index] if digit else inverted[bit_index]
                prefixes[prefix] = circuit.add("LogicGateAnd", prefixes[previous], source)
        addresses.append(prefixes[prefix])
    zero = circuit.add("ConstantSignal", config=constant(0))
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
    jumps = []
    for index, (address, instruction) in enumerate(zip(addresses, program)):
        if instruction.branch is None:
            continue
        if instruction.skip_to is None or not index < instruction.skip_to < len(program):
            raise ValueError("宏跳转必须指向当前控制行之后的有效指令地址")
        absent = circuit.add("LogicGateNot", instruction.branch)
        jumps.append((circuit.add("LogicGateAnd", address, absent), instruction.skip_to))
    return fields, _combine(circuit, "LogicGateOr", chosen), addresses[-1], jumps


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
    width = max(1, (len(program) - 1).bit_length())
    initial = (None,) * 6 + (0,) * (width + 5)
    reads = tuple(circuit.add("LogicGateIf", Literal(value), Literal(1)) for value in initial)
    pc = reads[8:8 + width]
    finished, failed, started = reads[8 + width:]
    halted = circuit.add("LogicGateOr", finished, failed)
    machine = _combine(circuit, "LogicGateAnd", [enable, flags.solved, started,
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
    next_finished = circuit.add("LogicGateOr", finished, circuit.add("LogicGateAnd", last, advance))
    next_failed = circuit.add("LogicGateOr", failed, error)
    next_state = (*next_items, *next_pc, next_finished, next_failed, Literal(1))
    accepted = circuit.add("LogicGateAnd", packet["enable"], circuit.add("LogicGateNot", error))
    record_data = tuple(packet[name] for name in RECORD_FIELDS) + (accepted,)
    # 目标解码在复位期间已运行；started使首个周期只初始化，不执行PC0。
    full_depth = circuit.settling_bound()["max_gate_depth"]
    depth = circuit.changing_depth(reads)
    timing = clock(circuit, enable, phase_steps=max(8, (depth + 7) // 3))
    timing = replace(timing, reset_ticks=max(timing.reset_ticks, 12 * full_depth + 256))
    reset = circuit.add("LogicGateNot", enable)
    master_load = circuit.add("LogicGateOr", timing.phases[0], reset)
    slave_load = circuit.add("LogicGateOr", timing.phases[2], reset)
    states = []
    for read, source, value in zip(reads, next_state, initial):
        data = select(circuit, enable, source, Literal(value))
        master = latch(circuit, data, master_load)
        slave_data = select(circuit, enable, master, Literal(value))
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
    final_finished, final_failed, final_started = states[8 + width:]
    running = circuit.add("LogicGateAnd", enable, final_started)
    window = circuit.add("LogicGateAnd", timing.phases[3], running)
    matches = circuit.add("LogicGateCompare", states[0], target, config="AQ==")
    success = circuit.add("LogicGateAnd", final_finished, matches)
    mismatch = circuit.add("LogicGateAnd", final_finished, circuit.add("LogicGateNot", matches))
    internal_error = circuit.add("LogicGateOr", final_failed, mismatch)
    terminal = _combine(circuit, "LogicGateOr", [success, internal_error, flags.unsolvable, flags.unknown])
    done = circuit.add("LogicGateAnd", window, terminal)
    sample = circuit.add("LogicGateAnd", window, captured[-1])
    records = [circuit.add("LogicGateIf", value, sample) for value in captured[:-1]]
    statuses = []
    conditions = (circuit.add("LogicGateNot", terminal), success, flags.unsolvable, flags.unknown, internal_error)
    for code, condition in enumerate(conditions):
        valid = circuit.add("LogicGateAnd", window, condition)
        valid = circuit.add("LogicGateAnd", valid, decoded.valid)
        statuses.append(circuit.add("LogicGateIf", Literal(code), valid))
    circuit.aliases.append(tuple(statuses))
    output = circuit.add("LogicGateIf", states[0], circuit.add("LogicGateAnd", window, success))
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + reserve - 1:
        raise ValueError("自动半形构造超出其保留频道范围")
    return circuit, {
        "component": "automatic_standard_half_synthesizer", "quadrants": 4, "height": 5,
        "inputs": {"target": channel_base, "enable": channel_base + 1},
        "outputs": {"window": channels[window], "sample": channels[sample], "done": channels[done],
                    "status": channels[statuses[0]], "result": channels[output],
                    "instruction": {name: channels[value] for name, value in zip(RECORD_FIELDS, records)}},
        "statuses": {"0": "程序运行中", "1": "可制作，指令流已回放并与完整目标相同",
                     "2": "标准半形违反完整局部判据，不可制作", "3": "非标准半形或cu供料未界定",
                     "4": "内部程序或回放失配，不构成不可制作结论", "null": "无效输入、停机或窗口之外"},
        "gate_platforms": len(circuit.gates), "program_rom_rows": len(program), "program_counter_bits": width,
        "item_registers": 6, "step_max_gate_depth": depth, "initial_max_gate_depth": full_depth,
        "reserved_channels": [channel_base, channel_base + reserve - 1], "timing": timing_contract(timing),
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
