"""按列 A 的落点安排制角调用，三空槽在四角之间复用。"""


def corner_column_ccw(column: int) -> bool:
    return (column == 0) | (column == 2)


def corner_job_selector(phase: int, suspended: bool, highest: int, pins: int,
                        far: bool, counterclockwise: bool) -> int:
    if phase == 14:
        if not counterclockwise:
            return 2
        return 0
    if phase == 0:
        if highest >= 0:
            return 1
        return 0
    if suspended:
        if (phase == 2) | (phase == 6) | (phase == 8):
            return 1
        if (phase == 4) | (phase == 9) | (phase == 12):
            return 4
        if (phase == 3) | (phase == 5) | (phase == 7) | (phase == 10) | (phase == 11) | (phase == 13):
            return 2
        return 0
    if phase == 1 and (highest >= 0) and (pins > 0):
        return 2
    if phase == 2:
        return 4
    if far:
        if phase == 3:
            return 1
        if phase == 4:
            return 2
    return 0


def corner_dense_role(phase: int, suspended: bool) -> int:
    if phase == 6:
        return 2
    if phase == 8:
        return 3
    if phase != 0:
        return 1
    return 0


def corner_dense_destination(phase: int, main: int) -> int:
    if phase == 0:
        return main
    return 3


def corner_dense_scratch(phase: int, main: int) -> int:
    if phase == 0:
        return 3
    return 4


def corner_append_mode(phase: int, suspended: bool) -> int:
    if suspended and phase == 4:
        return 1
    if phase == 9:
        return 2
    return 0


def corner_append_lower(phase: int, main: int) -> int:
    if phase == 4:
        return 3
    if phase == 9:
        return 4
    return main


def corner_append_upper(phase: int, main: int) -> int:
    if phase == 4:
        return 4
    if phase == 9:
        return 5
    return 3


def corner_append_initial(phase: int, main: int, highest: int) -> int:
    if (phase == 12) | ((phase == 2) & (highest >= 0)):
        return main
    return -1


def corner_release_stage(phase: int, suspended: bool) -> int:
    if phase == 14:
        return 8
    if suspended:
        if phase == 3:
            return 4
        if phase == 5:
            return 5
        if phase == 7:
            return 1
        if phase == 10:
            return 6
        if phase == 11:
            return 2
        if phase == 13:
            return 7
    if phase == 1:
        return 3
    return 0


def corner_release_main(phase: int, main: int) -> int:
    if phase == 10:
        return 3
    return main


def corner_release_support(phase: int, main: int) -> int:
    if phase == 10:
        return 4
    return 3


def corner_release_far(phase: int, main: int) -> int:
    return 4


def corner_release_upper(phase: int, main: int) -> int:
    return 5


def corner_job_successor(phase: int) -> int:
    if 0 <= phase and phase < 8:
        return (1, 2, 3, 4, 5, 6, 7, 8)[phase]
    if phase == 8:
        return 9
    if phase == 9:
        return 10
    if phase == 10:
        return 11
    if phase == 11:
        return 12
    if phase == 12:
        return 13
    if phase == 13:
        return 14
    return 15


def corner_job_next(phase: int, enable: bool, settled: bool, selector: int, confirmed: bool, successor: int) -> int:
    if not enable:
        return 0
    if settled & ((selector == 0) | confirmed):
        return successor
    return phase


def corner_job_done(phase: int, enable: bool, settled: bool, selector: int, confirmed: bool, successor: int) -> bool:
    return enable & (phase == 15)
