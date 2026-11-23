"""选择紧柱逐层发令所需的原格和当前结晶色。"""

from .column_build import dense_column_pending
from .physics import Shape
from .shape_methods import Color


def dense_input_row(row0: Shape | None, row1: Shape | None, row2: Shape | None,
                    row3: Shape | None, row4: Shape | None, level: int) -> Shape | None:
    if level == 0:
        return row0
    if level == 1:
        return row1
    if level == 2:
        return row2
    if level == 3:
        return row3
    if level == 4:
        return row4
    return None


def dense_input_pending(row0: Shape | None, row1: Shape | None, row2: Shape | None,
                        row3: Shape | None, row4: Shape | None, level: int) -> Color | None:
    if level <= 0:
        return None
    pending = dense_column_pending(None, None, row0)
    if level == 1:
        return pending
    pending = dense_column_pending(None, pending, row1)
    if level == 2:
        return pending
    pending = dense_column_pending(None, pending, row2)
    if level == 3:
        return pending
    pending = dense_column_pending(None, pending, row3)
    if level == 4:
        return pending
    return dense_column_pending(None, pending, row4)


def dense_input_assembled(row0: Shape | None, row1: Shape | None, row2: Shape | None,
                          row3: Shape | None, row4: Shape | None, level: int) -> bool:
    return (level > 0) & (row0 is not None)
