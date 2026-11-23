"""生成四角备料所需的紧柱与触顶补形六字段指令。"""

from collections.abc import Sequence

from ...synthesis.physics import EMPTY, PIN, Rules
from .half_assembly import append_five_instructions
from .recipe import BASE, CRYSTAL, _packet, _slot


def _column_cells(rows: Sequence[str | None]) -> tuple[str, ...]:
    if len(rows) > 5:
        raise ValueError('紧柱最多五层')
    rules = Rules(4, 5)
    cells = []
    ended = False
    for row in rows:
        if row is None:
            ended = True
            continue
        shape = rules.parse(row)
        cell, *rest = shape.layers[0]
        if ended or len(shape.layers) != 1 or cell == EMPTY or any(part != EMPTY for part in rest):
            raise ValueError('紧柱原料须从底到顶连续，每层仅用 q0')
        if cell == 'cu':
            raise ValueError('紧柱结晶需要有效原色')
        cells.append(cell)
    return tuple(cells)


def _crystallize(slot: int, color: str) -> dict:
    return {**_packet(CRYSTAL, slot), 'color': 'color:' + color}


def dense_column_instructions(rows: Sequence[str | None], *, destination: int,
                              scratch_slot: int) -> tuple[dict, ...]:
    output, scratch = _slot(destination), _slot(scratch_slot)
    if output == scratch:
        raise ValueError('紧柱结果和上料需要不同的槽')
    cells = _column_cells(rows)
    if not cells:
        return ()
    if PIN in cells and any(cell.startswith('c') for cell in cells):
        raise ValueError('紧柱批量结晶会填满已有顶针，含晶柱的针尾须另行追加')

    packets = []
    pending = None
    for i, cell in enumerate(cells):
        if cell.startswith('c'):
            color = cell[1]
            if pending is not None and pending != color:
                packets.append(_crystallize(output, pending))
            pending = color
            cell = PIN
        packets.append(_packet(BASE, destination=output if i == 0 else scratch, base=cell + 'CuCuCu'))
        if i:
            packets.append(_packet(7, output, scratch))
    if pending is not None:
        packets.append(_crystallize(output, pending))
    packets.extend((_packet(4, output), _packet(1, output), _packet(4, output), _packet(2, output)))
    return tuple(packets)


def pin_complement_instructions(trigger_rows: Sequence[str | None], *, destination: int, trigger_slot: int,
                                scratch_slot: int, counterclockwise: bool) -> tuple[dict, ...]:
    output, trigger, scratch = (_slot(slot) for slot in (destination, trigger_slot, scratch_slot))
    if len({output, trigger, scratch}) != 3:
        raise ValueError('触顶补形需要三个不同的空槽')
    cells = _column_cells(trigger_rows)
    if not cells or any(cell.startswith('c') for cell in cells):
        raise ValueError('触顶柱需要连续的非晶体原料')

    spine = dense_column_instructions(('cr------',) * 5, destination=output, scratch_slot=scratch)
    post = append_five_instructions(trigger_rows, has_lower=False, lower_slot=trigger, upper_slot=scratch)
    if counterclockwise:
        return (*spine, *post, _packet(3, output), _packet(1, trigger),
                _packet(8, trigger, output, destination=output))
    return (*spine, *post, _packet(1, output), _packet(3, trigger), _packet(8, output, trigger),
            _packet(1, output))
