"""核算四色长单的供货，并导出整片直达的三段实体样件。"""

import argparse
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from ..circuit import encode_document
from . import sender
from .acceptance import _islands, _require_port, _require_station
from .capacity import demands
from .interface import PACKET_TAG
from .layout import _check_footprints, assemble
from .recipe import BASE, _packet, replay


_REPORT = Path(__file__).resolve().parents[2] / 'blueprints/验收/实体/四色含晶/four-color.json'
_BASE_ROUTES = ((0, 1, 7, 8, 17), (18, 24, 25, 36, 38))
_CRYSTAL_STOPS = (3, 10, 20, 27)
_MODES = ('sample', 'four-color', 'four-color-direct')
_TARGET = 'CuCuCuCu:P-CuCuCu'
_PACKETS = (_packet(BASE, destination=0, base='CuCuCuCu'),
            _packet(BASE, destination=1, base='P-CuCuCu'), _packet(7, 0, 1))


def _routes(orders, belt_rate, interval):
    result = {}
    for name, order in orders.items():
        levels, ports = Counter(), Counter()
        production = replay(order['target'], order['instructions'])
        for demand in demands(production):
            port = demand.port
            if port is None:
                continue
            service = 'crystal' if port.station == 'crystal' else 'base'
            layer = service, port.wagon, port.layer, port.cargo
            levels[layer] += demand.per_product
            ports[(*layer, demand.stage, demand.row)] += demand.per_product
        result[name] = {
            'stages': len(production.stages),
            'levels': [dict(service=service, wagon=wagon, layer=level, cargo=cargo,
                            amount_per_product=str(amount), amount_per_cycle=str(amount * belt_rate * interval))
                       for (service, wagon, level, cargo), amount in sorted(levels.items())],
            'ports': [dict(service=service, wagon=wagon, layer=level, cargo=cargo, stage=stage, row=row,
                           amount_per_second=str(amount * belt_rate), buffer_for_interval=str(amount * belt_rate * interval))
                      for (service, wagon, level, cargo, stage, row), amount in sorted(ports.items())],
        }
    return result


def _stop_links(islands, station, service):
    x, y = station[service + '_head']
    _require_station(islands, 'WaitStation', x, y)
    if service == 'base':
        inbound, outbound = (x - 1, y - 1, 1), (x, y - 1, 3)
    else:
        inbound, outbound = (x, y + 4, 3), (x - 1, y + 4, 1)
    links = {}
    for label, (xx, yy, rotation) in (('arrival', inbound), ('departure', outbound)):
        rail = islands.get((xx, yy, 0), {})
        if rail.get('T') != 'Rail_Forward' or rail.get('R', 0) != rotation:
            raise ValueError(f'工段 {station["stage"]} 的 {service} 接轨 {xx, yy} 不符')
        links[label] = {'rail': (xx, yy, 0), 'next_tile': (xx, yy - 1 if service == 'base' else yy + 1, 0),
                        'rotation': rotation}
    return {'stage': station['stage'], 'head': (x, y), **links}


