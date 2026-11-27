"""导出 486 道工道册共用的单料、换装和回圈装配件。"""

import argparse
import base64
import gzip
import json
from fractions import Fraction
from pathlib import Path

from ..circuit import encode_document
from ..factory_book import _station
from ..slot_streams import SlotStreams
from .acceptance import _require_port, _require_station
from .compact_book import PAGE_COUNT, PAGE_SIZE
from .compact_book_rail import _move, _move_board, _pose, _station_track, build as build_rail
from .corner_line_sample import SAMPLES, corner_line
from .long_haul_transfer import _check_transfer, _north_ports
from .stage_pages import _connect, _document, _islands, _stats


_SECTIONS = {'single_arrivals': 'single-arrivals.spz2bp', 'transfers': 'mixed-transfers.spz2bp',
             'loops': 'mixed-loops.spz2bp', 'overlay': 'rail-overlay.spz2bp'}
_SUPPLY_ROWS = (28, 29, 30, 31)


def _native(path):
    data = path.read_bytes().strip()
    if not data.startswith(b'SHAPEZ2-4-') or not data.endswith(b'$'):
        raise ValueError(f'{path} 需要原生蓝图格式')
    return json.loads(gzip.decompress(base64.b64decode(data[10:-1], validate=True)))


def _loading(kind):
    lane = SlotStreams()
    fluid = kind == 'fluid'
    prefix = 'Fluid' if fluid else 'Belt'
    for row in _SUPPLY_ROWS:
        lane.put(prefix + 'PortReceiver', -18, row, config='AA==')
        lane.straight(-17, 37, row, pipe=fluid)
        lane.put(prefix + 'PortSender', 37, row, config='KAAAAAA=')
    board = lane.finish()
    station = [_move_board(e, 3) for e in _station(kind + '-loading')]
    doc = _document([board, *station, _pose(3, 2, 'Rail_Forward', 3)])
    native_kind = 'Fluids' if fluid else 'Shapes'
    _check_transfer(board, _SUPPLY_ROWS, 0, native_kind)
    _require_station(_islands(doc), 'Loader_' + native_kind, 3, 1)
    return doc, {'track': _north_ports(3, -1, 2), 'head': (3, 0, 0), 'wagon': 1, 'layer': 0,
                 'raw_inputs': [{'port': (-18, row, 0, 0), 'kind': prefix} for row in _SUPPLY_ROWS]}


def _split(overlay, routes):
    raw, transfer = set(), set()
    for route in routes.values():
        for bank in route['raw_banks']:
            track = bank['single_track']
            x, lo, z = track['departure']['tile']
            hi = track['arrival']['tile'][1]
            raw.update((x, y, z) for y in range(lo, hi + 1))
            for mount in bank['transfers']:
                transfer.update((mount['platform'], mount['loader']))
    islands = _islands(overlay)
    if raw & transfer or not (raw | transfer) <= islands.keys():
        raise ValueError('单料进站或换装台坐标不完整')
    docs = {'single_arrivals': _document([b for p, b in islands.items() if p in raw]),
            'transfers': _document([b for p, b in islands.items() if p in transfer]),
            'loops': _document([b for p, b in islands.items() if p not in raw | transfer]),
            'overlay': overlay}
    combined = _islands(_document([b for key in ('single_arrivals', 'transfers', 'loops')
                                   for b in docs[key]['BP']['Entries']]))
    if combined != islands:
        raise ValueError('三册叠放后与原铁路覆盖件不同')
    return docs


def _track_signature(index, point):
    entry = index[point]
    return entry['T'], entry.get('R', 0), entry.get('S')


def _check_factory(path, book, plan, overlay, reference):
    pages = book['pages']
    if len(pages) != PAGE_COUNT or len(plan['groups']) != PAGE_COUNT:
        raise ValueError('需要完整的 54 页工道册')
    overlay_index = _islands(overlay)
    ref = _islands(reference)
    expected = {}
    for service, route in plan['route_templates'].items():
        for s in route['stations']:
            station = dict(s, service=service)
            expected[service, s['stage']] = station
    previous = None
    for page, group in zip(pages, plan['groups'], strict=True):
        if any(page[key] != json.loads(json.dumps(group[key])) for key in ('page', 'start', 'stop', 'place_at', 'terminal')):
            raise ValueError(f'工道册第 {group["page"]} 页放置与线路不一致')
        start = page['start']
        dx = page['place_at'][0]
        document = _native(path / page['blueprint'])
        info = json.loads((path / page['connections']).read_bytes())
        indexed = _islands(document)
        combined = _islands(_document([*document['BP']['Entries'],
                                      *(_move_board(e, dx) for e in overlay['BP']['Entries'])]))
        first = indexed[tuple(info['input']['island'])]
        if previous is not None:
            _connect(previous, first)
        previous = indexed[tuple(info['output']['island'])]
        if (page['terminal'] != (page['page'] == PAGE_COUNT - 1) or
                info['output']['rows'] != ([31] if page['terminal'] else info['input']['rows'])):
            raise ValueError(f'第 {page["page"]} 页成品带口不符')
        if page['page'] == 0:
            _document([*combined.values(), *_native(path / book['controls']['file'])['BP']['Entries']])
        stops = {(s['service'], s['stage'] - start): s for s in info['stations']}
        if stops.keys() != expected.keys() or len(info['stations']) != len(expected):
            raise ValueError(f'第 {page["page"]} 页的双站数量不符')
        for key, station in expected.items():
            stop = stops[key]
            if tuple(stop['head']) != _move(station['head'], dx):
                raise ValueError(f'工段 {stop["stage"]} 车头坐标不符')
            for end in ('arrival', 'departure'):
                link = station[end]
                outside = link['outside_tile']
                if (tuple(stop[end]['outside_tile']) != _move(outside, dx) or stop[end]['rotation'] != link['rotation']
                        or _track_signature(overlay_index, outside) != _track_signature(combined, _move(outside, dx))):
                    raise ValueError(f'工段 {stop["stage"]} 外接轨 {end} 不符')
            for xy in _station_track(station):
                point = (*xy, 0)
                if _track_signature(indexed, _move(point, dx)) != _track_signature(ref, point):
                    raise ValueError(f'工段 {stop["stage"]} 轨段 {point} 不符')
        for route in group['routes']:
            service = route['service']
            for load in route['fixed_stop_loads']:
                stop = stops[service, load['stage'] - start]
                keys = ('wagon', 'layer', 'row', 'cargo', 'unit')
                if not any(all(load[k] == port[k] for k in keys) for port in stop['unload_ports']):
                    raise ValueError(f'工段 {load["stage"]} 的固定订单卸货口不符')
        for route in plan['route_templates'].values():
            for bank in route['raw_banks']:
                for link in bank['single_track'].values():
                    if _move(link['outside_tile'], dx) in combined:
                        raise ValueError(f'第 {page["page"]} 页单料车外接轨被占用')


