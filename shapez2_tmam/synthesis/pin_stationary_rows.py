"""把顶针活格和推定静止格编码成保留原层号的单层信号。"""

from .column_build import join_built_halves
from .layer_methods import append_layer
from .physics import Shape
from .pin_source_row import _adjacent_labels, pin_source_row
from .shape_methods import analyze_part, rotate_ccw, rotate_cw, shape_literal


def _ground_pin(material: int) -> Shape | None:
    if material != 0:
        return shape_literal("P-------")
    return None


def pin_stationary_ground(m0: int, m1: int, m2: int, m3: int) -> Shape | None:
    return pin_source_row(_ground_pin(m0), _ground_pin(m1), _ground_pin(m2), _ground_pin(m3))


def _ground_mark(material: int) -> Shape | None:
    if material != 0:
        return shape_literal("Cu------")
    return None


def pin_stationary_ground_mark(m0: int, m1: int, m2: int, m3: int) -> Shape | None:
    return pin_source_row(_ground_mark(m0), _ground_mark(m1), _ground_mark(m2), _ground_mark(m3))


def _live(material: int, deleted: bool) -> Shape | None:
    if deleted:
        return None
    if material == 1:
        return shape_literal("Cu------")
    if material == 2:
        return shape_literal("P-------")
    if material == 3:
        return shape_literal("cr------")
    return None


def pin_live_half(left: int, right: int, deleted_left: bool, deleted_right: bool) -> Shape | None:
    return _adjacent_labels(_live(left, deleted_left), _live(right, deleted_right))


def pin_live_row(front: Shape | None, back: Shape | None) -> Shape | None:
    return join_built_halves(front, back, False)


def _mark(material: int, deleted: bool, landing: int, height: int, target: Shape | None) -> Shape | None:
    if deleted | (material == 0):
        return None
    if material == 3:
        if analyze_part(target) == shape_literal("cu------"):
            return shape_literal("Cu------")
        return None
    if landing == height:
        return shape_literal("Cu------")
    return None


def _mark_half(left: int, right: int, deleted_left: bool, deleted_right: bool,
               landing_left: int, landing_right: int, height: int, target: Shape | None) -> Shape | None:
    a = _mark(left, deleted_left, landing_left, height, target)
    b = _mark(right, deleted_right, landing_right, height, rotate_ccw(target))
    return append_layer(a, rotate_cw(b))


def pin_fixed_front(left: int, right: int, deleted_left: bool, deleted_right: bool,
                    landing_left: int, landing_right: int, height: int, target: Shape | None) -> Shape | None:
    return _mark_half(left, right, deleted_left, deleted_right, landing_left, landing_right, height, target)


def pin_fixed_back(left: int, right: int, deleted_left: bool, deleted_right: bool,
                   landing_left: int, landing_right: int, height: int, target: Shape | None) -> Shape | None:
    return _mark_half(left, right, deleted_left, deleted_right, landing_left, landing_right, height,
                      rotate_ccw(rotate_ccw(target)))