def _attach_fleet(document, interfaces, orders, belt_rate, interval):
    islands = _islands(document)
    stations = {station['stage']: station for station in interfaces['stations']}
    load_table = {('crystal' if port['station'] == 'crystal' else 'base', port['wagon'], port['layer']): port
                  for port in interfaces['load']}
    fleets = {'base_west': ('base', _BASE_ROUTES[0]), 'base_east': ('base', _BASE_ROUTES[1]),
              'crystal': ('crystal', _CRYSTAL_STOPS)}
    for name, order in orders.items():
        for service in ('base', 'crystal'):
            expected = {stage for route_service, stops in fleets.values() if route_service == service for stage in stops}
            actual = {port['stage'] for port in order['ports'] if port['service'] == service}
            if actual != expected:
                raise ValueError(f'{name} 的 {service} 停靠地址与四色长单不同')
        for port in order['ports']:
            service, stage, wagon = (port[key] for key in ('service', 'stage', 'wagon'))
            layer, row = port['layer'], port['row']
            load = load_table[service, wagon, layer]
            if load['cargo'] != port['cargo'] or row not in load['rows']:
                raise ValueError(f'工段 {stage} 的车厢 {wagon} 层 {layer} 与混编装载表不符')
            x, head_y = stations[stage][service + '_head']
            fluid = load['kind'] == 'Fluids'
            _require_station(islands, 'Unloader_' + ('Fluids' if fluid else 'Shapes') + '_Flipped', x, head_y + wagon)
            y = head_y if service == 'crystal' else head_y + 2 + 3 * ((wagon - 1) // 3)
            if y + row // 20 != head_y + wagon:
                raise ValueError(f'工段 {stage} 的卸货行 {row} 与车厢 {wagon} 不符')
            _require_port(islands[x + 3, y, 0], 'FluidPortReceiver' if fluid else 'BeltPortReceiver', -18, row, layer)
            port['native'] = {'unloader': (x, head_y + wagon, 0), 'platform': (x + 3, y, 0),
                              'receiver': (-18, row, layer)}
    routes = {}
    for name, (service, addresses) in fleets.items():
        amounts = {}
        for order_name, order in orders.items():
            loads = Counter()
            for port in order['ports']:
                if port['service'] == service and port['stage'] in addresses:
                    key = port['wagon'], port['layer'], port['cargo']
                    loads[key] += Fraction(port['amount_per_second'])
            amounts[order_name] = [dict(wagon=wagon, layer=layer, cargo=cargo,
                                        amount_per_product=str(rate / belt_rate),
                                        amount_per_second=str(rate), amount_per_cycle=str(rate * interval))
                                   for (wagon, layer, cargo), rate in sorted(loads.items())]
        routes[name] = {'stops': [_stop_links(islands, stations[stage], service) for stage in addresses],
                        'wagons': 12 if service == 'base' else 1, 'levels_by_order': amounts}
    return routes


def build(path: Path = _REPORT, *, belt_rate=Fraction(2), interval=Fraction(60), mode='sample') -> tuple[dict, dict]:
    if belt_rate <= 0 or interval <= 0:
        raise ValueError('带速和车队间隔都须为正数')
    if mode not in _MODES:
        raise ValueError(f'未知工道模式 {mode!r}')
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    orders = _routes(data['orders'], belt_rate, interval)
    sample = mode == 'sample'
    if sample:
        source = {'plain-and-pin': {'target': _TARGET, 'instructions': _PACKETS}}
    else:
        if {name: order['stages'] for name, order in orders.items()} != {
                'four-color': 40, 'four-color-alternate': 41}:
            raise ValueError('四色整线需要已发布的两份 40/41 道订单')
        source = data['orders']
    programs = tuple(replay(order['target'], order['instructions']) for order in source.values())
    count = max(len(program.stages) for program in programs)
    document, interfaces = assemble(count, packet_tag=PACKET_TAG, handoff=True, compact_base=True,
                                    compact_dyes=not sample, plain_base=mode != 'four-color', fixed_orders=programs)
    transmitters, sender_ports = sender.build(source, PACKET_TAG)
    islands = document['BP']['Entries']
    islands.extend(transmitters)
    _check_footprints(islands)
    report = {'belt_items_per_second': str(belt_rate), 'fleet_interval_seconds': str(interval),
              'long_orders': orders, 'interfaces': interfaces, 'sender': sender_ports}
    if sample:
        report['sample'] = {**source['plain-and-pin'], 'product_slot': programs[0].product_slot}
    else:
        report['mode'] = mode
        report['fleets'] = _attach_fleet(document, interfaces, orders, belt_rate, interval)
        report['platforms'] = sum(e['T'] == 'Foundation_3x3' for e in islands)
    report.update(islands=len(islands), buildings=sum(len(e.get('B', {}).get('Entries', ())) for e in islands))
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description='导出整片直达样件，以及四色长单车厢和卸货行需求')
    parser.add_argument('--report', type=Path, default=_REPORT, help='40／41 道四色实体的配方接口 JSON')
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(2), help='目标成品带速，件/秒')
    parser.add_argument('--fleet-interval', type=Fraction, default=Fraction(60), help='用于核算的车队到站间隔，秒')
    parser.add_argument('--mode', choices=_MODES, default='sample',
                        help='三段样件、四色合板整线、四色整片直达整线')
    parser.add_argument('--output', type=Path, required=True, help='原生蓝图文件，同名 JSON 保存报告')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    try:
        document, report = build(args.report, belt_rate=args.belt_rate, interval=args.fleet_interval, mode=args.mode)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                    encoding='utf-8')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
