"""推进共用的释放、拼合和逐层追加指令。"""

from .physics import Shape



def packet_step_done(step: int, selector: int, release_stage: int) -> bool:
    if selector == 2:
        if release_stage == 0:
            return step >= 5
        if release_stage == 1:
            return step >= 18
        if release_stage == 2:
            return step >= 4
    if selector == 3:
        return step >= 5
    if selector == 4:
        return step >= 10
    return True


def packet_successor_low(step: int) -> int:
    if step >= 0 and step < 9:
        return (1, 2, 3, 4, 5, 6, 7, 8, 9)[step]
    return 18


def packet_successor_high(step: int) -> int:
    if step == 9:
        return 10
    if step == 10:
        return 11
    if step == 11:
        return 12
    if step == 12:
        return 13
    if step == 13:
        return 14
    if step == 14:
        return 15
    if step == 15:
        return 16
    if step == 16:
        return 17
    return 18


def packet_next_step(step: int, successor_low: int, successor_high: int, terminal: bool,
                     enable: bool, settled: bool, has_packet: bool, confirmed: bool) -> int:
    if not enable:
        return 0
    if (not terminal) & settled & ((not has_packet) | confirmed):
        if step < 9:
            return successor_low
        return successor_high
    return step


def packet_done(step: int, selector: int, release_stage: int, enable: bool) -> bool:
    return enable & packet_step_done(step, selector, release_stage)


def append_step_level(step: int, initial_lower: int, appended: int) -> int:
    if (step == 0) | (step == 1):
        return 0
    if (step == 2) | (step == 3):
        return 1
    if (step == 4) | (step == 5):
        return 2
    if (step == 6) | (step == 7):
        return 3
    if (step == 8) | (step == 9):
        return 4
    return -1


def append_step_load(step: int, initial_lower: int, appended: int) -> bool:
    return (step == 0) | (step == 2) | (step == 4) | (step == 6) | (step == 8)


def append_step_has_lower(step: int, initial_lower: int, appended: int) -> bool:
    return (initial_lower >= 0) | (appended == 1)


def append_next_presence(step: int, selector: int, row: Shape | None, appended: int,
                         enable: bool, settled: bool, has_packet: bool, confirmed: bool) -> int:
    # 在一层的第二步结束时才记录成品，首层领料后的无操作步仍使用旧状态。
    if not enable:
        return 0
    end = (step == 1) | (step == 3) | (step == 5) | (step == 7) | (step == 9)
    if (selector == 4) & end & settled & ((not has_packet) | confirmed) & (row is not None):
        return 1
    return appended
