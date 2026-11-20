"""半形两角时序复用；第二角以象限置换和旋转方向变换制造。"""

from .circuit import Literal, Ref
from .corner_program import CellRef, CornerProgram
from .decoder_circuit import DecodedCell


def shared_half_body(program: CornerProgram, columns: tuple[tuple[CellRef, ...], ...], second: Ref) -> tuple[Ref, int, int]:
    """所有标准半形统一用两角构造；共用槽0～3，第一角暂存槽4。"""
    if len(columns) != 2 or any(len(column) != 5 for column in columns):
        raise ValueError("共用两角程序需要两列各五个原层位")
    present = tuple(program.or_(*(cell.occupied for cell in column)) for column in columns)
    selected = tuple(program.choose(second, columns[1][z], columns[0][z]) for z in range(5))
    active = program.pick(second, present[1], present[0])
    block = program.begin(active)
    program.angle(selected, 3, 0, active)
    program.end(block)
    mirror_limit = len(program.instructions)
    program.rotate(0, 2, program.and_(program.not_(second), present[0]), destination=4)
    repeat_at = len(program.instructions) - 1
    both = program.and_(*present)
    program.rotate(4, 3, both)
    program.rotate(0, 1, both)
    program.emit(both, 8, 4, 0, destination=0)
    program.rotate(0, 3, both)
    program.rotate(4, 2, program.and_(present[0], program.not_(present[1])), destination=0)
    present_any = program.or_(*present)
    program.emit(present_any, 4, 0)
    return present_any, repeat_at, mirror_limit


def mirror_packet(program: CornerProgram, packet: dict[str, Ref], enabled: Ref) -> None:
    """就地变换角主体包：σ(q)=1−q，顺逆旋转互换，其余操作保持。"""
    circuit = program.circuit
    rotated = packet["base"]
    cells = []
    for q in range(4):
        if q == 3:
            rotated = circuit.add("VirtualRotator", packet["base"])
        elif q:
            rotated = circuit.add("VirtualRotatorCCW", rotated)
        analyzed = circuit.add("VirtualAnalyzer", rotated)
        cells.append(program.original(DecodedCell(
            analyzed, Ref(analyzed.node, 1),
            circuit.add("LogicGateCompare", analyzed, Literal(None), config="Bg=="),
            circuit.add("LogicGateCompare", analyzed, program.cell("P-").npc, config="AQ=="), program.zero)))
    reflected = program.layer(tuple(cells[(1 - q) % 4] for q in range(4)))
    if isinstance(reflected, Literal):
        raise ValueError("动态基础层置换必须生成信号通路")
    packet["base"] = program.pick(enabled, reflected, packet["base"])
    opcode = packet["opcode"]
    clockwise = circuit.add("LogicGateCompare", opcode, Literal(1), config="AQ==")
    anticlockwise = circuit.add("LogicGateCompare", opcode, Literal(2), config="AQ==")
    transformed = program.pick(clockwise, program.const(2), program.pick(anticlockwise, program.one, opcode))
    packet["opcode"] = program.pick(enabled, transformed, opcode)
