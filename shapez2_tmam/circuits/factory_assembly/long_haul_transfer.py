"""按长单四路运输表导出并行混合车配料场和车库。"""

import argparse
import csv
import json
from dataclasses import asdict
from fractions import Fraction
from math import ceil
from pathlib import Path

from ..circuit import encode_document
from ..factory_book import _station
from ..freight_loader import transfer
from ..freight_stage import CARS, depot
from .acceptance import _islands, _require_port, _require_station
from .layout import cargo_ports, crystal_loading
from .long_haul_routes import build as route_plan
from .stage_pages import _document, _stats


_CARGO_ORDER = 'CRSWrgb'
_ROUTE_PITCH = 18
_BANK_PITCH = 18
_CSV_COLUMNS = ('route', 'cargo', 'wagon', 'layer', 'unit', 'required_per_second', 'planned_mixed_interval_seconds',
                'min_mixed_load_per_visit', 'planned_single_interval_seconds', 'min_single_unload_per_visit',
                'measured_single_interval_seconds', 'measured_single_unload_per_visit',
                'measured_mixed_interval_seconds', 'measured_mixed_load_per_visit', 'measured_max_single_gap_seconds',
                'measured_usable_buffer', 'measured_mixed_round_trip_seconds')


def _north_rail(x: int, y: int) -> dict:
    return {'T': 'Rail_Forward', 'X': x, 'Y': y, 'R': 3, 'S': 'AQAAAAA='}


def _fill_track(entries: list[dict], x: int, low: int, high: int) -> None:
    occupied = {entry.get('Y', 0) for entry in entries if entry.get('X', 0) == x}
    entries.extend(_north_rail(x, y) for y in range(low, high + 1) if y not in occupied)


def _north_ports(x: int, low: int, high: int) -> dict:
    return {'arrival': {'tile': (x, high, 0), 'outside_tile': (x, high + 1, 0), 'rotation': 3},
            'departure': {'tile': (x, low, 0), 'outside_tile': (x, low - 1, 0), 'rotation': 3}}


def _check_transfer(board: dict, rows: tuple[int, ...], layer: int, kind: str) -> None:
    fluid = kind == 'Fluids'
    prefix = 'FluidPort' if fluid else 'BeltPort'
    straight = 'PipeForward' if fluid else 'BeltDefaultForward'
    lifts = ('PipeForward', 'PipeUpForward', 'Pipe2UpForward') if fluid else (
        'BeltDefaultForward', 'Lift1UpForward', 'Lift2UpForward')
    actual = {(e['X'], e['Y'], e['L']): (e['T'], e['R']) for e in board['B']['Entries']}
    for row in rows:
        _require_port(board, prefix + 'Receiver', -18, row, 0)
        _require_port(board, prefix + 'Sender', 37, row, layer)
        for x in range(-17, 37):
            expected = lifts[layer] if x == 0 else straight
            point = x, row, layer if x > 0 else 0
            if actual.get(point) != (expected + 'InternalVariant', 0):
                raise ValueError(f'换装台 {board["X"], board["Y"]} 的四路之一断开 {point}')


