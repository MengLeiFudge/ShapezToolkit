"""紧柱逐层调用只保留待结晶色与当前层。"""

from .column_build import dense_column_pending
from .physics import Shape
from .shape_methods import Color


_DYES = (None, "r", "g", "b", "c", "m", "y", "w")


def dense_stream_color(dye: int, present: int) -> Color | None:
    if dye < 1 or dye > 7:
        return None
    return _DYES[dye]


def dense_stream_assembled(dye: int, present: int) -> bool:
    return present == 1


def dense_stream_next_dye(phase: int, dye: int, row: Shape | None, pending: Color | None,
                          enable: bool, settled: bool, has_packet: bool, confirmed: bool) -> int:
    if not enable:
        return 0
    if (phase != 2) | (not settled) | (has_packet & (not confirmed)):
        return dye
    color = dense_column_pending(None, pending, row)
    if color == "r":
        return 1
    if color == "g":
        return 2
    if color == "b":
        return 3
    if color == "c":
        return 4
    if color == "m":
        return 5
    if color == "y":
        return 6
    if color == "w":
        return 7
    return 0


def dense_stream_next_presence(phase: int, present: int, row: Shape | None,
                               enable: bool, settled: bool, has_packet: bool, confirmed: bool) -> int:
    if not enable:
        return 0
    if (phase == 2) & settled & ((not has_packet) | confirmed) & (row is not None):
        return 1
    return present
