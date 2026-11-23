"""按固定六槽分配调用四角、双半形和尾料。"""


def pair_job_column(phase: int, h0: int, h1: int, h2: int, h3: int, alternate: bool) -> int:
    if phase == 0:
        return 0
    if phase == 1:
        return 1
    if phase == 3:
        return 2
    if phase == 4:
        return 3
    return -1


def pair_job_destination(phase: int, h0: int, h1: int, h2: int, h3: int, alternate: bool) -> int:
    if (phase == 1) | (phase == 3) | (phase == 5):
        return 1
    if phase == 4:
        return 2
    return 0


def pair_job_kind(phase: int, h0: int, h1: int, h2: int, h3: int, alternate: bool) -> int:
    """0 跳过，1 制角，2 拼半形，3 合并整形，4 堆叠尾料，5 恢复方向。"""
    front = (h0 > 0) | (h1 > 0)
    back = (h2 > 0) | (h3 > 0)
    if ((phase == 0) & (h0 > 0) | (phase == 1) & (h1 > 0)
            | (phase == 3) & (h2 > 0) | (phase == 4) & (h3 > 0)):
        return 1
    if ((phase == 2) & front) | ((phase == 5) & back):
        return 2
    if (phase == 6) & (front | back):
        return 3
    if phase == 7:
        return 4
    if (phase == 8) & alternate:
        return 5
    return 0


def pair_job_left(phase: int, h0: int, h1: int, h2: int, h3: int, alternate: bool) -> int:
    if (phase == 2) & (h0 > 0):
        return 0
    if (phase == 5) & (h2 > 0):
        return 1
    front = (h0 > 0) | (h1 > 0)
    back = (h2 > 0) | (h3 > 0)
    if ((phase == 6) & front) | ((phase == 7) & (front | back)) | ((phase == 8) & alternate):
        return 0
    return -1


def pair_job_right(phase: int, h0: int, h1: int, h2: int, h3: int, alternate: bool) -> int:
    if (phase == 5) & (h3 > 0):
        return 2
    if ((phase == 2) & (h1 > 0)) | ((phase == 6) & ((h2 > 0) | (h3 > 0))) | (phase == 7):
        return 1
    return -1


_NEXT_JOB = (1, 2, 3, 4, 5, 6, 7, 8, 9)


def pair_job_next(phase: int, enable: bool, settled: bool, kind: int, confirmed: bool) -> int:
    if not enable:
        return 0
    if phase < 0 or phase >= 9:
        return 9
    if settled & ((kind == 0) | confirmed):
        return _NEXT_JOB[phase]
    return phase


def pair_job_done(phase: int, enable: bool, settled: bool, kind: int, confirmed: bool) -> bool:
    return enable & (phase == 9)
