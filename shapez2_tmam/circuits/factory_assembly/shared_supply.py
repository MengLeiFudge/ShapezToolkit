"""导出混合车的共用卸货分配段及九道页的容量界。"""

import argparse
import json
from collections import deque
from fractions import Fraction
from math import ceil
from pathlib import Path

from ...mari.blueprint import DIRECTIONS
from ...synthesis.production_bill import CRYSTAL_LITERS, PAINT_LITERS
from ..circuit import encode_document
from ..freight_stage import CARS, approach_tracks
from ..production_line import check_jump
from ..quarter_gather import QUADRANTS
from ..slot_stream_ports import trace, transport_paths
from ..slot_streams import SlotStreams
from ..stock_selector import SOURCES
from ..work_lane import COLORS, COMMAND, WorkLane
from .base_feed import HEAD as BASE_HEAD
from .crystal_feed import HEAD, dye_intake
from .recipe import MAX_STAGES
from .stage_pages import _document, _islands, _rail_links, _stats


_ROWS = (-12, -11, -10, -9, 8, 9, 10)
_LIFTS = ('PipeForward', 'PipeUpForward', 'Pipe2UpForward')
_UNLOAD_ROWS = 4
_SLOTS = 6


def _next(point, direction):
    x, y, level = point
    dx, dy = DIRECTIONS[direction]
    return x + dx, y + dy, level


def _branch(lane, start, end, reserved):
    # 搜索两口管的朝向及升降，交叉处改走其他建筑层。
    blocked = lane.occupied | reserved
    initial = (start, 1)
    pending = deque([initial])
    parents = {initial: None}
    while pending:
        point, inlet = state = pending.popleft()
        if point == end:
            pending_outlets = (3,)
        else:
            pending_outlets = ((inlet + 2) % 4, (inlet + 1) % 4, (inlet - 1) % 4)
        for outlet in pending_outlets:
            levels = range(3) if (outlet + 2) % 4 == inlet and point != end else (point[2],)
            for z in levels:
                x, y, level = point
                footprint = {(x, y, k) for k in range(min(level, z), max(level, z) + 1)}
                if point == end and outlet == 3:
                    path = [(point, inlet, outlet, z)]
                    while parents[state] is not None:
                        state, pipe = parents[state]
                        path.append(pipe)
                    return path[::-1]
                next_point = _next((x, y, z), outlet)
                if not (-17 <= next_point[0] <= 36 and -17 <= next_point[1] <= 36):
                    continue
                if footprint & blocked or next_point in blocked:
                    continue
                next_state = (next_point, (outlet + 2) % 4)
                if next_state in parents:
                    continue
                parents[next_state] = (state, (point, inlet, outlet, z))
                pending.append(next_state)
    raise ValueError(f'共用染料从 {start} 到 {end} 无法布线')


def _place_branch(lane, path):
    for (x, y, level), inlet, outlet, target in path:
        if level != target:
            rotation = outlet if target > level else inlet
            lane.put(_LIFTS[abs(target - level)], x, y, min(level, target), rotation)
        elif (inlet + 2) % 4 == outlet:
            lane.put('PipeForward', x, y, level, outlet)
        else:
            straight = (inlet + 2) % 4
            lane.put('PipeLeft', x, y, level, straight, mirrored=(outlet - straight) % 4 == 1)


def _distribution():
    original = dye_intake()
    lane = SlotStreams()
    for entry in original['B']['Entries']:
        x, y, level, rotation = (entry[k] for k in ('X', 'Y', 'L', 'R'))
        if level == 2 and y in _ROWS and 34 <= x <= 36:
            continue
        name, _, mirror = entry['T'].partition('InternalVariant')
        lane.put(name, x, y, level, rotation, mirrored=bool(mirror), config=entry.get('C'))
    for i, row in enumerate(_ROWS):
        level = i % 2
        lift = _LIFTS[2 - level]
        lane.put(lift, 34, row, level, 2)
        lane.put('PipeCross', 35, row, level)
        lane.put(lift, 36, row, level)
        lane.put('FluidPortSender', row, -18, 2, 3, config='KAAAAAA=')
    starts = [(35, row - 1, i % 2) for i, row in enumerate(_ROWS)]
    ends = [(row, -17, 2) for row in _ROWS]
    for i in (2, 0, 1, 3, 4, 5, 6):
        start, end = starts[i], ends[i]
        reserved = set(starts + ends) - {start, end}
        _place_branch(lane, _branch(lane, start, end, reserved))
    return lane.finish()


