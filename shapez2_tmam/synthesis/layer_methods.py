"""逐层补料的编译入口。方法参数保持实际图形，供 Python 及游戏电路使用。"""

from .physics import Rules, Shape


_RULES = Rules(4, 5)


def stack(lower: Shape | None, upper: Shape | None) -> Shape | None:
    if lower is None or upper is None:
        return None
    return _RULES.stack(lower, upper)


def append_layer(lower: Shape | None, upper: Shape | None) -> Shape | None:
    """跳过空订单。没有下料时直接领上料，否则将这一层叠到下料上。"""
    if upper is None:
        return lower
    if lower is None:
        return upper
    return stack(lower, upper)


def append_five(lower: Shape | None, row0: Shape | None, row1: Shape | None,
                row2: Shape | None, row3: Shape | None, row4: Shape | None) -> Shape | None:
    """按原层号由低到高追加五个已确定的无晶体订单。"""
    for row in (row0, row1, row2, row3, row4):
        lower = append_layer(lower, row)
    return lower
