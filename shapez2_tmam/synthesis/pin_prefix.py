"""四象限五层最后一段顶针加堆叠的单列前缀上界。"""


def _two_empty(a: bool, b: bool, c: bool, d: bool) -> bool:
    return (a & b) | (c & d) | ((a | b) & (c | d))


def two_empty(a: int, b: int, c: int, d: int) -> bool:
    return _two_empty(a == 0, b == 0, c == 0, d == 0)


def _pin_prefix_limit(base_crystal: bool, base_pin: bool, crystal1: bool, crystal2: bool,
                      high_crystal: bool, empty1: bool, room: bool) -> int:
    if base_crystal | (crystal2 & empty1):
        return -1
    if base_pin:
        return 5
    if crystal1 | crystal2 | (high_crystal & (not room)):
        return -1
    return 3


def pin_prefix_limit(ground: int, z1: int, z2: int, z3: int, z4: int) -> int:
    """读入底到顶五格，空/普通/针/晶体用 0/1/2/3。返回最多保留格数，-1 表示排除。"""
    return _pin_prefix_limit(ground == 3, ground == 2, z1 == 3, z2 == 3, (z3 == 3) | (z4 == 3),
                             z1 == 0, two_empty(ground, z1, z2, z3))
