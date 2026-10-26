"""四象限五层完整尾部的四帧DFS：共用制造ROM，成功后才重放并发布指令。"""

import argparse
import json
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .circuit import Circuit, Gate, Literal, Ref, encode_document
from .clocked_state import ClockedState
from .corner_program import CornerProgram
from .decoder_circuit import decode
from .half_circuit import MaterialCell, column_admissible, half_stable
from .pin_source_circuit import pin_source
from .prefix_closure_circuit import prefix_closure
from .prefix_search import PrefixSearch
from .program_controller import RECORD_FIELDS, _rom
from .recipe_processor import _read, recipe_step
from .sequential_circuit import timing_contract
from .shared_angle import mirror_packet, shared_half_body
from .stationary_circuit import stationary_matches
from .support_circuit import in_support_class
from .synthesis.physics import Rules
from .tag_palette import TagPalette, same_grid


class Phase(IntEnum):
    """一份共享控制状态；挂起父帧只保存目标和游标。"""

    ENTRY = 0
    PREFIX = 1
    PREFIX_NEXT = 2
    PIN_PREFLIGHT = 3
    SOURCE = 4
    FAMILY_NEXT = 5
    SOURCE_NEXT = 6
    RETURN = 7
    FAIL = 8
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
    crystals: tuple[Ref, ...]
    pin_search: Ref
    family_checked: Ref


def _equals(program: CornerProgram, bits: tuple[Ref, ...], value: int) -> Ref:
    return program.and_(*(bit if value & (1 << k) else program.not_(bit) for k, bit in enumerate(bits)))


def _value(program: CornerProgram, bits: tuple[Ref, ...], limit: int) -> Ref:
    circuit = program.circuit
    branches = tuple(circuit.add("LogicGateIf", Literal(value), _equals(program, bits, value))
                     for value in range(limit))
    circuit.aliases.append(branches)
    return branches[0]


