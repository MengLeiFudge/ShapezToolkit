"""二代信号语义：Null、Conflict、整数、图形和颜色分别建模。

对应 SignalUtils、LogicGate*Simulation 与 Virtual*Simulation。这里只表达
门的稳定组合函数；传播延迟和反馈状态由控制器单独负责。
"""

import base64
import struct
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from . import shapes
from .shapes import Shape


class Special(Enum):
    """区别于整数与空信号的冲突标记；游戏中其真值为假。"""

    CONFLICT = "Conflict"


CONFLICT = Special.CONFLICT


@dataclass(frozen=True)
class Color:
    """游戏 ColorFluid 信号；与同字符的图形标签分开。"""

    code: str

    def __post_init__(self):
        if len(self.code) != 1 or self.code not in shapes.COLORS:
            raise ValueError(f"未知颜色：{self.code!r}")


Signal = Shape | Color | int | Special | None


def truthy(value: Signal) -> bool:
    """Null、Conflict 和整数零为假；负整数、图形、颜色为真。"""
    return value is not None and value is not CONFLICT and value != 0


def merge(values: Iterable[Signal]) -> Signal:
    """同线多源按值合并；Null 是单位元，相异非空值产生 Conflict。"""
    result = None
    for value in values:
        if result is None:
            result = value
        elif value is not None and value != result:
            return CONFLICT
    return result


def decode_constant(encoded: str) -> Signal:
    """读取蓝图 C 字段的 SignalSerializer 编码，拒绝未知或截断配置。"""
    raw = base64.b64decode(encoded, validate=True)
    simple = {b"\x01": None, b"\x02": CONFLICT, b"\x04": 0, b"\x05": 1}
    if raw in simple:
        return simple[raw]
    if raw[:1] == b"\x03" and len(raw) == 5:
        return struct.unpack("<i", raw[1:])[0]
    if raw[:3] == b"\x06\x01\x01" and len(raw) >= 5:
        length = struct.unpack("<H", raw[3:5])[0]
        if len(raw) == length + 5:
            return Shape.from_key(raw[5:].decode("ascii"))
    if raw[:2] == b"\x07\x01" and len(raw) == 3:
        return Color(raw[2:].decode("ascii"))
    raise ValueError(f"不支持的 Mari 信号配置：{raw.hex()}")


def describe(value: Signal) -> str | int | None:
    """返回可写入报告的信号，颜色显式加前缀。"""
    if isinstance(value, Shape):
        return value.to_key()
    if isinstance(value, Color):
        return "color:" + value.code
    if isinstance(value, Special):
        return value.value
    return value


def operate(operation: str, inputs: tuple[Signal, ...], config: int = 0) -> tuple[Signal, ...]:
    """执行一个门的组合方程；输入顺序与游戏端口索引一致。"""
    a = inputs[0]
    b = inputs[1] if len(inputs) > 1 else None
    if operation == "if":
        return (a if truthy(b) else None,)
    if operation == "not":
        return (int(not truthy(a)),)
    if operation == "and":
        return (int(truthy(a) and truthy(b)),)
    if operation == "or":
        return (int(truthy(a) or truthy(b)),)
    if operation == "xor":
        return (int(truthy(a) != truthy(b)),)
    if operation == "compare":
        if config == 1:
            return (int(a == b),)
        if config == 6:
            return (int(a != b),)
        if not isinstance(a, int) or not isinstance(b, int):
            return (0,)
        if config == 2:
            return (int(a >= b),)
        if config == 3:
            return (int(a > b),)
        if config == 4:
            return (int(a < b),)
        if config == 5:
            return (int(a <= b),)
        raise ValueError(f"未知比较方式：{config}")
    if operation not in ("analyze", "unstack", "rotate", "rotate_ccw", "cut_right",
                         "pin", "stack", "swap", "paint", "crystal"):
        raise ValueError(f"未知电路运算：{operation}")
    if not isinstance(a, Shape):
        return (None, None) if operation in ("analyze", "unstack", "swap") else (None,)
    if operation == "analyze":
        part, color = shapes.analyze(a)
        return part, Color(color) if color is not None else None
    if operation == "unstack":
        return shapes.unstack(a)
    if operation == "rotate":
        return (shapes.rotate(a),)
    if operation == "rotate_ccw":
        return (shapes.rotate(a, -1),)
    if operation == "cut_right":
        return (shapes.cut(a)[1],)
    if operation == "pin":
        return (shapes.push_pin(a),)
    if operation == "stack":
        return (shapes.stack(a, b) if isinstance(b, Shape) else None,)
    if operation == "swap":
        return shapes.swap_halves(a, b) if isinstance(b, Shape) else (None, None)
    if not isinstance(b, Color):
        return (None,)
    if operation == "paint":
        return (shapes.paint_top(a, b.code),)
    return (shapes.crystallize(a, b.code),)
