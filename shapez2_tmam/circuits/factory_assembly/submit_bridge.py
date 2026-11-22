"""隔离动态配方的计算与提交，按工道地址核对公开六字段。"""

import argparse
import json
from pathlib import Path

from ..circuit import encode_document
from ..local_module import Module
from ..stage_writer import WRITE_RESET
from .interface import FIELDS, ORDER_INPUTS, PACKET_TAG, WRITE_STATUS


CANDIDATE_FIELDS = {name: 1_680_000 + index for index, name in enumerate(FIELDS, 1)}
CANDIDATE_ADDRESS = 1_680_007
COMMIT = 1_680_008
RADIO_TICKS = 12
_GROUPS = (tuple(FIELDS)[:3], tuple(FIELDS)[3:])
_PREVIOUS = {name: 1_681_000 + index for index, name in enumerate(FIELDS)}
_BUFFERED = {name: 1_681_006 + index for index, name in enumerate(FIELDS)}
_STABLE = (1_681_012, 1_681_013)
_MATCHED = (1_681_014, 1_681_015)
_ELIGIBLE = 1_681_016
_PUBLISHED = 1_681_017
_DELAY_BASE = 1_681_018
_CHANNEL_LIMIT = 1_682_024


def _all(module, signals, name):
    first, *remaining = signals
    for index, other in enumerate(remaining):
        output = name if index == len(remaining) - 1 else f'{name}_{index}'
        module.gate('LogicGateAnd', (first, other), (output,))
        first = output


def _copy_fields(names):
    module = Module({name: CANDIDATE_FIELDS[name] for name in names})
    for name in names:
        module.gate('LogicGateIf', (name, 1), ('old_' + name,))
    module.outputs = {'old_' + name: _PREVIOUS[name] for name in names}
    return module


def _stage_fields(names, stable):
    module = Module({**{name: CANDIDATE_FIELDS[name] for name in names},
                     **{'old_' + name: _PREVIOUS[name] for name in names}})
    for name in names:
        module.gate('LogicGateCompare', (name, 'old_' + name), ('same_' + name,), 'AQ==')
        module.gate('LogicGateIf', ('old_' + name, 1), ('buffered_' + name,))
    _all(module, ['same_' + name for name in names], 'stable')
    module.outputs = {**{'buffered_' + name: _BUFFERED[name] for name in names}, 'stable': stable}
    return module


def _eligible():
    module = Module({'address': WRITE_STATUS['address'], 'stamp': CANDIDATE_ADDRESS,
                     'length': ORDER_INPUTS['length'], 'reset': WRITE_RESET,
                     'opcode': CANDIDATE_FIELDS['opcode'], 'low': _STABLE[0], 'high': _STABLE[1]})
    module.gate('LogicGateCompare', ('address', 'stamp'), ('addressed',), 'AQ==')
    module.gate('LogicGateCompare', ('address', 0), ('nonnegative',), 'Ag==')
    module.gate('LogicGateCompare', ('address', 'length'), ('in_range',), 'BA==')
    module.gate('LogicGateCompare', ('reset', 0), ('enabled',), 'AQ==')
    module.gate('LogicGateCompare', ('opcode', 0), ('instruction',), 'Aw==')
    _all(module, ('addressed', 'nonnegative', 'in_range', 'enabled', 'instruction', 'low', 'high'), 'valid')
    module.gate('LogicGateIf', ('address', 'valid'), ('eligible',))
    module.outputs = {'eligible': _ELIGIBLE}
    return module


def _delay(steps):
    previous = _ELIGIBLE
    for index in range(steps):
        channel = COMMIT if index == steps - 1 else _DELAY_BASE + index
        module = Module({'eligible': _ELIGIBLE} if index == 0 else
                        {'eligible': _ELIGIBLE, 'previous': previous})
        if index == 0:
            module.gate('LogicGateIf', ('eligible', 1), ('held',))
        else:
            module.gate('LogicGateCompare', ('eligible', 'previous'), ('same',), 'AQ==')
            module.gate('LogicGateIf', ('eligible', 'same'), ('held',))
        module.outputs = {'held': channel}
        yield module
        previous = channel


def _same_address(module):
    module.gate('LogicGateCompare', ('eligible', 'previous'), ('same',), 'AQ==')
    module.gate('LogicGateCompare', ('eligible', None), ('present',), 'Bg==')
    module.gate('LogicGateAnd', ('same', 'present'), ('continuing',))


