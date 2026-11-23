"""导出可逐页装配的六机六槽工道。"""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from ..circuit import encode_document
from ..production_line import check_jump
from ..slot_streams import SLOT_ROWS
from ..work_lane import A_X
from .acceptance import _check_loaders, _islands
from .changeover import controls
from .corner_line_sample import SAMPLES, corner_line
from .full_belt_sample import _add_reader, _observe_stack, _STACK
from .interface import FIELDS, PACKET_TAG
from .layout import COMPACT_BASE_HEAD, COMPACT_CRYSTAL_HEAD, STAGE_PITCH, _stack_lane, cargo_ports
from .parallel_stack_stage import add_parallel_stack
from .recipe import MAX_STAGES, OPCODES, Production, replay
from .stage_pages import _connect, _document, _page, _recipe_requirements, _stations, _stats, _supply


_BELT_RATE = Fraction(2)


def _configure(stages: int | None, order: dict | None, universal: bool) -> tuple[Production | None, dict | None, list[dict]]:
    if order is None and (stages is None or not universal):
        order = corner_line(*SAMPLES['suspended'])
    if order is not None:
        if (not isinstance(order, dict) or not isinstance(order.get('target'), str)
                or not isinstance(order.get('instructions'), (list, tuple))):
            raise ValueError('配方 JSON 须包含目标短代码 target 和六字段 instructions 列表')
        if any(not isinstance(packet, dict) or not FIELDS.keys() <= packet.keys()
               for packet in order['instructions']):
            raise ValueError('每笔指令须包含 opcode、a、b、destination、base、color')
        production = replay(order['target'], order['instructions'])
        length = len(production.stages)
    else:
        production, length = None, 0
    if stages is None:
        stages = length
    if type(stages) is not int or not 1 <= stages <= MAX_STAGES or not length <= stages:
        raise ValueError(f'容量须在 1 至 {MAX_STAGES} 之间并覆盖回放长度 {length}')
    if not universal and stages != length:
        raise ValueError('专用版容量取固定配方的长度，预留空地址请用 --universal')
    stations = _stations(production, universal) if production is not None else []
    for address in range(length, stages):
        x = address * STAGE_PITCH
        base_x, base_y = COMPACT_BASE_HEAD
        crystal_x, crystal_y = COMPACT_CRYSTAL_HEAD
        stations.append({'stage': address, 'opcode': None, 'origin': (x, 0, 0),
                         'base_head': (x + base_x, base_y), 'crystal_head': (x + crystal_x, crystal_y),
                         'allowed_opcodes': OPCODES})
    for station in stations:
        opcode = station['opcode']
        station['stack_machines'] = 6 if universal or opcode == _STACK else 1
        if not universal and opcode == _STACK:
            station['allowed_opcodes'] = (_STACK,)
        if opcode is not None and opcode not in station['allowed_opcodes']:
            raise ValueError(f'地址 {station["stage"]} 未安装操作 {opcode} 所需工段')
    return production, order, stations


def _full_page(stations: list[dict], *, terminal: bool, universal: bool) -> tuple[dict, dict]:
    document, report = _page(stations, terminal=terminal)
    entries = document['BP']['Entries']
    islands = _islands(document)
    stacks = {}
    for station in stations:
        if station['stack_machines'] != 6:
            continue
        x, _, _ = station['origin']
        take = islands[x, 0, 0]
        if universal:
            work = add_parallel_stack(entries, x)
        else:
            work = dict(_stack_lane(), X=x)
            for level in (0, 1):
                check_jump(take, work, A_X, 1, level)
            entries[entries.index(islands[x, 3, 0])] = work
        stacks[station['stage']] = _observe_stack(take, work)
    exit_board = islands[report['output']['island']]
    if terminal:
        report['product_reader'] = _add_reader(exit_board, (34, SLOT_ROWS[-1], 0), 0)
    document = _document(entries)
    return document, {**report, **_stats(document), 'stack': stacks}


def _save(output: Path, name: str, document: dict) -> None:
    (output / name).write_text(encode_document(document) + '\n', encoding='utf-8')


