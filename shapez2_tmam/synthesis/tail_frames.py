"""保存成功路径上的父目标行和顶针结果行。"""

from .physics import Shape


def _row(current: Shape | None, incoming: Shape | None, write: int, capture: bool,
         enable: bool, depth: int) -> Shape | None:
    if not enable:
        return None
    if capture:
        if write == depth:
            return incoming
        if write >= 0 and write < depth:
            return None
    return current


def tail_frame_store0(f0: Shape | None, f1: Shape | None, f2: Shape | None, incoming: Shape | None,
                      write: int, read: int, capture: bool, enable: bool) -> Shape | None:
    return _row(f0, incoming, write, capture, enable, 0)


def tail_frame_store1(f0: Shape | None, f1: Shape | None, f2: Shape | None, incoming: Shape | None,
                      write: int, read: int, capture: bool, enable: bool) -> Shape | None:
    return _row(f1, incoming, write, capture, enable, 1)


def tail_frame_store2(f0: Shape | None, f1: Shape | None, f2: Shape | None, incoming: Shape | None,
                      write: int, read: int, capture: bool, enable: bool) -> Shape | None:
    return _row(f2, incoming, write, capture, enable, 2)


def tail_frame_read(f0: Shape | None, f1: Shape | None, f2: Shape | None, incoming: Shape | None,
                    write: int, read: int, capture: bool, enable: bool) -> Shape | None:
    if enable:
        if read == 0:
            return f0
        if read == 1:
            return f1
        if read == 2:
            return f2
    return None


def _valid(current: bool, write: int, capture: bool, enable: bool, depth: int) -> bool:
    if not enable:
        return False
    if capture:
        if write == depth:
            return True
        if write >= 0 and write < depth:
            return False
    return current


def tail_frame_valid0(f0: bool, f1: bool, f2: bool, write: int, read: int, capture: bool, enable: bool) -> bool:
    return _valid(f0, write, capture, enable, 0)


def tail_frame_valid1(f0: bool, f1: bool, f2: bool, write: int, read: int, capture: bool, enable: bool) -> bool:
    return _valid(f1, write, capture, enable, 1)


def tail_frame_valid2(f0: bool, f1: bool, f2: bool, write: int, read: int, capture: bool, enable: bool) -> bool:
    return _valid(f2, write, capture, enable, 2)


def tail_frame_read_valid(f0: bool, f1: bool, f2: bool, write: int, read: int, capture: bool, enable: bool) -> bool:
    if enable:
        if read == 0:
            return f0
        if read == 1:
            return f1
        if read == 2:
            return f2
    return False
