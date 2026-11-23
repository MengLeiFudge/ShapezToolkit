"""按十次行闭包的依赖顺序调用同一份支撑传播方法。"""


def support_scan_row(step: int) -> int:
    if (step == 0) | (step == 11):
        return 0
    if (step == 1) | (step == 12):
        return 1
    if (step == 2) | (step == 6) | (step == 13):
        return 2
    if (step == 3) | (step == 5) | (step == 7) | (step == 9) | (step == 14):
        return 3
    if (step == 4) | (step == 8) | (step == 10) | (step == 15):
        return 4
    return -1


def support_scan_down(step: int) -> bool:
    return (step == 5) | (step == 6) | (step == 9)


def support_scan_neighbor(step: int) -> int:
    if (step == 2) | (step == 13):
        return 1
    if (step == 3) | (step == 7) | (step == 14):
        return 2
    if (step == 4) | (step == 6) | (step == 8) | (step == 10) | (step == 15):
        return 3
    if (step == 5) | (step == 9):
        return 4
    if (step == 1) | (step == 12):
        return 0
    return -1


def support_scan_check(step: int) -> bool:
    return (step >= 11) & (step <= 15)
