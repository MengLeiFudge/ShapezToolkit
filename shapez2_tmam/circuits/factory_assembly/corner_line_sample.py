"""按已选切向和闭合前缀，回放四角、两个半形及尾料的六槽装配。"""

import argparse
import json
from pathlib import Path

from ...synthesis.corners import CornerBuilder
from ...synthesis.physics import EMPTY, PIN, Rules
from ..slot_streams import SLOT_ROWS
from .corner_release import (pin_corner_handoff_instructions, pin_corner_top_break_instructions,
                             simple_corner_instructions)
from .dense_column import dense_column_instructions, pin_complement_instructions
from .half_assembly import append_five_instructions, join_built_halves_instructions, join_corner_half_instructions
from .recipe import _packet, replay

RULES = Rules(4, 5)
SAMPLES = {
    'direct': ('CuRuSuP-:--RuSucb:crRuSucb:SuRuWuRu:WuRuSuSu', (3, 3, 3, 3)),
    'suspended': ('CuRuSuP-:--RuSu--:crRuSuRb:SuRuSu--:WuRuSucg', (3, 3, 5, 5)),
}


def _rows(cells: tuple[str, ...] | list[str]) -> tuple[str | None, ...]:
    return tuple(None if cell == EMPTY else cell + '------' for cell in cells)


def expand_call(kind: str, parameters: dict) -> tuple[dict, ...]:
    if kind == 'append':
        return append_five_instructions(**parameters)
    if kind == 'transform':
        operations = parameters['operations']
        destinations = parameters.get('destinations', (None,) * len(operations))
        return tuple(_packet(*operation, destination=destination)
                     for operation, destination in zip(operations, destinations, strict=True))
    if kind == 'dense':
        if 'trigger_rows' in parameters:
            return pin_complement_instructions(**parameters)
        args = dict(parameters)
        side = args.pop('filler_side', None)
        prefix = args.pop('ground_pins', 0)
        packets = dense_column_instructions(**args)
        slot = args['destination']
        if side is not None:
            # 保留填充料中的近柱，只切掉第一次支撑交接会丢弃的半面。
            cut = (_packet(1, slot), _packet(4, slot), _packet(2, slot)) if side == 3 else (_packet(4, slot),)
            return (*packets[:-4], *cut)
        return (*packets, *(_packet(6, slot) for _ in range(prefix)))
    if kind == 'release':
        args = dict(parameters)
        action = args.pop('action')
        if action == 'direct':
            return simple_corner_instructions(**args)
        if action == 'handoff':
            cut_done = args.pop('first_cut_done', False)
            packets = pin_corner_handoff_instructions(**args)
            return packets[(2 if args['counterclockwise'] else 1):] if cut_done else packets
        if action == 'top_break':
            return pin_corner_top_break_instructions(**args)
    raise ValueError(f'未知四角调用 {kind!r}，参数 {parameters!r}')


def _append(rows, slot: int, scratch: int, *, has_lower: bool) -> tuple[str, dict]:
    return 'append', dict(rows=tuple(rows), has_lower=has_lower, lower_slot=slot, upper_slot=scratch)


def _column(cells: tuple[str, ...] | list[str], slot: int, scratch: int, *, filler_side: int | None = None
            ) -> tuple[tuple[str, dict], ...]:
    top = max((z for z, cell in enumerate(cells) if cell.startswith('c')), default=-1)
    if top < 0:
        return (_append(_rows(cells), slot, scratch, has_lower=False),) if cells else ()
    ground_pins = next(z for z, cell in enumerate(cells) if cell != PIN)
    dense = ('dense', dict(rows=_rows(cells[ground_pins:top + 1]), destination=slot, scratch_slot=scratch,
                          ground_pins=ground_pins, filler_side=filler_side))
    if top + 1 == len(cells):
        return (dense,)
    return dense, _append(_rows(cells[top + 1:]), slot, scratch, has_lower=True)


def _transform(*operations: tuple[int, ...]) -> tuple[str, dict]:
    return 'transform', {'operations': operations}


def _join(method, *slots, **kwargs) -> tuple[tuple[str, dict], ...]:
    packets = method(*slots, **kwargs)
    if not packets:
        return ()
    operations = tuple((p['opcode'], p['a'], p['b']) for p in packets)
    return (('transform', {'operations': operations, 'destinations': tuple(p['destination'] for p in packets)}),)