def _count_digit(channel, lower):
    inputs = {'eligible': _ELIGIBLE, 'previous': _DELAY_BASE, 'digit': channel}
    inputs.update({f'lower{i}': lower_channel for i, lower_channel in enumerate(lower)})
    module = Module(inputs)
    _same_address(module)
    module.gate('LogicGateNot', ('continuing',), ('restart',))
    module.gate('LogicGateIf', (0, 'restart'), ('count',))
    module.lookup('digit', 'incremented', ((value, (value + 1) % 8) for value in range(8)))
    if lower:
        full = []
        for index in range(len(lower)):
            signal = f'full{index}'
            module.gate('LogicGateCompare', (f'lower{index}', 7), (signal,), 'AQ==')
            full.append(signal)
        carry = full[0]
        if len(full) > 1:
            _all(module, full, 'carry')
            carry = 'carry'
        module.gate('LogicGateNot', (carry,), ('no_carry',))
        module.gate('LogicGateAnd', ('continuing', 'no_carry'), ('keep',))
        module.gate('LogicGateIf', ('digit', 'keep'), ('count',))
        module.gate('LogicGateAnd', ('continuing', carry), ('advance',))
    else:
        module.gate('LogicGateAnd', ('continuing', 1), ('advance',))
    module.gate('LogicGateIf', ('incremented', 'advance'), ('count',))
    module.outputs = {'count': channel}
    return module


def _counter(steps):
    threshold = steps - 2
    digits = tuple(int(digit) for digit in reversed(f'{threshold:o}'))
    channels = tuple(range(_DELAY_BASE + 1, _DELAY_BASE + 1 + len(digits)))
    for index, channel in enumerate(channels):
        yield _count_digit(channel, channels[:index])
    inputs = {'eligible': _ELIGIBLE, 'previous': _DELAY_BASE, 'committed': COMMIT}
    inputs.update({f'digit{i}': channel for i, channel in enumerate(channels)})
    module = Module(inputs)
    _same_address(module)
    matches = []
    for index, digit in enumerate(digits):
        signal = f'match{index}'
        module.gate('LogicGateCompare', (f'digit{index}', digit), (signal,), 'AQ==')
        matches.append(signal)
    reached = matches[0]
    if len(matches) > 1:
        _all(module, matches, 'reached')
        reached = 'reached'
    module.gate('LogicGateCompare', ('eligible', 'committed'), ('already',), 'AQ==')
    module.gate('LogicGateOr', (reached, 'already'), ('ready',))
    module.gate('LogicGateAnd', ('continuing', 'ready'), ('commit',))
    module.gate('LogicGateIf', ('eligible', 'commit'), ('stamp',))
    module.gate('LogicGateIf', ('eligible', 1), ('previous_stamp',))
    module.outputs = {'stamp': COMMIT, 'previous_stamp': _DELAY_BASE}
    yield module


def _publish(names, *, stamp=False):
    module = Module({'address': WRITE_STATUS['address'], 'eligible': _ELIGIBLE, 'commit': COMMIT,
                     **{name: _BUFFERED[name] for name in names}})
    module.gate('LogicGateCompare', ('commit', None), ('present',), 'Bg==')
    module.gate('LogicGateCompare', ('commit', 'address'), ('addressed',), 'AQ==')
    module.gate('LogicGateCompare', ('commit', 'eligible'), ('current',), 'AQ==')
    _all(module, ('present', 'addressed', 'current'), 'publish')
    for name in names:
        module.gate('LogicGateIf', (name, 'publish'), ('out_' + name,))
    module.outputs = {'out_' + name: FIELDS[name] for name in names}
    if stamp:
        module.gate('LogicGateIf', ('commit', 'publish'), ('published',))
        module.outputs['published'] = _PUBLISHED
    return module


def _readback(names, matched):
    module = Module({'address': WRITE_STATUS['address'], 'published': _PUBLISHED,
                     **{name: FIELDS[name] for name in names},
                     **{'expected_' + name: _BUFFERED[name] for name in names}})
    module.gate('LogicGateCompare', ('published', 'address'), ('addressed',), 'AQ==')
    for name in names:
        module.gate('LogicGateCompare', (name, 'expected_' + name), ('same_' + name,), 'AQ==')
    _all(module, ['addressed', *('same_' + name for name in names)], 'matches')
    module.gate('LogicGateIf', ('published', 'matches'), ('confirmed',))
    module.outputs = {'confirmed': matched}
    return module


def _tag():
    module = Module({'address': WRITE_STATUS['address'], 'eligible': _ELIGIBLE, 'reset': WRITE_RESET,
                     'commit': COMMIT, 'low': _MATCHED[0], 'high': _MATCHED[1]})
    for name in ('eligible', 'commit', 'low', 'high'):
        module.gate('LogicGateCompare', ('address', name), (name + '_ok',), 'AQ==')
    module.gate('LogicGateCompare', ('reset', 0), ('enabled',), 'AQ==')
    _all(module, ('eligible_ok', 'commit_ok', 'low_ok', 'high_ok', 'enabled'), 'valid')
    module.gate('LogicGateIf', ('address', 'valid'), ('tag',))
    module.outputs = {'tag': PACKET_TAG}
    return module


