"""导出用固定两步配方核对整组提交的原生工道。"""

import argparse
import json
from pathlib import Path

from ..circuit import Literal, encode_document
from ..local_module import Module
from .interface import FIELDS, OPERATOR_INPUTS, ORDER_INPUTS, PACKET_TAG, WRITE_STATUS
from .layout import _check_footprints, assemble
from .recipe import BASE, CRYSTAL, replay


TARGET = 'Cucrcrcr'
PACKETS = (
    {'opcode': BASE, 'a': None, 'b': None, 'destination': 2, 'base': 'Cu------', 'color': None},
    {'opcode': CRYSTAL, 'a': 2, 'b': None, 'destination': 0, 'base': None, 'color': 'color:r'},
)
START = 1_680_000
CANDIDATE = {name: START + index for index, name in enumerate(FIELDS, 1)}
PREPARED = START + len(FIELDS) + 1
COMMIT = PREPARED + 1
RESET_TICKS = 128
RADIO_TICKS = 12
RESET_STEPS = (RESET_TICKS + RADIO_TICKS - 1) // RADIO_TICKS + 1
RESET_READY = COMMIT + RESET_STEPS


def _reset_modules():
    previous = None
    for channel in range(COMMIT + 1, RESET_READY + 1):
        inputs = {'phase': WRITE_STATUS['phase']}
        if previous is not None:
            inputs['previous'] = previous
        module = Module(inputs)
        module.gate('LogicGateCompare', ('phase', 3), ('clear',), 'AQ==')
        output = 'clear'
        if previous is not None:
            output = 'held'
            module.gate('LogicGateAnd', ('clear', 'previous'), (output,))
        module.outputs = {output: channel}
        yield module
        previous = channel
    module = Module({'start': START, 'cleared': RESET_READY, 'running': OPERATOR_INPUTS['run']})
    module.gate('LogicGateCompare', ('start', 1), ('requested',), 'AQ==')
    module.gate('LogicGateOr', ('cleared', 'running'), ('armed',))
    module.gate('LogicGateAnd', ('requested', 'armed'), ('run',))
    module.gate('LogicGateIf', ('run', 1), ('clean_confirmed',))
    module.outputs = {name: OPERATOR_INPUTS[name] for name in ('run', 'clean_confirmed')}
    yield module


def _metadata(target, length):
    module = Module({'run': OPERATOR_INPUTS['run']})
    for name, value in (('target', target), ('replay_result', target), ('accepted', 1), ('length', length)):
        module.gate('LogicGateIf', (Literal(value), 'run'), (name,))
    module.outputs = dict(ORDER_INPUTS)
    return module


def _preview(rows):
    module = Module({'address': WRITE_STATUS['address'], 'run': OPERATOR_INPUTS['run']})
    for index, row in enumerate(rows):
        match, send = f'at{index}', f'send{index}'
        module.gate('LogicGateCompare', ('address', index), (match,), 'AQ==')
        module.gate('LogicGateAnd', (match, 'run'), (send,))
        module.gate('LogicGateIf', (index, send), ('stamp',))
        for name, value in row.items():
            module.gate('LogicGateIf', (Literal(value), send), (name,))
    module.outputs = {**CANDIDATE, 'stamp': PREPARED}
    return module


def _confirm(rows, fields, stamp, output):
    module = Module({'address': WRITE_STATUS['address'], 'stamp': stamp, **fields})
    for index, row in enumerate(rows):
        matched = f'address{index}'
        module.gate('LogicGateCompare', ('address', index), (matched,), 'AQ==')
        for name, value in (*row.items(), ('stamp', index)):
            same, both = f'{name}{index}', f'{name}_ok{index}'
            module.gate('LogicGateCompare', (name, Literal(value)), (same,), 'AQ==')
            module.gate('LogicGateAnd', (matched, same), (both,))
            matched = both
        module.gate('LogicGateIf', (index, matched), ('tag',))
    module.outputs = {'tag': output}
    return module


def _publish(names):
    module = Module({'address': WRITE_STATUS['address'], 'commit': COMMIT, **{name: CANDIDATE[name] for name in names}})
    module.gate('LogicGateCompare', ('commit', None), ('present',), 'Bg==')
    module.gate('LogicGateCompare', ('commit', 'address'), ('matched',), 'AQ==')
    module.gate('LogicGateAnd', ('present', 'matched'), ('submit',))
    for name in names:
        module.gate('LogicGateIf', (name, 'submit'), (name + '_out',))
    module.outputs = {name + '_out': FIELDS[name] for name in names}
    return module


def build() -> tuple[str, dict]:
    production = replay(TARGET, PACKETS)
    rows = [dict(packet, base=production.stages[index].result if packet['base'] is not None else None)
            for index, packet in enumerate(PACKETS)]
    document, interfaces = assemble(len(rows), packet_tag=PACKET_TAG)
    entries = document['BP']['Entries']
    names = tuple(FIELDS)
    modules = (*_reset_modules(), _metadata(production.target, len(rows)), _preview(rows),
               _confirm(rows, CANDIDATE, PREPARED, COMMIT), _publish(names[:3]), _publish(names[3:]),
               _confirm(rows, FIELDS, COMMIT, PACKET_TAG))
    for index, module in enumerate(modules):
        island = module.layout()['BP']['Entries'][0]
        column, row = divmod(index, 4)
        island.update(X=3 * column, Y=18 + 3 * row)
        entries.append(island)
    _check_footprints(entries)
    report = {'stage_capacity': len(rows), 'islands': len(entries), 'interfaces': interfaces,
              'sample': {'target': TARGET, 'instructions': PACKETS, 'start': START,
                         'private': {'fields': CANDIDATE, 'prepared_address': PREPARED, 'commit_address': COMMIT},
                         'reset_ready': RESET_READY, 'reset_hold_signal_ticks': RESET_TICKS,
                         'reset_sample_count': RESET_STEPS, 'reset_sample_interval_signal_ticks': RADIO_TICKS}}
    return encode_document(document), report


def main() -> int:
    parser = argparse.ArgumentParser(description='生成两步配方整组提交样件')
    parser.add_argument('--output', type=Path, required=True, help='原生 .spz2bp 文件，同名 JSON 保存接线和试接配方')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    try:
        blueprint, report = build()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(blueprint + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                    encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'两步配方样件，{report["islands"]} 个岛项目，原生编码 {len(blueprint)} 字符')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
