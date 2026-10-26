"""共用组编号传播及静止组剥离通路，精确核对顶针候选的F集合。"""

from dataclasses import dataclass

from .circuit import Literal, Ref
from .clocked_state import ClockedState
from .corner_program import CornerProgram
from .half_circuit import MaterialCell
from .pin_image_circuit import PinImageFlags


def _label_step(program: CornerProgram, cells: tuple[MaterialCell, ...], labels: tuple[Ref, ...]) -> tuple[Ref, ...]:
    """沿原始粘连边取最小编号；空格编号20始终不变。"""
    circuit = program.circuit
    nonpins = tuple(program.and_(cell.occupied, program.not_(cell.pin)) for cell in cells)
    following = []
    for i, cell in enumerate(cells):
        z, q = divmod(i, 4)
        neighbors = [(4 * z + (q + step) % 4, False) for step in (-1, 1)]
        neighbors += [(4 * r + q, True) for r in (z - 1, z + 1) if 0 <= r < 5]
        values = [labels[i]]
        for j, vertical in neighbors:
            edge = (program.and_(cell.crystal, cells[j].crystal) if vertical else
                    program.and_(nonpins[i], nonpins[j]))
            values.append(program.pick(edge, labels[j], program.const(20)))
        while len(values) > 1:
            following_values = []
            for k in range(0, len(values), 2):
                if k + 1 == len(values):
                    following_values.append(values[k])
                else:
                    a, b = values[k:k + 2]
                    less = circuit.add("LogicGateCompare", a, b, config="BA==")
                    following_values.append(program.pick(less, a, b))
            values = following_values
        following.append(values[0])
    return tuple(following)


def _stationary_step(program: CornerProgram, cells: tuple[MaterialCell, ...], labels: tuple[Ref, ...],
                     alive: tuple[Ref, ...]) -> tuple[Ref, ...]:
    """组内共享是否仍受地面或其他保留组阻挡，不将组内正下方格计作支撑。"""
    circuit = program.circuit
    owners = tuple(tuple(circuit.add("LogicGateCompare", label, Literal(g), config="AQ==")
                         for g in range(20)) for label in labels)
    supported = []
    for i, cell in enumerate(cells):
        if i < 4:
            supported.append(cell.occupied)
        else:
            same = circuit.add("LogicGateCompare", labels[i], labels[i - 4], config="AQ==")
            supported.append(program.and_(cell.occupied, cells[i - 4].occupied, alive[i - 4], program.not_(same)))
    groups = tuple(program.or_(*(program.and_(owners[i][g], supported[i]) for i in range(20))) for g in range(20))
    return tuple(program.and_(cells[i].occupied, program.or_(*(
        program.and_(owners[i][g], groups[g]) for g in range(20)))) for i in range(20))


@dataclass(frozen=True)
class StationaryCheck:
    """两段完成事件由外层FSM使用；matches只在剥离结束后的状态有效。"""

    labels_done: Ref
    stationary_done: Ref
    matches: Ref


def stationary_check(program: CornerProgram, bank: ClockedState, image: PinImageFlags,
                     start: Ref, labeling: Ref, peeling: Ref) -> StationaryCheck:
    """来源全程冻结；最多19轮编号、20轮剥离，整轮不变时提前结束。"""
    circuit = program.circuit
    cells = tuple(cell for row in image.live for cell in row)
    claimed = tuple(value for row in image.claimed_fixed for value in row)
    if len(cells) != 20 or len(claimed) != 20:
        raise ValueError("静止集合检查需要五层四列活格及推定F标记")
    labels = tuple(bank.add(20) for _ in cells)
    alive = tuple(bank.add() for _ in cells)
    count = tuple(bank.add() for _ in range(5))
    next_labels = _label_step(program, cells, labels)
    next_alive = _stationary_step(program, cells, labels, alive)

    def equals(bits: tuple[Ref, ...], value: int) -> Ref:
        return program.and_(*(bit if value & (1 << k) else program.not_(bit) for k, bit in enumerate(bits)))

    def unchanged(before: tuple[Ref, ...], after: tuple[Ref, ...]) -> Ref:
        return program.and_(*(circuit.add("LogicGateCompare", a, b, config="AQ==") for a, b in zip(before, after)))

    labels_done = program.and_(labeling, program.or_(equals(count, 18), unchanged(labels, next_labels)))
    stationary_done = program.and_(peeling, program.or_(equals(count, 19), unchanged(alive, next_alive)))
    advancing = program.or_(labeling, peeling)
    for k, bit in enumerate(count):
        value = circuit.add("LogicGateXOr", bit, program.and_(advancing, *count[:k]))
        bank.put(bit, value)
        bank.put(bit, 0, program.or_(start, labels_done))
    for i, (label, flag) in enumerate(zip(labels, alive)):
        bank.put(label, next_labels[i], labeling)
        bank.put(label, program.pick(cells[i].occupied, program.const(i), program.const(20)), start)
        bank.put(flag, next_alive[i], peeling)
        bank.put(flag, cells[i].occupied, start)
    return StationaryCheck(labels_done, stationary_done, unchanged(alive, claimed))
