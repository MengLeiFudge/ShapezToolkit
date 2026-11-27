"""对照自主拆层器的原生回放、原层号和公开端口。"""

import argparse
from itertools import cycle
import json
from pathlib import Path

from ...mari.shapes import Shape
from ...mari.signals import describe
from .ported_replay import BatchReplay
from .prefix_scan_wiring import _native_island

_TARGETS = (
    'CuRuSuWu:crCuP-Wg:--Ru----:--P---cb:----Cg--',
    '--------:P-------:--------:--cr----',
    None,
    'P-------',
    '--------:--------:--------:--------:----cb--',
)


def _expected(text):
    if text is None:
        return []
    rows = text.split(':')
    return [(row, i) for i, row in reversed(tuple(enumerate(rows, 1))) if row != '--------']


def _window(replay, schedule, text, enable, duration):
    values = {'target': None if text is None else Shape.from_key(text), 'enable': enable}
    stop = replay.tick + duration
    while replay.tick < stop:
        start = replay.tick
        batch = replay.batch(min(next(schedule), stop - start), values)
        yield from enumerate(batch, start)


def _verify_order(replay, schedule, text, timing):
    reset = timing['reset_hold_ticks']
    period = timing['cycle_ticks']
    width = timing['phase_ticks']
    start = replay.tick
    last = None
    for _, last in _window(replay, schedule, text, 0, reset):
        pass
    if last is None or last['sample'] or last['done']:
        raise ValueError('复位结束时仍在采样或完成')
    events = []
    active = None
    done = None
    for tick, value in _window(replay, schedule, text, 1, 7 * period):
        tick -= start + reset
        if value['sample'] == 1:
            sample = describe(value['top']), value['original_layer']
            if active is None:
                active = {'tick': tick, 'top': sample[0], 'original_layer': sample[1]}
                events.append(active)
            if sample != (active['top'], active['original_layer']):
                raise ValueError(f'样本窗内数据变化 {text}@{tick}: {value}')
        else:
            if value['top'] is not None or value['original_layer'] is not None:
                raise ValueError(f'有效窗外出现输出 {text}@{tick}: {value}')
            if active is not None:
                active['width'] = tick - active['tick']
                active = None
        if value['done'] == 1 and done is None:
            done = tick
        if done is not None and (value['sample'] == 1 or value['done'] != 1):
            raise ValueError(f'完成后出现采样或撤回 {text}@{tick}: {value}')
    wanted = _expected(text)
    actual = [(event['top'], event['original_layer']) for event in events]
    if actual != wanted or done is None or any(event.get('width') != width for event in events):
        raise ValueError(f'拆层结果失配 {text}: {events}, done={done}, 预期 {wanted}')
    if events and events[0]['tick'] != timing['startup_ticks']:
        raise ValueError(f'首层采样位置失配 {text}: {events[0]}')
    if any(right['tick'] - left['tick'] != period for left, right in zip(events, events[1:])):
        raise ValueError(f'拆层周期失配 {text}: {events}')
    return {'input': text, 'samples': events, 'done_tick': done, 'ticks': replay.tick - start}


def audit_scanner(blueprint, report):
    records = []
    profiles = (((1,), False), ((2,), False), ((3,), False), ((4,), False),
                ((1, 4, 2, 3), False), ((4, 1, 4, 1), True))
    for seed, (widths, adversarial) in enumerate(profiles):
        schedule = cycle(widths)
        replay = BatchReplay(blueprint, report, seed=seed, adversarial=adversarial)
        groups = [len(group) for group in replay.feedback_components]
        if groups != [8] or replay.feedback_flywires != 0 or (adversarial and replay.backward_edges != 7):
            raise ValueError(f'反馈拓扑失配：SCC {groups}，{replay.feedback_flywires} 对环内飞线，{replay.backward_edges} 条逆序边')
        timing = report['timing']
        start = replay.tick
        cases = [_verify_order(replay, schedule, text, timing) for text in _TARGETS]
        reset = timing['reset_hold_ticks']
        for _ in _window(replay, schedule, _TARGETS[0], 0, reset):
            pass
        interrupted = list(_window(replay, schedule, _TARGETS[0], 1, 2 * timing['cycle_ticks']))
        if not any(v['sample'] == 1 for _, v in interrupted) or any(v['done'] == 1 for _, v in interrupted):
            raise ValueError('未能在有效扫描期间中断')
        cases.append(dict(_verify_order(replay, schedule, _TARGETS[1], timing), interrupted=True))
        records.append({'batch_pattern': widths, 'adversarial': adversarial, 'components': groups,
                        'backward_edges': replay.backward_edges, 'feedback_flywires': replay.feedback_flywires,
                        'order': replay.order, 'cases': cases, 'ticks': replay.tick - start})
    return records


def main():
    parser = argparse.ArgumentParser(description='逐刻回放现有自主拆层蓝图')
    parser.add_argument('blueprint', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = json.loads(args.blueprint.with_suffix('.json').read_text(encoding='utf-8'))
        evidence = audit_scanner({'BP': _native_island(args.blueprint)}, report)
        args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
