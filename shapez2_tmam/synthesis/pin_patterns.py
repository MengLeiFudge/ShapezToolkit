"""顶针来源的固定控制字：按地面占用和保留NPC数量分桶，桶长至多20。"""

from itertools import product


# 每格0为空、1为保留NPC、2为C。这里只编排四格控制常量，不读取目标或物理状态。
SOURCE_PATTERNS = tuple(
    tuple(
        tuple((sum(1 << r for r, value in enumerate(word) if value == 1),
               sum(1 << r for r, value in enumerate(word) if value == 2))
              for word in product(range(3), repeat=4)
              if (word[0] != 0) == occupied and word.count(1) == count)
        for count in range(5)
    )
    for occupied in (False, True)
)
