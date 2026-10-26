"""复用一个材料通路遍历四列S前缀，静态判新增NPC块的落点条件。"""

from .circuit import Literal, Ref
from .corner_program import CellRef, CornerProgram
from .program_controller import StateUpdate
from .synthesis.physics import EMPTY


def height_value(program: CornerProgram, choices: tuple[Ref, ...], *, first: int = 0) -> Ref:
    """把互斥的高度选择编码为整数；全未选时为空，只可用于未采用的分支。"""
    branches = tuple(program.circuit.add("LogicGateIf", Literal(first + index), choice)
                     for index, choice in enumerate(choices))
    program.circuit.aliases.append(branches)
    return branches[0]


class PrefixSearch:
    """四列仅遍历保留全部C的不同前缀；命中后冻结前态供制造程序使用。"""

    def __init__(self, program: CornerProgram, target: tuple[tuple[CellRef, ...], ...], *,
                 optional_top: Ref | None = None):
        if len(target) != 4 or any(len(column) != 5 for column in target):
            raise ValueError("S前缀搜索需要四列，每列五个原层位")
        self.program = program
        self.target = target
        circuit = program.circuit
        self.valid_heights = tuple(tuple(program.and_(
            column[height - 1].occupied if height else program.one,
            program.not_(program.or_(*(cell.crystal for cell in column[height:]))))
            for height in range(6)) for column in target)
        highest = tuple(tuple(program.and_(valid[height], program.not_(program.or_(*valid[height + 1:])))
                              for height in range(6)) for valid in self.valid_heights)
        self.initial = tuple(height_value(program, choices) for choices in highest)
        self.values = tuple(circuit.add("LogicGateIf", value, Literal(1)) for value in self.initial)
        self.found = circuit.add("LogicGateIf", Literal(0), Literal(1))
        self.exhausted = circuit.add("LogicGateIf", Literal(0), Literal(1))
        self.digits = tuple(tuple(circuit.add("LogicGateCompare", value, Literal(height), config="AQ==")
                                  for height in range(6)) for value in self.values)
        keep = tuple(tuple(program.or_(*self.digits[q][z + 1:]) for z in range(5)) for q in range(4))
        empty = program.cell(EMPTY)
        self.columns = tuple(tuple(program.choose(keep[q][z], target[q][z], empty)
                                   for z in range(5)) for q in range(4))
        self.delta = tuple(tuple(program.and_(cell.occupied, program.not_(keep[q][z]))
                                 for z, cell in enumerate(column)) for q, column in enumerate(target))
        self.required_delta = tuple(tuple(
            program.and_(value, program.or_(program.not_(optional_top), target[q][z].crystal))
            if z == 4 and optional_top is not None else value
            for z, value in enumerate(column)) for q, column in enumerate(self.delta))
        clauses = [program.or_(program.not_(cell.crystal), keep[q][z])
                   for q, column in enumerate(target) for z, cell in enumerate(column)]
        clauses.append(program.or_(*(cell.occupied for column in self.columns for cell in column)))
        for z in range(5):
            ordinary = tuple(program.and_(self.required_delta[q][z], program.not_(target[q][z].pin),
                                         program.not_(target[q][z].crystal)) for q in range(4))
            below = tuple(target[q][z - 1].occupied if z else program.one for q in range(4))
            supported = tuple(program.and_(ordinary[q], below[q]) for q in range(4))
            # 环上最多四格；传播三条水平边覆盖每个新增N块的全部成员。
            for _ in range(3):
                supported = tuple(program.or_(supported[q], program.and_(ordinary[q], program.or_(
                    supported[(q - 1) % 4], supported[(q + 1) % 4]))) for q in range(4))
            clauses.extend(program.or_(program.not_(ordinary[q]), supported[q]) for q in range(4))
            clauses.extend(program.or_(program.not_(program.and_(self.required_delta[q][z], target[q][z].pin)), below[q])
                           for q in range(4))
        self.appendable = program.and_(*clauses)

    def finish(self, available: Ref, scope: Ref) -> tuple[StateUpdate, ...]:
        """通过即冻结，否则移到该列下一个不同前缀；到列底再进位。"""
        program = self.program
        active = program.and_(scope, program.not_(self.found), program.not_(self.exhausted))
        accepted = program.and_(self.appendable, available)
        found = program.or_(self.found, program.and_(active, accepted))
        advance = program.and_(active, program.not_(accepted))
        lower_choices = []
        at_bottom = []
        for valid, digits in zip(self.valid_heights, self.digits):
            eligible = tuple(program.and_(valid[height], program.or_(*digits[height + 1:]))
                             for height in range(6))
            at_bottom.append(program.not_(program.or_(*eligible)))
            lower_choices.append(tuple(program.and_(eligible[height], program.not_(program.or_(*eligible[height + 1:])))
                                       for height in range(6)))
        last = program.and_(*at_bottom)
        exhausted = program.or_(self.exhausted, program.and_(advance, last))
        carry = advance
        next_values = []
        for q, value in enumerate(self.values):
            wrap = program.and_(carry, at_bottom[q])
            lower = height_value(program, lower_choices[q])
            next_value = program.pick(at_bottom[q], self.initial[q], lower)
            next_values.append(program.pick(carry, next_value, value))
            carry = wrap
        updates = [StateUpdate(read, source, initial)
                   for read, source, initial in zip(self.values, next_values, self.initial)]
        updates.extend((StateUpdate(self.found, found, 0), StateUpdate(self.exhausted, exhausted, 0)))
        return tuple(updates)
