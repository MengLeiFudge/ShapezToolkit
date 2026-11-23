"""为直接释放和顶破交接生成当前六槽指令。"""

from .physics import Shape
from .shape_methods import shape_literal


# 1～8 通常操作主槽，11～13 转辅助槽。
# 14 领远柱首层，34 领上料，27 堆叠远柱，28 将主形与远柱交换。


def release_word(stage: int, step: int, counterclockwise: bool, support: int, handoff_word: int) -> int:
    if support < 0 or support > 5:
        return 0
    if stage == 1:
        return handoff_word
    simple = stage == 0
    top_break = stage == 2
    if ((step == 2) & simple) | ((step == 1) & top_break):
        return 8
    if step == 3:
        if simple:
            return 4
        if top_break:
            return 6
    if simple & (step == 1):
        if counterclockwise:
            return 13
        return 12
    if counterclockwise:
        if ((step == 4) & simple) | ((step == 2) & top_break):
            return 2
        if step == 0:
            if simple:
                return 1
            if top_break:
                return 11
    return 0


def release_handoff_word(step: int, counterclockwise: bool) -> int:
    # 两方向均从步 1 开始切主形，之后共用五层远柱的领料和堆叠。
    if (step == 1) | (step == 13) | (step == 17):
        return 4
    if (step == 3) | (step == 5) | (step == 7) | (step == 9):
        return 34
    if (step == 4) | (step == 6) | (step == 8) | (step == 10):
        return 27
    if step == 2:
        return 14
    if step == 11:
        return 28
    if step == 15:
        return 8
    if step == 12:
        if counterclockwise:
            return 2
        return 1
    if step == 14:
        if counterclockwise:
            return 12
        return 13
    if step == 16:
        if counterclockwise:
            return 1
        return 2
    if step == 0 and counterclockwise:
        return 1
    return 0


def release_opcode(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    if (word == 14) | (word == 34):
        return 14
    if (word == 8) | (word == 28):
        return 8
    if (word == 1) | (word == 11):
        return 1
    if (word == 2) | (word == 12):
        return 2
    if word == 13:
        return 3
    if word == 27:
        return 7
    return word


def release_a(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    if (word == 11) | (word == 12) | (word == 13):
        return support
    if word == 27:
        return far
    return main


def release_b(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    if word == 27:
        return upper
    if word == 28:
        return far
    return support


def release_destination(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    if word == 34:
        return upper
    if word == 14:
        return far
    return release_a(word, counterclockwise, main, support, far, upper)


def release_base(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> Shape:
    if counterclockwise:
        return shape_literal("----Cu--")
    return shape_literal("------Cu")


def release_has_packet(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return word != 0


def release_uses_a(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return (word != 0) & (word != 14) & (word != 34)


def release_uses_b(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return (word == 8) | (word == 27) | (word == 28)


def release_uses_base(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return (word == 14) | (word == 34)
