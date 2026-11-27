"""缩短四角合板工段之间的六槽直通带。"""

import argparse
import json
from collections import Counter
from pathlib import Path

from ..circuit import encode_document
from ..slot_stream_ports import trace, transport_paths
from ..slot_streams import SLOT_ROWS
from .compact_quarter_join import build as build_join_page
from .layout import STAGE_PITCH
from .recipe import MAX_STAGES
from .stage_pages import _connect, _document, _islands, _stats


PITCH = 12
_RELAY_OFFSETS = (6, 9)


def _shift(point, dx):
    return (point[0] + dx, *point[1:])


def _shift_port(port, dx):
    return dict(port, island=_shift(port['island'], dx))


def _check_through(islands, address, terminal):
    x = address * PITCH
    receiver = islands[x + 3, 0, 0]
    _connect(islands[x, 0, 0], receiver)
    if terminal:
        _connect(receiver, islands[x + 6, 0, 0])
        return
    for offset in _RELAY_OFFSETS:
        bridge = islands[x + offset, 0, 0]
        _connect(receiver, bridge)
        paths = transport_paths(bridge)
        for row in SLOT_ROWS:
            trace(paths, (-17, row, 0, 2), {(37, row, 0, 2)}, set())
        receiver = bridge


def build(start: int, count: int, *, terminal: bool = False) -> tuple[dict, dict]:
    if not 0 <= start < start + count <= MAX_STAGES or count > 9:
        raise ValueError('地址须连续，单页支持 1 至 9 道')
    entries, rails, joins = [], [], []
    stack = {}
    before, after_join = Counter(), Counter()
    first, last = None, None
    stop = start + count
    for address in range(start, stop):
        is_final = terminal and address == stop - 1
        single, page = build_join_page(address, 1, terminal=is_final)
        before.update(page['baseline'])
        after_join.update(page['compact'])
        old_x = address * STAGE_PITCH
        dx = address * PITCH - old_x
        original = _islands(single)
        removed = set() if is_final else {(old_x + k, 0, 0) for k in range(PITCH, STAGE_PITCH, 3)}
        for point in removed:
            if original.get(point, {}).get('T') != 'Foundation_3x3':
                raise ValueError(f'地址 {address} 缺少六槽中继 {point}')
        entries.extend(dict(board, X=point[0] + dx) for point, board in original.items() if point not in removed)
        if first is None:
            first = _shift_port(page['input'], dx)
        if is_final:
            last = _shift_port(page['output'], dx)
            product_reader = _shift_port(page['product_reader'], dx)
        else:
            last = dict(page['output'], island=(address * PITCH + _RELAY_OFFSETS[-1], 0, 0))
        for rail in page['rails']:
            rail = dict(rail, head=_shift(rail['head'], dx))
            for end in ('arrival', 'departure'):
                link = rail[end]
                rail[end] = dict(link, tile=_shift(link['tile'], dx), outside_tile=_shift(link['outside_tile'], dx))
            rails.append(rail)
        join, = page['joins']
        joins.append(dict(join, platform=_shift(join['platform'], dx)))
        station = page['stack'][address]
        stack[address] = dict(station, island=_shift(station['island'], dx),
                              readers={k: _shift_port(v, dx) for k, v in station['readers'].items()})
    document = _document(entries)
    islands = _islands(document)
    for address in range(start, stop):
        _check_through(islands, address, terminal and address == stop - 1)
        if address + 1 < stop:
            _connect(islands[address * PITCH + _RELAY_OFFSETS[-1], 0, 0], islands[(address + 1) * PITCH, 0, 0])
    assert first is not None and last is not None
    report = {'start': start, 'stop': stop, 'terminal': terminal, 'stage_pitch': PITCH,
              'place_at': first['island'], 'input': first, 'output': last,
              'rails': rails, 'joins': joins, 'stack': stack,
              'original': dict(before), 'quarter_join': dict(after_join), 'compact': _stats(document)}
    if terminal:
        report['product_reader'] = product_reader
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description='导出六槽中继缩短后的通用工道页')
    parser.add_argument('--output', required=True, type=Path, help='蓝图路径，旁边生成同名接线表')
    parser.add_argument('--start', type=int, default=0, help='页首工段的绝对地址')
    parser.add_argument('--count', type=int, default=9, help='本页工段数，1 至 9')
    parser.add_argument('--terminal', action='store_true', help='本页为末页，安装成品出口')
    args = parser.parse_args()
    try:
        if args.output.suffix != '.spz2bp':
            raise ValueError('--output 需要 .spz2bp 路径')
        document, report = build(args.start, args.count, terminal=args.terminal)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
