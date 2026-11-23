"""恢复顶针前态单列的原色标签。"""

from .physics import Shape
from .shape_methods import analyze_part, pin, read_labeled_corner, shape_literal


_PREVIOUS_RANK = (-1, 0, 1, 2)


def _counts_as_npc(material: int) -> int:
    if (material == 1) | (material == 2):
        return 1
    return 0


def source_rank(z0: int, z1: int, z2: int, level: int) -> int:
    if level < 0 or level > 3:
        return -1
    rank = 0
    if level >= 1:
        rank = _counts_as_npc(z0)
    if level >= 2:
        rank = rank + _counts_as_npc(z1)
    if level == 3:
        rank = rank + _counts_as_npc(z2)
    return rank


def _is_retained(row: Shape | None, level: int) -> bool:
    part = analyze_part(row)
    if (part is None) | (part == shape_literal("cu------")):
        return False
    return (level != 0) | (part != shape_literal("P-------"))


def retained_rank(rank: int, label: Shape | None, row: Shape | None, level: int) -> int:
    if rank < 0 or rank > 3:
        return -1
    if _is_retained(row, level):
        return _PREVIOUS_RANK[rank]
    return rank


def retained_label(rank: int, label: Shape | None, row: Shape | None, level: int) -> Shape | None:
    if (rank == 0) & _is_retained(row, level):
        return read_labeled_corner(row)
    return label


def source_cell(material: int, forced_row: Shape | None, label: Shape | None) -> Shape | None:
    """强制晶体保留原色，顶破用的辅助晶体用红色。"""
    if material == 3:
        if analyze_part(forced_row) == shape_literal("cu------"):
            return read_labeled_corner(forced_row)
        return shape_literal("cr------")
    if material == 2:
        return shape_literal("P-------")
    if material == 1:
        return label
    return None


def pin_replay(source: Shape | None, target: Shape | None, ready: bool) -> Shape | None:
    if ready:
        return pin(source)
    return None


def pin_replay_matches(source: Shape | None, target: Shape | None, ready: bool) -> bool:
    return ready & (target is not None) & (pin_replay(source, target, ready) == target)