def _direct_candidate():
    module = Module({'address': WRITE_STATUS['address'], 'length': ORDER_INPUTS['length'],
                     'accepted': ORDER_INPUTS['accepted'], 'reset': WRITE_RESET})
    module.gate('LogicGateCompare', ('address', 0), ('nonnegative',), 'Ag==')
    module.gate('LogicGateCompare', ('address', 'length'), ('in_range',), 'BA==')
    module.gate('LogicGateCompare', ('accepted', 1), ('verified',), 'AQ==')
    module.gate('LogicGateCompare', ('reset', 0), ('enabled',), 'AQ==')
    _all(module, ('nonnegative', 'in_range', 'verified', 'enabled'), 'valid')
    module.gate('LogicGateIf', ('address', 'valid'), ('stamp',))
    module.outputs = {'stamp': CANDIDATE_ADDRESS}
    return module


def build(hold_ticks: int, *, direct_stack: bool = False, delay_chain: bool = False) -> tuple[dict, dict]:
    if type(hold_ticks) is not int or hold_ticks < 1:
        raise ValueError('稳定等待须为正整数信号 tick')
    steps = (hold_ticks + RADIO_TICKS - 1) // RADIO_TICKS
    if steps > _CHANNEL_LIMIT - _DELAY_BASE:
        raise ValueError('稳定等待超出提交桥的保留频道范围')
    timed = not delay_chain and steps > 1
    timer = tuple(_counter(steps) if timed else _delay(steps))
    last_channel = _DELAY_BASE + (len(timer) - 1 if timed else steps - 2)
    low, high = _GROUPS
    modules = (*(_copy_fields(names) for names in _GROUPS),
               *(_stage_fields(names, stable) for names, stable in zip(_GROUPS, _STABLE)),
               _eligible(), *timer, _publish(low, stamp=True), _publish(high),
               *(_readback(names, matched) for names, matched in zip(_GROUPS, _MATCHED)), _tag())
    if direct_stack:
        modules += (_direct_candidate(),)
    entries = []
    for index, module in enumerate(modules):
        island = module.layout()['BP']['Entries'][0]
        column, row = divmod(index, 4)
        island.update(X=3 * column, Y=18 + 3 * row)
        entries.append(island)
    report = {
        'inputs': {'address': WRITE_STATUS['address'], 'length': ORDER_INPUTS['length'], 'reset': WRITE_RESET,
                   'candidate_address': CANDIDATE_ADDRESS, 'candidate_fields': CANDIDATE_FIELDS},
        'outputs': {'fields': FIELDS, 'commit_address': COMMIT, 'packet_tag': PACKET_TAG},
        'reserved_internal_channels': [min(_PREVIOUS.values()), last_channel],
        'timing': {'hold_signal_ticks': hold_ticks, 'radio_signal_ticks': RADIO_TICKS, 'delay_steps': steps,
                   'timer': 'counter' if timed else 'delay_chain', 'timer_islands': len(timer),
                   'eligible_to_commit_signal_ticks': steps * RADIO_TICKS,
                   'commit_to_public_signal_ticks': RADIO_TICKS, 'public_to_tag_signal_ticks': 2 * RADIO_TICKS},
        'islands': len(entries),
        'buildings': sum(len(island['B']['Entries']) for island in entries),
    }
    if direct_stack:
        report['inputs']['accepted'] = ORDER_INPUTS['accepted']
        report['inputs'].pop('candidate_address')
        report['outputs']['candidate_address'] = CANDIDATE_ADDRESS
    return {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': entries}}, report


def main() -> int:
    parser = argparse.ArgumentParser(description='导出六槽动态配方提交桥')
    timing = parser.add_mutually_exclusive_group(required=True)
    timing.add_argument('--hold-signal-ticks', type=int, help='编译报告给出的稳定等待时间')
    timing.add_argument('--settling-report', type=Path, help='含 settling.hold_signal_ticks 的编译接口 JSON')
    parser.add_argument('--direct-stack', action='store_true', help='从通过纯堆叠回放的工道地址生成候选地址')
    parser.add_argument('--delay-chain', action='store_true', help='导出逐级无线等待版，用于离线时序对照')
    parser.add_argument('--output', type=Path, required=True, help='原生 .spz2bp 文件，同名 JSON 保存接线和时序')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    try:
        hold = args.hold_signal_ticks
        if args.settling_report is not None:
            data = json.loads(args.settling_report.read_text(encoding='utf-8-sig'))
            hold = data['settling']['hold_signal_ticks']
        document, report = build(hold, direct_stack=args.direct_stack, delay_chain=args.delay_chain)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                    encoding='utf-8')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(f'{report["islands"]} 个岛项目，稳定等待 {report["timing"]["eligible_to_commit_signal_ticks"]} 信号 tick')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