def _swap_sides(first: int, second: int, *, counterclockwise: bool) -> tuple[tuple[int, ...], ...]:
    if counterclockwise:
        return (1, first), (1, second), (8, first, second), (2, first)
    return ((8, first, second),)


def _side_rows(cells: tuple[str, ...] | list[str], helper: tuple[str, ...], side: int) -> tuple[str, ...]:
    return tuple(''.join((cell, support, EMPTY, EMPTY) if side == 1 else (cell, EMPTY, EMPTY, support))
                 for cell, support in zip(cells, helper, strict=True))


def _corner(cells: tuple[str, ...], slot: int, reserved: tuple[int, ...], *,
            counterclockwise: bool) -> list[tuple[str, tuple[tuple[str, dict], ...]]]:
    side = 3 if counterclockwise else 1
    side_turn, far_turn = (2, 1) if counterclockwise else (1, 2)
    scratch, spare, extra = [i for i in range(len(SLOT_ROWS)) if i not in (slot, *reserved)][:3]
    top = max((z for z, cell in enumerate(cells) if cell.startswith('c')), default=-1)
    gaps = CornerBuilder._gaps(cells)
    suspended = next(((z, land) for z, land in gaps if land > 0 and cells[land - 1] == EMPTY), None)
    helper = CornerBuilder.helper(cells)

    if suspended is None:
        source = list(cells)
        for z, landing in gaps:
            source[z - 1], source[landing] = cells[landing], EMPTY
        removed = {z for z in range(top + 1) if source[z] == EMPTY}
        for z in removed:
            source[z] = 'cr'
        prefix = _column(source[:top + 1], slot, scratch)
        rows = _side_rows([EMPTY] * (top + 1) + source[top + 1:], helper, side)
        supplement = _append(rows, slot, scratch, has_lower=bool(prefix))
        far = (_column(['cr' if z in removed else 'Cu' for z in range(5)], scratch, spare)
               if removed else ())
        release = ('release', dict(action='direct', retained_slot=slot, far_slot=scratch if removed else None,
                                   counterclockwise=counterclockwise))
        return [('主柱含晶前缀', prefix), ('助手和无晶原格逐层补料', (supplement,)),
                ('远锚备料' if far else '跳过空远锚', far), ('直接释放', (release,))]

    crystal, landing = suspended
    source = [cell if cell.startswith('c') else EMPTY for cell in cells[1:top + 1]]
    source[crystal - 2] = cells[landing]
    if cells[0] == PIN:
        source[:crystal - 2] = ['cr'] * (crystal - 2)
    elif cells[0] != EMPTY:
        source[crystal - 3] = cells[0]
    first = next(z for z, cell in enumerate(source) if cell != EMPTY)
    source[:first] = ['cr'] * first
    if first == 0:
        # 地面无待碎填充晶体。近柱接到五层即等同于原来的第一次半切出口。
        main = _column(source, slot, scratch, filler_side=side)
        near_row = '------Cu' if counterclockwise else '--Cu----'
        initial = (_append((near_row,) * (5 - len(source)), slot, scratch, has_lower=True),)
        if counterclockwise:
            initial += (_transform((1, slot)),)
    else:
        main = _column(source, slot, scratch)
        initial_far = _column(['cr'] * first + ['Cu'] * (5 - first), scratch, spare)
        near = _column(('Cu',) * 5, scratch, spare)
        initial = (*initial_far, _transform((far_turn, scratch), *_swap_sides(slot, scratch,
                    counterclockwise=counterclockwise)), *near,
                   _transform((side_turn, scratch), *_swap_sides(slot, scratch, counterclockwise=not counterclockwise)))
    anchor = _column(('Cu',) * (landing - 1) + ('cr',) * (crystal - landing - 1) + ('Cu',), scratch, spare)
    handoff = ('release', dict(action='handoff', initial_slot=slot, anchor_slot=scratch,
                               counterclockwise=counterclockwise, reserved_slots=reserved, first_cut_done=first == 0))
    complement = ('dense', dict(trigger_rows=_rows((PIN,) * (crystal - 1) + ('Cu',)), destination=scratch,
                                trigger_slot=spare, scratch_slot=extra, counterclockwise=counterclockwise))
    top_break = ('release', dict(action='top_break', initial_slot=slot, complement_slot=scratch,
                                 counterclockwise=counterclockwise))
    rows = _side_rows([EMPTY] * (top + 1) + list(cells[top + 1:]), helper, side)[landing + 1:]
    supplement = _append(rows, slot, scratch, has_lower=True)
    cut = _transform((1, slot), (4, slot), (2, slot)) if counterclockwise else _transform((4, slot))
    return [('顶破主柱含晶前缀', main), ('底部碎晶与初始支撑', initial), ('近锚备料', anchor),
            ('远柱接力并转交近锚', (handoff,)), ('触顶补形备料', (complement,)), ('顶破', (top_break,)),
            ('顶破后逐层补料', (supplement,)), ('悬空角释放', (cut,))]


