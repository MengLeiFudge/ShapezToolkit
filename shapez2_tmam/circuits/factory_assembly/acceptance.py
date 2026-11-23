"""为固定订单生成六槽验收工道、发送器和供料记录。"""

import argparse
import json
from collections import Counter
from pathlib import Path

from ...synthesis.physics import Rules
from ...synthesis.recipe import Builder
from ..circuit import encode_document
from ..freight_loader import loading
from ..slot_streams import SLOT_ROWS
from ..stage_memory import WRITE_BUS
from . import four_color_sample, sender
from .capacity import demands
from .layout import _check_footprints, assemble, cargo_ports, crystal_loading
from .recipe import BASE, CRYSTAL, MAX_STAGES, replay


STACK_TARGET = 'CuCuCuCu:RuRuRuRu:SuSuSuSu:WuWuWuWu:CuCuCuCu'
PIN_EXAMPLE = Path(__file__).resolve().parents[2] / 'examples/json/4q-required-tail-pin.instructions.json'


def _orders():
    rules = Rules(4, 5)
    stack = Builder(rules).noncrystal(rules.parse(STACK_TARGET))
    if stack is None:
        raise ValueError(f'逐层堆叠未得到目标 {STACK_TARGET}')
    pin = json.loads(PIN_EXAMPLE.read_text(encoding='utf-8'))
    return {
        'stack': {'target': STACK_TARGET, 'instructions': list(stack.instructions())},
        'pin-crystal': {'target': pin['target'], 'instructions': pin['instructions']},
    }


def _solver_order(path: Path) -> dict:
    order = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(order, dict) or order.get('status') != 'solved':
        raise ValueError('需要 Solver4 的 solved 指令 JSON')
    if (order.get('quadrants'), order.get('height')) != (4, 5):
        raise ValueError('配方必须是四象限五层')
    target, packets = order.get('target'), order.get('instructions')
    if not isinstance(target, str) or not isinstance(packets, list) or not 1 <= len(packets) <= MAX_STAGES:
        raise ValueError(f'配方须包含目标短代码和 1 至 {MAX_STAGES} 条加工指令')
    for address, packet in enumerate(packets):
        if not isinstance(packet, dict) or not sender.FIELDS.keys() <= packet.keys():
            raise ValueError(f'工段 {address} 须包含 {"、".join(sender.FIELDS)} 六字段')
        for field in ('a', 'b'):
            value = packet[field]
            if type(value) is not int or not 0 <= value < len(SLOT_ROWS):
                raise ValueError(f'工段 {address} 的 {field} 须为 0 至 {len(SLOT_ROWS) - 1} 的整数槽号')
        for field, opcode in (('base', BASE), ('color', CRYSTAL)):
            if packet['opcode'] != opcode and packet[field] is not None:
                raise ValueError(f'工段 {address} 的 {field} 仅在操作 {opcode} 使用')
    return {'target': target, 'instructions': packets}


def _islands(document):
    return {(e.get('X', 0), e.get('Y', 0), e.get('Z', 0)): e for e in document['BP']['Entries']}


def _require_station(islands, kind, x, y):
    entry = islands.get((x, y, 0), {})
    if entry.get('T') != 'Layout_Train' + kind or entry.get('R', 0) != 3:
        raise ValueError(f'站场 {(x, y)} 需要朝北的 {kind}')


def _require_port(board, kind, x, row, level):
    entries = board.get('B', {}).get('Entries', ())
    if not any(e['T'] == kind + 'InternalVariant' and (e['X'], e['Y'], e['L'], e['R']) == (x, row, level, 0)
               for e in entries):
        raise ValueError(f'平台 {(board.get("X", 0), board.get("Y", 0))} 缺少东向 {kind} {(x, row, level)}')


def _check_intakes(islands, stations, ports):
    for station in stations:
        for key in ('base_head', 'crystal_head'):
            if key in station:
                _require_station(islands, 'WaitStation', *station[key])
        for port in ports:
            key = 'crystal_head' if port.station == 'crystal' else 'base_head'
            if key not in station:
                continue
            x, start = station[key]
            wagon_y = start + port.wagon
            _require_station(islands, 'Unloader_' + port.kind + '_Flipped', x, wagon_y)
            connector = 'FluidPortReceiver' if port.kind == 'Fluids' else 'BeltPortReceiver'
            group = (port.wagon - 1) // 3
            board_y = start if port.station == 'crystal' else start + 2 + 3 * group
            board = islands[x + 3, board_y, 0]
            for row in port.rows:
                if board_y + row // 20 != wagon_y:
                    raise ValueError(f'工段 {station["stage"]} 的 {port} 对不上卸货车厢')
                _require_port(board, connector, -18, row, port.layer)


