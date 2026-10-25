"""用固定原目标标签表表示递归候选，不把候选网格伪造成原生图形原料。"""

from dataclasses import dataclass

from .circuit import Circuit, Literal, Ref
from .corner_program import CellRef, CornerProgram
from .decoder_circuit import DecodedShape
from .synthesis.physics import EMPTY, PIN


@dataclass(frozen=True)
class TaggedGrid:
    """原层位的材料与标签引用；valid要求每格编号均有真实表项。"""

    columns: tuple[tuple[CellRef, ...], ...]
    valid: Ref


class TagPalette:
    """0空、1辅助Cu、2针、3辅助红C、4～23原目标的20格。"""

    def __init__(self, program: CornerProgram, decoded: DecodedShape):
        if len(decoded.cells) != 5 or any(len(row) != 4 for row in decoded.cells):
            raise ValueError("四象限标签表需要五层四列的固定原目标")
        self.program = program
        self.entries = tuple(program.cell(code) for code in (EMPTY, "Cu", PIN, "cr")) + tuple(
            program.original(cell) for row in decoded.cells for cell in row)
        self.lookups: dict[Ref, tuple[CellRef, Ref]] = {}

    def lookup(self, tag: Ref) -> tuple[CellRef, Ref]:
        """查一格；原目标空格编号和0～23以外的信号都作为无效编号。"""
        if tag in self.lookups:
            return self.lookups[tag]
        program = self.program
        circuit = program.circuit
        picks = []
        for index, cell in enumerate(self.entries):
            chosen = circuit.add("LogicGateCompare", tag, Literal(index), config="AQ==")
            picks.append(chosen if index < 4 else program.and_(chosen, cell.occupied))
        valid = program.or_(*picks)
        flags = [program.or_(*(program.and_(chosen, getattr(cell, name))
                               for chosen, cell in zip(picks, self.entries)))
                 for name in ("occupied", "pin", "crystal")]
        fields = []
        for name in ("npc", "color"):
            groups: dict[Ref, list[Ref]] = {}
            for chosen, cell in zip(picks, self.entries):
                groups.setdefault(getattr(cell, name), []).append(chosen)
            branches = [circuit.add("LogicGateIf", source, program.or_(*conditions))
                        for source, conditions in groups.items()]
            circuit.aliases.append(tuple(branches))
            fields.append(branches[0])
        result = CellRef(fields[0], flags[0], flags[1], flags[2], fields[1]), valid
        self.lookups[tag] = result
        return result

    def grid(self, tags: tuple[tuple[Ref, ...], ...]) -> TaggedGrid:
        """接收按列排列的20份ID，保持原五个层位；不执行重力或图形编码。"""
        if len(tags) != 4 or any(len(column) != 5 for column in tags):
            raise ValueError("候选网格需要四列、每列五个编号")
        lookups = tuple(tuple(self.lookup(tag) for tag in column) for column in tags)
        return TaggedGrid(tuple(tuple(cell for cell, _ in column) for column in lookups),
                          self.program.and_(*(valid for column in lookups for _, valid in column)))


def same_grid(program: CornerProgram, actual: DecodedShape, expected: TaggedGrid) -> Ref:
    """比较非空原生图形与网格；actual须按原层号解码，空格不比较颜色。"""
    if len(actual.cells) != 5 or any(len(row) != 4 for row in actual.cells):
        raise ValueError("图形比较需要按原层号解码的五层四列")
    if len(expected.columns) != 4 or any(len(column) != 5 for column in expected.columns):
        raise ValueError("目标网格比较需要四列、每列五格")
    circuit: Circuit = program.circuit
    clauses = [actual.valid, expected.valid]
    for z, row in enumerate(actual.cells):
        for q, decoded in enumerate(row):
            source = program.original(decoded)
            target = expected.columns[q][z]
            clauses.extend(circuit.add("LogicGateCompare", a, b, config="AQ==") for a, b in (
                (source.occupied, target.occupied), (source.pin, target.pin), (source.crystal, target.crystal)))
            npc = circuit.add("LogicGateCompare", source.npc, target.npc, config="AQ==")
            color = circuit.add("LogicGateCompare", source.color, target.color, config="AQ==")
            clauses.append(program.or_(program.not_(target.occupied), program.and_(npc, color)))
    return program.and_(*clauses)
