"""导出两地址独立锁存样件，核对六字段写入与保持路接管。"""

import argparse
import json
from pathlib import Path

from ..circuit import encode_document
from ..local_module import Module
from ..production_stage import instruction_decoder
from ..slot_streams import DEST
from ..stage_memory import READBACK, STREAM_STATE, WRITE_BUS
from ..stage_writer import WRITE_ACK, WRITE_READY, WRITE_REQUEST, WRITE_RESET
from ..stream_controller import PROGRAM_LENGTH, STREAM_NEXT, release
from .changeover import LOADED, LOAD_PERMIT, TARGET_INPUT
from .interface import FIELDS, ORDER_INPUTS, PACKET_TAG
from .layout import _check_footprints


RADIO_TICKS = 12
HOLD_STEPS = 11
_PRIVATE = 1_740_000
STATE = _PRIVATE
TAPS = tuple(range(STATE + 1, STATE + 1 + HOLD_STEPS))
APPROVED = TAPS[-1] + 1
HELD_APPROVAL = APPROVED + 1


def _gate(m, kind, out, *args, config=None):
    m.gate('LogicGate' + kind, args, (out,), config)
    return out


def _equals(m, out, left, right):
    return _gate(m, 'Compare', out, left, right, config='AQ==')


def _select(m, out, enable, active, inactive):
    # 控制的正反路各经过一门，再进入同深度的两路 IF。
    yes = _gate(m, 'And', out + '_yes', enable, 1)
    no = _gate(m, 'Not', out + '_no', enable)
    _gate(m, 'If', out, active, yes)
    return _gate(m, 'If', out, inactive, no)


def _delay_local(m, prefix, value, count):
    for i in range(count):
        value = _gate(m, 'If', f'{prefix}{i}', value, 1)
    return value


def _advance():
    m = Module({'state': STREAM_STATE, 'tag': PACKET_TAG, 'length': PROGRAM_LENGTH,
                'ready': WRITE_READY, 'ack': WRITE_ACK})
    m.lookup('state', 'successor', ((0, -1), (-1, 1), (1, -2), (-2, 2), (2, 2)))
    preparing = _gate(m, 'Compare', 'preparing', 'state', 0, config='Ag==')
    writing = _gate(m, 'Compare', 'writing', 'state', 0, config='BA==')
    in_range = _gate(m, 'Compare', 'in_range', 'state', 'length', config='BA==')
    live = _gate(m, 'And', 'live', preparing, in_range)
    tagged = _gate(m, 'And', 'tagged', _equals(m, 'tag_matches', 'state', 'tag'),
                   _delay_local(m, 'ready_stage', 'ready', 1))
    begin = _gate(m, 'And', 'begin', live, tagged)
    stored = _gate(m, 'And', 'stored', writing, _delay_local(m, 'ack_stage', 'ack', 1))
    step = _gate(m, 'Or', 'step', begin, _delay_local(m, 'stored_stage', stored, 1))
    current = _delay_local(m, 'current', 'state', 5)
    successor = _delay_local(m, 'next', 'successor', 3)
    m.outputs = {_select(m, 'stream_next', step, successor, current): STREAM_NEXT}
    return m


def _timer():
    for source, target in zip((STATE, *TAPS), TAPS):
        m = Module({'state': STATE} if source == STATE else {'state': STATE, 'previous': source})
        enabled = 1 if source == STATE else _equals(m, 'same', 'state', 'previous')
        m.outputs = {_gate(m, 'If', 'sample', 'state', enabled): target}
        yield m


def _approval():
    m = Module({'mature': TAPS[-1], 'operands': READBACK[0], 'materials': READBACK[1]})
    for i, expected in enumerate((2, 3, 1), 1):
        low = _equals(m, f'low{i}', 'operands', expected)
        high = _equals(m, f'high{i}', 'materials', expected)
        both = _gate(m, 'And', f'both{i}', low, high)
        phase = _equals(m, f'at{i}', 'mature', i)
        same_sample = _delay_local(m, f'phase{i}_', phase, 1)
        confirmed = _gate(m, 'And', f'confirmed{i}', both, same_sample)
        _gate(m, 'If', 'approved', i, confirmed)
    m.outputs = {'approved': APPROVED}
    return m


