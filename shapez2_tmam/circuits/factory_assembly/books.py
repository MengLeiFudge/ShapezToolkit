"""独立导出六槽验收的实体、配料和通用火车三册。"""

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from ...synthesis.physics import PIN
from ..circuit import encode_document
from ..factory_book import TRAIN_BOOK, _station
from ..freight_loader import loading
from ..freight_stage import depot
from . import acceptance, sender
from .capacity import TrainDelivery, check_capacity, demands, parallel_lines
from .layout import cargo_ports, crystal_loading
from .recipe import replay

BOOKS = ('physical', 'proportioning', 'trains')


def _island_blueprint(entries):
    return {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': entries}}


def _measurements(data):
    rates = {name: Fraction(rate) for name, rate in data.get('rates', {}).items()}
    deliveries = {}
    for stop in data.get('deliveries', ()):
        key = stop['stage'], stop['station']
        if key in deliveries:
            raise ValueError(f'站场 {key} 的到货记录重复')
        payloads = {}
        for row in stop['payload']:
            port = row['wagon'], row['layer'], row['row']
            if port in payloads:
                raise ValueError(f'站场 {key} 的卸货端口 {port} 重复')
            payloads[port] = Fraction(row['amount'])
        deliveries[key] = TrainDelivery(Fraction(stop['interval_seconds']), payloads)
    return rates, deliveries


def _capacity_status(required, *rates):
    if any(rate is not None and rate < required for rate in rates):
        return 'insufficient'
    return 'unmeasured' if None in rates else 'meets_target'


def _order_capacity(plan, belt_rate, rates, deliveries, *, output=None):
    checks = check_capacity(plan, belt_rate, rates, deliveries)
    paths = []
    layers = defaultdict(Fraction)
    margins = []
    missing = 0
    for entry in checks:
        d = entry.demand
        required = entry.required_per_second
        key = {'stage': d.stage, 'path': d.path, 'resource': d.resource, 'unit': d.unit}
        paths.append(dict(key, required_per_second=str(required),
                          capacity_per_second=None if entry.available_per_second is None else str(entry.available_per_second)))
        margins.append((entry.available_per_second, required, dict(key, kind='processing_or_transport')))
        if d.port is None:
            if output is not None:
                paths[-1]['status'] = _capacity_status(required, entry.available_per_second)
            continue
        port = d.port
        service = 'crystal' if port.station == 'crystal' else 'base'
        layer = d.stage, service, port.wagon, port.layer, port.cargo, d.unit
        layers[layer] += required
        stop = deliveries.get((d.stage, service))
        amount = stop.payload.get((port.wagon, port.layer, d.row)) if stop is not None else None
        berth = dict(station=service, wagon=port.wagon, layer=port.layer, row=d.row)
        paths[-1].update(berth, train_per_second=None if entry.train_per_second is None else str(entry.train_per_second),
                         min_payload_per_trip=None if stop is None else str(required * stop.interval_seconds),
                         max_arrival_interval_seconds=None if amount is None else str(amount / required),
                         min_arrivals_per_minute=None if not amount else str(60 * required / amount))
        if output is not None:
            usage = service
            if service == 'base' and d.unit == 'liter':
                cell = plan.stages[d.stage].result.layers[0][int(port.station[1:])]
                if cell == PIN:
                    usage = 'pin'
            paths[-1].update(usage=usage, status=_capacity_status(required, entry.available_per_second,
                                                                 entry.train_per_second),
                             arrival_interval_seconds=None if stop is None else str(stop.interval_seconds),
                             payload_per_trip=None if amount is None else str(amount))
        margins.append((entry.train_per_second, required, dict(key, **berth, kind='train')))
    if output is not None:
        rate = rates.get('output_belt')
        key = {'path': 'product_exit', 'resource': 'output_belt', 'unit': 'item'}
        output_row = dict(output, **key, required_per_second=str(belt_rate),
                          capacity_per_second=None if rate is None else str(rate),
                          status=_capacity_status(belt_rate, rate))
        margins.append((rate, belt_rate, dict(key, kind='output')))
    bottleneck = None
    lowest = None
    for capacity, required, key in margins:
        if capacity is None:
            missing += 1
        elif lowest is None or capacity / required < lowest:
            lowest = capacity / required
            bottleneck = dict(key, fraction_of_target=str(lowest))
    report = {'belt_items_per_second': str(belt_rate), 'paths': paths,
              'loads': [dict(stage=stage, station=station, wagon=wagon, layer=layer, cargo=cargo, unit=unit,
                             required_per_second=str(required))
                        for (stage, station, wagon, layer, cargo, unit), required in sorted(layers.items())],
              'unknown_capacity_checks': missing, 'lowest_measured_capacity': bottleneck,
              'parallel_lines': parallel_lines(checks)}
    if output is not None:
        report['output'] = output_row
        if output_row['status'] != 'meets_target':
            report['parallel_lines'] = None
        statuses = {row['status'] for row in (*paths, output_row)}
        report['status'] = next(status for status in ('insufficient', 'unmeasured', 'meets_target') if status in statuses)
    return report


def _recipe_load(plan):
    used = {d.port for d in demands(plan) if d.port is not None}
    return tuple(port for port in cargo_ports() if port in used)


def _proportioning(ports):
    base = {port.cargo for port in ports if port.station != 'crystal'}
    crystal = {port.cargo for port in ports if port.station == 'crystal'}
    base_load = {f'base-load-{kind}-{cargo}': loading(cargo)
                 for kind, cargoes in (('shape', 'CRSW'), ('dye', 'rgb')) for cargo in cargoes if cargo in base}
    crystal_load = {f'crystal-load-{cargo}': crystal_loading(cargo) for cargo in 'rgb' if cargo in crystal}
    documents = {**base_load, **crystal_load}
    if base:
        documents['base-mixed-depot'] = depot()
    if crystal:
        documents['crystal-mixed-depot'] = _island_blueprint(_station('fluid-depot'))
    report = {'base_load': list(base_load), 'crystal_load': list(crystal_load),
              'load': [asdict(port) for port in ports], 'train_direction': 'north'}
    return documents, report


def _trains(ports):
    cargo = {port.cargo: 'fluid' if port.kind == 'Fluids' else 'shape' for port in ports}
    needed = set(cargo.values())
    documents = {name: _island_blueprint(_station(name)) for name in TRAIN_BOOK if name.split('-', 1)[0] in needed}
    report = {'single_cargo': {name: ('Fluids' if name.startswith('fluid') else 'Shapes') for name in documents},
              'train_direction': 'north'}
    return documents, report, cargo


def build(book: str, belt_rate: Fraction, measurements: dict, *,
          recipe_path: Path | None = None, direct_stack: bool = False,
          four_color: bool = False) -> tuple[dict[str, str], dict]:
    if four_color and (book != 'physical' or recipe_path is not None or direct_stack):
        raise ValueError('--four-color 只能单独用于实体分册')
    if direct_stack and recipe_path is not None:
        raise ValueError('--direct-stack 与 --recipe 只能选一个')
    if direct_stack and book == 'physical':
        raise ValueError('纯堆叠实体请使用 production --direct-stack 导出')
    if belt_rate <= 0:
        raise ValueError('成品带速须为正数')
    if book == 'physical':
        rates, deliveries = _measurements(measurements)
        blueprint, report = acceptance.build(sender.PACKET_TAG, compact=recipe_path is not None or four_color,
                                             recipe_path=recipe_path, four_color=four_color,
                                             compact_feeds=four_color)
        orders = report['orders']
        if four_color and {name: len(order['instructions']) for name, order in orders.items()} != {
                'four-color': 40, 'four-color-alternate': 41}:
            raise ValueError('--four-color 需要已发布的两份 40/41 道订单')
        plans = {name: replay(order['target'], order['instructions']) for name, order in orders.items()}
        output = report['interfaces']['output'] if four_color else None
        report['capacity'] = {name: _order_capacity(plan, belt_rate, rates, deliveries, output=output)
                              for name, plan in plans.items()}
        if four_color:
            return {'six-slot-four-color': blueprint}, report
        if recipe_path is not None:
            report['interfaces']['load'] = [asdict(port) for port in _recipe_load(plans['solver4'])]
            return {'six-slot-solver4': blueprint}, report
        return {'six-slot-acceptance': blueprint}, report
    ports = cargo_ports(machine_dyes=not direct_stack)
    if recipe_path is not None:
        order = acceptance._solver_order(recipe_path)
        ports = _recipe_load(replay(order['target'], order['instructions']))
    if book == 'proportioning':
        documents, report = _proportioning(ports)
    elif book == 'trains':
        documents, report, cargo = _trains(ports)
        if recipe_path is not None or direct_stack:
            report['cargo'] = cargo
    else:
        raise ValueError(f'未知分册 {book!r}')
    return {name: encode_document(document) for name, document in documents.items()}, report


def main() -> int:
    parser = argparse.ArgumentParser(description='分别生成六槽验收的实体、配料或通用火车分册')
    parser.add_argument('book', choices=BOOKS)
    parser.add_argument('--output-dir', type=Path, help='导出原生蓝图和分册 JSON 的目录')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--recipe', type=Path, help='Solver4 生成的 solved 指令 JSON')
    mode.add_argument('--direct-stack', action='store_true', help='生成纯堆叠工道的配料或通用火车册')
    mode.add_argument('--four-color', action='store_true', help='实体册使用 40/41 道四色含晶订单')
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(1), help='实体册目标件数/秒，默认按每秒 1 件列需求')
    parser.add_argument('--measurements', type=Path, help='实体册的机器、管带和到货实测 JSON')
    args = parser.parse_args()
    try:
        measurements = json.loads(args.measurements.read_text(encoding='utf-8')) if args.measurements else {}
        blueprints, report = build(args.book, args.belt_rate, measurements, recipe_path=args.recipe,
                                   direct_stack=args.direct_stack, four_color=args.four_color)
    except (ArithmeticError, KeyError, OSError, ValueError) as error:
        parser.error(str(error))
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, text in blueprints.items():
            (args.output_dir / f'{name}.spz2bp').write_text(text + '\n', encoding='utf-8')
        (args.output_dir / f'{args.book}.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{args.book} 分册共 {len(blueprints)} 份蓝图')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
