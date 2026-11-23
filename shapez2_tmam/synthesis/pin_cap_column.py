"""顶针逆推每列的顶盖边界，供两个切向和所有候选共用。"""

from .column_rules import column_admissible
from .physics import Shape
from .shape_methods import shape_literal, unstack_upper


def top_crystal_allowed(word: Shape | None, z0: int, z1: int, z2: int, z3: int) -> bool:
    if word is None or unstack_upper(word) == shape_literal("Wu------"):
        return False
    return column_admissible(z0, z1, z2, z3, 3)


def top_pin_allowed(word: Shape | None, z0: int, z1: int, z2: int, z3: int) -> bool:
    return (z3 >= 1) & (z3 <= 3)


def cap_material(word: Shape | None, z0: int, z1: int, z2: int, z3: int) -> int:
    if top_crystal_allowed(word, z0, z1, z2, z3):
        return 3
    return 0
