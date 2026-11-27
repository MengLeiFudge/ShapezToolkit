"""给 12 格通用工道页配两条混合车环线和单料车换装场。"""

import argparse
import base64
import json
from collections import Counter
from fractions import Fraction
from math import ceil
from pathlib import Path

from ...mari.blueprint import DIRECTIONS
from ..circuit import encode_document
from ..freight_stage import CARS
from .capacity import demands
from .compact_book import CAPACITY, PAGE_COUNT, PAGE_SIZE, StageTemplate, _entry, _supply_ports, build_page
from .compact_slot_pages import PITCH
from .corner_line_sample import SAMPLES, corner_line
from .long_haul_transfer import _yard
from .recipe import replay
from .stage_pages import _document, _islands, _stats


_CARGO = 'CRSWrgb'
_WAGONS = {'base': CARS * 4, 'crystal': (CARS[-1],)}
_PLACEMENT = {'base': (33, -180), 'crystal': (57, 30)}
_CONNECTIONS = {'Rail_Forward': ((2, 0),), 'Rail_LeftTurn': ((2, 3),), 'Rail_RightTurn': ((2, 1),),
                'Rail_LeftFwdMerger': ((2, 0), (3, 0)), 'Rail_RightFwdMerger': ((2, 0), (1, 0))}


def _pose(x, y, kind, rotation):
    config = base64.b64encode(bytes([len(_CONNECTIONS[kind])]) + bytes(4 * len(_CONNECTIONS[kind]))).decode('ascii')
    return {'T': kind, 'X': x, 'Y': y, 'R': rotation, 'S': config}


def _walk(*corners):
    points = [corners[0]]
    for (x, y), (u, v) in zip(corners, corners[1:]):
        if (x == u) == (y == v):
            raise ValueError(f'轨段 {(x, y)} 到 {(u, v)} 须为非零直线')
        dx, dy = (u > x) - (u < x), (v > y) - (v < y)
        points.extend((x + i * dx, y + i * dy) for i in range(1, abs(u - x) + abs(v - y) + 1))
    return points


def _direction(a, b):
    return DIRECTIONS.index((b[0] - a[0], b[1] - a[1]))


def _lay(points):
    for a, (x, y), b in zip(points, points[1:], points[2:]):
        enter = _direction(a, (x, y))
        leave = _direction((x, y), b)
        turn = (leave - enter) % 4
        kind = {0: 'Rail_Forward', 1: 'Rail_RightTurn', 3: 'Rail_LeftTurn'}[turn]
        yield _pose(x, y, kind, enter)


def _move_board(entry, dx, dy=0):
    return dict(entry, X=entry.get('X', 0) + dx, Y=entry.get('Y', 0) + dy)


def _move(point, dx, dy=0):
    return (point[0] + dx, point[1] + dy, *point[2:])


def _shift_ports(ports, dx, dy):
    return {end: dict(link, tile=_move(link['tile'], dx, dy), outside_tile=_move(link['outside_tile'], dx, dy))
            for end, link in ports.items()}


def _transfer(service, name, peaks):
    route = {'route': name, 'service': service, 'stops': (), 'layers': peaks}
    document, depots, manifests = _yard({'routes': [route]})
    manifest, = manifests
    dx, dy = _PLACEMENT[service]
    mixed = _shift_ports(manifest['mixed_track'], dx, dy)
    banks = []
    for bank in manifest['banks_in_driving_order']:
        transfers = []
        for transfer in bank['transfers']:
            moved = {key: _move(transfer[key], dx, dy) for key in ('single_head', 'unloader', 'loader', 'platform')}
            transfers.append({**moved, **{k: transfer[k] for k in ('wagon', 'layer', 'rows', 'input_level')}})
        banks.append({'cargo': bank['cargo'], 'single_track': _shift_ports(bank['single_track'], dx, dy),
                      'mixed_head': _move(bank['mixed_head'], dx, dy), 'transfers': transfers})
    entries = [_move_board(entry, dx, dy) for doc in (document, depots) for entry in doc['BP']['Entries']]
    return entries, {'mixed_track': mixed, 'raw_banks': banks, 'return_join': _move(manifest['return_join'], dx, dy),
                     'depot_head': _move(manifest['depot_head'], dx, dy),
                     'depot_departure': _move(manifest['depot_departure'], dx, dy)}