def _check_loaders(ports):
    for port in ports:
        crystal = port.station == 'crystal'
        if not crystal and port.wagon > 3:
            continue
        islands = _islands(crystal_loading(port.cargo) if crystal else loading(port.cargo))
        prefix = 'FluidPort' if port.kind == 'Fluids' else 'BeltPort'
        rows = port.rows if crystal else tuple(-12 + 20 * (port.wagon - 1) + i for i in range(4))
        for y in ((0,) if crystal else range(0, 12, 3)):
            board = islands[0, y, 0]
            wagon_y = 1 if crystal else y + port.wagon - 2
            _require_station(islands, 'Unloader_' + port.kind + '_Flipped', -3, wagon_y)
            _require_station(islands, 'Loader_' + port.kind, 3, wagon_y)
            for row in rows:
                # 结晶换装台北端为空，车厢位于平台原点南侧一格。
                if y + row // 20 != wagon_y:
                    raise ValueError(f'{port.cargo} 的装货口对不上车厢 {port.wagon}')
                _require_port(board, prefix + 'Receiver', -18, row, 0)
                _require_port(board, prefix + 'Sender', 37, row, port.layer)


def _requirements(production):
    per_product = Counter()
    paths = []
    for demand in demands(production):
        item = {'stage': demand.stage, 'path': demand.path, 'resource': demand.resource,
                'amount_per_product': str(demand.per_product), 'unit': demand.unit}
        if demand.port is not None:
            port = demand.port
            service = 'crystal' if port.station == 'crystal' else 'base'
            item.update(station=service, wagon=port.wagon, layer=port.layer, row=demand.row)
            per_product[demand.resource, demand.unit] += demand.per_product
        paths.append(item)
    return {'product_slot': production.product_slot,
            'cargo_per_product': {f'{cargo}_{unit}': str(amount) for (cargo, unit), amount in per_product.items()},
            'paths': paths}


def build(packet_tag: int, *, compact: bool = False, recipe_path: Path | None = None,
          four_color: bool = False, compact_feeds: bool = False) -> tuple[str, dict]:
    if recipe_path is not None:
        if four_color:
            raise ValueError('四色样件与外部配方只能选一个')
        orders = {'solver4': _solver_order(recipe_path)}
    else:
        orders = four_color_sample.orders() if four_color else _orders()
    programs = {name: replay(order['target'], order['instructions']) for name, order in orders.items()}
    count = max(len(program.stages) for program in programs.values())
    fixed = tuple(programs.values()) if compact else None
    document, interfaces = assemble(count, packet_tag=packet_tag, fixed_orders=fixed, handoff=four_color and compact,
                                    compact_base=compact_feeds, compact_dyes=compact_feeds)
    ports = cargo_ports()
    islands = _islands(document)
    _check_intakes(islands, interfaces['stations'], ports)
    _check_loaders(ports)
    output = interfaces['output']
    _require_port(islands[tuple(output['platform'])], 'BeltPortSender', 37, output['east_y'], output['level'])
    modules, sender_ports = sender.build(orders, packet_tag)
    entries = document['BP']['Entries']
    entries.extend(modules)
    _check_footprints(entries)
    blueprint = encode_document(document)
    return blueprint, {'packet_tag': packet_tag, 'write_bus': WRITE_BUS, 'stage_capacity': count,
                       'islands': len(entries), 'interfaces': interfaces, 'sender': sender_ports,
                       'orders': {name: dict(order, **_requirements(programs[name]))
                                  for name, order in orders.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description='生成固定配方的六槽验收工道')
    parser.add_argument('--packet-tag', type=int, default=sender.PACKET_TAG,
                        help=f'配方地址回读的独占频道，默认 {sender.PACKET_TAG}')
    sample = parser.add_mutually_exclusive_group()
    sample.add_argument('--recipe', type=Path, help='Solver4 生成的 solved 指令 JSON，默认使用两份内置订单')
    sample.add_argument('--four-color', action='store_true', help='使用两种切向的四色含晶验收订单')
    parser.add_argument('--output', type=Path, help='原生蓝图输出，邻接 JSON 包含订单和供货需求')
    parser.add_argument('--compact', action='store_true', help='仅保留所选固定订单需要的供料站')
    parser.add_argument('--compact-feeds', action='store_true', help='将基础料和结晶染料的卸货与转接分别合板')
    args = parser.parse_args()
    if args.output is not None and args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    try:
        blueprint, report = build(args.packet_tag, compact=args.compact, recipe_path=args.recipe,
                                  four_color=args.four_color, compact_feeds=args.compact_feeds)
    except (OSError, ValueError) as error:
        parser.error(f'{args.recipe}: {error}' if args.recipe is not None else str(error))
    if args.output is not None:
        args.output.write_text(blueprint + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{report["stage_capacity"]} 工段，{report["islands"]} 个岛项目，原生编码 {len(blueprint)} 字符')
    for name, order in report['orders'].items():
        print(f'{name} {order["target"]}，{len(order["instructions"])} 条指令，成品槽 {order["product_slot"]}，'
              f'每件用料 {order["cargo_per_product"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
