"""补齐含晶角各次备料之间的转向、接柱和顶针步骤。"""

from .packet_cursor import packet_done
from .physics import Shape
from .release_packet import release_a, release_b, release_base, release_destination, release_opcode, release_uses_b, release_word


def _attach_word(step: int, cross: bool) -> int:
    if cross:
        if step == 0:
            return 1
        if step == 1:
            return 13
        if step == 2:
            return 8
        if step == 3:
            return 2
    else:
        if step == 0:
            return 12
        if step == 1:
            return 8
    return 0


def corner_transform_word(stage: int, step: int, counterclockwise: bool, pins: int) -> int:
    if stage == 3:
        if step < pins:
            return 6
        return 0
    if (stage == 4) | (stage == 5):
        return _attach_word(step, counterclockwise == (stage == 4))
    return 0


def corner_finish_word(stage: int, step: int, counterclockwise: bool) -> int:
    if stage == 6:
        if step == 0:
            if counterclockwise:
                return 3
            return 1
        if step == 1:
            if counterclockwise:
                return 11
            return 13
        if step == 2:
            if counterclockwise:
                # 交换触顶针柱与红晶柱，产物仍写回红晶柱槽。
                return 38
            return 8
        if step == 3 and not counterclockwise:
            return 1
        return 0
    if stage == 7:
        if counterclockwise:
            if step == 0:
                return 1
            if step == 1:
                return 4
            if step == 2:
                return 2
        elif step == 0:
            return 4
    if stage == 8 and step == 0:
        return 1
    return 0


def corner_release_word(stage: int, step: int, counterclockwise: bool, support: int,
                        handoff_word: int, pins: int) -> int:
    if stage <= 2:
        return release_word(stage, step, counterclockwise, support, handoff_word)
    if stage <= 5:
        return corner_transform_word(stage, step, counterclockwise, pins)
    return corner_finish_word(stage, step, counterclockwise)


def corner_select_release_word(stage: int, release: int, transform: int, finish: int) -> int:
    if stage <= 2:
        return release
    if stage <= 5:
        return transform
    return finish


def corner_release_opcode(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    if word == 38:
        return 8
    return release_opcode(word, counterclockwise, main, support, far, upper)


def corner_release_a(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    if word == 38:
        return support
    return release_a(word, counterclockwise, main, support, far, upper)


def corner_release_b(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    if word == 38:
        return main
    return release_b(word, counterclockwise, main, support, far, upper)


def corner_release_uses_b(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return (word == 38) | release_uses_b(word, counterclockwise, main, support, far, upper)


def corner_release_destination(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> int:
    return release_destination(word, counterclockwise, main, support, far, upper)


def corner_release_base(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> Shape:
    return release_base(word, counterclockwise, main, support, far, upper)


def corner_release_active(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return word != 0


def corner_release_uses_base(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return (word == 14) | (word == 34)


def corner_release_uses_a(word: int, counterclockwise: bool, main: int, support: int, far: int, upper: int) -> bool:
    return (word != 0) & (word != 14) & (word != 34)


def corner_packet_done(step: int, selector: int, release_stage: int, enable: bool) -> bool:
    if selector == 2 and release_stage >= 3 and release_stage <= 8:
        return enable & (step >= 5)
    return packet_done(step, selector, release_stage, enable)