def export(output: Path, *, stages: int | None = None, order: dict | None = None, universal: bool = False,
           page_size: int = 9, window: tuple[int, int] | None = None) -> dict:
    production, order, stations = _configure(stages, order, universal)
    count = len(stations)
    start, stop = (0, count) if window is None else window
    if not 0 <= start < stop <= count or page_size < 1:
        raise ValueError('页大小须为正数，导出区间须位于配置容量内')
    load = cargo_ports()
    _check_loaders(load)
    control = _document(controls(count, PACKET_TAG, handoff=True))
    output.mkdir(parents=True, exist_ok=True)
    pages = []
    totals = Counter(_stats(control))
    previous = None
    for lo in range(start, stop, page_size):
        hi = min(lo + page_size, stop)
        document, page = _full_page(stations[lo:hi], terminal=hi == count, universal=universal)
        islands = _islands(document)
        if previous is not None:
            _connect(previous, islands[page['input']['island']])
        previous = islands[page['output']['island']]
        name = f'page-{lo:03d}-{hi - 1:03d}.spz2bp'
        _save(output, name, document)
        pages.append({'file': name, **page})
        totals.update(_stats(document))
    _save(output, 'controls.spz2bp', control)
    installed = stations[start:stop]
    supply = _supply(production, _BELT_RATE) if production is not None else None
    rails = {(rail['stage'], rail['service']) for page in pages for rail in page['rails']}
    if supply is not None:
        wanted = {(row['stage'], row['service']) for row in supply['unload_rows'] if start <= row['stage'] < stop}
        if not wanted <= rails:
            raise ValueError('配方有用料地址未接至对应站点')
    report = {'target': None if order is None else order['target'], 'mode': 'universal' if universal else 'fixed',
              'capacity': count, 'max_supported_stages': MAX_STAGES, 'exported_window': (start, stop),
              'stage_pitch': STAGE_PITCH, 'stations': stations, 'pages': pages, 'size': dict(totals),
              'station_counts': {service: sum(service + '_head' in station for station in installed)
                                 for service in ('base', 'crystal')},
              'six_stacker_stages': sum(s['stack_machines'] == 6 for s in installed),
              'stacker_count': sum(s['stack_machines'] for s in installed),
              'load': [asdict(port) for port in load], 'supply': supply,
              'control': {'file': 'controls.spz2bp', 'place_at': (0, 12, 0), **_stats(control)},
              'recipe': _recipe_requirements(count),
              'replayed_order': None if production is None else {
                  'length': len(production.stages), 'product_slot': production.product_slot,
                  'instructions': order['instructions']},
              'changeover': {'wait_for_physical_empty': True,
                             'inspect': ['slot_belts', 'parallel_a_and_b', 'stacker_buffers', 'merge_and_exit'],
                             'idle_tail': 'all_six_slots_through', 'reset_phase': 3, 'reset_signal_ticks': 128}}
    report['recipe']['before_run']['length'] = {'minimum': 1, 'maximum': count}
    (output / 'full-line.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='导出六机并联的全线页签、共用控制及装配坐标')
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--universal', action='store_true', help='每地址支持全部操作、双站点和六机堆叠')
    parser.add_argument('--stages', type=int, help=f'工段容量，1 至 {MAX_STAGES}')
    parser.add_argument('--recipe', type=Path, help='已求出的六字段配方 JSON')
    parser.add_argument('--page-size', type=int, default=9, help='每页包含的工段数')
    parser.add_argument('--window', type=int, nargs=2, metavar=('START', 'STOP'), help='导出左闭右开地址区间')
    args = parser.parse_args()
    try:
        order = json.loads(args.recipe.read_text(encoding='utf-8-sig')) if args.recipe is not None else None
        report = export(args.output_dir, stages=args.stages, order=order, universal=args.universal,
                        page_size=args.page_size, window=args.window)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'{report["capacity"]} 道容量，已导出 {len(report["pages"])} 个工道页签和 1 个控制页签')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
