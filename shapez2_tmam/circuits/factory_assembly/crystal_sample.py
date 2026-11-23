"""将有色结晶配方经动态提交桥送入六槽实体工道。"""

import argparse
import json
from pathlib import Path

from ..circuit import encode_document
from .capacity import demands
from .interface import PACKET_TAG
from .layout import _check_footprints, assemble
from .recipe import BASE, CRYSTAL, _packet, replay
from .sender import ORDER_SELECT, ROWS_PER_BOARD, _order_metadata, _publish, _replay_result, _rows
from .submit_bridge import CANDIDATE_FIELDS, build as build_bridge


_ORDERS = {
    'crystal': {
        'target': 'CucmRuWu:CuCuCuCu',
        'instructions': (
            _packet(BASE, destination=0, base='Cu--SuWu'),
            {**_packet(CRYSTAL, 0), 'color': 'color:m'},
            _packet(BASE, destination=1, base='--CuRuWu'),
            _packet(8, 0, 1),
            _packet(BASE, destination=1, base='CuCuCuCu'),
            _packet(7, 0, 1),
        ),
    },
    'stack': {
        'target': 'RuRuRuRu:SuSuSuSu',
        'instructions': (
            _packet(BASE, destination=0, base='RuRuRuRu'),
            _packet(BASE, destination=1, base='SuSuSuSu'),
            _packet(7, 0, 1),
        ),
    },
}
# 候选查表有三个本地门，提交桥再等待整组前后读数稳定。
_HOLD_TICKS = 120


def _candidate_modules(order_ids):
    yield _order_metadata(_ORDERS, order_ids)
    yield _replay_result()
    for name, order in _ORDERS.items():
        rows = list(_rows(order['instructions']))
        for offset in range(0, len(rows), ROWS_PER_BOARD):
            yield _publish(order_ids[name], rows[offset:offset + ROWS_PER_BOARD], channels=CANDIDATE_FIELDS)


def build(*, compact_stations: bool = False) -> tuple[str, dict]:
    orders = {name: replay(order['target'], order['instructions']) for name, order in _ORDERS.items()}
    count = max(len(order.stages) for order in orders.values())
    document, interfaces = assemble(count, packet_tag=PACKET_TAG, handoff=True,
                                    fixed_orders=tuple(orders.values()) if compact_stations else None)
    entries = document['BP']['Entries']
    bridge, bridge_report = build_bridge(_HOLD_TICKS, direct_stack=True)
    bridge_entries = bridge['BP']['Entries']
    entries.extend(bridge_entries)
    x = max(board['X'] for board in bridge_entries) + 3
    order_ids = {name: number for number, name in enumerate(orders, 1)}
    for index, module in enumerate(_candidate_modules(order_ids)):
        island = module.layout()['BP']['Entries'][0]
        column, row = divmod(index, 4)
        island.update(X=x + column * 3, Y=18 + row * 3)
        entries.append(island)
    _check_footprints(entries)

    reports = {}
    for name, order in orders.items():
        ports = [{'stage': demand.stage, 'station': demand.port.station, 'wagon': demand.port.wagon,
                  'layer': demand.port.layer, 'row': demand.row, 'cargo': demand.resource,
                  'per_product': str(demand.per_product), 'unit': demand.unit}
                 for demand in demands(order) if demand.port is not None]
        reports[name] = {**_ORDERS[name], 'product_slot': order.product_slot, 'cargo_per_product': ports}
    return encode_document(document), {
        'select': {'channel': ORDER_SELECT, 'orders': order_ids}, 'orders': reports,
        'stage_capacity': count, 'compact_stations': compact_stations, 'interfaces': interfaces,
        'submit_bridge': bridge_report, 'islands': len(entries),
        'buildings': sum(len(board.get('B', {}).get('Entries', ())) for board in entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='导出六段动态有色含晶实体工道和两份验收配方')
    parser.add_argument('--compact-stations', action='store_true', help='仅为样件配方会用到的地址接入供料站')
    parser.add_argument('--output', type=Path, required=True, help='原生蓝图输出路径，同名 JSON 保存接线和配方')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    text, report = build(compact_stations=args.compact_stations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + '\n', encoding='utf-8')
    args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