def _hold_approval():
    m = Module({'approved': APPROVED})
    # 逐门一拍模型中，令许可覆盖状态反馈的全部采样位置。
    tap = 'approved'
    _gate(m, 'If', 'held', tap, 1)
    for i in range(11):
        tap = _gate(m, 'If', f'tap{i}', tap, 1)
        _gate(m, 'If', 'held', tap, 1)
    m.outputs = {'held': HELD_APPROVAL}
    return m


def _step():
    m = Module({'state': STATE, 'approved': HELD_APPROVAL, 'request': WRITE_REQUEST, 'reset': WRITE_RESET})
    m.lookup('state', 'advanced', ((i, min(i + 1, 4)) for i in range(5)))
    enabled = _gate(m, 'And', 'enabled', _equals(m, 'requested', 'request', 1),
                    _equals(m, 'running', 'reset', 0))
    idle = _equals(m, 'idle', 'state', 0)
    approved = _equals(m, 'same_phase', 'approved', 'state')
    proceed = _gate(m, 'Or', 'proceed', idle, approved)
    current = _delay_local(m, 'current', 'state', 3)
    successor = _delay_local(m, 'successor', 'advanced', 1)
    active = _select(m, 'active_state', proceed, successor, current)
    same_input = _delay_local(m, 'enable_stage', enabled, 2)
    m.outputs = {_select(m, 'next_state', same_input, _delay_local(m, 'active_stage', active, 1), 0): STATE}
    return m


def _status():
    m = Module({'state': STATE, 'request': WRITE_REQUEST, 'reset': WRITE_RESET,
                'operands': READBACK[0], 'materials': READBACK[1]})
    m.lookup('state', 'work_phase', enumerate((4, 1, 2, 0, 0)))
    running = _equals(m, 'running', 'reset', 0)
    phase = _select(m, 'phase', running, 'work_phase', 3)
    requested = _equals(m, 'requested', 'request', 1)
    idle = _equals(m, 'idle', 'state', 0)
    quiet = _gate(m, 'And', 'quiet', _equals(m, 'low_empty', 'operands', None),
                  _equals(m, 'high_empty', 'materials', None))
    standby = _gate(m, 'And', 'standby', idle, _equals(m, 'no_request', 'request', 0))
    ready = _gate(m, 'And', 'ready', _gate(m, 'And', 'can_start', running, standby), quiet)
    ack = _gate(m, 'And', 'ack', _equals(m, 'acked', 'state', 4),
                _gate(m, 'And', 'active', running, requested))
    m.outputs = {phase: WRITE_BUS['phase'], ready: WRITE_READY, ack: WRITE_ACK}
    return m


def _selection(index, load, retain, selected):
    m = Module({'state': STREAM_STATE, 'phase': WRITE_BUS['phase']})
    commit = _equals(m, 'commit', 'state', -index - 1)
    addressed = _gate(m, 'Or', 'addressed', _equals(m, 'prepare', 'state', index), commit)
    _gate(m, 'If', 'address', index, addressed)
    writing = _equals(m, 'writing', 'phase', 1)
    overlap = _equals(m, 'overlap', 'phase', 2)
    _gate(m, 'And', 'load', commit, _gate(m, 'Or', 'write_enabled', writing, overlap))
    reset = _equals(m, 'reset', 'phase', 3)
    replace = _gate(m, 'And', 'replace', commit, writing)
    _gate(m, 'Not', 'retain', _gate(m, 'Or', 'disable_retention', replace, reset))
    m.outputs = {'load': load, 'retain': retain, 'commit': selected, 'address': WRITE_BUS['address']}
    return m


