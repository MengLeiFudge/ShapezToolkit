"""五个原层位的列 A 判定。"""


def column_admissible(z0: int, z1: int, z2: int, z3: int, z4: int) -> bool:
    """材料按空、普通格、针、晶体分别编码为 0、1、2、3。"""
    empty0 = z0 == 0
    empty1 = z1 == 0
    empty2 = z2 == 0
    empty3 = z3 == 0
    pin0 = z0 == 2
    pin1 = z1 == 2
    pin2 = z2 == 2
    pin3 = z3 == 2
    c0 = z0 == 3
    c1 = z1 == 3
    c2 = z2 == 3
    c3 = z3 == 3
    c4 = z4 == 3
    unsupported_pin = (empty0 & pin1) | (empty1 & pin2) | (empty2 & pin3) | (empty3 & (z4 == 2))
    pin_outside_prefix = ((pin1 & (not pin0) & (c2 | c3 | c4))
                          | (pin2 & (not (pin0 & pin1)) & (c3 | c4))
                          | (pin3 & (not (pin0 & pin1 & pin2)) & c4))

    ordinary0 = z0 == 1
    ordinary1 = z1 == 1
    ordinary2 = z2 == 1
    nearest1 = ordinary1 | (empty1 & ordinary0)
    nearest2 = ordinary2 | (empty2 & nearest1)
    unsupported_crystal = ((c1 & empty0) | (c2 & empty1 & (not ordinary0))
                           | (c3 & empty2 & (not nearest1)) | (c4 & empty3 & (not nearest2)))

    gap = ((empty1 & c0 & (c2 | c3 | c4))
           | (empty2 & (c0 | c1) & (c3 | c4))
           | (empty3 & (c0 | c1 | c2) & c4))
    supported_gap = c0 & c4 & ordinary1 & ((empty2 & (z3 == 1)) | (ordinary2 & empty3))
    return not (unsupported_pin | pin_outside_prefix | unsupported_crystal | (gap & (not supported_gap)))
