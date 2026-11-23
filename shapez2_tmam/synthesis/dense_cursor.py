"""紧柱发令的原层、相位和确认后的推进。"""


_NEXT_PHASE = (1, 2, 3, 4, 5, 6, 7, 8)
_NEXT_LEVEL = (1, 2, 3, 4, 5)


def _may_advance(settled: bool, has_packet: bool, confirmed: bool) -> bool:
    return settled & ((not has_packet) | confirmed)


def dense_advance_phase(phase: int, level: int, enable: bool, settled: bool,
                        has_packet: bool, confirmed: bool) -> int:
    if not enable:
        return 0
    if phase < 0 or phase >= 8:
        return 8
    if not _may_advance(settled, has_packet, confirmed):
        return phase
    if phase == 2 and level < 4:
        return 0
    return _NEXT_PHASE[phase]


def dense_advance_level(phase: int, level: int, enable: bool, settled: bool,
                        has_packet: bool, confirmed: bool) -> int:
    if not enable:
        return 0
    if phase == 2 and level >= 0 and level < 5:
        if _may_advance(settled, has_packet, confirmed):
            return _NEXT_LEVEL[level]
    return level


def dense_done(phase: int, level: int, enable: bool, settled: bool,
               has_packet: bool, confirmed: bool) -> bool:
    return enable & (phase == 8)