def _field(source, storage, load, retain, written, retained):
    m = Module({'data': source, 'old': storage, 'load': load, 'retain': retain})
    _gate(m, 'If', 'write_value', 'data', 'load')
    # 同一保持值分别用于读回检查和合流。存储通过无线回边取上一次发布值。
    _gate(m, 'If', 'held_value', 'old', 'retain')
    _gate(m, 'If', 'stored', 'write_value', 1)
    _gate(m, 'If', 'stored', 'held_value', 1)
    same = _equals(m, 'same', 'old', 'data')
    held = _equals(m, 'held', 'held_value', 'data')
    ret_ok = _gate(m, 'And', 'retained', held, _delay_local(m, 'retain_stage', 'retain', 2))
    m.outputs = {'stored': storage, same: written, ret_ok: retained}
    return m


def _reply(selected, written, retained, channel):
    m = Module({'selected': selected, 'phase': WRITE_BUS['phase']})
    ready = {}
    for name, channels in (('written', written), ('retained', retained)):
        names = tuple(f'{name}{i}' for i in range(3))
        m.inputs.update(zip(names, channels))
        pair = _gate(m, 'And', name + '_pair', *names[:2])
        ready[name] = _gate(m, 'And', name + '_all', pair, _delay_local(m, name + '_last', names[2], 1))
    selected_sample = _delay_local(m, 'selected_stage', 'selected', 3)
    for phase, code, name in ((1, 2, 'written'), (2, 3, 'retained'), (0, 1, 'retained')):
        phase_match = _equals(m, f'phase{code}', 'phase', phase)
        phase_sample = _delay_local(m, f'phase{code}_stage', phase_match, 1)
        all_fields = _gate(m, 'And', f'fields{code}', phase_sample, ready[name])
        confirmed = _gate(m, 'And', f'confirmed{code}', selected_sample, all_fields)
        _gate(m, 'If', 'reply', code, confirmed)
    m.outputs = {'reply': channel}
    return m


def storage_ports(index):
    offset = 32 * index
    inputs = instruction_decoder(offset).inputs
    return {name: DEST + offset if name == 'destination' else inputs[name] for name in FIELDS}


def _memory(index):
    offset = _PRIVATE + 32 * (index + 1)
    load, retain, selected = range(offset, offset + 3)
    written = tuple(range(offset + 3, offset + 9))
    retained = tuple(range(offset + 9, offset + 15))
    yield _selection(index, load, retain, selected)
    for (name, storage), written_ch, retained_ch in zip(storage_ports(index).items(), written, retained):
        yield _field(FIELDS[name], storage, load, retain, written_ch, retained_ch)
    for bank, start in zip(READBACK, (0, 3)):
        yield _reply(selected, written[start:start + 3], retained[start:start + 3], bank)


def build():
    boards = (_advance(), release(LOAD_PERMIT, TARGET_INPUT, LOADED), _step(), _status(),
              _approval(), _hold_approval(), *_timer(), *_memory(0), *_memory(1))
    entries = []
    for i, board in enumerate(boards):
        island = board.layout()['BP']['Entries'][0]
        column, row = divmod(i, 6)
        island.update(X=3 * column, Y=3 * row)
        entries.append(island)
    _check_footprints(entries)
    document = {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': entries}}
    report = {'stage_capacity': 2,
              'inputs': {**ORDER_INPUTS, 'run_permit': LOAD_PERMIT, 'packet_tag': PACKET_TAG, 'fields': FIELDS},
              'outputs': {'address': WRITE_BUS['address'], 'phase': WRITE_BUS['phase'], 'stream_state': STREAM_STATE,
                          'reset': WRITE_RESET, 'request': WRITE_REQUEST, 'ack': WRITE_ACK, 'ready': WRITE_READY,
                          'loaded': LOADED, 'readback': READBACK, 'storage': [storage_ports(i) for i in range(2)]},
              'timing': {'phase_hold_signal_ticks': RADIO_TICKS * HOLD_STEPS, 'radio_signal_ticks': RADIO_TICKS},
              'islands': len(entries), 'buildings': sum(len(e['B']['Entries']) for e in entries)}
    return document, report


def main():
    parser = argparse.ArgumentParser(description='导出六字段锁存接管样件')
    parser.add_argument('--output', type=Path, required=True, help='原生 .spz2bp 文件及配套接线表')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    try:
        document, report = build()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                   encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'{report["islands"]} 个平台，{report["buildings"]} 个建筑')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
