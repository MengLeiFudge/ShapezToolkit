"""Python 方法与 Shapez 2 蓝图后端共用的类型、控制流和图形内建操作。"""

from dataclasses import dataclass
from enum import Enum


class ValueType(str, Enum):
    BOOL = "bool"
    INT = "int"
    SHAPE = "shape"
    COLOR = "color"


@dataclass(frozen=True)
class Variable:
    name: str
    type: ValueType


@dataclass(frozen=True)
class Reference:
    name: str


@dataclass(frozen=True)
class Constant:
    # int 为有符号 32 位。图形用短代码，颜色用单字符，None 仅表示空图形或空颜色。
    type: ValueType
    value: bool | int | str | None


Operand = Reference | Constant


# 同类型值可用 eq/ne，包含图形、颜色和各自的空值。
# 虚拟二元加工的任一操作数为空时，得到空图形。
BOOL, INT, SHAPE, COLOR = ValueType
BUILTINS = {
    "not": ((BOOL,), BOOL),
    "and": ((BOOL, BOOL), BOOL),
    "or": ((BOOL, BOOL), BOOL),
    "lt": ((INT, INT), BOOL),
    "le": ((INT, INT), BOOL),
    "add": ((INT, INT), INT),
    "rotate_cw": ((SHAPE,), SHAPE),
    "rotate_ccw": ((SHAPE,), SHAPE),
    "cut_front": ((SHAPE,), SHAPE),
    "cut_back": ((SHAPE,), SHAPE),
    "pin": ((SHAPE,), SHAPE),
    "stack": ((SHAPE, SHAPE), SHAPE),
    "swap_front_a": ((SHAPE, SHAPE), SHAPE),
    "swap_front_b": ((SHAPE, SHAPE), SHAPE),
    "crystal": ((SHAPE, COLOR), SHAPE),
    # 拆层保留原下半层号，顶层移到地面。分析读取底层 q0。
    "unstack_lower": ((SHAPE,), SHAPE),
    "unstack_upper": ((SHAPE,), SHAPE),
    "analyze_part": ((SHAPE,), SHAPE),
    "analyze_color": ((SHAPE,), COLOR),
}


@dataclass(frozen=True)
class Bind:
    target: str
    value: Operand


@dataclass(frozen=True)
class Apply:
    # operation 为 BUILTINS 的键或同类型比较 eq/ne。stack 依次接下料、上料。
    target: str
    operation: str
    args: tuple[Operand, ...]


@dataclass(frozen=True)
class Call:
    target: str
    function: str
    args: tuple[Operand, ...]


Instruction = Bind | Apply | Call


@dataclass(frozen=True)
class Jump:
    target: str


@dataclass(frozen=True)
class Branch:
    condition: Operand
    if_true: str
    if_false: str


@dataclass(frozen=True)
class Return:
    value: Operand


@dataclass(frozen=True)
class Block:
    # 块内指令顺序执行，于出口处选择下一个块。参数与局部变量共享命名空间。
    name: str
    instructions: tuple[Instruction, ...]
    end: Jump | Branch | Return


@dataclass(frozen=True)
class Function:
    # blocks[0] 是入口。max_block_visits 是一次调用访问本函数块的总上界，不计入子调用。
    # 前端负责证明局部变量赋值、整数范围、循环上界及无递归调用。
    name: str
    inputs: tuple[Variable, ...]
    result: ValueType
    locals: tuple[Variable, ...]
    blocks: tuple[Block, ...]
    max_block_visits: int


@dataclass(frozen=True)
class Program:
    entry: str
    functions: tuple[Function, ...]
    quadrants: int = 4
    height: int = 5
