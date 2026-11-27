"""按绝对地址分批导出 486 道通用工道和混合车站接线表。"""

import argparse
import base64
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from ...synthesis.production_bill import CRYSTAL_LITERS, PAINT_LITERS, PRIMARY
from ..circuit import constant, encode_document
from .capacity import DYE_ROWS
from .changeover import controls
from .compact_slot_pages import PITCH, build as build_slot_page
from .interface import PACKET_TAG
from .layout import cargo_ports
from .stage_pages import _connect, _document, _islands, _recipe_requirements, _stats


CAPACITY = 486
PAGE_SIZE = 9
PAGE_COUNT = CAPACITY // PAGE_SIZE
_ADDRESS_COEFFICIENTS = Counter({32: 25, 8: 16, 1: 4, -1: 3})
_SUFFIX = '.spz2bp'


def _const_int(code):
    raw = base64.b64decode(code, validate=True)
    if raw in (b'\x04', b'\x05'):
        return raw[0] - 4
    if len(raw) == 5 and raw[0] == 3:
        return int.from_bytes(raw[1:], 'little', signed=True)
    raise ValueError('工段地址模板使用了非整数常量')


def _patches(first, second):
    changes = {}
    for point, board in first.items():
        counterpart = second[point]
        if board == counterpart:
            continue
        left, right = board['B'], counterpart['B']
        if dict(board, B=dict(left, Entries=right['Entries'])) != counterpart:
            raise ValueError(f'工段模板的岛块随地址改变 {point}')
        edits = []
        for i, (a, b) in enumerate(zip(left['Entries'], right['Entries'], strict=True)):
            if a == b:
                continue
            if a['T'] != 'ConstantSignalDefaultInternalVariant' or dict(a, C=b['C']) != b:
                raise ValueError(f'工段模板在 {point} 出现依赖地址的非整数建筑')
            value = _const_int(a['C'])
            edits.append((i, value, _const_int(b['C']) - value))
        changes[point] = edits
    if Counter(step for edits in changes.values() for _, _, step in edits) != _ADDRESS_COEFFICIENTS:
        raise ValueError('工段变址常量与六字段协议不一致')
    return changes


def _shift(point, dx):
    return (point[0] + dx, *point[1:])


def _move_port(port, dx):
    return dict(port, island=_shift(port['island'], dx))


def _move_rail(rail, address, dx):
    moved = dict(rail, stage=address, head=_shift(rail['head'], dx))
    for end in ('arrival', 'departure'):
        link = rail[end]
        moved[end] = dict(link, tile=_shift(link['tile'], dx), outside_tile=_shift(link['outside_tile'], dx))
    return moved


class StageTemplate:
    def __init__(self):
        doc, self.through = build_slot_page(0, 1)
        following, _ = build_slot_page(1, 1)
        terminal, self.terminal = build_slot_page(0, 1, terminal=True)
        self.boards = _islands(doc)
        next_boards = _islands(following)
        normalized = {_shift(p, -PITCH): dict(b, X=p[0] - PITCH) for p, b in next_boards.items()}
        if normalized.keys() != self.boards.keys():
            raise ValueError('工段岛块坐标随地址改变')
        self.patches = _patches(self.boards, normalized)
        self.outlet = self.terminal['output']['island']
        self.last_relay = self.through['output']['island']
        self.terminal_boards = _islands(terminal)
        if ({p: b for p, b in self.boards.items() if p not in (self.outlet, self.last_relay)}
                != {p: b for p, b in self.terminal_boards.items() if p != self.outlet}):
            raise ValueError('成品末页改变了六槽加工工段')

    def stage(self, address, dx, *, terminal):
        source = self.terminal_boards if terminal else self.boards
        for point, board in source.items():
            board = dict(board, X=point[0] + dx)
            if address and point in self.patches:
                buildings = list(board['B']['Entries'])
                for i, value, step in self.patches[point]:
                    buildings[i] = dict(buildings[i], C=constant(value + step * address))
                board['B'] = dict(board['B'], Entries=buildings)
            yield board


def _supply_ports(rate, headway):
    services = {'base': [], 'crystal': []}
    for port in cargo_ports():
        service = 'crystal' if port.station == 'crystal' else 'base'
        if port.kind == 'Shapes':
            uses = {'shape': Fraction(1)}
            unit = 'item'
        else:
            unit = 'liter'
            colors = (*PRIMARY, 'pin') if service == 'base' else PRIMARY
        for row in port.rows:
            if port.kind == 'Fluids':
                uses = {}
                for color in colors:
                    if DYE_ROWS[color].get(port.cargo) != row:
                        continue
                    liters = CRYSTAL_LITERS if color == 'pin' or service == 'crystal' else PAINT_LITERS
                    blend = 'r' if color == 'pin' else color
                    uses[color] = Fraction(liters * PRIMARY[blend].count(port.cargo), 4)
            peak = max(uses.values()) * rate
            services[service].append({'wagon': port.wagon, 'layer': port.layer, 'row': row, 'cargo': port.cargo,
                                      'path': port.station, 'unit': unit,
                                      'per_product': {k: str(v) for k, v in uses.items()},
                                      'max_per_second': str(peak), 'min_per_visit_at_peak': str(peak * headway)})
    return services


