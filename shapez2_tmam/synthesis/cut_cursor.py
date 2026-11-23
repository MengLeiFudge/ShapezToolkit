"""按顺序尝试双半形起点的两个切向。"""


# 0/3 等闭包完工，1/4 等列判据稳定。2 切换方向和复位，5/6/7 保存结论。


def next_cut_phase(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> int:
    if not enable:
        return 0
    if not (settled & confirmed):
        return phase
    if phase == 0 and done:
        return 1
    if phase == 1 and done:
        if has_prefix:
            return 5
        return 2
    if phase == 2 and not done:
        return 3
    if phase == 3 and done:
        return 4
    if phase == 4 and done:
        if has_prefix:
            return 6
        return 7
    return phase


def cut_start(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> bool:
    return enable & (phase >= 0) & (phase <= 6) & (phase != 2)


def cut_alternate(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> bool:
    return enable & ((phase == 2) | (phase == 3) | (phase == 4) | (phase == 6))


def cut_chosen(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> bool:
    return enable & ((phase == 5) | (phase == 6))


def cut_exhausted(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> bool:
    return enable & (phase == 7)


def cut_terminal(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> bool:
    return enable & (phase >= 5)


def cut_event(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> bool:
    waiting = (phase == 0) | (phase == 1) | (phase == 3) | (phase == 4)
    return enable & ((waiting & done) | ((phase == 2) & (not done)))


def cut_address(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> int:
    return 0


def cut_event_opcode(phase: int, enable: bool, settled: bool, confirmed: bool, done: bool, has_prefix: bool) -> int:
    return 1
