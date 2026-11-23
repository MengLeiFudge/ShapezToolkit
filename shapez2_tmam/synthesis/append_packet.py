"""将当前待追加单层转换成六槽领料与堆叠指令。"""

from .physics import Shape


def append_packet_opcode(row: Shape | None, load: bool, has_lower: bool,
                         lower: int, upper: int) -> int:
    if (lower < 0) | (lower > 5) | (upper < 0) | (upper > 5) | (lower == upper) | (row is None):
        return 0
    if load:
        return 14
    if has_lower:
        return 7
    return 0


def append_packet_a(row: Shape | None, load: bool, has_lower: bool,
                    lower: int, upper: int) -> int:
    return lower


def append_packet_b(row: Shape | None, load: bool, has_lower: bool,
                    lower: int, upper: int) -> int:
    return upper


def append_packet_destination(row: Shape | None, load: bool, has_lower: bool,
                               lower: int, upper: int) -> int:
    if load & has_lower:
        return upper
    return lower


def append_packet_base(row: Shape | None, load: bool, has_lower: bool,
                       lower: int, upper: int) -> Shape | None:
    return row


def append_packet_active(row: Shape | None, load: bool, has_lower: bool,
                         lower: int, upper: int) -> bool:
    return append_packet_opcode(row, load, has_lower, lower, upper) != 0


def append_packet_stack(row: Shape | None, load: bool, has_lower: bool,
                        lower: int, upper: int) -> bool:
    return append_packet_opcode(row, load, has_lower, lower, upper) == 7


def append_packet_load(row: Shape | None, load: bool, has_lower: bool,
                       lower: int, upper: int) -> bool:
    return append_packet_opcode(row, load, has_lower, lower, upper) == 14
