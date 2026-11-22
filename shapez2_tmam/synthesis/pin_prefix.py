"""四象限五层最后一段顶针加堆叠的单列前缀上界。"""


def two_empty(a: int, b: int, c: int, d: int) -> bool:
    if a == 0:
        return b == 0 or c == 0 or d == 0
    if b == 0:
        return c == 0 or d == 0
    return c == 0 and d == 0


def pin_prefix_limit(ground: int, z1: int, z2: int, z3: int, z4: int) -> int:
    """读入底到顶五格，空/普通/针/晶体用 0/1/2/3。返回最多保留格数，-1 表示排除。"""
    if ground == 3 or (z2 == 3 and z1 == 0):
        return -1
    if ground == 2:
        return 5
    if z1 == 3 or z2 == 3:
        return -1
    if (z3 == 3 or z4 == 3) and not two_empty(ground, z1, z2, z3):
        return -1
    return 3
