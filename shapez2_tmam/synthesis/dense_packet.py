"""编译紧柱单步的六字段配方，供角的各路备料共用。"""

from .column_build import dense_column_base, dense_column_flush, dense_column_pending
from .physics import Shape
from .shape_methods import Color


# 工序 0～2 逐层执行换色、领料、堆叠。工序 3～7 在尾部执行结晶和取柱。


def dense_packet_opcode(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                        destination: int, scratch: int) -> int:
    if (destination < 0) | (destination > 5) | (scratch < 0) | (scratch > 5) | (destination == scratch):
        return 0
    if phase == 0:
        if dense_column_flush(None, pending, row) is not None:
            return 10
    if phase == 1 and row is not None:
        return 14
    if phase == 2 and assembled and row is not None:
        return 7
    if assembled:
        if phase == 3 and pending is not None:
            return 10
        if (phase == 4) | (phase == 6):
            return 4
        if phase == 5:
            return 1
        if phase == 7:
            return 2
    return 0


def dense_packet_has_step(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                          destination: int, scratch: int) -> bool:
    return dense_packet_opcode(phase, row, pending, assembled, destination, scratch) != 0


def dense_packet_uses_a(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                        destination: int, scratch: int) -> bool:
    opcode = dense_packet_opcode(phase, row, pending, assembled, destination, scratch)
    return (opcode != 0) & (opcode != 14)


def dense_packet_uses_b(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                        destination: int, scratch: int) -> bool:
    return dense_packet_opcode(phase, row, pending, assembled, destination, scratch) == 7


def dense_packet_a(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                   destination: int, scratch: int) -> int:
    return destination


def dense_packet_b(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                   destination: int, scratch: int) -> int:
    return scratch


def dense_packet_destination(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                             destination: int, scratch: int) -> int:
    if phase == 1 and assembled:
        return scratch
    return destination


def dense_packet_base(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                      destination: int, scratch: int) -> Shape | None:
    if phase == 1:
        return dense_column_base(None, pending, row)
    return None


def dense_packet_color(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                       destination: int, scratch: int) -> Color | None:
    if (phase == 0) | (phase == 3):
        return pending
    return None


def dense_packet_uses_base(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                           destination: int, scratch: int) -> bool:
    return dense_packet_opcode(phase, row, pending, assembled, destination, scratch) == 14


def dense_packet_uses_color(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                            destination: int, scratch: int) -> bool:
    return dense_packet_opcode(phase, row, pending, assembled, destination, scratch) == 10


def dense_packet_next_pending(phase: int, row: Shape | None, pending: Color | None, assembled: bool,
                              destination: int, scratch: int) -> Color | None:
    return dense_column_pending(None, pending, row)