def _station_track(station):
    start = tuple(station['arrival']['tile'][:2])
    end = tuple(station['departure']['tile'][:2])
    y = -4 if station['service'] == 'base' else 2
    return _walk(start, (start[0], y), (end[0], y), end)


def _circuit(service, stations, yard):
    start = tuple(yard['mixed_track']['departure']['tile'][:2])
    merge = yard['return_join'][:2]
    join = tuple(yard['mixed_track']['arrival']['tile'][:2])
    first, last = _station_track(stations[0])[0], _station_track(stations[-1])[-1]
    outer = start[1] - 6 if service == 'base' else 15
    between = -21 if service == 'base' else 10
    feed = _walk(start, (start[0], outer), (first[0], outer), first)
    segments = [feed]
    circuit = feed[:-1]
    for index, station in enumerate(stations):
        own = _station_track(station)
        circuit.extend(own)
        if index + 1 < len(stations):
            a = own[-1]
            b = _station_track(stations[index + 1])[0]
            line = _walk(a, (a[0], between), (b[0], between), b)
            segments.append(line)
            circuit.extend(line[1:-1])
    if service == 'base':
        into_yard = _walk(last, (last[0], merge[1]), merge, join)
    else:
        # 回程横轨绕过红料单车进站口。
        bend_x, bypass_y = merge[0] - 3, merge[1] + 3
        into_yard = _walk(last, (last[0], bypass_y), (bend_x, bypass_y), (bend_x, merge[1]), merge, join)
    reach = _walk(join, start)
    circuit.extend(into_yard[1:-1])
    circuit.extend(reach[:-1])
    kind = 'Rail_RightFwdMerger' if service == 'base' else 'Rail_LeftFwdMerger'
    rails = [entry for points in segments for entry in _lay(points)]
    rails.extend(_lay(into_yard))
    rails[-1] = _pose(*merge, kind, 3)
    return rails, circuit


def _check_circuit(indexed, circuit, depot):
    if len(circuit) != len(set(circuit)):
        raise ValueError('混合车环线在同一格交叠')
    def require(a, b, c):
        x, y = b
        rail = indexed[x, y, 0]
        r = rail.get('R', 0)
        inputs = _CONNECTIONS.get(rail['T'])
        if inputs is None:
            if not rail['T'].startswith(('Layout_TrainWaitStation', 'Layout_TrainLoader_', 'Layout_TrainUnloader_',
                                         'Layout_TrainSpacerStraight')):
                raise ValueError(f'环线含未识别岛块 {b}')
            inputs = ((2, 0),)
        elif base64.b64decode(rail['S']) != bytes([len(inputs)]) + bytes(4 * len(inputs)):
            raise ValueError(f'轨道颜色筛选与通车条件不符 {b}')
        needed = (_direction(b, a), _direction(b, c))
        if needed not in {((p + r) % 4, (q + r) % 4) for p, q in inputs}:
            raise ValueError(f'原生铁轨 {b} 的 {rail["T"]} 无法从 {a} 接向 {c}')

    for a, b, c in zip(circuit[-1:] + circuit[:-1], circuit, circuit[1:] + circuit[:1], strict=True):
        require(a, b, c)
    head = tuple(depot['depot_head'][:2])
    merge = tuple(depot['return_join'][:2])
    if indexed[(*head, 0)]['T'] != 'Layout_TrainProducer_Red':
        raise ValueError(f'车库 {head} 缺少发车口')
    # 车库自带相邻出车连接，第一段原生直轨从车头以北两格开始。
    launch = _walk((head[0], head[1] - 1), (merge[0], merge[1] - 1))
    for a, b, c in zip(launch, launch[1:], launch[2:]):
        require(a, b, c)
    for bank in depot['raw_banks']:
        for link in bank['single_track'].values():
            if link['outside_tile'] in indexed:
                raise ValueError(f'单料车 {bank["cargo"]} 接轨口被占用 {link["outside_tile"]}')


