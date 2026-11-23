"""预先补齐两列半形的含晶区间支撑。"""

from .column_scan import column_crystal_height
from .physics import Shape
from .shape_methods import shape_literal, unstack_lower, unstack_upper


def seed_swap(left_word: Shape | None, right_word: Shape | None, left_height: int, right_height: int) -> bool:
    return left_height > right_height


def seed_low_word(left_word: Shape | None, right_word: Shape | None, left_height: int, right_height: int) -> Shape | None:
    if seed_swap(left_word, right_word, left_height, right_height):
        return right_word
    return left_word


def seed_high_word(left_word: Shape | None, right_word: Shape | None,
                   left_height: int, right_height: int) -> Shape | None:
    if seed_swap(left_word, right_word, left_height, right_height):
        return left_word
    return right_word


def seed_low_height(left_word: Shape | None, right_word: Shape | None, left_height: int, right_height: int) -> int:
    if seed_swap(left_word, right_word, left_height, right_height):
        return right_height
    return left_height


def seed_high_height(left_word: Shape | None, right_word: Shape | None, left_height: int, right_height: int) -> int:
    if seed_swap(left_word, right_word, left_height, right_height):
        return left_height
    return right_height


def pair_seed_swap(left_word: Shape | None, right_word: Shape | None) -> bool:
    crystal = shape_literal("Wu------")
    for _ in (5, 4, 3, 2, 1):
        if unstack_upper(right_word) == crystal:
            return False
        if unstack_upper(left_word) == crystal:
            return True
        left_word = unstack_lower(left_word)
        right_word = unstack_lower(right_word)
    return False


def pair_seed_low_word(left_word: Shape | None, right_word: Shape | None) -> Shape | None:
    if pair_seed_swap(left_word, right_word):
        return right_word
    return left_word


def pair_seed_high_word(left_word: Shape | None, right_word: Shape | None) -> Shape | None:
    if pair_seed_swap(left_word, right_word):
        return left_word
    return right_word


def pair_seed_low_height(left_word: Shape | None, right_word: Shape | None) -> int:
    return column_crystal_height(pair_seed_low_word(left_word, right_word))


def pair_seed_high_height(left_word: Shape | None, right_word: Shape | None) -> int:
    return column_crystal_height(pair_seed_high_word(left_word, right_word))


def seed_left(required: int, high_height: int, swapped: bool) -> int:
    if swapped:
        return high_height
    return required


def seed_right(required: int, high_height: int, swapped: bool) -> int:
    if swapped:
        return required
    return high_height


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
