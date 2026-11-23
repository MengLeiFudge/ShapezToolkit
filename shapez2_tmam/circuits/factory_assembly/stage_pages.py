"""按全线地址导出六槽工道页签，并核对冻结配方的供料。"""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from ..circuit import encode_document
from ..layer_factory import slot_bridge
from ..production_line import check_jump, product_exit
from ..production_stage import build_stage
from ..slot_streams import SLOT_ROWS
from ..work_lane import A_X
from .acceptance import _check_intakes, _check_loaders, _islands, _require_port
from .base_feed import build_base_stage
from .capacity import demands
from .changeover import controls
from .corner_line_sample import SAMPLES, corner_line
from .crystal_feed import add_crystal_feed
from .interface import FIELDS, PACKET_TAG, recipe_interface
from .layout import COMPACT_BASE_HEAD, COMPACT_CRYSTAL_HEAD, STAGE_PITCH, _check_footprints, cargo_ports
from .recipe import BASE, CRYSTAL, MAX_STAGES, OPCODES, Production, replay
from .submit_bridge import CANDIDATE_ADDRESS, CANDIDATE_FIELDS


_FEED_HEADS = {'base': COMPACT_BASE_HEAD, 'crystal': COMPACT_CRYSTAL_HEAD}


def _document(entries: list[dict]) -> dict:
    _check_footprints(entries)
    return {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': entries}}


def _stats(document: dict) -> dict:
    entries = document['BP']['Entries']
    return {'islands': len(entries), 'platforms': sum(e['T'] == 'Foundation_3x3' for e in entries),
            'buildings': sum(len(e.get('B', {}).get('Entries', ())) for e in entries)}


def _point(island: dict) -> tuple[int, int, int]:
    return tuple(island.get(axis, 0) for axis in 'XYZ')


def _connect(sender: dict, receiver: dict) -> None:
    for row in SLOT_ROWS:
        check_jump(sender, receiver, row, 0)


def _stations(production: Production, universal: bool) -> list[dict]:
    stations = []
    for stage in production.stages:
        origin = stage.index * STAGE_PITCH
        site = {'stage': stage.index, 'opcode': stage.opcode, 'origin': (origin, 0, 0)}
        for name, opcode in (('base', BASE), ('crystal', CRYSTAL)):
            if universal or stage.opcode == opcode:
                x, y = _FEED_HEADS[name]
                site[name + '_head'] = (origin + x, y)
        site['allowed_opcodes'] = tuple(op for op in OPCODES if (op != BASE or 'base_head' in site)
                                        and (op != CRYSTAL or 'crystal_head' in site))
        stations.append(site)
    return stations


def _rail_links(islands: dict, head: tuple[int, int], service: str) -> dict:
    x, y = head
    if service == 'base':
        endpoints = ((x - 1, y - 1, 1), (x, y - 1, 3))
        outer = -1
    else:
        endpoints = ((x, y + 4, 3), (x - 1, y + 4, 1))
        outer = 1
    links = {}
    for name, (xx, yy, rotation) in zip(('arrival', 'departure'), endpoints, strict=True):
        point = (xx, yy, 0)
        rail = islands.get(point, {})
        if (rail.get('T'), rail.get('R')) != ('Rail_Forward', rotation):
            raise ValueError(f'接轨 {point} 须为旋转 {rotation} 的直轨')
        links[name] = {'tile': point, 'outside_tile': (xx, yy + outer, 0), 'rotation': rotation}
    return links


def _page(stations: list[dict], *, terminal: bool) -> tuple[dict, dict]:
    islands = []
    bridge = slot_bridge()
    first = None
    previous = None
    for station in stations:
        index = station['stage']
        x = index * STAGE_PITCH
        entries = (build_base_stage(index) if 'base_head' in station
                   else build_stage(index, stream=True)['BP']['Entries'])
        if 'crystal_head' in station:
            add_crystal_feed(entries)
        for obj in entries:
            obj['X'] = obj.get('X', 0) + x
        take, receive, work = entries[:3]
        if previous is not None:
            _connect(previous, take)
        else:
            first = take
        _connect(take, receive)
        for level in (0, 1):
            check_jump(take, work, A_X, 1, level)
        islands.extend(entries)
        previous = receive
        if station is stations[-1] and terminal:
            outlet = product_exit()
            outlet['X'] = x + 6
            _connect(previous, outlet)
            islands.append(outlet)
            previous = outlet
        else:
            for offset in range(x + 6, x + STAGE_PITCH, 3):
                relay = dict(bridge, X=offset)
                _connect(previous, relay)
                islands.append(relay)
                previous = relay
    assert first is not None and previous is not None
    document = _document(islands)
    indexed = _islands(document)
    _check_intakes(indexed, stations, cargo_ports())
    start = stations[0]['stage']
    stop = stations[-1]['stage'] + 1
    output = {'island': _point(previous), 'x': 37, 'rows': (SLOT_ROWS[-1],) if terminal else SLOT_ROWS, 'level': 0}
    report = {'start': start, 'stop': stop, 'place_at': (start * STAGE_PITCH, 0, 0),
              'input': {'island': _point(first), 'x': -18, 'rows': SLOT_ROWS, 'level': 0},
              'output': output,
              'rails': [dict(stage=s['stage'], service=service, head=s[service + '_head'],
                             **_rail_links(indexed, s[service + '_head'], service))
                        for s in stations for service in _FEED_HEADS if service + '_head' in s],
              **_stats(document)}
    for row in output['rows']:
        _require_port(previous, 'BeltPortSender', output['x'], row, output['level'])
    for row in SLOT_ROWS:
        _require_port(first, 'BeltPortReceiver', -18, row, 0)
    return document, report


def _shortest_window(production: Production) -> tuple[int, int]:
    stages = production.stages
    opcodes = {stage.opcode for stage in stages}
    active = Counter()
    start, best_start, best_stop = 0, 0, len(stages)
    for stop, stage in enumerate(stages, 1):
        active[stage.opcode] += 1
        while len(active) == len(opcodes):
            if stop - start < best_stop - best_start:
                best_start, best_stop = start, stop
            leaving = stages[start].opcode
            active[leaving] -= 1
            if not active[leaving]:
                del active[leaving]
            start += 1
    return best_start, best_stop


def _supply(production: Production, belt_rate: Fraction) -> dict:
    totals, layers, ports = Counter(), Counter(), Counter()
    for demand in demands(production):
        port = demand.port
        if port is None:
            continue
        service = 'crystal' if port.station == 'crystal' else 'base'
        key = service, port.wagon, port.layer, port.cargo
        totals[port.cargo, demand.unit] += demand.per_product
        layers[key] += demand.per_product
        ports[(*key, demand.stage, demand.row)] += demand.per_product
    return {'belt_items_per_second': str(belt_rate),
            'per_product': {f'{cargo}_{unit}': str(amount) for (cargo, unit), amount in sorted(totals.items())},
            'wagon_layers': [dict(service=service, wagon=wagon, layer=layer, cargo=cargo,
                                  per_product=str(amount), per_second=str(amount * belt_rate))
                             for (service, wagon, layer, cargo), amount in sorted(layers.items())],
            'unload_rows': [dict(service=service, wagon=wagon, layer=layer, cargo=cargo, stage=stage, row=row,
                                 per_product=str(amount), per_second=str(amount * belt_rate))
                            for (service, wagon, layer, cargo, stage, row), amount in sorted(ports.items())]}


def _recipe_requirements(count: int) -> dict:
    return {'channels': recipe_interface(count, PACKET_TAG),
            'before_run': {'target': 'shape', 'length': count, 'replay_result': 'target', 'accepted': 1},
            'candidate': {'address': CANDIDATE_ADDRESS, 'fields': CANDIDATE_FIELDS,
                          'public_fields': FIELDS, 'hold_until_current_ack': True},
            'reset_phase': 3, 'reset_signal_ticks': 128}


def export(output: Path, *, window: tuple[int, int] | None = None, page_size: int = 9,
           universal: bool = False, belt_rate: Fraction = Fraction(2)) -> dict:
    sample = corner_line(*SAMPLES['suspended'])
    production = replay(sample['target'], sample['instructions'])
    count = len(production.stages)
    start, stop = _shortest_window(production) if window is None else window
    if not 1 <= count <= MAX_STAGES or not 0 <= start < stop <= count or page_size <= 0 or belt_rate <= 0:
        raise ValueError('地址区间、每页段数或目标带速无效')
    stations = _stations(production, universal)
    load = cargo_ports()
    _check_loaders(load)
    output.mkdir(parents=True, exist_ok=True)
    pages = []
    for page_start in range(start, stop, page_size):
        page_stop = min(page_start + page_size, stop)
        document, page = _page(stations[page_start:page_stop], terminal=page_stop == count)
        filename = f'stage-page-{page_start}-{page_stop - 1}.spz2bp'
        (output / filename).write_text(encode_document(document) + '\n', encoding='utf-8')
        pages.append({'file': filename, **page})
    control = _document(controls(count, PACKET_TAG, handoff=True))
    control_file = 'stage-page-controls.spz2bp'
    (output / control_file).write_text(encode_document(control) + '\n', encoding='utf-8')
    report = {'target': sample['target'], 'stages': count, 'max_supported_stages': MAX_STAGES,
              'product_slot': production.product_slot, 'universal': universal, 'stage_pitch': STAGE_PITCH,
              'stations': stations, 'pages': pages, 'load': [asdict(port) for port in load],
              'control': {'file': control_file, 'place_at': (0, 12, 0), **_stats(control)},
              'recipe': _recipe_requirements(count), 'supply': _supply(production, belt_rate)}
    (output / 'stage-pages.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='分段导出 145 道悬空样件的六槽实体工道和页签接口')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--window', nargs=2, type=int, metavar=('START', 'STOP'), help='导出左闭右开的全线地址区间')
    parser.add_argument('--page-size', type=int, default=9, help='每页签最多包含的工段数')
    parser.add_argument('--universal', action='store_true', help='每个地址均保留基础料站和结晶站')
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(2), help='成品目标带速，件/秒')
    args = parser.parse_args()
    try:
        report = export(args.output_dir, window=args.window, page_size=args.page_size,
                        universal=args.universal, belt_rate=args.belt_rate)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'{report["stages"]} 道，已导出 {len(report["pages"])} 个工道页签和 1 个控制页签')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