def _station_names(group):
    page = group['page']
    for route in group['routes']:
        service = route['service']
        prefix = f'{page:02d}-{service}'
        route['game_line_name'] = prefix
        route['factory_station_names'] = {str(n): f'{prefix}-unload-{n:03d}' for n in route['factory_stop_addresses']}
        route['mixed_loading_names'] = {r['cargo']: f'{prefix}-load-{r["cargo"]}' for r in route['raw_orders']}
        for r in route['raw_orders']:
            cargo = r['cargo']
            r['game_line_name'] = f'{prefix}-raw-{cargo}'
            r['load_station_name'] = f'{r["game_line_name"]}-source'
            r['arrival_station_name_prefix'] = f'{r["game_line_name"]}-transfer'


def export(factory_book: Path, output: Path, order: dict) -> dict:
    book = json.loads((factory_book / 'book.json').read_bytes())
    rate, headway = (Fraction(book[k]) for k in ('belt_items_per_second', 'headway_seconds'))
    loads = {'item': None, 'liter': None}
    reference, overlay, plan = build_rail(0, 0, order, rate, headway, Fraction(120), Fraction(120), loads, loads)
    origin = book['origin_x']
    for group in plan['groups']:
        group['place_at'] = _move(group['place_at'], origin)
        _station_names(group)
    _check_factory(factory_book, book, plan, overlay, reference)
    parts = _split(overlay, plan['route_templates'])
    docs = {_SECTIONS[key]: doc for key, doc in parts.items()}
    suppliers = {}
    for kind in ('shape', 'fluid'):
        name = f'single-{kind}-loading.spz2bp'
        depot = f'single-{kind}-depot.spz2bp'
        docs[name], loader = _loading(kind)
        docs[depot] = _document(_station(kind + '-depot'))
        suppliers[kind] = {**loader, 'loading_file': name, 'depot_file': depot, 'depot_departure': (0, -2, 0),
                           'place_at': (0, 0, 0), 'depot_outside': (0, -3, 0), 'depot_output_rotation': 3}
    manifest = {k: plan[k] for k in ('fixed_order', 'belt_items_per_second', 'headway_seconds',
                                     'planned_mixed_cycle_seconds', 'planned_raw_cycle_seconds',
                                     'assumed_mixed_payload', 'assumed_raw_payload', 'route_templates', 'groups')}
    manifest.update(factory_pages=PAGE_COUNT, stages_per_page=PAGE_SIZE, merged_overlay=_SECTIONS['overlay'],
                    single_cargo={'arrival_file': _SECTIONS['single_arrivals'], 'source_kits': suppliers},
                    transfer_file=_SECTIONS['transfers'], loop_file=_SECTIONS['loops'],
                    sizes={name: _stats(doc) for name, doc in docs.items()},
                    game_setup={'station_names': 'suggested', 'place_source_at_mine_or_dye_supply': True,
                                'connect_raw_loaded_and_empty_return': True, 'set_train_lines_and_dispatch': True})
    output.mkdir(parents=True, exist_ok=True)
    for name, doc in docs.items():
        (output / name).write_text(encode_document(doc) + '\n', encoding='utf-8')
    (output / 'index.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description='按原生工道册导出单料、换装和回圈三册')
    parser.add_argument('--factory-book', required=True, type=Path, help='485 号末道所在的整册目录')
    parser.add_argument('--output-dir', required=True, type=Path, help='三册蓝图和接线表输出目录')
    parser.add_argument('--recipe', type=Path, help='固定订单的 target 和 instructions JSON')
    args = parser.parse_args()
    try:
        order = json.loads(args.recipe.read_text(encoding='utf-8-sig')) if args.recipe else corner_line(*SAMPLES['suspended'])
        export(args.factory_book, args.output_dir, order)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
