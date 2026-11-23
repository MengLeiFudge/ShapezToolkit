"""把四角转向和基础料拼合放在同一块大平台。"""

import argparse
import json
from pathlib import Path

from ..circuit import encode_document
from ..production_line import check_jump
from ..quarter_gather import QUADRANTS
from ..quarter_join import quarter_join
from ..slot_stream_ports import trace, transport_paths
from ..slot_streams import SlotStreams
from .acceptance import _check_intakes, _islands
from .full_line_pages import _configure, _full_page
from .layout import STAGE_PITCH, cargo_ports
from .recipe import MAX_STAGES
from .stage_pages import _document, _rail_links, _stats


_SHIFT = 12
_CHANNEL = 1_600_077


def _keep_join_entry(entry):
    x, y = entry['X'], entry['Y']
    if entry['T'] == 'BeltPortReceiverInternalVariant':
        return False
    if y in (8, 9, 10) and x < 0:
        # 北口在原拼合入带的末端切入。
        return x + _SHIFT > 19 - y
    return not ((y == 11 and x > 18) or (x == 30 and y > 11))


def _put(lane, entry, shift):
    kind, _, mirrored = entry['T'].partition('InternalVariant')
    return lane.put(kind, entry['X'] + shift, entry['Y'], entry['L'], entry['R'], mirrored=bool(mirrored),
                    config=entry.get('C'))


def _inputs(lane):
    for i in range(3):
        x, row = 11 - i, 8 + i
        lane.put('BeltPortReceiver', x, -18, rotation=1, config='AA==')
        for y in range(-17, row):
            lane.put('BeltDefaultForward', x, y, rotation=1)
        lane.put('BeltDefaultLeft', x, row, rotation=1)
    # q0 从西侧进原分流器，保留整片直通和四角拼合两路。
    lane.put('BeltPortReceiver', 8, -18, rotation=1, config='AA==')
    for y in range(-17, 4):
        lane.put('BeltDefaultForward', 8, y, rotation=1)
    lane.put('BeltDefaultLeft', 8, 4, rotation=1, mirrored=True)
    for x in range(-5, 8):
        lane.put('BeltDefaultForward', x, 4, rotation=2)
    lane.put('BeltDefaultLeft', -6, 4, rotation=2)
    for y in range(5, 11):
        lane.put('BeltDefaultForward', -6, y, rotation=1)
    lane.put('BeltDefaultLeft', -6, 11, rotation=1)


def _output(lane):
    lane.put('BeltDefaultLeft', 31, 11, mirrored=True)
    for y in range(12, 34):
        lane.put('BeltDefaultForward', 31, y, rotation=1)
    lane.put('BeltDefaultLeft', 31, 34, rotation=1, mirrored=True)
    lane.put('BeltDefaultLeft', 30, 34, rotation=2)
    for y in range(35, 37):
        lane.put('BeltDefaultForward', 30, y, rotation=1)
    lane.put('BeltPortSender', 30, 37, rotation=1, config='KAAAAAA=')


def _check_join(board):
    entries = board['B']['Entries']
    parts = {(e['X'], e['Y'], e['L']): (e['T'], e['R']) for e in entries}
    paths = transport_paths(board)
    feeds = {(12, row, 0, 2) for row in range(8, 12)}
    output = (30, 37, 0, 3)
    filter_turn = {(3, 18, 0)}
    for i, quadrant in enumerate(QUADRANTS):
        start = (11-i, -17, 0, 3)
        if trace(paths, start, feeds, filter_turn) != (12, 8+i, 0, 2):
            raise ValueError(f'q{quadrant} 未接到同一交换机输入')
    trace(paths, (8, -17, 0, 3), {output}, set())
    trace(paths, (14, 9, 0, 2), {(22, 10, 0, 2)}, set())
    trace(paths, (14, 11, 0, 2), {(22, 11, 0, 2)}, set())
    trace(paths, (23, 11, 0, 2), {output}, set())
    for position in ((12, 9, 0), (12, 11, 0), (22, 11, 0)):
        if parts.get(position) != ('HalvesSwapperDefaultInternalVariant', 0):
            raise ValueError(f'四角拼合缺少原交换机 {position}')
    for position in ((13, 8, 0), (13, 10, 0), (23, 10, 0)):
        if parts.get(position) != ('TrashDefaultInternalVariant', 0):
            raise ValueError(f'拼合副产物缺少废料口 {position}')


