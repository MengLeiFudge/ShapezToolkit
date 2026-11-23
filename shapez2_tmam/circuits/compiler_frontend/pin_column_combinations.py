"""四列顶针候选顺序枚举的可编译推进方法。"""

from ...synthesis.physics import Shape


def select_word(column: int, q0: Shape, q1: Shape, q2: Shape, q3: Shape) -> Shape | None:
    if column == 0:
        return q0
    if column == 1:
        return q1
    if column == 2:
        return q2
    if column == 3:
        return q3
    return None


def retained_start(column: int, q0_next: int, q1_next: int, q2_next: int, q3_next: int) -> int:
    if column == 1:
        return q0_next
    if column == 2:
        return q1_next
    if column == 3:
        return q2_next
    if column == 4:
        return q3_next
    return 0


def next_column(column: int, start: int, restart: int, reset: bool,
                result_ready: bool, result_valid: bool, consume: bool) -> int:
    if reset:
        return 0
    if column == 4:
        if consume:
            return 3
        return 4
    if 0 <= column and column < 4:
        if result_ready:
            if result_valid:
                return (1, 2, 3, 4)[column]
            return (-1, 0, 1, 2)[column]
        return column
    return -1


def next_start(column: int, start: int, restart: int, reset: bool,
               result_ready: bool, result_valid: bool, consume: bool) -> int:
    if reset:
        return 0
    if column == 4:
        if consume:
            return restart
        return 0
    if 0 <= column and column < 4:
        if result_ready:
            if result_valid or column == 0:
                return 0
            return restart
        return start
    return 0


def update_value(lane: int, column: int, previous: int, result: int, empty: int,
                 reset: bool, result_ready: bool, result_valid: bool) -> int:
    if reset:
        return empty
    if result_ready and 0 <= column and column < 4:
        if column == lane and result_valid:
            return result
        if column <= lane:
            return empty
    return previous
