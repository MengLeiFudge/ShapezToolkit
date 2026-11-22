"""用单层针掩码筛选最大顶盖之后的其他候选。"""

from .layer_methods import stack
from .physics import Shape
from .shape_methods import unstack_lower


def _covers(cap: Shape | None, contacts: Shape | None) -> bool:
    if contacts is None:
        return True
    return unstack_lower(stack(cap, contacts)) is not None


def cap_covers_required(cap: Shape | None, first: Shape | None, second: Shape | None,
                        third: Shape | None, fourth: Shape | None) -> bool:
    """四个接触集各用一个单层针掩码，空信号表示无约束。"""
    return (_covers(cap, first) and _covers(cap, second)
            and _covers(cap, third) and _covers(cap, fourth))
