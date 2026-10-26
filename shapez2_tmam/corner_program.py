"""把两列角构造编成依赖目标信号的有限指令程序，不执行目标物理。"""

from dataclasses import dataclass, replace

from .circuit import Circuit, Literal, Ref, constant
from .decoder_circuit import DecodedCell, DecodedShape
from .half_circuit import _combine
from .sequential_circuit import SignalControl
from .synthesis.physics import EMPTY, PIN, Rules, Shape


@dataclass(frozen=True)
class CellRef:
    """NPC片段中的C以针占位；真实C类型和颜色仅供后续结晶指令。"""

    npc: Ref
    occupied: Ref
    pin: Ref
    crystal: Ref
    color: Ref


@dataclass(frozen=True)
class Instruction:
    """条件成立才执行的消费式指令；条件依赖目标及上层固定的调用状态。"""

    condition: Ref
    opcode: int
    a: int = 0
    b: int = 0
    destination: int | Ref = 0
    base: Ref | Literal = Literal(None)
    color: Ref | Literal = Literal(None)
    branch: Ref | None = None
    skip_to: int | None = None


class CornerProgram:
    """共用目标表达式和基础层信号，把既有角证明展开为指令ROM。"""

    def __init__(self, circuit: Circuit, *, share_controls: bool = False):
        self.circuit = circuit
        self.controls: dict[Ref, SignalControl] | None = {} if share_controls else None
        self.rules = Rules(4)
        self.instructions: list[Instruction] = []
        self.constants: dict[int | str | Shape | None, Ref] = {}
        self.booleans: dict[Ref, int] = {}
        self.expressions: dict[tuple, Ref] = {}
        self.cells: dict[str, CellRef] = {}
        self.npc_codes: dict[Ref, str] = {}
        self.layers: dict[tuple[Ref, ...], Ref | Literal] = {}
        self.zero = self.const(0)
        self.one = self.const(1)
        for code in (EMPTY, PIN, "Cu", "cr"):
            self.cell(code)

    def const(self, value: int | str | Shape | None) -> Ref:
        if value not in self.constants:
            result = self.circuit.add("ConstantSignal", config=constant(value))
            self.constants[value] = result
            if isinstance(value, int) and value in (0, 1):
                self.booleans[result] = value
        return self.constants[value]

    def and_(self, *values: Ref) -> Ref:
        return self._boolean("LogicGateAnd", values, 1)

    def or_(self, *values: Ref) -> Ref:
        return self._boolean("LogicGateOr", values, 0)

    def _boolean(self, kind: str, values: tuple[Ref, ...], identity: int) -> Ref:
        if any(self.booleans.get(value) == 1 - identity for value in values):
            return self.const(1 - identity)
        remaining = sorted({value for value in values if self.booleans.get(value) != identity},
                           key=lambda value: (value.node, value.port))
        if not remaining:
            return self.const(identity)
        key = (kind, *remaining)
        if key not in self.expressions:
            self.expressions[key] = _combine(self.circuit, kind, remaining)
        return self.expressions[key]

    def not_(self, value: Ref) -> Ref:
        if value in self.booleans:
            return self.const(1 - self.booleans[value])
        key = ("not", value)
        if key not in self.expressions:
            self.expressions[key] = self.circuit.add("LogicGateNot", value)
        return self.expressions[key]

    def control(self, condition: Ref) -> SignalControl:
        """仅共享相同原条件的一对等深控制，数据分支及反馈仍分别生成。"""
        if self.controls is None:
            return SignalControl(self.circuit, condition)
        if condition not in self.controls:
            self.controls[condition] = SignalControl(self.circuit, condition)
        return self.controls[condition]

    def pick(self, condition: Ref, yes: Ref, no: Ref) -> Ref:
        if yes == no:
            return yes
        if condition in self.booleans:
            return yes if self.booleans[condition] else no
        key = ("pick", condition, yes, no)
        if key not in self.expressions:
            self.expressions[key] = self.control(condition).select(yes, no)
        return self.expressions[key]

    def cell(self, code: str) -> CellRef:
        if code not in self.cells:
            npc = PIN if code[0] == "c" else code
            shape = None if npc == EMPTY else self.rules.parse(npc + "------")
            reference = self.const(shape)
            self.npc_codes[reference] = npc
            self.cells[code] = CellRef(reference, self.const(int(code != EMPTY)),
                                       self.const(int(code == PIN)), self.const(int(code[0] == "c")),
                                       self.const(f"color:{code[1]}" if code not in (EMPTY, PIN) else None))
        return self.cells[code]

    def original(self, cell: DecodedCell) -> CellRef:
        painted = self.circuit.add("VirtualPainter", cell.shape, cell.color)
        npc = self.pick(self.or_(cell.pin, cell.crystal), self.cell(PIN).npc, painted)
        return CellRef(npc, cell.occupied, cell.pin, cell.crystal, cell.color)

    def choose(self, condition: Ref, yes: CellRef, no: CellRef) -> CellRef:
        return CellRef(*(self.pick(condition, a, b) for a, b in zip(
            (yes.npc, yes.occupied, yes.pin, yes.crystal, yes.color),
            (no.npc, no.occupied, no.pin, no.crystal, no.color))))

    def typed(self, cell: CellRef, kind: str) -> CellRef:
        """仅在外层模式已保证类型时特化，保留原目标的普通部件和颜色。"""
        if kind == "C":
            return CellRef(self.cell(PIN).npc, self.one, self.zero, self.one, cell.color)
        if kind == "N":
            return CellRef(cell.npc, self.one, self.zero, self.zero, cell.color)
        raise ValueError("保留目标格只按已知N或C特化")

    def layer(self, cells: tuple[CellRef, ...]) -> Ref | Literal:
        """把不同象限的NPC单格落到同一地面层，静态部分直接合成常量。"""
        if len(cells) != 4:
            raise ValueError("基础层需要四个象限")
        key = tuple(cell.npc for cell in cells)
        if key in self.layers:
            return self.layers[key]
        static = [self.npc_codes.get(cell.npc, EMPTY) for cell in cells]
        result: Ref | Literal = Literal(self.rules.parse("".join(static))) if any(code != EMPTY for code in static) else Literal(None)
        for q, cell in enumerate(cells):
            if cell.npc in self.npc_codes:
                continue
            rotated = cell.npc
            for _ in range(1 if q == 3 else q):
                rotated = self.circuit.add("VirtualRotatorCCW" if q == 3 else "VirtualRotator", rotated)
            if isinstance(result, Literal) and result.value is None:
                result = rotated
                continue
            lower_empty = self.circuit.add("LogicGateCompare", result, Literal(None), config="AQ==")
            upper_empty = self.circuit.add("LogicGateCompare", rotated, Literal(None), config="AQ==")
            stacked = self.circuit.add("VirtualStacker", result, rotated)
            upper_only = self.circuit.add("LogicGateIf", rotated, lower_empty)
            lower_only = self.circuit.add("LogicGateIf", result, upper_empty)
            self.circuit.aliases.append((stacked, upper_only, lower_only))
            result = stacked
        self.layers[key] = result
        return result

    def emit(self, condition: Ref, opcode: int, a: int = 0, b: int = 0,
             destination: int | Ref | None = None, base: Ref | Literal = Literal(None),
             color: Ref | Literal = Literal(None)) -> None:
        if self.booleans.get(condition) != 0:
            self.instructions.append(Instruction(condition, opcode, a, b,
                                                 a if destination is None else destination, base, color))

    def begin(self, condition: Ref) -> int | None:
        """用一个不可发出的控制行，跳过整段目标条件不成立的宏。"""
        if condition in self.booleans:
            return None
        index = len(self.instructions)
        self.instructions.append(Instruction(self.zero, 0, branch=condition))
        return index

    def end(self, index: int | None) -> None:
        if index is not None:
            self.instructions[index] = replace(self.instructions[index], skip_to=len(self.instructions))

    def rotate(self, slot: int, turns: int, condition: Ref, destination: int | Ref | None = None) -> None:
        if turns % 4:
            self.emit(condition, {1: 1, 2: 3, 3: 2}[turns % 4], slot, destination=destination)

    def window(self, slot: int, start: int, condition: Ref) -> None:
        self.rotate(slot, -start, condition)
        self.emit(condition, 4, slot)
        self.rotate(slot, start, condition)

    def join(self, first: int, second: int, start: int, condition: Ref) -> None:
        self.rotate(first, -start, condition)
        self.rotate(second, -start, condition)
        self.emit(condition, 8, first, second)
        self.rotate(first, start, condition)

    def column(self, cells: tuple[CellRef, ...], q: int, work: int, condition: Ref,
               known_crystal: bool = False) -> None:
        """使用范围仅为连续独立列；空尾保留为条件，C下方不允许任意间隙。"""
        if len(cells) != 5:
            raise ValueError("独立列微程序需要五个原层位")
        empty = self.cell(EMPTY)
        copper = self.cell("Cu")
        has_crystal = self.one if known_crystal else self.or_(*(cell.crystal for cell in cells))
        ordinary_mode = self.and_(condition, self.not_(has_crystal))
        for z, cell in enumerate(cells):
            active = self.and_(ordinary_mode, cell.occupied)
            row = self.layer((cell, empty, empty, empty))
            self.emit(active, 14, destination=work if z == 0 else work + 1, base=row)
            if z:
                self.emit(active, 7, work, work + 1)
        crystal_mode = self.and_(condition, has_crystal)
        prefix = self.one
        prefixes = []
        for cell in cells:
            prefix = self.and_(prefix, cell.pin)
            prefixes.append(prefix)
        higher = [self.or_(*(cell.crystal for cell in cells[z:])) for z in range(5)]
        for z, cell in enumerate(cells):
            active = self.and_(crystal_mode, higher[z], self.not_(prefixes[z]))
            first = self.and_(prefixes[z - 1] if z else self.one, self.not_(cell.pin))
            destination = self.pick(first, self.const(work), self.const(work + 1))
            self.emit(active, 14, destination=destination, base=self.layer((cell, copper, copper, copper)))
            self.emit(self.and_(active, self.not_(first)), 7, work, work + 1)
            self.emit(self.and_(active, cell.crystal), 10, work, color=cell.color)
        self.window(work, 3, crystal_mode)
        self.window(work, 0, crystal_mode)
        for prefix in prefixes:
            self.emit(self.and_(crystal_mode, prefix), 6, work)
        for z, cell in enumerate(cells):
            active = self.and_(crystal_mode, self.not_(higher[z]), cell.occupied)
            self.emit(active, 14, destination=work + 1, base=self.layer((cell, empty, empty, empty)))
            self.emit(active, 7, work, work + 1)
        self.rotate(work, q, condition)

    def independent(self, columns: dict[int, tuple[CellRef, ...]], work: int, condition: Ref) -> None:
        """调用者列出已知非空列；每半面逐列拼合后再拼两个半面。"""
        groups = [[q for q in sorted(columns) if q // 2 == side] for side in (0, 1)]
        present = [group for group in groups if group]
        for index, group in enumerate(present):
            slot = work + index
            self.column(columns[group[0]], group[0], slot, condition)
            for q in group[1:]:
                self.column(columns[q], q, slot + 1, condition)
                self.join(slot, slot + 1, q - 2, condition)
        if len(present) == 2:
            self.join(work, work + 1, 0, condition)

    def simple(self, cells: tuple[CellRef, ...], near: int, work: int, condition: Ref) -> None:
        empty, copper, pin, crystal = (self.cell(code) for code in (EMPTY, "Cu", PIN, "cr"))
        outgoing: list[list[Ref]] = [[] for _ in range(5)]
        incoming: list[list[tuple[Ref, CellRef]]] = [[] for _ in range(5)]
        for z in range(1, 5):
            gap = self.and_(cells[z].crystal, self.not_(cells[z - 1].occupied))
            for lower in range(z - 1):
                nearest = self.and_(gap, cells[lower].occupied,
                                    self.not_(self.or_(*(cell.occupied for cell in cells[lower + 1:z - 1]))))
                outgoing[lower].append(nearest)
                incoming[z - 1].append((nearest, cells[lower]))
        source = []
        helper = []
        deleted = []
        higher = [self.or_(*(cell.crystal for cell in cells[z:])) for z in range(5)]
        for z, cell in enumerate(cells):
            moved = self.choose(self.or_(*outgoing[z]), empty, cell)
            for chosen, original in incoming[z]:
                moved = self.choose(chosen, original, moved)
            vanish = self.and_(higher[z], self.not_(moved.occupied))
            deleted.append(vanish)
            source.append(self.choose(vanish, crystal, moved))
            helper.append(self.choose(self.or_(*(chosen for chosen, _ in incoming[z])), pin, copper))
        has_crystal = higher[0]
        prefix = tuple(self.choose(higher[z], cell, empty) for z, cell in enumerate(source))
        self.column(prefix, 0, work, self.and_(condition, has_crystal), known_crystal=True)
        for z in range(5):
            row = [empty] * 4
            row[0] = self.choose(self.not_(higher[z]), source[z], empty)
            row[near] = helper[z]
            if z == 0:
                destination = self.pick(has_crystal, self.const(work + 1), self.const(work))
            else:
                destination = work + 1
            self.emit(condition, 14, destination=destination, base=self.layer(tuple(row)))
            self.emit(self.and_(condition, has_crystal if z == 0 else self.one), 7, work, work + 1)
        with_far = self.and_(condition, self.or_(*deleted))
        far_block = self.begin(with_far)
        far = 4 - near
        self.column(tuple(self.choose(flag, crystal, copper) for flag in deleted), far, work + 1,
                    with_far, known_crystal=True)
        start = 0 if near == 1 else 3
        self.join(work, work + 1, start, with_far)
        self.window(work, start, with_far)
        self.end(far_block)

    def hard(self, cells: tuple[CellRef, ...], cases: dict[str, Ref], near: int, work: int, condition: Ref) -> None:
        """五组难列共用支撑转交流程，只选择初始列、锚列和最后补料。"""
        empty, copper, pin, crystal = (self.cell(code) for code in (EMPTY, "Cu", PIN, "cr"))
        far = 4 - near
        start = 0 if near == 1 else 3
        opposite = 3 if near == 1 else 0
        low = cases["-N-C"]
        two_gaps = cases["-N--C"]
        empty_bottom = self.or_(cases["--N-C"], two_gaps)
        first_normal = self.choose(cases["N-N-C"], self.typed(cells[0], "N"), crystal)
        second = self.choose(low, self.typed(cells[1], "N"), first_normal)
        third_normal = self.choose(two_gaps, self.typed(cells[1], "N"), self.typed(cells[2], "N"))
        third = self.choose(low, self.typed(cells[3], "C"), third_normal)
        fourth = self.choose(low, self.choose(cells[4].crystal, self.typed(cells[4], "C"), empty),
                             self.typed(cells[4], "C"))
        full = (crystal, second, third, fourth, empty)
        far_initial = (self.choose(cases["P-N-C"], copper, crystal),
                       self.choose(empty_bottom, crystal, copper), copper, copper, copper)
        anchor = (self.choose(self.or_(low, two_gaps), crystal, copper),
                  self.choose(low, copper, crystal), self.choose(low, empty, copper), empty, empty)
        self.independent({0: full, near: (copper,) * 5, far: far_initial}, work, condition)
        self.window(work, start, condition)
        self.column((copper,) * 5, far, work + 1, condition)
        self.join(work, work + 1, start, condition)
        self.window(work, opposite, condition)
        self.column(anchor, near, work + 1, condition, known_crystal=True)
        self.join(work, work + 1, opposite, condition)
        self.window(work, start, condition)
        far_tail = (pin, pin, self.choose(low, copper, pin), self.choose(low, empty, copper), empty)
        self.independent({2: (crystal,) * 5, far: far_tail}, work + 1, condition)
        self.join(work, work + 1, start, condition)
        self.emit(condition, 6, work)
        for cell, needed in ((pin, self.one), (self.choose(two_gaps, pin, copper), self.one),
                             (copper, self.or_(low, two_gaps))):
            active = self.and_(condition, needed)
            row = tuple(cell if q == near else empty for q in range(4))
            self.emit(active, 14, destination=work + 1, base=self.layer(row))
            self.emit(active, 7, work, work + 1)
        ordinary = self.and_(cells[4].occupied, self.not_(cells[4].crystal))
        extra = self.and_(condition, low, ordinary)
        self.emit(extra, 14, destination=work + 1, base=self.layer((cells[4], empty, empty, empty)))
        self.emit(extra, 7, work, work + 1)
        self.window(work, start, condition)

    def angle(self, cells: tuple[CellRef, ...], near: int, work: int, condition: Ref) -> None:
        flags = []
        for cell in cells:
            flags.append({"-": self.not_(cell.occupied), "P": cell.pin, "C": cell.crystal,
                          "N": self.and_(cell.occupied, self.not_(self.or_(cell.pin, cell.crystal)))})
        cases = {pattern: self.and_(*(flags[z][kind] for z, kind in enumerate(pattern)))
                 for pattern in ("-N-C", "N-N-C", "P-N-C", "--N-C", "-N--C")}
        hard = self.or_(*cases.values())
        hard_condition = self.and_(condition, hard)
        block = self.begin(hard_condition)
        self.hard(cells, cases, near, work, hard_condition)
        self.end(block)
        simple_condition = self.and_(condition, self.not_(hard))
        block = self.begin(simple_condition)
        self.simple(cells, near, work, simple_condition)
        self.end(block)


def half_body(program: CornerProgram, columns: tuple[tuple[CellRef, ...], ...]) -> tuple[Ref, Ref]:
    """在槽0起制造两角并合并；调用者另发最后半切，可按遍次复用本体。"""
    if len(columns) != 2 or any(len(column) != 5 for column in columns):
        raise ValueError("半形程序需要两列，每列五个原层位")
    present = [program.or_(*(cell.occupied for cell in column)) for column in columns]
    block = program.begin(present[0])
    program.angle(columns[0], 3, 0, present[0])
    program.end(block)
    block = program.begin(present[1])
    program.angle(columns[1], 1, 1, present[1])
    destination = program.pick(present[0], program.const(1), program.const(0))
    program.rotate(1, 1, present[1], destination=destination)
    program.end(block)
    program.join(0, 1, 3, program.and_(*present))
    return present[0], present[1]


def half_program(circuit: Circuit, decoded: DecodedShape) -> tuple[Instruction, ...]:
    """两列标准半形：先造两角，必要时拼接，再切去外侧NPC助手。"""
    program = CornerProgram(circuit)
    columns = tuple(tuple(program.original(row[q]) for row in decoded.cells) for q in (0, 1))
    half_body(program, columns)
    program.emit(program.one, 4, 0)
    return tuple(program.instructions)
