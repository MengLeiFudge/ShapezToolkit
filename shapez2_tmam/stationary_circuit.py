"""列A四象限顶针活图的静止格：下部按层支撑，上部两次往返传播。"""

from .circuit import Ref
from .corner_program import CornerProgram
from .pin_image_circuit import PinImageFlags
from .ring_circuit import row_reach


def stationary_matches(program: CornerProgram, image: PinImageFlags) -> Ref:
    """完整列A为前提；直接比较地面可达格与推定F，不建立迭代寄存器。"""
    cells = image.live
    if len(cells) != 5 or any(len(row) != 4 for row in cells) or len(image.claimed_fixed) != 5 or any(
            len(row) != 4 for row in image.claimed_fixed):
        raise ValueError("静止集合检查需要五层四列活格及推定F标记")
    nonpins = tuple(tuple(program.and_(cell.occupied, program.not_(cell.pin)) for cell in row) for row in cells)
    # 抬升后的第1层压在新增地面针上；第2层所有保留C也有第1层直接支撑。
    middle = row_reach(program, nonpins[2], tuple(program.and_(cells[2][q].occupied, cells[1][q].occupied)
                                                  for q in range(4)))
    lower = row_reach(program, nonpins[3], tuple(program.and_(cells[3][q].occupied, middle[q]) for q in range(4)))
    upper = row_reach(program, nonpins[4], tuple(program.and_(cells[4][q].occupied, lower[q]) for q in range(4)))
    lower = row_reach(program, nonpins[3], tuple(program.or_(lower[q], program.and_(
        cells[3][q].crystal, cells[4][q].crystal, upper[q])) for q in range(4)))
    upper = row_reach(program, nonpins[4], tuple(program.or_(upper[q], program.and_(
        cells[4][q].occupied, lower[q])) for q in range(4)))
    reached = (tuple(cell.occupied for cell in cells[0]), tuple(cell.occupied for cell in cells[1]), middle, lower, upper)
    return program.and_(*(program.circuit.add("LogicGateCompare", actual, claimed, config="AQ==")
                          for row, expected in zip(reached, image.claimed_fixed) for actual, claimed in zip(row, expected)))
