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
