"""将两种含晶订单的私有字段接到六槽接管工道。"""

import argparse
import json
from pathlib import Path

from ...synthesis.physics import Rules
from ..circuit import Literal, encode_document
from ..local_module import Module
from .acceptance import _check_intakes, _islands, _requirements
from .interface import FIELDS, ORDER_INPUTS, PACKET_TAG, WRITE_STATUS
from .layout import _check_footprints, assemble, cargo_ports
from .recipe import BASE, CRYSTAL, _packet, replay
from .sender import ORDER_SELECT, ROWS_PER_BOARD
from .submit_bridge import CANDIDATE_ADDRESS, CANDIDATE_FIELDS
from .submit_bridge import build as build_bridge


HOLD_TICKS = 384
ORDERS = (
    ('CucyRuRu:CuCuCuCu', (
        _packet(BASE, destination=0, base='Cu------'),
        _packet(BASE, destination=1, base='----RuRu'),
        _packet(8, 0, 1),
        {**_packet(CRYSTAL, 0), 'color': 'color:y'},
        _packet(BASE, destination=1, base='CuCuCuCu'),
        _packet(7, 0, 1),
    )),
    ('cbcbWuWu', (
        _packet(BASE, destination=0, base='----SuSu'),
        {**_packet(CRYSTAL, 0), 'color': 'color:b'},
        _packet(BASE, destination=1, base='----WuWu'),
        _packet(8, 0, 1),
    )),
)


def _header(orders):
    module = Module({'order': ORDER_SELECT})
    for choice, order in enumerate(orders, 1):
        selected = f'order{choice}'
        module.gate('LogicGateCompare', ('order', choice), (selected,), 'AQ==')
        for name, value in (('target', order.target), ('length', len(order.stages)),
                            ('replay_result', order.stages[-1].result), ('accepted', 1)):
            module.gate('LogicGateIf', (value, selected), (name,))
    module.outputs = ORDER_INPUTS.copy()
    return module


def _candidate(choice, offset, packets):
    module = Module({'order': ORDER_SELECT, 'address': WRITE_STATUS['address']})
    module.gate('LogicGateCompare', ('order', choice), ('selected',), 'AQ==')
    rules = Rules(4, 5)
    for address, packet in enumerate(packets, offset):
        active = f'row{address}'
        module.gate('LogicGateCompare', ('address', address), (f'at{address}',), 'AQ==')
        module.gate('LogicGateAnd', ('selected', f'at{address}'), (active,))
        module.gate('LogicGateIf', (address, active), ('stamp',))
        for name, value in packet.items():
            if value is None:
                continue
            signal = rules.parse(value) if name == 'base' else value
            module.gate('LogicGateIf', (Literal(signal), active), (name,))
            module.outputs[name] = CANDIDATE_FIELDS[name]
    module.outputs['stamp'] = CANDIDATE_ADDRESS
    return module


def build(*, compact: bool = False) -> tuple[dict, dict]:
    orders = tuple(replay(target, packets) for target, packets in ORDERS)
    count = max(len(order.stages) for order in orders)
    document, interfaces = assemble(count, packet_tag=PACKET_TAG, handoff=True, compact_dyes=True,
                                    fixed_orders=orders if compact else None)
    entries = document['BP']['Entries']
    _check_intakes(_islands(document), interfaces['stations'], cargo_ports())
    bridge, bridge_report = build_bridge(HOLD_TICKS)
    entries.extend(bridge['BP']['Entries'])
    modules = [_header(orders)]
    for choice, (_, packets) in enumerate(ORDERS, 1):
        for offset in range(0, len(packets), ROWS_PER_BOARD):
            modules.append(_candidate(choice, offset, packets[offset:offset + ROWS_PER_BOARD]))
    fixture = []
    for index, module in enumerate(modules):
        island = module.layout()['BP']['Entries'][0]
        island.update(X=3 * index, Y=33)
        fixture.append((island['X'], island['Y'], 0))
        entries.append(island)
    _check_footprints(entries)
    profiles = []
    for (target, packets), order in zip(ORDERS, orders):
        profiles.append({'target': target, 'instructions': packets,
                         'base_stages': [stage.index for stage in order.stages if stage.opcode == BASE],
                         'crystal_stages': [stage.index for stage in order.stages if stage.opcode == CRYSTAL],
                         **_requirements(order)})
    return document, {
        'stage_capacity': count, 'sample_only_stations': compact, 'interfaces': interfaces,
        'submit_bridge': bridge_report, 'orders': profiles,
        'fixture': {'select': ORDER_SELECT, 'choices': [1, 2], 'platforms': fixture},
        'islands': len(entries), 'buildings': sum(len(e.get('B', {}).get('Entries', ())) for e in entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='合装六槽动态含晶配方、供料站和真实实体工段')
    parser.add_argument('--compact', action='store_true', help='安装两份样件订单共用的站点')
    parser.add_argument('--output', type=Path, required=True, help='原生蓝图文件，同名 JSON 保存接线表和用量')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    try:
        document, report = build(compact=args.compact)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                    encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