def corner_line(target: str, heights: tuple[int, int, int, int], *, alternate: bool = False) -> dict:
    """以已闭合的四列高度生成配方，逐地址回放后返回六字段与存活形状。"""
    original = RULES.parse(target)
    oriented = RULES.rotate(original, -1) if alternate else original
    if len(heights) != 4 or any(type(h) is not int or not 0 <= h <= len(oriented.layers) for h in heights):
        raise ValueError('需提供四个已闭合前缀高度')
    phases = []
    halves = []
    for q in (0, 2):
        corners = []
        for col in (q, q + 1):
            cells = tuple(row[col] for row in oriented.layers[:heights[col]])
            cells += (EMPTY,) * (5 - len(cells))
            if all(cell == EMPTY for cell in cells):
                corners.append(None)
                continue
            if not CornerBuilder.admissible(cells):
                raise ValueError(f'q{col} 的闭合前缀未通过列条件')
            reserved = tuple(i for i in (*halves, *corners) if i is not None)
            slot = next(i for i in range(len(SLOT_ROWS)) if i not in reserved)
            ccw = col == q
            corner_phases = _corner(cells, slot, reserved, counterclockwise=ccw)
            phases.extend((f'q{col} {name}', packets) for name, packets in corner_phases)
            if not ccw:
                phases.append((f'q{col} 转到半形右侧', (_transform((1, slot)),)))
            corners.append(slot)
        halves.append(next((i for i in corners if i is not None), None))
        phases.append((f'q{q}/q{q + 1} 半形', _join(join_corner_half_instructions, *corners)))
    has_lower = any(i is not None for i in halves)
    phases.append(('双半形合并', _join(join_built_halves_instructions, *halves, alternate=False, destination=0)
                   if has_lower else ()))
    rows = []
    for z, row in enumerate(oriented.layers):
        layer = ''.join(cell if z >= heights[q] else EMPTY for q, cell in enumerate(row))
        rows.append(None if layer == EMPTY * 4 else layer)
    phases.append(('原色尾料逐层堆叠', (_append(rows, 0, 1, has_lower=has_lower),)))
    if alternate:
        phases.append(('恢复原切向', (_transform((1, 0)),)))
    expanded = [(name, [(kind, parameters, expand_call(kind, parameters)) for kind, parameters in calls])
                for name, calls in phases]
    packets = tuple(packet for _, calls in expanded for _, _, group in calls for packet in group)
    production = replay(target, packets)
    if production.product_slot != 0:
        raise RuntimeError('成品没有写入槽 0')

    live = {}
    stages = []
    checkpoints = []
    calls = []
    cursor = 0
    for name, phase_calls in expanded:
        phase_start = cursor
        for kind, parameters, group in phase_calls:
            start = cursor
            cursor += len(group)
            for stage in production.stages[start:cursor]:
                for i in stage.operands:
                    del live[i]
                live[stage.destination] = stage.result.to_key()
                stages.append({'address': stage.index, 'live': dict(sorted(live.items()))})
            calls.append({'phase': name, 'kind': kind, 'parameters': parameters, 'start': start,
                          'count': len(group), 'live': dict(sorted(live.items()))})
        checkpoints.append({'phase': name, 'start': phase_start, 'stop': cursor, 'live': dict(sorted(live.items()))})
    return {'target': original.to_key(), 'instructions': packets, 'product_slot': production.product_slot,
            'heights': heights, 'alternate': alternate, 'peak_slots': max(len(stage['live']) for stage in stages),
            'calls': calls, 'phases': checkpoints, 'stages': stages}


def main() -> None:
    parser = argparse.ArgumentParser(description='导出连续六槽工序及每工段活槽')
    parser.add_argument('sample', choices=SAMPLES)
    parser.add_argument('--output', type=Path, help='输出 JSON 文件，默认输出到终端')
    args = parser.parse_args()
    text = json.dumps(corner_line(*SAMPLES[args.sample]), ensure_ascii=False, indent=2) + '\n'
    if args.output is None:
        print(text, end='')
    else:
        args.output.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