def _increment(program: CornerProgram, bits: tuple[Ref, ...], advance: Ref, modulus: int, *,
               last: Ref | None = None) -> tuple[tuple[Ref, ...], Ref]:
    """布尔加一；动态末槽或固定模数决定归零及传给下一位的进位。"""
    wrap = program.and_(advance, last if last is not None else _equals(program, bits, modulus - 1))
    values = tuple(program.circuit.add("LogicGateXOr", bit, program.and_(advance, *bits[:k]))
                   for k, bit in enumerate(bits))
    if last is not None or modulus != 1 << len(bits):
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
        tuple(tuple(bank.add() for _ in range(2)) for _ in range(4)),
        tuple(bank.add() for _ in range(4)), bank.add(), bank.add()) for i in range(4))
    phase = bank.add(int(Phase.ENTRY))
    depth = bank.add()
    leaf_depth = bank.add()
    status = bank.add()
    support_prefix = bank.add()
    leaf_direction = bank.add()
    leaf_mode = bank.add()
    optional_top = circuit.add("LogicGateCompare", leaf_mode, Literal(1), config="AQ==")
    known_no_leaf = circuit.add("LogicGateCompare", leaf_mode, Literal(2), config="AQ==")
    modes = {value: circuit.add("LogicGateCompare", phase, Literal(int(value)), config="AQ==") for value in Phase}
    levels = [circuit.add("LogicGateCompare", depth, Literal(i), config="AQ==") for i in range(4)]
    root = levels[0]

    def active(values: tuple[Ref, ...]) -> Ref:
        return _read(circuit, values, levels)

    tags = tuple(tuple(active(tuple(frame.goal[q][z] for frame in frames)) for z in range(5)) for q in range(4))
    prefix = tuple(active(tuple(frame.prefix[k] for frame in frames)) for k in range(12))
    slots = tuple(tuple(active(tuple(frame.slots[q][k] for frame in frames)) for k in range(5)) for q in range(4))
    top = tuple(tuple(active(tuple(frame.top[q][k] for frame in frames)) for k in range(2)) for q in range(4))
    crystals = tuple(active(tuple(frame.crystals[q] for frame in frames)) for q in range(4))
    pin_search = active(tuple(frame.pin_search for frame in frames))
    family_checked = active(tuple(frame.family_checked for frame in frames))
    grid = palette.grid(tags, preserve_columns=True)
    original = grid.columns
    nonempty = program.or_(*(cell.occupied for column in original for cell in column))
    geometry = tuple(tuple(MaterialCell(cell.occupied, cell.pin, cell.crystal) for cell in column) for column in original)
    admissible = program.and_(*(column_admissible(circuit, column) for column in geometry))
    uncolored = program.or_(*(program.and_(cell.crystal, circuit.add(
        "LogicGateCompare", cell.color, Literal("color:u"), config="AQ==")) for row in decoded.cells for cell in row))
    in_scope = program.and_(decoded.valid, program.not_(uncolored))
    has_crystal = program.or_(*(cell.crystal for column in original for cell in column))
    pin_base = program.and_(*(program.and_(
        program.not_(column[0].crystal),
        program.or_(program.not_(program.or_(column[1].crystal, column[2].crystal)), column[0].pin),
        program.or_(program.not_(column[2].crystal), column[1].occupied)) for column in original))
    depth_allowed = program.or_(*(program.and_(levels[i], program.or_(*(
        cell.crystal for row in decoded.cells[i + 2:] for cell in row))) for i in range(3)))
    tail_candidate = program.and_(has_crystal, pin_base, depth_allowed)
    pin_allowed = program.and_(tail_candidate, program.not_(optional_top))

    finder = PrefixSearch(program, original, optional_top=optional_top)
    for read, source in zip(finder.bits, prefix):
        circuit.gates[read.node] = Gate("LogicGateIf", (source, Literal(1)))
    # 此处found/exhausted保持常0；复用finish的单步游标计算，由帧控制是否写回。
    prefix_step = finder.finish(program.zero, program.one)
    next_prefix = tuple(state.source for state in prefix_step[:12])
    last_prefix = prefix_step[-1].source
    closure = prefix_closure(program, finder, leaf_direction)
    checking_prefix = support_prefix
    support_grid = tuple(tuple(MaterialCell(
        program.pick(checking_prefix, finder.columns[q][z].occupied, original[q][z].occupied),
        program.pick(checking_prefix, finder.columns[q][z].pin, original[q][z].pin),
        program.pick(checking_prefix, finder.columns[q][z].crystal, original[q][z].crystal))
        for z in range(5)) for q in range(4))
    optional_grounding = program.and_(optional_top, pin_search, program.not_(support_prefix))
    anchored = in_support_class(program, support_grid, grounded=pin_search, optional_top=optional_grounding, admissible=True)
    appendable = program.and_(finder.appendable, anchored)
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
                           tuple(program.pick(crystal, program.const(3), _value(program, bits, 3))
                                 for crystal, bits in zip(crystals, top)), program.one)
    source_ground_crystal = program.or_(*(program.or_(candidate.image.deleted[0][q],
                                                      candidate.image.live[1][q].crystal) for q in range(4)))

    # candidate.valid提供完整列A前提；物理匹配直接由下部支撑及上部八格传播计算。
    physics_matches = stationary_matches(program, candidate.image)
    items = tuple(bank.add(None) for _ in range(6))
    ack, item_status = bank.add(), bank.add()
    second_pass = bank.add()
    second_corner = bank.add()
    shifted = program.not_(partitions[0])
    aligned = tuple(tuple(program.choose(shifted, finder.columns[(q + 1) % 4][z], finder.columns[q][z])
                          for z in range(5)) for q in range(4))
    flipped = program.not_(program.or_(*(cell.occupied for column in aligned[:2] for cell in column)))
    take_back = circuit.add("LogicGateXOr", flipped, second_pass)
    columns = tuple(tuple(program.choose(take_back, aligned[q + 2][z], aligned[q][z]) for z in range(5)) for q in (0, 1))
    present, corner_last, mirror_limit = shared_half_body(program, columns, second_corner)
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
    in_corner = program.or_(*(program.and_(program.not_(pc[k]), *(
        pc[j] if mirror_limit & (1 << j) else program.not_(pc[j]) for j in range(k + 1, width)))
        for k in range(width) if mirror_limit & (1 << k)))
    mirror_packet(program, packet, program.and_(second_corner, in_corner))
    replay = program.or_(modes[Phase.REPLAY_LEAF], modes[Phase.REPLAY_PARENT])
    packet["enable"] = program.and_(enable, replay, selected)
    packet["request"] = program.not_(ack)
    next_items = recipe_step(circuit, items, ack, item_status, packet)
    error = program.and_(packet["enable"], circuit.add("LogicGateCompare", next_items[7], Literal(2), config="AQ=="))
    advance = program.and_(replay, program.not_(error))
    next_pc = [circuit.add("LogicGateXOr", bit, program.and_(advance, *pc[:k])) for k, bit in enumerate(pc)]
    if jumps:
        jump_selected = program.or_(*(event for event, _ in jumps))
        take_jump = program.and_(advance, jump_selected)
        next_pc = [program.pick(take_jump, program.or_(*(event for event, destination in jumps if destination & (1 << k))), value)
                   for k, value in enumerate(next_pc)]
    end_macro = program.and_(advance, _equals(program, pc, macro_last))
    repeat = program.and_(end_macro, program.not_(second_pass))
    repeat_corner = program.and_(advance, _equals(program, pc, corner_last), program.not_(second_corner))
    next_pc = [program.pick(program.or_(repeat, repeat_corner), program.zero, bit) for bit in next_pc]
    macro_done = program.and_(end_macro, second_pass)
    parent_done = program.and_(advance, last)
    for read, source in zip((*items, ack, item_status), next_items):
        bank.put(read, source)
    for read, source in zip(pc, next_pc):
        bank.put(read, source)
    bank.put(second_pass, program.or_(second_pass, repeat))
    bank.put(second_corner, 1, repeat_corner)
    bank.put(second_corner, 0, repeat)

    cpu_matches = same_grid(program, decode(circuit, items[0], program.one, Rules(4)), grid)

    entry = modes[Phase.ENTRY]
    valid_goal = program.and_(grid.valid, nonempty)
    necessary = program.and_(admissible, program.or_(optional_top, anchored),
                             program.or_(program.not_(known_no_leaf), pin_allowed))
    enter = program.and_(entry, in_scope, valid_goal, necessary)
    enter_leaf = program.and_(enter, program.not_(known_no_leaf))
    enter_pin = program.and_(enter, known_no_leaf)
    entry_fail = program.and_(entry, in_scope, valid_goal, program.not_(necessary))
    bad_goal = program.and_(entry, in_scope, program.not_(valid_goal))
    leaf_found = program.and_(modes[Phase.PREFIX], program.not_(pin_search), appendable, available)
    commit_top = program.and_(leaf_found, optional_top)
    start_source = program.and_(modes[Phase.PREFIX], pin_search, appendable, pin_allowed, candidate.has_slots)
    leaf_active = program.and_(modes[Phase.PREFIX], program.not_(pin_search), program.not_(leaf_found))
    grow_prefix = program.and_(leaf_active, program.not_(closure.impossible), closure.changed)
    cut_finished = program.and_(leaf_active, program.or_(closure.impossible, program.not_(closure.changed)))
    next_cut = program.and_(cut_finished, program.not_(leaf_direction))
    leaf_finished = program.and_(cut_finished, leaf_direction)
    skip_prefix = program.and_(modes[Phase.PREFIX], pin_search,
                               program.or_(program.not_(appendable), program.not_(pin_allowed), program.not_(candidate.has_slots)))
    move_prefix = program.and_(modes[Phase.PREFIX_NEXT], program.not_(last_prefix))
    prefix_scan_finished = program.and_(modes[Phase.PREFIX_NEXT], last_prefix)
    begin_pin_search = program.and_(leaf_finished, tail_candidate)
    grounded_ready = program.and_(modes[Phase.PIN_PREFLIGHT], anchored, program.not_(optional_top))
    grounded_fail = program.and_(modes[Phase.PIN_PREFLIGHT], program.not_(anchored))
    family_preflight_done = program.and_(modes[Phase.PIN_PREFLIGHT], optional_top)
    prefixes_finished = program.or_(prefix_scan_finished, grounded_fail, family_preflight_done,
                                    program.and_(leaf_finished, program.not_(tail_candidate)))

    valid_source = program.and_(candidate.valid, physics_matches)
    descend = program.and_(modes[Phase.SOURCE], valid_source)
    skip_source = program.and_(modes[Phase.SOURCE], program.not_(valid_source))
    search_return = modes[Phase.RETURN]
    search_pop = program.and_(search_return, program.not_(root))
    root_solved = program.and_(search_return, root)
    fail_pop = program.and_(modes[Phase.FAIL], program.not_(root))
    retry_family = program.and_(fail_pop, optional_top, pin_search, anchored)
    skip_family = program.and_(fail_pop, optional_top, program.not_(retry_family))
    root_failed = program.and_(modes[Phase.FAIL], root)
    replay_check = program.or_(modes[Phase.REPLAY_LEAF_CHECK], modes[Phase.REPLAY_PARENT_CHECK])
    original_matches = circuit.add("LogicGateCompare", items[0], target, config="AQ==")
    replay_ok = program.and_(replay_check, cpu_matches, program.or_(program.not_(root), original_matches))
    replay_up = program.and_(replay_ok, program.not_(root))
    replay_finished = program.and_(replay_ok, root)
    outside = program.and_(entry, root, decoded.valid, uncolored)
    invalid = program.and_(entry, root, program.not_(decoded.valid))
    internal = program.or_(error, bad_goal,
        program.and_(replay_check, program.not_(program.and_(cpu_matches,
                     program.or_(program.not_(root), original_matches)))))

    # 相邻晶体保留状态冲突时，推进涉及的最快槽；多个冲突取最高槽跳过。
    counter_event = program.or_(modes[Phase.SOURCE_NEXT], modes[Phase.FAMILY_NEXT])
    bad_slots = tuple(program.or_(program.not_(valid), conflict)
                      for valid, conflict in zip(candidate.column_valid, candidate.slot_conflicts))
    bad_slot = program.or_(*bad_slots)
    skip_at = tuple(program.and_(counter_event, bad_slots[q], program.not_(program.or_(*bad_slots[q + 1:])))
                    for q in range(4))
    skip_columns = program.or_(*skip_at)
    family_jump = program.and_(counter_event, program.not_(bad_slot),
                               program.or_(modes[Phase.FAMILY_NEXT], source_ground_crystal,
                                           program.not_(candidate.image.passed), program.not_(physics_matches)))
    carry = program.and_(counter_event, program.not_(bad_slot), program.not_(family_jump))
    next_top = []
    for bits, crystal in zip(top, crystals):
        values, overflow = _increment(program, bits, carry, 3)
        next_top.append(tuple(program.pick(program.or_(crystal, family_jump, skip_columns), program.zero, value)
                              for value in values))
        carry = program.pick(crystal, carry, overflow)
    new_family = program.or_(carry, family_jump, skip_columns)
    cap_advance = program.or_(carry, family_jump)
    forbidden_caps = tuple(column[4].crystal for column in original)
    cap_pass = tuple(program.or_(bit, forbidden) for bit, forbidden in zip(crystals, forbidden_caps))
    next_crystals = tuple(program.pick(skip_columns, program.zero, circuit.add("LogicGateXOr", bit,
        program.and_(cap_advance, program.not_(forbidden_caps[q]), *cap_pass[:q]))) for q, bit in enumerate(crystals))
    carry = program.and_(cap_advance, *cap_pass)
    next_slots = []
    for q, bits in enumerate(slots):
        values, carry = _increment(program, bits, program.or_(carry, skip_at[q]), 20, last=candidate.last_slots[q])
        reset_lower = program.or_(*skip_at[q + 1:])
        next_slots.append(tuple(program.pick(reset_lower, program.zero, value) for value in values))
    sources_finished = carry
    depth_choices: list[tuple[Ref, Ref | int | None]] = []
    for i, frame in enumerate(frames):
        selected_frame = levels[i]
        initialize = program.and_(program.or_(enter_leaf, next_cut), selected_frame)
        initialize_pin = program.and_(program.or_(begin_pin_search, enter_pin), selected_frame)
        grow_s = program.and_(grow_prefix, selected_frame)
        bank.put(frame.pin_search, 0, program.and_(enter_leaf, selected_frame))
        bank.put(frame.pin_search, 1, initialize_pin)
        next_s = program.and_(move_prefix, selected_frame)
        reset_source = program.and_(start_source, selected_frame)
        next_d = program.and_(counter_event, selected_frame)
        bank.put(frame.family_checked, 1, program.and_(descend, selected_frame))
        bank.put(frame.family_checked, 0, program.or_(reset_source, program.and_(new_family, next_d)))
        for read, value in zip(frame.crystals, next_crystals):
            bank.put(read, value, next_d)
            bank.put(read, 0, reset_source)
        for k, read in enumerate(frame.prefix):
            bank.put(read, closure.initial[k], initialize)
            bank.put(read, closure.next_bits[k], grow_s)
            bank.put(read, finder.initial[k], initialize_pin)
            bank.put(read, next_prefix[k], next_s)
        for old, new in zip((*frame.top, *frame.slots), (*next_top, *next_slots)):
            for read, value in zip(old, new):
                bank.put(read, value, next_d)
                bank.put(read, 0, reset_source)
        for q in range(4):
            chosen_top = program.pick(finder.columns[q][4].occupied, tags[q][4], program.zero)
            bank.put(frame.goal[q][4], chosen_top, program.and_(commit_top, selected_frame))
        if i < 3:
            pushing = program.and_(descend, selected_frame)
            bank.put(frames[i + 1].pin_search, 0, pushing)
            bank.put(frames[i + 1].family_checked, 0, pushing)
            for q in range(4):
                for z in range(5):
                    value = candidate.tags[q][z]
                    if z == 4:
                        value = program.pick(program.and_(program.not_(family_checked), program.not_(crystals[q])),
                                             program.one, value)
                    bank.put(frames[i + 1].goal[q][z], value, pushing)
            depth_choices.append((pushing, i + 1))
        if i:
            popping = program.and_(selected_frame, program.or_(search_pop, fail_pop, replay_up))
            depth_choices.append((popping, i - 1))
    depth_choices.append((root_solved, leaf_depth))
    bank.put_exclusive(depth, tuple(depth_choices))
    bank.put(leaf_depth, depth, leaf_found)
    bank.put(leaf_direction, 0, enter_leaf)
    bank.put(leaf_direction, 1, next_cut)
    bank.put(leaf_mode, program.pick(family_checked, program.const(2), program.one), descend)
    bank.put(leaf_mode, 0, program.or_(commit_top, fail_pop))

    # 搜索仅保存材料参数与精确Pin关系；根成功后才执行并发布制造流。
    accepted = program.and_(packet["enable"], program.not_(error), replay)
    record = tuple(bank.add(None) for _ in RECORD_FIELDS)
    record_valid = bank.add()
    for read, name in zip(record, RECORD_FIELDS):
        bank.put(read, packet[name])
    bank.put(record_valid, accepted)
    reset_cpu = root_solved
    for read in items:
        bank.put(read, None, reset_cpu)
    bank.put(ack, 0, reset_cpu)
    bank.put(item_status, 0, reset_cpu)
    bank.put(second_pass, 0, reset_cpu)
    bank.put(second_corner, 0, reset_cpu)
    for k, read in enumerate(pc):
        bank.put(read, 0, reset_cpu)
        bank.put(read, int(bool(parent_start & (1 << k))), replay_up)

    transitions = (
        (enter_leaf, Phase.PREFIX), (enter_pin, Phase.PIN_PREFLIGHT), (entry_fail, Phase.FAIL),
        (leaf_found, Phase.RETURN), (start_source, Phase.SOURCE), (skip_prefix, Phase.PREFIX_NEXT),
        (move_prefix, Phase.PREFIX), (begin_pin_search, Phase.PIN_PREFLIGHT),
        (grounded_ready, Phase.PREFIX), (prefixes_finished, Phase.FAIL),
        (descend, Phase.ENTRY), (skip_source, Phase.SOURCE_NEXT),
        (program.and_(counter_event, program.not_(sources_finished)), Phase.SOURCE),
        (sources_finished, Phase.PREFIX_NEXT),
        (search_pop, Phase.RETURN), (root_solved, Phase.REPLAY_LEAF),
        (retry_family, Phase.SOURCE), (skip_family, Phase.FAMILY_NEXT),
        (program.and_(fail_pop, program.not_(optional_top)), Phase.SOURCE_NEXT),
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
    # K的重通路只由慢状态切换；业务冻结时脉冲清零，避免重复发包。
    bank.put(support_prefix, 0, program.or_(descend, begin_pin_search, enter_pin))
    bank.put(support_prefix, 1, program.or_(enter_leaf, grounded_ready, search_pop, fail_pop, root_solved, replay_up))
    slow_reads = (depth, second_pass, second_corner, support_prefix, leaf_direction, leaf_mode,
                  *(read for frame in frames for read in (
        *(cell for column in frame.goal for cell in column), *frame.prefix,
        *(bit for bits in (*frame.slots, *frame.top) for bit in bits), *frame.crystals,
        frame.pin_search, frame.family_checked)))
    slow_event = program.or_(enter, next_cut, grow_prefix, begin_pin_search, grounded_ready, move_prefix, start_source, counter_event,
                             descend, commit_top, search_pop, fail_pop, root_solved, replay_up, repeat, repeat_corner)
    timing, state_report = bank.close(enable, slow_reads=slow_reads, slow_event=slow_event, pulses=(record_valid,))
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
        "palette_entries_per_cell": 9, "grounded_pin_tail_required": True, "shared_family_grounding_check": True,
        "support_row_closures": 10, "pin_base_precheck": True, "crystal_conflict_slot_skip": True,
        "top_crystal_forbidden_above_retained": True, "source_slots_use_bucket_lengths": True,
        "search_frames": 4, "tail_pin_limit": "max(0, 最高原目标C层号-1)，层号从0开始",
        "item_registers": 6, "program_rom_rows": len(instructions),
        "physical_check": {"horizontal_path_max": 2, "upper_upward_sweeps": 2, "upper_downward_sweeps": 1,
                           "requires_column_admissibility": True, "iterative_state_registers": 0,
                           "manufacture_during_search": False},
        "prefix_closure": {"directions": 2, "growth_rounds_max_per_direction": 20,
                           "final_checks_per_direction": 1, "pin_pass_keeps_full_enumeration": True,
                           "optional_top_for_ground_crystal_families": True,
                           "shared_leaf_check_for_all_families": True},
        "shared_angle_rows": corner_last + 1, "angle_calls": 4,
        "instruction_bound": 2 * (macro_last + corner_last + 2) + 3 * (len(instructions) - parent_start),
        "leaf_program_rows": macro_last + 1, "parent_tail_rows": len(instructions) - parent_start,
        "statuses": {"0": "搜索或成功路径重放中", "1": "已输出完整制造流程，原生回放等于原目标",
                     "2": "穷尽全部有界尾部后不可制作", "3": "cu晶体供料未界定", "4": "内部状态或回放失配，不能判不可制作",
                     "null": "输入无效、关闭或窗口之外"},
        "input_protocol": "target全程保持；enable=0持续timing规定的完整复位时间，再启用并保持到done。忽略启动的不完整阶段3。",
        "output_protocol": "每个完整window上升后等96信号tick，窗口内读一次；sample为真收instruction，随后处理done/status。搜索期间不发布指令，无背压。",
        "resource_bound": "每格只查本列5个原标签及4种辅助料；四帧各20目标ID、12前缀位、20来源槽位、8NPC顶盖位、4顶层C位、1遍次位及1族检查位；物理检查为组合通路，共享一份制造ROM及六槽；另有K模式、首轮切向、叶端模式、制造角遍次和冷却位，慢更新后冻结一轮且脉冲清零。成功参数留帧，重放一次，不保存数百条指令。",
        "termination": "最高原目标C层号H给出max(0,H-1)条尾部Pin边，至多三边；达到H次的历史可改写为A→S；最低C沿边仍严格下降；零Pin首轮每切向至多20次强制补格加一次最终检查；Pin第二轮每帧至多1296个S前缀，每前缀至多20^4×4^4个来源地址。每族共用两个可选顶格闭包；失败后，地面C族或无G成员族全拒，其余成员仅搜Pin尾部。完整穷尽才返回2。",
        "scope": "在既定基础单层及合法晶体供料模型内完整四象限五层尾部搜索；规模和最坏等待仍需压缩，未通过游戏实用性能验收。",
        "proof": "4q5l/prefix-closure.md；optional-top.md；family-grounding.md；three-pin-tail.md；pin-source-conflicts.md；full-tail-circuit.md；shared-angle.md；multicycle-control.md；pin-grounded.md；grounded-tail.md；pin-base.md；pin-image-exact.md；support-reachability.md；support-row-scan.md；tail-solver.md；pin-patterns.md；clocked-control.md。",
        "verification": "仅静态源代码推导、DAG、端口和实际占地生产编译；未执行目标、搜索、指令、反馈模拟、测试或游戏",
    }


def main() -> int:
    """仅编译生产蓝图及接口，不执行求解。"""
    parser = argparse.ArgumentParser(description="生成四帧递归及成功路径重放的完整四象限尾部电路")
    parser.add_argument("--channel-base", type=int)
    parser.add_argument("--pack", action="store_true", help="就地放置固定常量并装箱门组件；默认使用独立频道1277000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    default_base = 1_277_000 if args.pack else 1_211_000
    circuit, report = build_solver(args.channel_base if args.channel_base is not None else default_base)
    document = circuit.document(packed=args.pack)
    if args.pack:
        platforms = document["BP"]["Entries"]
        report.update({"logical_gates": len(circuit.gates), "gate_platforms": len(platforms),
                       "local_constant_inputs": True,
                       "layout": "未参与别名的固定常量输入就地复制；其余连接保持，复用旧平台的行内及上方空位，组件间隔一格、平台边缘两格，方阵排列。",
                       "platform_grid": [max(platform["X"] for platform in platforms) + 1,
                                         max(platform["Y"] for platform in platforms) + 1]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(document) + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完整四象限尾部电路已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