def _envelope(rate, headway):
    limits = {}
    for service, ports in _supply_ports(rate, headway).items():
        alternatives = {}
        for port in ports:
            key = port['wagon'], port['layer'], port['cargo']
            choices = alternatives.setdefault(key, Counter())
            choices.update({name: Fraction(v) for name, v in port['per_product'].items()})
        # 区间可带入六活槽，基础料每次添一槽，归并一次最多收回一槽。
        steps = min(PAGE_SIZE, (PAGE_SIZE + 6) // 2) if service == 'base' else PAGE_SIZE
        limits[service] = [dict(wagon=w, layer=l, cargo=c, unit='item' if c.isupper() else 'liter',
                                required_per_second=str(max(choices.values()) * rate * steps))
                           for (w, l, c), choices in sorted(alternatives.items())]
    return limits


def _dispatch(rate, headway, cycle, payload, unit):
    required = ceil(rate * headway) if unit == 'item' else rate * headway
    trains = ceil(cycle / headway) if rate else 0
    visits = 60 / headway if rate else Fraction(0)
    if payload is not None and rate:
        visits = max(visits, 60 * rate / payload)
        trains = ceil(cycle * visits / 60)
    return {'per_second': str(rate), 'min_payload_at_planned_headway': str(required),
            'visits_per_minute': str(visits), 'min_parallel_trains': trains}


def _requirements(page, limits, fixed, headway, mixed_cycle, raw_cycle, mixed_loads, raw_loads):
    groups = []
    for service, layers in limits.items():
        loaded, raw, raw_fixed = [], Counter(), Counter()
        for item in layers:
            wagon, level, cargo = (item[k] for k in ('wagon', 'layer', 'cargo'))
            unit = item['unit']
            bound = Fraction(item['required_per_second'])
            actual = fixed[page, service, wagon, level, cargo]
            if actual > bound:
                raise ValueError(f'第 {page} 页 {service} 车厢 {wagon} 层 {level} 超出通用供货上界')
            raw[cargo] += bound
            raw_fixed[cargo] += actual
            loaded.append(dict(item, upper_bound=_dispatch(bound, headway, mixed_cycle, mixed_loads[unit], unit),
                               fixed_order=_dispatch(actual, headway, mixed_cycle, mixed_loads[unit], unit)))
        orders = []
        for cargo in _CARGO:
            if cargo not in raw:
                continue
            unit = 'item' if cargo.isupper() else 'liter'
            orders.append({'cargo': cargo, 'unit': unit, 'single_wagon_layer': 0,
                           'upper_bound': _dispatch(raw[cargo], headway, raw_cycle, raw_loads[unit], unit),
                           'fixed_order': _dispatch(raw_fixed[cargo], headway, raw_cycle, raw_loads[unit], unit)})
        groups.append({'service': service, 'layers': loaded, 'raw_orders': orders,
                       'mixed_parallel_upper_bound': max(item['upper_bound']['min_parallel_trains'] for item in loaded),
                       'mixed_parallel_fixed_order': max(item['fixed_order']['min_parallel_trains'] for item in loaded)})
    return groups


def build(page, origin_x, order, rate, headway, mixed_cycle, raw_cycle, mixed_loads, raw_loads):
    production = replay(order['target'], order['instructions'])
    if len(production.stages) > CAPACITY:
        raise ValueError('冻结配方超过 486 道容量')
    actual = Counter()
    stop_loads = {}
    for demand in demands(production):
        if demand.port is None:
            continue
        port = demand.port
        service = 'crystal' if port.station == 'crystal' else 'base'
        load = demand.per_product * rate
        actual[demand.stage // PAGE_SIZE, service, port.wagon, port.layer, port.cargo] += load
        table = stop_loads.setdefault((demand.stage, service), Counter())
        table[port.wagon, port.layer, demand.row, port.cargo, demand.unit] += load
    limits = _envelope(rate, headway)
    template = StageTemplate()
    supply = _supply_ports(rate, headway)
    zero, first = build_page(template, _entry(0, 0), supply)
    overlay = []
    routes = {}
    for service, layers in limits.items():
        yards, yard = _transfer(service, service, layers)
        stations = [s for s in first['stations'] if s['service'] == service]
        if service == 'crystal':
            stations.reverse()
        rails, circuit = _circuit(service, stations, yard)
        _check_circuit(_islands(_document([*zero['BP']['Entries'], *yards, *rails])), circuit, yard)
        overlay.extend((*yards, *rails))
        routes[service] = {**yard, 'stop_order': [s['stage'] for s in stations],
                           'stations': [{k: s[k] for k in ('stage', 'head', 'arrival', 'departure')} for s in stations],
                           'wagons': [{'wagon': i, 'kind': kind, 'layers': layers}
                                      for i, (kind, layers) in enumerate(_WAGONS[service], 1)],
                           'loop_island_steps': len(circuit)}
    # 相邻页的装配间距恒定，核对一次共用边界。
    next_page, _ = build_page(template, _entry(1, 0), supply)
    _document([*zero['BP']['Entries'], *overlay, *next_page['BP']['Entries'],
               *(_move_board(board, PAGE_SIZE * PITCH) for board in overlay)])
    factory, contacts = build_page(template, _entry(page, origin_x), supply)
    shifted = _document([_move_board(board, contacts['place_at'][0]) for board in overlay])
    connected = _document([*factory['BP']['Entries'], *shifted['BP']['Entries']])
    groups = []
    for number in range(PAGE_COUNT):
        group = _entry(number, origin_x)
        group['routes'] = _requirements(number, limits, actual, headway, mixed_cycle, raw_cycle, mixed_loads, raw_loads)
        for route in group['routes']:
            service = route['service']
            stops = [group['start'] + i for i in routes[service]['stop_order']]
            route['factory_stop_addresses'] = stops
            route['fixed_stop_loads'] = [
                {'stage': stage, 'wagon': wagon, 'layer': layer, 'row': row, 'cargo': cargo, 'unit': unit,
                 'per_second': str(load),
                 'min_per_visit': str(ceil(load * headway) if unit == 'item' else load * headway)}
                for stage in stops
                for (wagon, layer, row, cargo, unit), load in sorted(stop_loads.get((stage, service), {}).items())
            ]
        groups.append(group)
    report = {'sample': {**contacts, 'rail_overlay_size': _stats(shifted), 'connected_size': _stats(connected)},
              'fixed_order': {'target': production.target.to_key(), 'instructions': len(production.stages)},
              'belt_items_per_second': str(rate), 'headway_seconds': str(headway),
              'planned_mixed_cycle_seconds': str(mixed_cycle), 'planned_raw_cycle_seconds': str(raw_cycle),
              'assumed_mixed_payload': {k: str(v) if v is not None else None for k, v in mixed_loads.items()},
              'assumed_raw_payload': {k: str(v) if v is not None else None for k, v in raw_loads.items()},
              'route_templates': routes, 'groups': groups}
    return connected, shifted, report


def main() -> int:
    parser = argparse.ArgumentParser(description='导出一页真实双环和 486 道分组运输表')
    parser.add_argument('--output-prefix', type=Path, required=True)
    parser.add_argument('--page', type=int, default=0)
    parser.add_argument('--origin-x', type=int, default=0)
    parser.add_argument('--recipe', type=Path, help='固定订单的 target 与 instructions JSON')
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(2))
    parser.add_argument('--headway', type=Fraction, default=Fraction(60))
    parser.add_argument('--mixed-cycle', type=Fraction, default=Fraction(120))
    parser.add_argument('--raw-cycle', type=Fraction, default=Fraction(120))
    for flag in ('mixed-shape-payload', 'mixed-fluid-payload', 'raw-shape-payload', 'raw-fluid-payload'):
        parser.add_argument('--' + flag, type=Fraction)
    args = parser.parse_args()
    try:
        mixed_loads = {'item': args.mixed_shape_payload, 'liter': args.mixed_fluid_payload}
        raw_loads = {'item': args.raw_shape_payload, 'liter': args.raw_fluid_payload}
        values = (args.belt_rate, args.headway, args.mixed_cycle, args.raw_cycle, *mixed_loads.values(), *raw_loads.values())
        if not 0 <= args.page < PAGE_COUNT or any(v <= 0 for v in values if v is not None):
            raise ValueError('页码须在 0 至 53，流量、载量和时间须为正数')
        order = json.loads(args.recipe.read_text(encoding='utf-8-sig')) if args.recipe else corner_line(*SAMPLES['suspended'])
        page, overlay, plan = build(args.page, args.origin_x, order, args.belt_rate, args.headway, args.mixed_cycle,
                                    args.raw_cycle, mixed_loads, raw_loads)
        prefix = args.output_prefix
        prefix.parent.mkdir(parents=True, exist_ok=True)
        for suffix, doc in (('-page.spz2bp', page), ('-overlay.spz2bp', overlay)):
            prefix.with_name(prefix.name + suffix).write_text(encode_document(doc) + '\n', encoding='utf-8')
        prefix.with_name(prefix.name + '.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
