"""导出悬空配方的满带验收工段、观察点和货运下限。"""

import argparse
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from ..circuit import encode_document
from ..production_line import check_jump
from ..slot_stream_ports import transport_paths
from ..work_lane import A_X
from .acceptance import _islands
from .capacity import demands
from .corner_line_sample import SAMPLES, corner_line
from .interface import PACKET_TAG, recipe_interface
from .layout import _stack_lane
from .recipe import Production, replay
from .stage_pages import _document, _page, _shortest_window, _stations, _stats, _supply


_BELT_RATE = Fraction(2)
# 两侧入带各一条，分两组各三路后全部从原东口回料。
_STACK_ROWS = (-15, -9, -3, 18, 24, 30)
_STACK = 7
_STACK_MACHINE = 'StackerStraightInternalVariant'

def _add_reader(island: dict, point: tuple[int, int, int], rotation: int) -> dict:
    entries = island['B']['Entries']
    for index, entry in enumerate(entries):
        if ((entry['X'], entry['Y'], entry['L']) == point
                and entry['T'] == 'BeltDefaultForwardInternalVariant' and entry['R'] == rotation):
            path = transport_paths(island).get((*point, (rotation + 2) % 4))
            if path == ((*point, rotation),):
                # 直通桥共用建筑列表，只替换当前平台。
                updated = list(entries)
                updated[index] = dict(entry, T='BeltReaderDefaultInternalVariant')
                island['B'] = dict(island['B'], Entries=updated)
                return {'island': (island['X'], island.get('Y', 0), island.get('Z', 0)),
                        'building': point, 'rotation': rotation}
    raise ValueError(f'观察点 {point} 缺少方向正确的直带')


def _observe_stack(take: dict, work: dict) -> dict:
    machines = [entry for entry in work['B']['Entries'] if entry['T'] == _STACK_MACHINE]
    if tuple(sorted(e['Y'] for e in machines)) != _STACK_ROWS:
        raise ValueError('六机堆叠平台的六个支路未对齐')
    readers = {'a': _add_reader(take, (A_X, 36, 0), 1), 'b': _add_reader(take, (A_X, 36, 1), 1),
               'result': _add_reader(work, (34, 30, 0), 0)}
    return {'island': (work['X'], work['Y'], 0), 'readers': readers,
            'machines': [(e['X'], e['Y'], e['L']) for e in machines],
            'remaining_slots': 'through', 'required_opcode': _STACK}


def _machine_budget(production: Production, start: int, stop: int) -> list[dict]:
    groups = defaultdict(list)
    for demand in demands(production):
        if demand.port is None and demand.resource != 'belt':
            key = demand.resource, demand.unit, demand.per_product
            groups[key].append((demand.stage, demand.path))
    result = []
    for (machine, unit, amount), sites in sorted(groups.items()):
        rate = _BELT_RATE * amount
        result.append({'machine': machine, 'unit': unit, 'whole_recipe_sites': len(sites),
                       'representative_sites': [dict(stage=stage, path=path) for stage, path in sites
                                                if start <= stage < stop],
                       'required_rate_per_second': str(rate),
                       'required_parallel_after_measurement': 'ceil(required_rate_per_second / measured_rate_per_machine)'})
    return result


def _route_load(rows: list[dict], service: str, stops: list[int], headway: Fraction) -> dict:
    levels = Counter()
    used = []
    for row in rows:
        if row['service'] == service and row['stage'] in stops:
            rate = Fraction(row['per_second'])
            levels[row['wagon'], row['layer'], row['cargo']] += rate
            used.append({**row, 'required_unload_per_visit': str(rate * headway)})
    return {'service': service, 'stops': stops, 'headway_seconds': str(headway),
            'layers': [dict(wagon=wagon, layer=layer, cargo=cargo,
                            required_per_second=str(rate), required_load_per_visit=str(rate * headway))
                       for (wagon, layer, cargo), rate in sorted(levels.items())], 'rows': used}


def build(headway: Fraction = Fraction(60)) -> tuple[dict, dict]:
    if headway <= 0:
        raise ValueError('到站间隔须为正数')
    order = corner_line(*SAMPLES['suspended'])
    production = replay(order['target'], order['instructions'])
    start, stop = _shortest_window(production)
    stations = _stations(production, False)[start:stop]
    document, page = _page(stations, terminal=False)
    entries = document['BP']['Entries']
    islands = _islands(document)
    stack = {}
    for station in stations:
        if station['opcode'] != _STACK:
            continue
        x, _, _ = station['origin']
        previous = islands[x, 3, 0]
        work = dict(_stack_lane(), X=x)
        for level in (0, 1):
            check_jump(islands[x, 0, 0], work, A_X, 1, level)
        bridge = [('SpaceBelt_LeftTurn', 4, 0), ('SpaceBelt_Forward', 3, 3), ('SpaceBelt_Forward', 2, 3)]
        for kind, y, rotation in bridge:
            rail = islands.get((x + 2, y, 0), {})
            if (rail.get('T'), rail.get('R', 0)) != (kind, rotation):
                raise ValueError(f'工段 {station["stage"]} 缺少原南侧回料桥')
        ports = work['B']['Entries']
        if not any((e['T'], e['X'], e['Y'], e['L'], e['R']) == ('BeltPortSenderInternalVariant', 37, 30, 0, 0)
                   for e in ports):
            raise ValueError('六机堆叠回料未对齐原加工台出口')
        stack[station['stage']] = _observe_stack(islands[x, 0, 0], work)
        entries[entries.index(previous)] = work
    outlet = islands[page['output']['island']]
    outlet_readers = {slot: _add_reader(outlet, (34, row, 0), 0)
                      for slot, row in enumerate(page['output']['rows'])
                      if slot in order['stages'][stop - 1]['live']}
    document = _document(entries)
    supply = _supply(production, _BELT_RATE)
    rows = supply['unload_rows']
    base = [s['stage'] for s in stations if 'base_head' in s]
    crystal = [s['stage'] for s in stations if 'crystal_head' in s]
    midpoint = len(base) // 2
    routes = [_route_load(rows, 'base', stops, headway) for stops in (base[:midpoint], base[midpoint:]) if stops]
    routes += [_route_load(rows, 'crystal', crystal, headway)]
    report = {'target': order['target'], 'window': (start, stop), 'belt_items_per_minute': '120',
              'installed_packets': order['instructions'][start:stop], 'input_live_slots': order['stages'][start - 1]['live'],
              'expected_output_slots': order['stages'][stop - 1]['live'], 'page': {**page, **_stats(document)},
              'outlet_readers': outlet_readers,
              'stack': {'stages': stack, 'parallel_physical_machines': len(stack) * 6,
                        'standalone_wait_seconds': '5/2', 'ideal_one_machine_per_minute': '24',
                        'design_one_machine_per_minute': '20', 'theoretical_minimum': 5,
                        'installed_per_stage': 6, 'minimum_measured_rate_per_machine_per_minute': '20',
                        'a_and_b_each_per_minute': '120', 'merged_output_per_minute': '120'},
              'machine_budget': _machine_budget(production, start, stop),
              'whole_recipe_supply': supply,
              'representative_routes': routes,
              'recipe': recipe_interface(len(production.stages), PACKET_TAG)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description='导出悬空配方的六机堆叠代表段及满带观察点')
    parser.add_argument('--output', type=Path, required=True, help='原生蓝图及同名供货接口表')
    parser.add_argument('--headway', type=Fraction, default=Fraction(60), help='核算每路来车间隔，秒')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 路径')
    try:
        document, report = build(args.headway)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                   encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