def _work(address, x, y, *, turn=False):
    board = WorkLane(COMMAND + 32 * address).build()['BP']['Entries'][0]
    if turn:
        board['B']['Entries'] = [dict(e, X=e['Y'], Y=19 - e['X'], R=(e['R'] + 3) % 4)
                                 for e in board['B']['Entries']]
    return dict(board, X=x, Y=y)


def _base_segment(start, belt_rate, headway):
    head_x, head_y = BASE_HEAD
    head_x -= 9
    entries = [{'T': 'Layout_TrainWaitStation', 'X': head_x, 'Y': head_y, 'R': 3}]
    outlets = []
    for group, quadrant in enumerate(QUADRANTS):
        y = head_y + 2 + 3 * group
        lane = SlotStreams()
        for kind, base_row, level, wagon, cargo in (
            *(('Belt', row, level, 3 * group + (1 if i < 3 else 2), cargo)
              for i, ((row, level), cargo) in enumerate(zip(SOURCES, 'CRSW', strict=True))),
            *(('Fluid', 28, level, 3 * group + 3, cargo) for level, cargo in enumerate('rgb')),
        ):
            fluid = kind == 'Fluid'
            for i in range(_UNLOAD_ROWS):
                row = base_row + i
                lane.put(kind + 'PortReceiver', -18, row, level, config='AA==')
                lane.straight(-17, 37, row, level, pipe=fluid)
                lane.put(kind + 'PortSender', 37, row, level, config='KAAAAAA=')
                demand = belt_rate * (CRYSTAL_LITERS if cargo == 'r' else PAINT_LITERS) if fluid else belt_rate
                outlets.append({'address': start + i, 'quadrant': quadrant, 'cargo': cargo, 'wagon': wagon,
                                'unit': 'liter' if fluid else 'item', 'island': (head_x + 3, y, 0),
                                'inlet': (-18, row, level), 'outlet': (37, row, level),
                                'max_per_second': str(demand), 'max_per_visit': str(demand * headway)})
        board = dict(lane.finish(), X=head_x + 3, Y=y)
        belts = transport_paths(board)
        for row, level in SOURCES:
            for i in range(_UNLOAD_ROWS):
                yy = row + i
                trace(belts, (-17, yy, level, 2), {(37, yy, level, 2)}, set())
        entries.append(board)
        entries.extend({'T': 'Layout_TrainUnloader_' + kind + '_Flipped', 'X': head_x, 'Y': y + i - 1, 'R': 3}
                       for i, (kind, _) in enumerate(CARS))
    entries.extend(dict(e, X=e['X'] - 6) for e in approach_tracks(machine_dyes=False))
    doc = _document(entries)
    return entries, {'head': (head_x, head_y, 0), 'rail': _rail_links(_islands(doc), (head_x, head_y), 'base'),
                     'addresses': tuple(range(start, start + _UNLOAD_ROWS)), 'outlets': outlets, **_stats(doc)}


