"""用同一组六字段和双回读，验收有等待时间的写入交接。"""

import argparse
import json
from pathlib import Path

from ..circuit import encode_document
from ..layer_controller import RUN
from ..local_module import Module
from ..stage_memory import READBACK, STREAM_STATE, STREAM_SUCCESSOR, WRITE_BUS, packet_memory
from ..stage_writer import WRITE_ACK, WRITE_READY, WRITE_REQUEST, WRITE_RESET
from ..stream_controller import PROGRAM_LENGTH, STREAM_NEXT, release
from . import sender
from .changeover import LOADED, TARGET_INPUT
from .interface import FIELDS, PACKET_TAG, recipe_interface
from .layout import _check_footprints
from .recipe import BASE, CRYSTAL, _packet, replay
from .submit_bridge import RADIO_TICKS

_STATE, _ELIGIBLE, _PREVIOUS, _COUNT, _CONFIRMED = range(1_683_000, 1_683_005)
_SAMPLES = 11


def _select(module, condition, yes, no, output):
    enabled, disabled = output + '_yes', output + '_no'
    module.gate('LogicGateAnd', (condition, 1), (enabled,))
    module.gate('LogicGateNot', (condition,), (disabled,))
    module.gate('LogicGateIf', (yes, enabled), (output,))
    module.gate('LogicGateIf', (no, disabled), (output,))


def _delay(module, signal, ticks, name):
    for i in range(ticks):
        output = f'{name}{i}'
        module.gate('LogicGateIf', (signal, 1), (output,))
        signal = output
    return signal


def stream_advance(packet_tag: int) -> Module:
    module = Module({'state': STREAM_STATE, 'successor': STREAM_SUCCESSOR, 'tag': packet_tag,
                     'length': PROGRAM_LENGTH, 'ready': WRITE_READY, 'ack': WRITE_ACK})
    module.gate('LogicGateCompare', ('state', 'tag'), ('tagged',), 'AQ==')
    module.gate('LogicGateCompare', ('state', 0), ('preparing',), 'Ag==')
    module.gate('LogicGateCompare', ('state', 'length'), ('in_range',), 'BA==')
    module.gate('LogicGateAnd', ('preparing', 'in_range'), ('live',))
    tagged = _delay(module, 'tagged', 1, 'tagged_wait')
    module.gate('LogicGateAnd', ('live', tagged), ('addressed',))
    module.gate('LogicGateCompare', ('successor', 0), ('write_token',), 'BA==')
    ready = _delay(module, 'ready', 1, 'ready_wait')
    module.gate('LogicGateAnd', ('write_token', ready), ('can_write',))
    can_write = _delay(module, 'can_write', 1, 'write_wait')
    module.gate('LogicGateAnd', ('addressed', can_write), ('begin',))
    module.gate('LogicGateCompare', ('state', 0), ('writing',), 'BA==')
    module.gate('LogicGateCompare', ('successor', 0), ('next_address',), 'Aw==')
    module.gate('LogicGateAnd', ('writing', 'next_address'), ('committing',))
    ack = _delay(module, 'ack', 2, 'ack_wait')
    module.gate('LogicGateAnd', ('committing', ack), ('stored',))
    stored = _delay(module, 'stored', 1, 'stored_wait')
    module.gate('LogicGateOr', ('begin', stored), ('step',))
    # 两路判断同为五级，再给选择门留一级。保持值和后继读同一拍快照。
    state = _delay(module, 'state', 6, 'state_wait')
    successor = _delay(module, 'successor', 6, 'successor_wait')
    _select(module, 'step', successor, state, 'next')
    module.outputs = {'next': STREAM_NEXT}
    return module


def _advance():
    module = Module({'request': WRITE_REQUEST, 'reset': WRITE_RESET, 'state': _STATE,
                     'confirmed': _CONFIRMED, 'operands': READBACK[0], 'materials': READBACK[1]})
    module.gate('LogicGateCompare', ('reset', 0), ('enabled',), 'AQ==')
    module.gate('LogicGateAnd', ('request', 'enabled'), ('active',))
    module.gate('LogicGateCompare', ('state', 0), ('idle',), 'AQ==')
    module.gate('LogicGateCompare', ('state', 'confirmed'), ('current',), 'AQ==')
    module.gate('LogicGateOr', ('idle', 'current'), ('step',))
    module.lookup('state', 'successor', tuple((i, min(i + 1, 4)) for i in range(5)))
    successor = _delay(module, 'successor', 1, 'successor_wait')
    state = _delay(module, 'state', 3, 'state_wait')
    _select(module, 'step', successor, state, 'next')
    _select(module, 'active', 'next', 0, 'state_out')
    module.gate('LogicGateCompare', ('state', 4), ('finished',), 'AQ==')
    module.gate('LogicGateAnd', ('active', 'finished'), ('ack',))
    for bank in ('operands', 'materials'):
        module.gate('LogicGateCompare', (bank, None), (bank + '_quiet',), 'AQ==')
    module.gate('LogicGateAnd', ('operands_quiet', 'materials_quiet'), ('quiet',))
    module.gate('LogicGateCompare', ('request', 0), ('no_request',), 'AQ==')
    module.gate('LogicGateAnd', ('enabled', 'no_request'), ('standby',))
    module.gate('LogicGateAnd', ('standby', 'idle'), ('rearmed',))
    module.gate('LogicGateAnd', ('rearmed', 'quiet'), ('ready',))
    module.outputs = {'state_out': _STATE, 'ack': WRITE_ACK, 'ready': WRITE_READY}
    return module


