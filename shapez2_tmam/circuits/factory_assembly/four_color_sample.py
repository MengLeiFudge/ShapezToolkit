"""固定四色含晶验收订单，合并备角和拼半形之间的旋转。"""

from .dense_column import dense_column_instructions
from .half_assembly import append_five_instructions, join_built_halves_instructions
from .recipe import _packet


def _half(left_rows: tuple[str, str], right_rows: tuple[str, str], *, destination: int) -> tuple[dict, ...]:
    left = dense_column_instructions(left_rows, destination=0, scratch_slot=1)
    right = dense_column_instructions(right_rows, destination=4, scratch_slot=1)
    # 两刀后的紧柱已在 q1。左列就地使用，右列顺转到 q2，再交换拼合。
    return (*left[:-1], *right[:-1], _packet(1, 4), _packet(8, 0, 4),
            _packet(2, 0, destination=destination))


def orders() -> dict:
    front = _half(('Cu------', 'cr------'), ('Ru------', 'cb------'), destination=5)
    back = _half(('Su------', 'cg------'), ('Wu------', 'cy------'), destination=0)
    lower = (*front, *back, *join_built_halves_instructions(5, 0, alternate=False, destination=0))
    tail = append_five_instructions(('CuRuSuWu',) * 2, has_lower=True)
    # 先将尾料逆转一格，最后把整件顺转，两个订单就能共用领料地址。
    alternate_tail = append_five_instructions(('RuSuWuCu',) * 2, has_lower=True)
    return {
        'four-color': {
            'target': 'CuRuSuWu:crcbcgcy:CuRuSuWu:CuRuSuWu',
            'instructions': (*lower, *tail),
        },
        'four-color-alternate': {
            'target': 'WuCuRuSu:cycrcbcg:CuRuSuWu:CuRuSuWu',
            'instructions': (*lower, *alternate_tail, _packet(1, 0)),
        },
    }
