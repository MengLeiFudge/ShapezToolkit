"""合装经编译的纯堆叠配方、动态提交桥和九段实体接管工道。"""

import argparse
import base64
import gzip
import json
from pathlib import Path

from ..circuit import encode_document
from ..compiler_frontend import FrontendError
from . import direct_fields
from .interface import FIELDS, ORDER_INPUTS, PACKET_TAG, WRITE_STATUS
from .layout import DIRECT_STACK_STAGES, _check_footprints, assemble_direct_stack
from .submit_bridge import build as build_bridge


_ORDER_PARTS = ('direct-stability', 'direct-stack-scan', 'direct-order-header')
_FIELD_PARTS = ('direct-recipe-fields', 'direct-base-depth', 'direct-base-read')
_CIRCUITS = Path(__file__).resolve().parents[2] / 'blueprints/验收/电路/纯堆叠'


def _read_part(directory, name):
    text = (directory / (name + '.spz2bp')).read_text(encoding='utf-8').strip()
    if not text.startswith('SHAPEZ2-4-') or not text.endswith('$'):
        raise ValueError(f'{name} 需要 SHAPEZ2-4 原生蓝图')
    document = json.loads(gzip.decompress(base64.b64decode(text[10:-1], validate=True)))
    entries = document['BP']['Entries']
    if not entries or any(entry['T'] != 'Foundation_3x3' for entry in entries):
        raise ValueError(f'{name} 需要至少一块 3×3 电路平台')
    report = json.loads((directory / (name + '.json')).read_text(encoding='utf-8'))
    return entries, report


def build(directory: Path = _CIRCUITS, *, fast_fields: bool = False) -> tuple[str, dict]:
    document, interfaces = assemble_direct_stack(packet_tag=PACKET_TAG, handoff=True)
    entries = document['BP']['Entries']
    parts = {name: _read_part(directory, name) for name in _ORDER_PARTS}
    if fast_fields:
        parts.update({name: (blueprint['BP']['Entries'], report)
                      for name, (blueprint, report) in direct_fields.build().items()})
        base_part = 'direct-base-for-address'
    else:
        parts.update({name: _read_part(directory, name) for name in _FIELD_PARTS})
        base_part = 'direct-base-read'
    timings = {name: report['settling']['hold_signal_ticks'] for name, (_, report) in parts.items()
               if 'settling' in report}
    base_hold = timings[base_part] + (timings['direct-base-depth'] if not fast_fields else 0)
    hold = max(timings['direct-recipe-fields'], base_hold)
    bridge, bridge_report = build_bridge(hold, direct_stack=True)
    channels = {name: {key: {field: port['channel'] for field, port in report[key].items()}
                       for key in ('inputs', 'outputs')} for name, (_, report) in parts.items()}
    fields = channels['direct-recipe-fields']['outputs'] | channels[base_part]['outputs']
    if fields != {name: channel for name, channel in bridge_report['inputs']['candidate_fields'].items()
                  if name != 'color'}:
        raise ValueError('编译字段频道与动态提交桥不符')
    header_outputs = {'accepted': ORDER_INPUTS['accepted'], 'length': ORDER_INPUTS['length'],
                      'replay': ORDER_INPUTS['replay_result']}
    if channels['direct-order-header']['outputs'] != header_outputs:
        raise ValueError('装方信息频道与实体工道不符')
    if bridge_report['outputs']['fields'] != FIELDS or bridge_report['outputs']['packet_tag'] != PACKET_TAG:
        raise ValueError('动态提交桥的公开总线与实体工道不符')
    address_inputs = {'address': WRITE_STATUS['address'], 'length': ORDER_INPUTS['length']}
    if channels['direct-recipe-fields']['inputs'] != address_inputs:
        raise ValueError('工序板的地址和长度频道与工道不符')
    source = channels['direct-stability']['outputs']
    scan_ports = channels['direct-stack-scan']
    scan_outputs = scan_ports['outputs']
    target = ORDER_INPUTS['target']
    header_inputs = {'target': target, 'done': scan_outputs['done'],
                     'valid': scan_outputs['result_valid'], 'replay': scan_outputs['result_replay']}
    if (channels['direct-stability']['inputs'] != {'target': target}
            or scan_ports['inputs']['initial_remaining'] != source['target']
            or scan_ports['inputs']['initial_valid'] != source['valid']
            or channels['direct-order-header']['inputs'] != header_inputs):
        raise ValueError('目标、扫描与装方信息板的频道不符')
    if fast_fields:
        base_inputs = {'target': target, **address_inputs}
    else:
        depth = channels['direct-base-depth']
        if depth['inputs'] != address_inputs:
            raise ValueError('基础料查层板的地址和长度频道与工道不符')
        base_inputs = {'target': target, 'depth': depth['outputs']['depth']}
    if channels[base_part]['inputs'] != base_inputs:
        raise ValueError('基础料读料板的输入频道不符')
    scan = parts['direct-stack-scan'][1]
    timing = scan['timing']
    x = 0
    placement = {}
    groups = {name: part[0] for name, part in parts.items()}
    groups['direct-submit-bridge'] = bridge['BP']['Entries']
    for name, group in groups.items():
        dx = x - min(board.get('X', 0) for board in group)
        dy = 18 - min(board.get('Y', 0) for board in group)
        moved = [dict(board, X=board.get('X', 0) + dx, Y=board.get('Y', 0) + dy) for board in group]
        entries.extend(moved)
        placement[name] = {'translation': (dx, dy), 'platforms': len(moved)}
        x = max(board['X'] for board in moved) + 3
    _check_footprints(entries)
    return encode_document(document), {
        'stage_capacity': DIRECT_STACK_STAGES, 'interfaces': interfaces, 'circuits': channels,
        'placement': placement, 'submit_bridge': bridge_report,
        'timing': {'target_before_scan_reset_signal_ticks': timings['direct-stability'],
                   'scan_reset_signal_ticks': timing['reset_hold_signal_ticks'],
                   'scan_sample_signal_ticks': timing['start_to_sample_signal_ticks'],
                   'order_header_hold_signal_ticks': timings['direct-order-header'],
                   'write_reset_signal_ticks': 128},
        'islands': len(entries), 'buildings': sum(len(entry.get('B', {}).get('Entries', ())) for entry in entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='合装动态纯堆叠电路和九段实体接管工道')
    parser.add_argument('--circuits', type=Path, default=_CIRCUITS, help='纯堆叠电路蓝图及同名 JSON 所在目录')
    parser.add_argument('--fast-fields', action='store_true', help='重编工序槽号板和按地址读基础料板，缩短逐笔等待')
    parser.add_argument('--output', type=Path, required=True, help='原生蓝图输出路径')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    try:
        text, report = build(args.circuits, fast_fields=args.fast_fields)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                    encoding='utf-8')
    except (OSError, ValueError, KeyError, TypeError, FrontendError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