def _stock_bound(stages):
    # 14 添一个活槽，二元操作最多收回一个槽。区间可从任意合法活槽状态开始。
    return min(stages, (stages + _SLOTS) // 2)


def _bounds(belt_rate, unload_belt, pipe_rate, headway):
    groups = []
    for n in range(1, 10):
        stock_steps = _stock_bound(n)
        solid = stock_steps * belt_rate
        # 结晶填满当前形状。下一次要耗染料，须换件或先产生新的空格、针。
        crystal = stock_steps * belt_rate * CRYSTAL_LITERS
        groups.append({'stages': n, 'max_base_steps': stock_steps,
                       'base_item_per_layer_per_second': str(solid),
                       'base_belt_ports_needed': ceil(solid / unload_belt),
                       'base_pin_red_per_quadrant_per_second': str(stock_steps * belt_rate * CRYSTAL_LITERS),
                       'base_paint_per_quadrant_per_second': str(stock_steps * belt_rate * PAINT_LITERS),
                       'max_effective_crystal_steps': stock_steps,
                       'crystal_pipe_per_final_color_per_second': str(crystal),
                       'crystal_pipe_reserved_per_second_if_all_opcode_10_counted': str(n * belt_rate * CRYSTAL_LITERS),
                       'one_shape_stop_has_ports': solid <= _UNLOAD_ROWS * unload_belt,
                       'one_shared_pure_pipe_has_capacity': None if pipe_rate is None else
                       crystal <= pipe_rate,
                       'max_solid_load_per_visit': str(solid * headway),
                       'max_crystal_primary_load_per_visit': str(crystal * headway)})
    return groups


def build(start=0, belt_rate=Fraction(2), unload_belt=Fraction(2), pipe_rate=None, headway=Fraction(60)):
    if (not 0 <= start <= MAX_STAGES - _UNLOAD_ROWS or min(belt_rate, unload_belt, headway) <= 0
            or (pipe_rate is not None and pipe_rate <= 0)):
        raise ValueError('地址须留出连续四道，带速、管速与到站间隔须为正数')
    feed = dict(_distribution(), X=0, Y=0)
    first, second = _work(start, 3, 0), _work(start + 1, 0, -3, turn=True)
    for row in _ROWS:
        check_jump(feed, first, row, 0, 2, fluid=True)
        if sum(e['T'] == 'FluidPortReceiverInternalVariant' and
               (e['X'], e['Y'], e['L'], e['R']) == (row, 37, 2, 3) for e in second['B']['Entries']) != 1:
            raise ValueError(f'第二道结晶 {row} 口未旋转到南面')
    head = (HEAD[0] + 3, 0)
    station = [{'T': 'Layout_TrainWaitStation', 'X': head[0], 'Y': 0, 'R': 3},
               {'T': 'Layout_TrainUnloader_Fluids_Flipped', 'X': head[0], 'Y': 1, 'R': 3}]
    rails = [dict(e, X=e['X'] + 6, Y=e['Y'] - 3) for e in approach_tracks(corner_stock=False)]
    crystal = _document([feed, first, second, *station, *rails])
    stock_entries, stock_report = _base_segment(start, belt_rate, headway)
    document = _document([*crystal['BP']['Entries'], *stock_entries])
    report = {'belt_items_per_second': str(belt_rate), 'unload_belt_items_per_second': str(unload_belt),
              'shared_pipe_liters_per_second': None if pipe_rate is None else str(pipe_rate),
              'planned_arrival_seconds': str(headway), 'groups': _bounds(belt_rate, unload_belt, pipe_rate, headway),
              'base_segment': stock_report,
              'crystal_segment': {'head': (*head, 0), 'rail': _rail_links(_islands(document), head, 'crystal'),
                                  'wagon': 1, 'raw_rows': (28, 29, 30, 31), 'primaries_by_layer': 'rgb',
                                  'work': [{'address': start, 'board': (3, 0, 0), 'rotation': 0,
                                            'operands': {'north': (-12, -18), 'levels': (0, 1)},
                                            'result': (37, 30, 0)},
                                           {'address': start + 1, 'board': (0, -3, 0), 'rotation': 3,
                                            'operands': {'west': (-18, 31), 'levels': (0, 1)},
                                            'result': (30, -18, 0)}],
                                  'dyes': [dict(color=c, floor=2, east=(37, y), north=(y, -18))
                                           for c, y in zip(COLORS, _ROWS, strict=True)],
                                  'max_per_dye_liters_per_second': str(2 * belt_rate * CRYSTAL_LITERS),
                                  'platforms_saved_at_intake': 1, **_stats(crystal)}}
    return document, report


def main():
    parser = argparse.ArgumentParser(description='导出四道基础料和两道结晶的混合车共用分配段')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--start', default=0, type=int)
    parser.add_argument('--belt-rate', default=Fraction(2), type=Fraction)
    parser.add_argument('--unload-belt', default=Fraction(2), type=Fraction)
    parser.add_argument('--pipe-rate', type=Fraction, help='共用管、混色和卸货各单路的最小持续实测速率，升/秒')
    parser.add_argument('--headway', default=Fraction(60), type=Fraction)
    args = parser.parse_args()
    try:
        if args.output.suffix != '.spz2bp':
            raise ValueError('--output 需要 .spz2bp 路径')
        document, report = build(args.start, args.belt_rate, args.unload_belt, args.pipe_rate, args.headway)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
