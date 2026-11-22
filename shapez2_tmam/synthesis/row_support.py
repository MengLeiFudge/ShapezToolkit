"""四象限纯普通格与针的逐层支撑判定。"""


def addition_needs_lower(cell: int, left: int, right: int, opposite: int) -> bool:
    """状态 0 表示无新增格，1/2 表示普通格，3/4 表示针；2 和 4 有直接下挡。"""
    if cell == 3:
        return True
    if cell != 1 or left == 2 or right == 2:
        return False
    return opposite != 2 or (left != 1 and right != 1)
