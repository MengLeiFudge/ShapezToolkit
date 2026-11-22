"""两列半形按层检查针支撑与普通块、晶体组的支撑。"""


def half_support_row(lower0: int, lower1: int, upper0: int, upper1: int,
                     supported_below: bool, ground: bool, continues: bool, side_support: bool) -> int:
    """返回本段是否已有支撑。-1 表示本层针或结束的组缺少支撑。"""
    if (not ground) & (((upper0 == 2) & (lower0 == 0)) | ((upper1 == 2) & (lower1 == 0))):
        return -1
    linked = ((lower0 == 3) & (upper0 == 3)) | ((lower1 == 3) & (upper1 == 3))
    attached0 = (upper0 == 1) | (upper0 == 3)
    attached1 = (upper1 == 1) | (upper1 == 3)
    witness0 = attached0 & ((lower0 == 2) | ((not linked) & (lower0 != 0)))
    witness1 = attached1 & ((lower1 == 2) | ((not linked) & (lower1 != 0)))
    supported = ground | side_support | (linked & supported_below) | witness0 | witness1
    if supported:
        return 1
    if (attached0 | attached1) & (not continues):
        return -1
    return 0
