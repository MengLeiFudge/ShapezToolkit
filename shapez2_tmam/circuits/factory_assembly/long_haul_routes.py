"""按 145 道冻结配方划分混合车路线，导出接轨表和卸货记录表。"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from fractions import Fraction
from math import ceil
from pathlib import Path

from ..production_stage import build_stage
from .acceptance import _check_intakes, _check_loaders, _islands, _require_port
from .base_feed import build_base_stage
from .corner_line_sample import SAMPLES, corner_line
from .crystal_feed import add_crystal_feed
from .full_belt_sample import _route_load
from .layout import cargo_ports
from .recipe import replay
from .stage_pages import _document, _rail_links, _stations, _supply


_CSV_COLUMNS = ('route', 'stage', 'station', 'wagon', 'layer', 'row', 'cargo', 'unit', 'required_per_second',
                'planned_interval_seconds', 'min_amount_per_visit', 'measured_interval_seconds', 'measured_amount')


def _segment_peaks(stops: list[int], rows: list[dict]) -> dict[tuple[int, int], tuple[Fraction, Fraction]]:
    demand = defaultdict(Counter)
    for row in rows:
        if row['service'] == 'base':
            key = row['wagon'], row['layer'], row['cargo']
            demand[row['stage']][key] += Fraction(row['per_second'])
    peaks = {}
    for start in range(len(stops)):
        total = Counter()
        for stop in range(start + 1, len(stops) + 1):
            total.update(demand[stops[stop - 1]])
            shape = max((rate for (_, _, cargo), rate in total.items() if cargo.isupper()), default=Fraction(0))
            fluid = max((rate for (_, _, cargo), rate in total.items() if cargo.islower()), default=Fraction(0))
            peaks[start, stop] = shape, fluid
    return peaks


def _partition(peaks: dict, stops: int, routes: int, *, shape_cap: Fraction | None = None
               ) -> tuple[Fraction, tuple[int, ...]]:
    best = {0: (Fraction(0), ())}
    for route in range(1, routes + 1):
        next_best = {}
        for start, (previous, ends) in best.items():
            for stop in range(start + 1, stops - (routes - route) + 1):
                shape, fluid = peaks[start, stop]
                if shape_cap is not None and shape > shape_cap:
                    break
                peak = shape if shape_cap is None else fluid
                candidate = (max(previous, peak), (*ends, stop))
                if stop not in next_best or candidate < next_best[stop]:
                    next_best[stop] = candidate
        best = next_best
    return best[stops]


def _native_stops(stations: list[dict], rows: list[dict]) -> dict:
    crystal = build_stage(0, stream=True)['BP']['Entries']
    add_crystal_feed(crystal)
    layouts = {'base': _islands(_document(build_base_stage(0))), 'crystal': _islands(_document(crystal))}
    ports = cargo_ports()
    _check_loaders(ports)
    load = {('crystal' if p.station == 'crystal' else 'base', p.wagon, p.layer): p for p in ports}
    stop_rows = defaultdict(list)
    for row in rows:
        stop_rows[row['service'], row['stage']].append(row)
    result = {}
    for (service, stage), used in stop_rows.items():
        station = stations[stage]
        head_x, head_y = station[service + '_head']
        origin, _, _ = station['origin']
        local_head = head_x - origin, head_y
        islands = layouts[service]
        _check_intakes(islands, [{**station, service + '_head': local_head}], ports)
        rails = _rail_links(islands, local_head, service)
        for link in rails.values():
            for key in ('tile', 'outside_tile'):
                x, y, z = link[key]
                link[key] = (x + origin, y, z)
        unloads = []
        for row in used:
            wagon, layer, row_y = (row[key] for key in ('wagon', 'layer', 'row'))
            port = load[service, wagon, layer]
            if port.cargo != row['cargo'] or row_y not in port.rows:
                raise ValueError(f'工段 {stage} 的车厢 {wagon}、层 {layer}、行 {row_y} 与装载表不符')
            board_y = head_y if service == 'crystal' else head_y + 2 + 3 * ((wagon - 1) // 3)
            kind = 'FluidPortReceiver' if port.kind == 'Fluids' else 'BeltPortReceiver'
            _require_port(islands[local_head[0] + 3, board_y, 0], kind, -18, row_y, layer)
            unloads.append(dict(row, unloader=(head_x, head_y + wagon, 0),
                                platform=(head_x + 3, board_y, 0), receiver=(-18, row_y, layer)))
        result[service, stage] = {'stage': stage, 'head': (head_x, head_y, 0), 'rails': rails, 'unloads': unloads}
    return result


def build(route_count: int, headway: Fraction, belt_rate: Fraction) -> tuple[dict, list[dict]]:
    if headway <= 0 or belt_rate <= 0:
        raise ValueError('到站间隔和成品带速须为正数')
    sample = corner_line(*SAMPLES['suspended'])
    production = replay(sample['target'], sample['instructions'])
    stations = _stations(production, False)
    rows = _supply(production, belt_rate)['unload_rows']
    base = [s['stage'] for s in stations if 'base_head' in s]
    crystal = [s['stage'] for s in stations if 'crystal_head' in s]
    if not 1 <= route_count <= len(base):
        raise ValueError(f'基础料路线数须在 1 至 {len(base)} 之间')
    peaks = _segment_peaks(base, rows)
    # 用全线最优物品层峰值约束第二次划分，避免混用件数和升数。
    shape_cap, _ = _partition(peaks, len(base), route_count)
    fluid_cap, ends = _partition(peaks, len(base), route_count, shape_cap=shape_cap)
    groups = [('base', base[start:stop]) for start, stop in zip((0, *ends[:-1]), ends, strict=True)]
    groups.append(('crystal', crystal))
    native = _native_stops(stations, rows)
    routes = []
    records = []
    for index, (service, addresses) in enumerate(groups, 1):
        name = f'base-{index}' if service == 'base' else 'crystal'
        route = _route_load(rows, service, addresses, headway)
        visit_load = Counter()
        for row in route['rows']:
            fluid = row['cargo'].islower()
            amount = Fraction(row['required_unload_per_visit'])
            minimum = amount if fluid else ceil(amount)
            visit_load[row['wagon'], row['layer'], row['cargo']] += minimum
            records.append(dict(route=name, stage=row['stage'], station=service, wagon=row['wagon'],
                                layer=row['layer'], row=row['row'], cargo=row['cargo'],
                                unit='liter' if fluid else 'item', required_per_second=row['per_second'],
                                planned_interval_seconds=str(headway),
                                min_amount_per_visit=str(minimum),
                                measured_interval_seconds='', measured_amount=''))
        for layer in route['layers']:
            key = layer['wagon'], layer['layer'], layer['cargo']
            layer['required_load_per_visit'] = str(visit_load[key])
        routes.append({'route': name, 'service': service, 'layers': route['layers'],
                       'stops': [native[service, stage] for stage in addresses]})
    records.sort(key=lambda r: (r['stage'], r['station'], r['wagon'], r['layer'], r['row']))
    one_route_shape, one_route_fluid = peaks[0, len(base)]
    report = {'target': sample['target'], 'stages': len(production.stages),
              'belt_items_per_second': str(belt_rate), 'planned_interval_seconds': str(headway),
              'base_stations': len(base), 'crystal_stations': len(crystal),
              'active_unload_rows': len(records),
              'base_layer_peak_items_per_second': {'one_route': str(one_route_shape), 'split': str(shape_cap)},
              'base_layer_peak_liters_per_second': {'one_route': str(one_route_fluid), 'split': str(fluid_cap)},
              'routes': routes}
    return report, records


def main() -> int:
    parser = argparse.ArgumentParser(description='为 145 道悬空配方导出混合车接轨和逐站卸货量')
    parser.add_argument('--output-dir', type=Path, required=True, help='接轨 JSON 和实测 CSV 的保存目录')
    parser.add_argument('--base-routes', type=int, default=4, help='基础料混合车路线数，默认 4')
    parser.add_argument('--headway', type=Fraction, default=Fraction(60), help='每路规划到站间隔，秒')
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(2), help='成品目标带速，件/秒')
    args = parser.parse_args()
    try:
        report, records = build(args.base_routes, args.headway, args.belt_rate)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / 'long-haul-routes.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                            encoding='utf-8')
        with (args.output_dir / 'long-haul-unloads.csv').open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=_CSV_COLUMNS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(records)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    peak = report['base_layer_peak_items_per_second']
    print(f'{args.base_routes} 条基础料路线，单层峰值 {peak["one_route"]} → {peak["split"]} 件/秒，{len(records)} 条卸货行')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
