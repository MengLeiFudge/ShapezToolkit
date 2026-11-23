"""读取同一层的原色行及尾料掩码，供逐层装配使用。"""

from .physics import Shape
from .shape_methods import unstack_lower, unstack_upper


def tail_mask_at(mask: Shape | None, level: int) -> Shape | None:
    if level < 0 or level >= 5:
        return None
    if level == 0:
        return unstack_upper(mask)
    mask = unstack_lower(mask)
    if level == 1:
        return unstack_upper(mask)
    mask = unstack_lower(mask)
    if level == 2:
        return unstack_upper(mask)
    mask = unstack_lower(mask)
    if level == 3:
        return unstack_upper(mask)
    return unstack_upper(unstack_lower(mask))