def _bank(route: dict, cargo: str, x: int, head_y: int) -> tuple[list[dict], dict]:
    base = route['service'] == 'base'
    if base:
        board, car, kind = transfer(cargo)
        layer = CARS[car][1].index(cargo)
        kinds = [car_kind for car_kind, _ in CARS * 4]
        rows = tuple(range(-12 + car * 20, -8 + car * 20))
    else:
        board = crystal_loading(cargo)['BP']['Entries'][0]
        layer, kind = 'rgb'.index(cargo), 'Fluids'
        kinds = [kind]
        rows = (28, 29, 30, 31)
    active = {l['wagon']: l for l in route['layers'] if l['cargo'] == cargo}
    entries = [{'T': 'Layout_TrainWaitStation', 'X': x + 3, 'Y': head_y, 'R': 3}]
    transfers = []
    for wagon, car_kind in enumerate(kinds, 1):
        wagon_y = head_y + wagon
        if wagon not in active:
            spacer = 'Shape' if car_kind == 'Shapes' else 'Fluid'
            entries.append({'T': 'Layout_TrainSpacerStraight' + spacer, 'X': x + 3, 'Y': wagon_y, 'R': 3})
            continue
        if car_kind != kind or active[wagon]['layer'] != layer:
            raise ValueError(f'{route["route"]} 的第 {wagon} 节车层与 {cargo} 装载表不符')
        board_y = wagon_y - rows[0] // 20
        if any(board_y + row // 20 != wagon_y for row in rows):
            raise ValueError(f'{cargo} 四路端口跨出第 {wagon} 节车厢')
        platform = dict(board, X=x, Y=board_y)
        _check_transfer(platform, rows, layer, kind)
        entries.extend((platform, {'T': 'Layout_TrainWaitStation', 'X': x - 3, 'Y': wagon_y - 1, 'R': 3},
                        {'T': 'Layout_TrainUnloader_' + kind + '_Flipped', 'X': x - 3, 'Y': wagon_y, 'R': 3},
                        {'T': 'Layout_TrainLoader_' + kind, 'X': x + 3, 'Y': wagon_y, 'R': 3}))
        transfers.append({**active[wagon], 'single_head': (x - 3, wagon_y - 1, 0),
                          'unloader': (x - 3, wagon_y, 0), 'loader': (x + 3, wagon_y, 0),
                          'platform': (x, board_y, 0), 'rows': rows, 'input_level': 0})
    low = min(row['single_head'][1] for row in transfers) - 1
    high = max(row['unloader'][1] for row in transfers) + 1
    _fill_track(entries, x - 3, low, high)
    return entries, {'cargo': cargo, 'mixed_head': (x + 3, head_y, 0), 'single_track': _north_ports(x - 3, low, high),
                     'transfers': list(reversed(transfers))}


def _check_track(indexed: dict, ports: dict) -> None:
    for link in ports.values():
        rail = indexed[link['tile']]
        if (rail['T'], rail['R']) != ('Rail_Forward', 3) or link['outside_tile'] in indexed:
            raise ValueError(f'铁路外接格被占用或轨向错误 {link["outside_tile"]}')
    x, low, _ = ports['departure']['tile']
    high = ports['arrival']['tile'][1]
    for y in range(low, high + 1):
        if indexed.get((x, y, 0), {}).get('R') != 3:
            raise ValueError(f'缺少连续北向轨 {(x, y)}')


def _yard(plan: dict) -> tuple[dict, dict, list[dict]]:
    yard, depots, routes = [], [], []
    for index, route in enumerate(plan['routes']):
        x = index * _ROUTE_PITCH
        cargoes = [cargo for cargo in _CARGO_ORDER if any(l['cargo'] == cargo for l in route['layers'])]
        blocks = []
        banks = []
        for index_in_route, cargo in enumerate(cargoes):
            head_y = (len(cargoes) - index_in_route - 1) * _BANK_PITCH
            bank, manifest = _bank(route, cargo, x, head_y)
            blocks.extend(bank)
            banks.append(manifest)
        base = route['service'] == 'base'
        count = 12 if base else 1
        low, high = -1, (len(cargoes) - 1) * _BANK_PITCH + count + 1
        _fill_track(blocks, x + 3, low, high)
        yard.extend(blocks)
        depot_entries = depot()['BP']['Entries'] if base else _station('fluid-depot')
        depots.extend(dict(e, X=e.get('X', 0) + x + 3, Y=e.get('Y', 0) + high + 5) for e in depot_entries)
        depots.append(_north_rail(x + 3, high + 2))
        routes.append({'route': route['route'], 'service': route['service'], 'wagons': count,
                       'mixed_track': _north_ports(x + 3, low, high), 'banks_in_driving_order': banks,
                       'depot_head': (x + 3, high + 5, 0), 'depot_departure': (x + 3, high + 2, 0),
                       'return_join': (x + 3, high + 1, 0),
                       'factory_stops': [{'stage': s['stage'], 'head': s['head'], 'rails': s['rails']}
                                         for s in route['stops']]})
    document, depot_document = _document(yard), _document(depots)
    _document([*yard, *depots])
    indexed = _islands(document)
    depot_index = _islands(depot_document)
    for route in routes:
        _check_track(indexed, route['mixed_track'])
        x, y, z = route['depot_departure']
        for point in ((x, y, z), (x, y + 1, z)):
            rail = depot_index[point]
            if (rail['T'], rail['R']) != ('Rail_Forward', 3):
                raise ValueError(f'车库出轨方向错误 {point}')
        if route['return_join'] in depot_index:
            raise ValueError(f'{route["route"]} 的回程接点被车库占用')
        for bank in route['banks_in_driving_order']:
            _check_track(indexed, bank['single_track'])
            hx, hy, _ = bank['mixed_head']
            _require_station(indexed, 'WaitStation', hx, hy)
            for n in range(1, route['wagons'] + 1):
                car = indexed[hx, hy + n, 0]['T']
                if not car.startswith(('Layout_TrainLoader_', 'Layout_TrainSpacerStraight')):
                    raise ValueError(f'{route["route"]} 的装货站第 {n} 节车位失去连续性')
            for port in bank['transfers']:
                kind = 'Shapes' if bank['cargo'].isupper() else 'Fluids'
                _require_station(indexed, 'WaitStation', *port['single_head'][:2])
                _require_station(indexed, f'Unloader_{kind}_Flipped', *port['unloader'][:2])
                _require_station(indexed, f'Loader_{kind}', *port['loader'][:2])
    return document, depot_document, routes


def build(mixed_interval: Fraction, single_interval: Fraction) -> tuple[dict, dict, dict, list[dict]]:
    if single_interval <= 0:
        raise ValueError('单料车到站间隔须为正数')
    plan, _ = route_plan(4, mixed_interval, Fraction(2))
    document, depots, routes = _yard(plan)
    records = []
    for route in routes:
        for bank in route['banks_in_driving_order']:
            cargo = bank['cargo']
            for layer in sorted(bank['transfers'], key=lambda row: row['wagon']):
                required = Fraction(layer['required_per_second'])
                amount = required * single_interval
                if cargo.isupper():
                    amount = ceil(amount)
                records.append(dict.fromkeys(_CSV_COLUMNS, '') | {
                    'route': route['route'], 'cargo': cargo, 'wagon': layer['wagon'], 'layer': layer['layer'],
                    'unit': 'item' if cargo.isupper() else 'liter', 'required_per_second': str(required),
                    'planned_mixed_interval_seconds': str(mixed_interval),
                    'min_mixed_load_per_visit': layer['required_load_per_visit'],
                    'planned_single_interval_seconds': str(single_interval), 'min_single_unload_per_visit': str(amount),
                })
    report = {'target': plan['target'], 'stages': plan['stages'], 'belt_items_per_second': plan['belt_items_per_second'],
              'planned_mixed_interval_seconds': str(mixed_interval),
              'planned_single_interval_seconds': str(single_interval), 'load': [asdict(p) for p in cargo_ports()],
              'transfer_yard': _stats(document), 'mixed_depots': _stats(depots), 'routes': routes}
    return document, depots, report, records


def main() -> int:
    parser = argparse.ArgumentParser(description='导出 145 道配方的混合车配料场、车库和补货记录表')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--headway', type=Fraction, default=Fraction(60), help='混合车规划到站间隔，秒')
    parser.add_argument('--single-headway', type=Fraction, default=Fraction(60), help='单料车规划到站间隔，秒')
    args = parser.parse_args()
    try:
        document, depots, report, records = build(args.headway, args.single_headway)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, data in (('long-haul-transfer', document), ('long-haul-mixed-depots', depots)):
            (args.output_dir / (name + '.spz2bp')).write_text(encode_document(data) + '\n', encoding='utf-8')
        (args.output_dir / 'long-haul-transfer.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                               encoding='utf-8')
        with (args.output_dir / 'long-haul-replenishment.csv').open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=_CSV_COLUMNS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(records)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'{len(report["routes"])} 条混合车配料轨，{len(records)} 项补货车层')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
