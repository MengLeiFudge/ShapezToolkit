"""根订单选择直接闭包结果或转入尾针搜索。"""


def root_search_next(phase: int, enable: bool, rows_ready: bool, nonempty: bool,
                     unknown: bool, chosen: bool, exhausted: bool, snapshot_ready: bool) -> int:
    if not enable:
        return 0
    if phase == 0:
        return 1
    if phase == 1 and rows_ready:
        if not nonempty:
            return 5
        if unknown:
            return 4
        return 2
    if phase == 2:
        if chosen & exhausted:
            return 7
        if chosen:
            return 3
        if exhausted:
            return 6
    if phase == 3 and snapshot_ready:
        return 8
    return phase


def root_search_closure(phase: int, enable: bool) -> bool:
    return enable & ((phase == 2) | (phase == 3))


def root_search_keep_closure(phase: int, enable: bool) -> bool:
    return root_search_closure(phase, enable) | (enable & (phase == 8))


def root_search_snapshot(phase: int, enable: bool) -> bool:
    return enable & (phase == 3)


def root_search_tail(phase: int, enable: bool) -> bool:
    return enable & (phase == 6)


def root_search_unknown(phase: int, enable: bool) -> bool:
    return enable & (phase == 4)


def root_search_invalid(phase: int, enable: bool) -> bool:
    return enable & (phase == 5)


def root_search_fault(phase: int, enable: bool) -> bool:
    return enable & (phase == 7)


def root_search_replay(phase: int, enable: bool) -> bool:
    return enable & (phase == 8)
