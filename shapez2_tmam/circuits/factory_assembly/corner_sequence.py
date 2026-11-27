"""回放两份四象限五层目标的四角、双半形和六槽工序。"""

import argparse
import json
from collections.abc import Iterator
from pathlib import Path

from ...synthesis.column_build import pin_corner_upper_layer
from ...synthesis.column_scan import (pin_corner_anchor, pin_corner_base_far, pin_corner_source,
                                      pin_corner_trigger, simple_corner_far, simple_corner_source)
from ...synthesis.corners import CornerBuilder
from ...synthesis.physics import EMPTY, PIN, Rules, Shape
from ..slot_streams import SLOT_ROWS
from .corner_release import (pin_corner_handoff_instructions, pin_corner_top_break_instructions,
                             simple_corner_instructions)
from .dense_column import dense_column_instructions, pin_complement_instructions
from .half_assembly import append_five_instructions, join_built_halves_instructions, join_corner_half_instructions
from .recipe import _packet, replay


_TARGETS = {
    'direct': 'P-RuWuCu:CuRu--cr:--RuWucr:cbRu--Cu:SuRuSuCu',
    'suspended': 'P-SuCu--:P-SuCuRu:cgSuCu--:RuSuCucy:WuSuCuSu',
}
_ROTATIONS = (None, 1, 3, 2)


def _row(cell: str) -> str | None:
    return None if cell == EMPTY else cell + '------'


def _key(shape: Shape | None) -> str | None:
    return shape.to_key() if shape is not None else None


def _rows(shape: Shape) -> tuple[str, ...]:
    return tuple(''.join(row) for row in shape.layers)


def _rotate(slot: int, turns: int) -> tuple[dict, ...]:
    opcode = _ROTATIONS[turns % 4]
    return () if opcode is None else (_packet(opcode, slot),)


def _join(main: int, other: int, start: int) -> tuple[dict, ...]:
    return (*_rotate(main, -start), *_rotate(other, -start), _packet(8, main, other), *_rotate(main, start))


def _column(rows: tuple[str | None, ...], slot: int, scratch: int) -> tuple[dict, ...]:
    highest = max((z for z, row in enumerate(rows) if row and row[0] == 'c'), default=-1)
    if highest < 0:
        return append_five_instructions(rows, has_lower=False, lower_slot=slot, upper_slot=scratch)
    prefix = next(z for z, row in enumerate(rows) if row != _row(PIN))
    return (*dense_column_instructions(rows[prefix:highest + 1], destination=slot, scratch_slot=scratch),
            *(_packet(6, slot) for _ in range(prefix)),
            *append_five_instructions(rows[highest + 1:], has_lower=True, lower_slot=slot, upper_slot=scratch))