def _station_ports(islands, rail, supply):
    x, y = rail['head']
    service = rail['service']
    rows = []
    receivers = {}
    for port in supply[service]:
        wagon, row, level = (port[k] for k in ('wagon', 'row', 'layer'))
        board_y = y if service == 'crystal' else y + 2 + 3 * ((wagon - 1) // 3)
        point = (x + 3, board_y, 0)
        if point not in receivers:
            receivers[point] = Counter((e['T'], e['Y'], e['L']) for e in islands[point]['B']['Entries']
                                       if e['X'] == -18 and e['R'] == 0 and 'PortReceiver' in e['T'])
        prefix = 'Belt' if port['unit'] == 'item' else 'Fluid'
        key = (prefix + 'PortReceiverInternalVariant', row, level)
        if board_y + row // 20 != y + wagon or receivers[point][key] != 1:
            raise ValueError(f'站场 {rail["head"]} 缺少车厢 {wagon} 层 {level} 行 {row} 卸货口')
        rows.append(dict(port, island=point, port=(-18, row, level, 0)))
    return dict(rail, unload_ports=rows)


def _entry(page, origin_x):
    start = page * PAGE_SIZE
    stop = start + PAGE_SIZE
    name = f'page-{start:03d}-{stop - 1:03d}'
    return {'page': page, 'start': start, 'stop': stop, 'place_at': (origin_x + start * PITCH, 0, 0),
            'blueprint': name + _SUFFIX, 'connections': name + '.json', 'terminal': stop == CAPACITY}


def build_page(template, entry, supply):
    boards, rails = [], []
    origin_x = entry['place_at'][0] - entry['start'] * PITCH
    for address in range(entry['start'], entry['stop']):
        terminal = entry['terminal'] and address == CAPACITY - 1
        dx = origin_x + PITCH * address
        boards.extend(template.stage(address, dx, terminal=terminal))
        rails.extend(_move_rail(rail, address, dx) for rail in template.through['rails'])
    doc = _document(boards)
    islands = _islands(doc)
    for address in range(entry['start'] + 1, entry['stop']):
        take_x = origin_x + address * PITCH
        _connect(islands[take_x - 3, 0, 0], islands[take_x, 0, 0])
    last = template.terminal if entry['terminal'] else template.through
    report = {**entry, 'input': _move_port(template.through['input'], entry['place_at'][0]),
              'output': _move_port(last['output'], dx), 'size': _stats(doc),
              'stations': [_station_ports(islands, rail, supply) for rail in rails]}
    if entry['terminal']:
        report['product_reader'] = _move_port(last['product_reader'], dx)
    return doc, report


def _save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def export(output: Path, windows, *, origin_x=0, rate=Fraction(2), headway=Fraction(60)) -> dict:
    if rate <= 0 or headway <= 0:
        raise ValueError('成品带速和到站间隔须为正数')
    selected = set()
    for start, stop in windows:
        if not 0 <= start < stop <= PAGE_COUNT:
            raise ValueError(f'页码区间须为 0 至 {PAGE_COUNT} 的左闭右开区间')
        selected.update(range(start, stop))
    template = StageTemplate()
    supply = _supply_ports(rate, headway)
    common = _document([dict(board, X=board['X'] + origin_x) for board in controls(CAPACITY, PACKET_TAG, handoff=True)])
    totals = {k: (CAPACITY - 1) * template.through['compact'][k] + template.terminal['compact'][k] + v
              for k, v in _stats(common).items()}
    pages = [_entry(page, origin_x) for page in range(PAGE_COUNT)]
    recipe = _recipe_requirements(CAPACITY)
    recipe['before_run']['length'] = {'minimum': 1, 'maximum': CAPACITY}
    report = {'capacity': CAPACITY, 'stage_pitch': PITCH, 'origin_x': origin_x, 'page_size': PAGE_SIZE,
              'pages': pages, 'size': totals, 'belt_items_per_second': str(rate), 'headway_seconds': str(headway),
              'supply_basis': 'port_peaks_by_opcode_and_material',
              'controls': {'file': 'controls.spz2bp', 'place_at': (origin_x, 12, 0), 'size': _stats(common)},
              'recipe': recipe, 'changeover': {'wait_for_physical_empty': True,
                  'inspect': ['slot_belts', 'parallel_a_and_b', 'stacker_buffers', 'merge_and_exit'],
                  'idle_tail': 'all_six_slots_through', 'reset_phase': 3, 'reset_signal_ticks': 128}}
    output.mkdir(parents=True, exist_ok=True)
    book = output / 'book.json'
    expected = json.loads(json.dumps(report))
    if book.exists() and json.loads(book.read_text(encoding='utf-8')) != expected:
        raise ValueError('目标目录的原点或供货参数不同，请使用另一个输出目录')
    _save_json(book, report)
    (output / report['controls']['file']).write_text(encode_document(common) + '\n', encoding='utf-8')
    for page in sorted(selected):
        doc, connections = build_page(template, pages[page], supply)
        (output / connections['blueprint']).write_text(encode_document(doc) + '\n', encoding='utf-8')
        _save_json(output / connections['connections'], connections)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='按页导出 486 道通用工道和共用控制')
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--pages', nargs=2, type=int, action='append', metavar=('START', 'STOP'),
                        help='页码区间，左闭右开，可重复指定，省略时导出 54 页')
    parser.add_argument('--origin-x', type=int, default=0, help='整册原点的 X 岛格坐标')
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(2), help='一满带每秒的成品数')
    parser.add_argument('--headway', type=Fraction, default=Fraction(60), help='同一站两次有效到货间隔，单位为秒')
    args = parser.parse_args()
    try:
        export(args.output_dir, args.pages or [(0, PAGE_COUNT)], origin_x=args.origin_x,
               rate=args.belt_rate, headway=args.headway)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