def _publish_phase():
    module = Module({'state': _STATE, 'reset': WRITE_RESET})
    module.lookup('state', 'normal', ((0, 4), (1, 1), (2, 2), (3, 0), (4, 0)))
    module.gate('LogicGateCompare', ('reset', 1), ('clearing',), 'AQ==')
    _select(module, 'clearing', 3, 'normal', 'phase')
    module.outputs = {'phase': WRITE_BUS['phase']}
    return module


def _observe():
    module = Module({'state': _STATE, 'operands': READBACK[0], 'materials': READBACK[1]})
    module.lookup('state', 'expected', ((1, 2), (2, 3), (3, 1)))
    module.gate('LogicGateCompare', ('expected', None), ('valid',), 'Bg==')
    for bank in ('operands', 'materials'):
        module.gate('LogicGateCompare', (bank, 'expected'), (bank + '_ok',), 'AQ==')
    module.gate('LogicGateAnd', ('operands_ok', 'materials_ok'), ('both',))
    module.gate('LogicGateAnd', ('both', 'valid'), ('match',))
    state = _delay(module, 'state', 5, 'observed_state')
    module.gate('LogicGateIf', (state, 'match'), ('eligible',))
    module.outputs = {'eligible': _ELIGIBLE}
    return module


def _wait():
    module = Module({'eligible': _ELIGIBLE, 'previous': _PREVIOUS, 'count': _COUNT})
    module.gate('LogicGateCompare', ('eligible', 'previous'), ('same',), 'AQ==')
    module.gate('LogicGateCompare', ('eligible', None), ('present',), 'Bg==')
    module.gate('LogicGateAnd', ('same', 'present'), ('continuing',))
    module.lookup('count', 'incremented', tuple((i, min(i + 1, _SAMPLES)) for i in range(_SAMPLES + 1)))
    incremented = _delay(module, 'incremented', 1, 'increment_wait')
    _select(module, 'continuing', incremented, 0, 'count_out')
    # 相位见证与计数走同样的四级本地门，同一轮随无线返回。
    stamp = _delay(module, 'eligible', 4, 'stamp')
    module.gate('LogicGateCompare', ('count', _SAMPLES), ('enough',), 'AQ==')
    enough = _delay(module, 'enough', 1, 'enough_wait')
    module.gate('LogicGateAnd', (enough, 'continuing'), ('settled',))
    current = _delay(module, 'eligible', 3, 'eligible_wait')
    module.gate('LogicGateIf', (current, 'settled'), ('confirmed',))
    module.outputs = {stamp: _PREVIOUS, 'count_out': _COUNT, 'confirmed': _CONFIRMED}
    return module


def writer_modules() -> tuple[Module, ...]:
    return _advance(), _publish_phase(), _observe(), _wait()


def build() -> tuple[dict, dict]:
    packets = (_packet(BASE, destination=0, base='Cu------'),
               {**_packet(CRYSTAL, 0), 'color': 'color:r'})
    target = 'Cucrcrcr'
    replay(target, packets)
    order = {'target': target, 'instructions': packets}
    transmitters, sender_ports = sender.build({'handoff': order}, PACKET_TAG)
    modules = (stream_advance(PACKET_TAG), release(RUN, TARGET_INPUT, LOADED), *writer_modules())
    islands = [module.layout()['BP']['Entries'][0] for module in modules]
    stored = []
    for index in range(len(packets)):
        channels = {name: 1_683_010 + 6 * index + i for i, name in enumerate(FIELDS)}
        names = tuple(channels)
        for group, reply in zip((names[:3], names[3:]), READBACK):
            banks = {name: channels[name] for name in group}
            islands.append(packet_memory(index, banks, reply, stream=True))
        stored.append(channels)
    for i, island in enumerate(islands):
        row, col = divmod(i, 5)
        island.update(X=col * 3, Y=row * 3)
    islands.extend(transmitters)
    _check_footprints(islands)
    report = {'recipe': recipe_interface(len(packets), PACKET_TAG), 'sender': sender_ports,
              'order': order, 'stored': stored, 'stream_state': STREAM_STATE,
              'private_channels': [_STATE, max(stored[-1].values())],
              'minimum_hold_signal_ticks': _SAMPLES * RADIO_TICKS, 'islands': len(islands),
              'buildings': sum(len(island['B']['Entries']) for island in islands)}
    return {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': islands}}, report


def main() -> int:
    parser = argparse.ArgumentParser(description='导出双回读与保持接管样件')
    parser.add_argument('--output', type=Path, required=True, help='原生蓝图文件，同名 JSON 保存接线表')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    document, report = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encode_document(document) + '\n', encoding='utf-8')
    args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
