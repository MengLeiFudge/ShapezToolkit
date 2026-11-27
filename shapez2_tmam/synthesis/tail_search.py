"""四帧尾部逆推共用的候选调度。"""


# 阶段值同时是原生状态寄存器和接口表里的编码。
IDLE = 0
PREFLIGHT = 1
S_WAIT = 2
S_SKIP = 3
PIN_WARM = 4
PIN_WAIT = 5
PIN_SKIP = 6
PIN_RESUME = 7
SAVE_MEMBER = 8
SAVE_LEAF = 9
DESCEND = 10
LOAD_PARENT = 11
RESTORE = 12
CHILD_FAILED = 13
SOLVED = 14
EXHAUSTED = 15
FAULT = 16


def tail_entry_next(phase: int, elapsed: bool, checked: bool, legal: bool, can_pin: bool) -> int:
    if phase == 0:
        return 1
    if phase == 1 and elapsed:
        if not can_pin:
            return 13
        if checked:
            if legal:
                return 2
            return 13
    return phase


def tail_stack_next(phase: int, ready: bool, exhausted: bool, resuming: bool, count_match: bool) -> int:
    if phase == 2:
        if ready & exhausted:
            return 16
        if exhausted:
            if resuming:
                return 16
            return 13
        if ready:
            if resuming and not count_match:
                return 3
            return 4
    if phase == 3 and not ready:
        return 2
    return phase


def tail_pin_next(phase: int, elapsed: bool, proof: bool, exhausted: bool, fault: bool,
                  resuming: bool, cursor_match: bool, member: bool) -> int:
    if phase == 4 and elapsed:
        return 5
    if phase == 5:
        if fault | (proof & exhausted):
            return 16
        if exhausted:
            if resuming:
                return 16
            return 3
        if proof:
            if resuming:
                if not member:
                    return 16
                if cursor_match:
                    return 7
                return 6
            if member:
                return 8
            return 9
    if ((phase == 6) | (phase == 7)) and not proof:
        return 5
    return phase


def tail_frame_next(phase: int, elapsed: bool, parent_ready: bool, leaf_ready: bool,
                    has_parent: bool) -> int:
    if phase == 13:
        if has_parent:
            return 11
        return 15
    if not elapsed:
        return phase
    if phase == 8:
        return 10
    if phase == 9 and leaf_ready:
        return 14
    if phase == 10:
        return 1
    if phase == 11 and parent_ready:
        return 12
    if phase == 12:
        return 1
    return phase


def tail_search_preflight(phase: int, enable: bool) -> bool:
    return enable & (phase == 1)


def tail_search_stack(phase: int, enable: bool) -> bool:
    return enable & (phase >= 2) & (phase <= 10)


def tail_search_stack_reject(phase: int, enable: bool) -> bool:
    return enable & (phase == 3)


def tail_search_pin(phase: int, enable: bool) -> bool:
    return enable & (phase >= 5) & (phase <= 10)


def tail_search_proof_missed(phase: int, enable: bool) -> bool:
    return enable & ((phase == 6) | (phase == 7))


def tail_search_save(phase: int, enable: bool) -> bool:
    return enable & ((phase == 8) | (phase == 9))


def tail_search_capture_leaf(phase: int, enable: bool) -> bool:
    return enable & (phase == 9)


def tail_search_down(phase: int, enable: bool) -> bool:
    return enable & (phase == 10)


def tail_search_read_parent(phase: int, enable: bool) -> bool:
    return enable & ((phase == 11) | (phase == 12))


def tail_search_restore(phase: int, enable: bool) -> bool:
    return enable & (phase == 12)


def tail_search_resumed(phase: int, enable: bool) -> bool:
    return enable & (phase == 7)


def tail_search_solved(phase: int, enable: bool) -> bool:
    return enable & (phase == 14)


def tail_search_exhausted(phase: int, enable: bool) -> bool:
    return enable & (phase == 15)


def tail_search_fault(phase: int, enable: bool) -> bool:
    return enable & (phase == 16)
