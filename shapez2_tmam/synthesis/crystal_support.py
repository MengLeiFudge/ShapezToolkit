"""预先补齐两列半形的含晶区间支撑。"""

from .physics import Shape
from .shape_methods import shape_literal, unstack_lower, unstack_upper


def _word_through(word: Shape | None, height: int) -> Shape | None:
    for z in (5, 4, 3, 2):
        if z == height:
            return word
        word = unstack_lower(word)
    return word


def _crystal_link(low: Shape | None, high: Shape | None) -> bool:
    crystal = shape_literal("Wu------")
    return (((unstack_upper(low) == crystal) & (unstack_upper(unstack_lower(low)) == crystal))
            | ((unstack_upper(high) == crystal) & (unstack_upper(unstack_lower(high)) == crystal)))


def _witness(word: Shape | None, height: int, linked: bool) -> bool:
    cell = unstack_upper(word)
    below = unstack_upper(unstack_lower(word))
    nonpin = (cell == shape_literal("Ru------")) | (cell == shape_literal("Wu------"))
    return nonpin & ((height == 1) | (below == shape_literal("Su------"))
                     | ((not linked) & (below is not None) & (below != shape_literal("Cu------"))))


def _kept_witness(required: int, supported: bool, low: Shape | None, high: Shape | None,
                  high_height: int, height: int, linked: bool) -> bool:
    return (supported | ((required >= height) & _witness(low, height, linked))
            | ((high_height >= height) & _witness(high, height, linked)))


def seed_required(required: int, candidate: int, supported: bool, low_word: Shape | None,
                  high_word: Shape | None, high_height: int, height: int) -> int:
    """到含晶区间底部时补入最低见证，-1 表示没有见证。"""
    low = _word_through(low_word, height)
    high = _word_through(high_word, height)
    linked = _crystal_link(low, high)
    crystal = shape_literal("Wu------")
    crystal_row = (unstack_upper(low) == crystal) | (unstack_upper(high) == crystal)
    if ((required < 0) | linked | (not crystal_row)
            | _kept_witness(required, supported, low, high, high_height, height, linked)):
        return required
    if _witness(low, height, linked) & (unstack_upper(low) == shape_literal("Ru------")):
        return height
    if candidate == 0:
        return -1
    return candidate


def seed_candidate(required: int, candidate: int, supported: bool, low_word: Shape | None,
                   high_word: Shape | None, high_height: int, height: int) -> int:
    low = _word_through(low_word, height)
    high = _word_through(high_word, height)
    linked = _crystal_link(low, high)
    if not linked:
        return 0
    if _witness(low, height, linked) & (unstack_upper(low) == shape_literal("Ru------")):
        return height
    return candidate


def seed_supported(required: int, candidate: int, supported: bool, low_word: Shape | None,
                   high_word: Shape | None, high_height: int, height: int) -> bool:
    low = _word_through(low_word, height)
    high = _word_through(high_word, height)
    linked = _crystal_link(low, high)
    return linked & _kept_witness(required, supported, low, high, high_height, height, linked)
