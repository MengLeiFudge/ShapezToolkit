"""独立导出六槽验收的实体、配料和通用火车三册。"""

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from ..circuit import encode_document
from ..factory_book import TRAIN_BOOK, _station
from ..freight_loader import loading
from ..freight_stage import depot
from . import acceptance, sender
from .capacity import TrainDelivery, check_capacity, parallel_lines
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


def _order_capacity(order, belt_rate, rates, deliveries):
    plan = replay(order['target'], order['instructions'])
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
        margins.append((entry.train_per_second, required, dict(key, **berth, kind='train')))
    bottleneck = None
    lowest = None
    for capacity, required, key in margins:
        if capacity is None:
            missing += 1
        elif lowest is None or capacity / required < lowest:
            lowest = capacity / required
            bottleneck = dict(key, fraction_of_target=str(lowest))
    return {'belt_items_per_second': str(belt_rate), 'paths': paths,
            'loads': [dict(stage=stage, station=station, wagon=wagon, layer=layer, cargo=cargo, unit=unit,
                           required_per_second=str(required))
                      for (stage, station, wagon, layer, cargo, unit), required in sorted(layers.items())],
            'unknown_capacity_checks': missing, 'lowest_measured_capacity': bottleneck,
            'parallel_lines': parallel_lines(checks)}


def build(book: str, belt_rate: Fraction, measurements: dict) -> tuple[dict[str, str], dict]:
    if belt_rate <= 0:
        raise ValueError('成品带速须为正数')
    if book == 'physical':
        rates, deliveries = _measurements(measurements)
        blueprint, report = acceptance.build(sender.PACKET_TAG)
        report['capacity'] = {name: _order_capacity(order, belt_rate, rates, deliveries)
                              for name, order in report['orders'].items()}
        return {'six-slot-acceptance': blueprint}, report
    if book == 'proportioning':
        base_load = {f'base-load-{kind}-{cargo}': loading(cargo)
                     for kind, cargoes in (('shape', 'CRSW'), ('dye', 'rgb')) for cargo in cargoes}
        crystal_load = {f'crystal-load-{cargo}': crystal_loading(cargo) for cargo in 'rgb'}
        documents = {**base_load, **crystal_load, 'base-mixed-depot': depot(),
                     'crystal-mixed-depot': _island_blueprint(_station('fluid-depot'))}
        report = {'base_load': list(base_load), 'crystal_load': list(crystal_load),
                  'load': [asdict(port) for port in cargo_ports()], 'train_direction': 'north'}
    elif book == 'trains':
        documents = {name: _island_blueprint(_station(name)) for name in TRAIN_BOOK}
        report = {'single_cargo': {name: ('Fluids' if name.startswith('fluid') else 'Shapes') for name in TRAIN_BOOK},
                  'train_direction': 'north'}
    else:
        raise ValueError(f'未知分册 {book!r}')
    return {name: encode_document(document) for name, document in documents.items()}, report


def main() -> int:
    parser = argparse.ArgumentParser(description='分别生成六槽验收的实体、配料或通用火车分册')
    parser.add_argument('book', choices=BOOKS)
    parser.add_argument('--output-dir', type=Path, help='导出原生蓝图和分册 JSON 的目录')
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(1), help='实体册目标件数/秒，默认按每秒 1 件列需求')
    parser.add_argument('--measurements', type=Path, help='实体册的机器、管带和到货实测 JSON')
    args = parser.parse_args()
    try:
        measurements = json.loads(args.measurements.read_text(encoding='utf-8')) if args.measurements else {}
        blueprints, report = build(args.book, args.belt_rate, measurements)
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