def compact_join(address):
    channel = _CHANNEL + 32 * address
    lane = SlotStreams()
    original = quarter_join(channel, south_output=True)['B']['Entries']
    pins = {}
    for entry in original:
        if _keep_join_entry(entry):
            pin = _put(lane, entry, _SHIFT)
            if (entry['X'], entry['Y']) in {(-9, 18), (-9, 21), (-11, 21)}:
                pins[entry['X'], entry['Y']] = pin
    _inputs(lane)
    _output(lane)
    filt, receiver, config = (pins[p] for p in ((-9, 18), (-9, 21), (-11, 21)))
    lane.pins.extend(((receiver, 0, config), (filt, 0, receiver)))
    board = lane.finish()
    _check_join(board)
    return board


def _move_base(entries, page, addresses):
    original = _islands(_document(entries))
    moved = {}
    removed = set()
    stations = []
    for address in addresses:
        x = address * STAGE_PITCH
        rail = next(r for r in page['rails'] if r['stage'] == address and r['service'] == 'base')
        head_x, head_y = rail['head']
        stock_head = head_x + 3, head_y
        for y in range(head_y, head_y + 13):
            key = head_x, y, 0
            moved[key] = dict(original[key], X=stock_head[0])
        track_x = head_x - 1
        for y in range(head_y - 1, -3):
            key = track_x, y, 0
            moved[key] = dict(original[key], X=track_x + 3)
        for y in (-18, -4):
            key = head_x, y, 0
            moved[key] = dict(original[key], X=stock_head[0])
        for row in range(-15, -5, 3):
            for column, level in ((-6,0), (-3,0), (0,0), (-6,1)):
                key = x + column, row, level
                moved[key] = dict(original[key], X=x + column + 3)
        removed.add((x, -3, 0))
        moved[x+3, -3, 0] = dict(compact_join(address), X=x+3, Y=-3)
        stations.append({'stage': address, 'base_head': stock_head})
    updated = _document([moved.get(key, board) for key, board in original.items() if key not in removed])
    islands = _islands(updated)
    _check_intakes(islands, stations, cargo_ports())
    for station in stations:
        address = station['stage']
        x = address * STAGE_PITCH
        for i, row in enumerate(range(-15, -5, 3)):
            select, prepare, gather = (islands[x+dx, row, 0] for dx in (-3, 0, 3))
            check_jump(select, prepare, 9, 0)
            for y in (-12, -11, -10, -9, 8, 9, 10, 11):
                check_jump(select, prepare, y, 0, 1 if y == 11 else 2, fluid=True)
            check_jump(prepare, gather, 30, 0)
            next_board = islands[x+3, row+3, 0]
            for lane in range(11-i, 12):
                check_jump(gather, next_board, lane, 1)
        check_jump(islands[x+3, -3, 0], islands[x+3, 0, 0], 30, 1)
    return updated, stations


def build(start: int, count: int, *, terminal: bool = False) -> tuple[dict, dict]:
    if not 0 <= start < start + count <= MAX_STAGES or count > 9:
        raise ValueError('地址须连续，单页支持 1 至 9 道')
    _, _, stations = _configure(start + count, None, True)
    original, page = _full_page(stations[start:], terminal=terminal, universal=True)
    addresses = range(start, start + count)
    document, moved = _move_base(original['BP']['Entries'], page, addresses)
    before, after = _stats(original), _stats(document)
    if before['platforms'] - after['platforms'] != count:
        raise ValueError('四角拼装每道应合并一块平台')
    islands = _islands(document)
    rails = [rail for rail in page['rails'] if rail['service'] == 'crystal']
    for stage in moved:
        head = stage['base_head']
        rails.append(dict(stage=stage['stage'], service='base', head=head, **_rail_links(islands, head, 'base')))
    report = {'start': start, 'stop': start + count, 'terminal': terminal, 'baseline': before, 'compact': after,
              'input': page['input'], 'output': page['output'], 'rails': rails, 'stack': page['stack'],
              'joins': [{'stage': address, 'platform': (address * STAGE_PITCH + 3, -3, 0),
                         'north_belts': {f'q{q}': (11-i, -18, 0) for i, q in enumerate(QUADRANTS)},
                         'base_result': (30, 37, 0), 'direct_channel': _CHANNEL + 32 * address}
                        for address in addresses],
              'capacity_486': {'stages': 486, '9_stage_pages': 54,
                               'baseline_platforms_with_control': 486 * 32 - 3 + 8,
                               'compact_platforms_with_control': 486 * 31 - 3 + 8}}
    if terminal:
        report['product_reader'] = page['product_reader']
    return document, report


def main():
    parser = argparse.ArgumentParser(description='导出四角转向和拼装合板的通用工道页')
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