def _corner_phases(rules: Rules, cells: tuple[str, ...], main: int, reserved: set[int], *, right: bool
                   ) -> Iterator[tuple[str, tuple[dict, ...]]]:
    free = [slot for slot in range(len(SLOT_ROWS)) if slot != main and slot not in reserved]
    near, far, scratch = free[:3]
    counterclockwise = not right
    neighbor = 1 if right else -1
    start = 0 if right else -1
    helper = CornerBuilder.helper(cells)
    highest = max((z for z, cell in enumerate(cells) if cell[0] == 'c'), default=-1)
    original = tuple(rules.parse(row) if row is not None else None for row in map(_row, cells))
    crystal, landing = next(iter(CornerBuilder._gaps(cells)), (-1, -1))
    moved = original[landing] if landing >= 0 else None
    if landing > 0 and cells[landing - 1] == EMPTY:
        before = (*original[1:], None)
        main_rows = tuple(_key(pin_corner_source(label, moved, original[0], z, highest, crystal))
                          for z, label in enumerate(before[:highest]))
        far_rows = tuple(_key(pin_corner_base_far(label, moved, original[0], z, highest, crystal))
                         for z, label in enumerate(before))
        yield 'main', _column(main_rows, main, scratch)
        yield 'initial-near', (*_column((_row('Cu'),) * 5, near, scratch), *_rotate(near, neighbor),
                               *_join(main, near, -1 if right else 0))
        yield 'initial-far', (*_column(far_rows, far, scratch), *_rotate(far, -neighbor), *_join(main, far, start))
        yield 'near-anchor', _column(_rows(pin_corner_anchor(crystal, landing)), near, scratch)
        yield 'handoff', pin_corner_handoff_instructions(main, near, counterclockwise=counterclockwise,
                                                        reserved_slots=reserved)
        yield 'complement', pin_complement_instructions(_rows(pin_corner_trigger(crystal, landing)),
                                                        destination=near, trigger_slot=far, scratch_slot=scratch,
                                                        counterclockwise=counterclockwise)
        yield 'top-break', pin_corner_top_break_instructions(main, near, counterclockwise=counterclockwise)
        upper_rows = tuple(_key(pin_corner_upper_layer(label, z, highest, crystal, landing, counterclockwise))
                           for z, label in enumerate(original))
        yield 'upper-layers', append_five_instructions(upper_rows, has_lower=True, lower_slot=main, upper_slot=scratch)
        yield 'finish-cut', (*_rotate(main, -start), _packet(4, main), *_rotate(main, start))
    else:
        if highest >= 0:
            main_rows = tuple(_key(simple_corner_source(label, moved, z, highest, crystal, landing))
                              for z, label in enumerate(original[:highest + 1]))
            yield 'main', _column(main_rows, main, scratch)
            yield 'near-helper', (*_column(tuple(map(_row, helper[:highest + 1])), near, scratch),
                                  *_rotate(near, neighbor), *_join(main, near, -1 if right else 0))
        upper_rows = []
        for cell, support in zip(cells[highest + 1:], helper[highest + 1:]):
            row = [cell, EMPTY, EMPTY, EMPTY]
            row[neighbor] = support
            upper_rows.append(''.join(row))
        yield 'upper-layers', append_five_instructions(upper_rows, has_lower=highest >= 0,
                                                       lower_slot=main, upper_slot=scratch)
        far_rows = tuple(_key(simple_corner_far(label, moved, z, highest, crystal, landing))
                         for z, label in enumerate(original))
        if any(row is not None and row[0] == 'c' for row in far_rows):
            yield 'far-anchor', _column(far_rows, far, scratch)
            yield 'direct-release', simple_corner_instructions(main, far, counterclockwise=counterclockwise)
        else:
            yield 'skip-far-anchor', ()
    yield 'orient', _rotate(main, int(right))


def order(name: str) -> dict:
    target = _TARGETS[name]
    rules = Rules(4, 5)
    columns = tuple(zip(*rules.parse(target).layers))
    phases = []
    for start, half_name, slots in ((0, 'front', (0, 1)), (2, 'back', (1, 2))):
        reserved = {0} if start else set()
        for offset, slot in enumerate(slots):
            q = start + offset
            phases.extend((f'q{q}/{phase}', packets) for phase, packets in
                          _corner_phases(rules, columns[q], slot, reserved, right=bool(offset)))
            reserved.add(slot)
        phases.append((f'{half_name}/join', join_corner_half_instructions(*slots)))
    phases.append(('product/join', join_built_halves_instructions(0, 1, alternate=False)))

    packets = tuple(packet for _, batch in phases for packet in batch)
    production = replay(target, packets)
    live = {}
    phase_trace, stage_trace = [], []
    address = 0
    for phase, batch in phases:
        start = address
        for stage in production.stages[start:start + len(batch)]:
            for slot in stage.operands:
                del live[slot]
            live[stage.destination] = stage.result.to_key()
            stage_trace.append({'address': address, 'phase': phase, 'live': dict(sorted(live.items()))})
            address += 1
        phase_trace.append({'phase': phase, 'start': start, 'stop': address, 'live': dict(sorted(live.items()))})
    return {'target': target, 'instructions': packets, 'product_slot': production.product_slot,
            'peak_live_slots': max(len(stage['live']) for stage in stage_trace),
            'phases': phase_trace, 'stages': stage_trace}


def main() -> int:
    parser = argparse.ArgumentParser(description='回放四角到双半形的五层六槽配方')
    parser.add_argument('case', choices=tuple(_TARGETS))
    parser.add_argument('--output', type=Path, help='六字段配方与逐工段活槽 JSON')
    args = parser.parse_args()
    report = order(args.case)
    if args.output is not None:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{report["target"]}  {len(report["instructions"])} 工段  '
          f'{report["peak_live_slots"]} 个活槽  成品槽 {report["product_slot"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
