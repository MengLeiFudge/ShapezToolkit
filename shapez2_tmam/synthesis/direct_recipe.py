"""读取已通过纯堆叠判定的目标所需的订单和工序。"""

BASE_LEVELS = (1, 2, 0, 3, 0, 4, 0, 5, 0)


def direct_recipe_length(height: int) -> int:
    if height < 1 or height > 5:
        return 0
    return (0, 1, 3, 5, 7, 9)[height]


def direct_recipe_opcode(address: int, length: int) -> int:
    if address < 0 or address >= length or address > 8:
        return 0
    if BASE_LEVELS[address] == 0:
        return 7
    return 14


def direct_recipe_level(address: int) -> int:
    """返回工段需要读取的原层号。零表示无需基础料。"""
    if address < 0 or address > 8:
        return 0
    return BASE_LEVELS[address]


def direct_recipe_base_depth(address: int, length: int) -> int:
    """返回从目标顶层往下的基础料深度，其他工段返回 -1。"""
    a0 = address == 0
    a1 = address == 1
    a3 = address == 3
    a5 = address == 5
    a7 = address == 7
    n1 = length == 1
    n3 = length == 3
    n5 = length == 5
    n7 = length == 7
    n9 = length == 9
    if a0 & n9:
        return 4
    if (a0 & n7) | (a1 & n9):
        return 3
    if (a0 & n5) | (a1 & n7) | (a3 & n9):
        return 2
    if (a0 & n3) | (a1 & n5) | (a3 & n7) | (a5 & n9):
        return 1
    if (a0 & n1) | (a1 & n3) | (a3 & n5) | (a5 & n7) | (a7 & n9):
        return 0
    return -1


def direct_recipe_destination(address: int, length: int) -> int:
    """首份基础料进槽 0，其他上料进槽 1，堆叠结果写回槽 0。"""
    opcode = direct_recipe_opcode(address, length)
    if opcode == 0:
        return -1
    if opcode == 14 and address != 0:
        return 1
    return 0


def direct_recipe_lower(address: int, length: int) -> int:
    """返回下料槽号，-1 表示本地址无需此操作数。"""
    if direct_recipe_opcode(address, length) == 7:
        return 0
    return -1


def direct_recipe_upper(address: int, length: int) -> int:
    """返回上料槽号，-1 表示本地址无需此操作数。"""
    if direct_recipe_opcode(address, length) == 7:
        return 1
    return -1


def direct_recipe_has_step(address: int, length: int) -> bool:
    return direct_recipe_opcode(address, length) != 0


def direct_recipe_uses_operands(address: int, length: int) -> bool:
    return direct_recipe_opcode(address, length) == 7
