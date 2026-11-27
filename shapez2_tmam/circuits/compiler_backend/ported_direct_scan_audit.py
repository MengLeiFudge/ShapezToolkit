"""用真实 direct_scan 方法逐轮对照有线定步工作板。"""

import argparse
from itertools import cycle
import json
from pathlib import Path

from ...mari.shapes import Shape as NativeShape
from ...mari.signals import describe
from ...synthesis import direct_stack
from ...synthesis.physics import Rules
from .ported_replay import BatchReplay
from .prefix_scan_wiring import _native_island


_CASES = (
    (None, 1, None),
    ('cr------', 1, None),
    ('CuCu----:RuRu----:SuSu----:WuWu----:CuCu----', 1, None),
    ('Cu------:--------:P-------:----Ru--', 1, None),
    ('--cu----:----Cb--', 1, None),
    ('CuCu----:RuRu----', 0, 'SuSu----'),
    ('P-P-P-P-', 1, None),
)


def _expected(case, steps):
    target, valid, seed = case
    rules = Rules()
    old = rules.parse(target) if target else None, bool(valid), rules.parse(seed) if seed else None
    states = [old]
    for _ in range(steps):
        old = (direct_stack.direct_scan_remaining(*old), direct_stack.direct_scan_valid(*old),
               direct_stack.direct_scan_replay(*old))
        states.append(old)
    return [tuple(int(v) if isinstance(v, bool) else v.to_key() if v is not None else None for v in state)
            for state in states]


def _window(replay, sequence, case, run, duration):
    target, valid, seed = case
    inputs = {'enable': run, 'initial_remaining': None if target is None else NativeShape.from_key(target),
              'initial_valid': valid, 'initial_replay': None if seed is None else NativeShape.from_key(seed)}
    stop = replay.tick + duration
    while replay.tick < stop:
        start = replay.tick
        batch = replay.batch(min(stop - start, next(sequence)), inputs)
        yield from enumerate(batch, start)


def _verify(replay, sequence, case, timing, steps):
    final_names = ('result_remaining', 'result_valid', 'result_replay')
    period, startup = timing['cycle_ticks'], timing['startup_ticks']
    reset = None
    for _, reset in _window(replay, sequence, case, 0, timing['reset_hold_ticks']):
        pass
    if reset is None or reset['done'] or any(reset[name] is not None for name in final_names):
        raise ValueError('复位后仍公布旧结果')
    start = replay.tick
    done = None
    first_output = None
    rounds = []
    expected = _expected(case, steps)
    for tick, sample in _window(replay, sequence, case, 1, startup + (steps + 2) * period):
        tick -= start
        # 每轮写回结束至下一轮清空前，取一个包含整个批次的连续窗口。
        n = (tick - startup - 7 * timing['phase_ticks']) // period + 1
        if 0 <= n <= steps and 12 <= (tick - startup - 7 * timing['phase_ticks']) % period < 24:
            state = tuple(describe(sample[name]) for name in ('state_remaining', 'state_valid', 'state_replay'))
            if state != expected[n]:
                raise ValueError(f'第 {n} 轮状态失配，{case} @ {tick} 得到 {state}，预期 {expected[n]}')
            if not rounds or rounds[-1]['round'] != n:
                rounds.append({'round': n, 'tick': tick, 'state': state})
        if sample['done'] == 1:
            final = tuple(describe(sample[name]) for name in final_names)
            if final != expected[-1] or len(rounds) != steps + 1:
                raise ValueError(f'过早完成或最终结果失配，{case} @ {tick} 得到 {final}，预期 {expected[-1]}')
            if done is None:
                done = tick
        elif done is not None:
            raise ValueError(f'完成位撤回，{case} @ {tick}')
        elif any(sample[name] is not None for name in final_names):
            if first_output is None:
                first_output = tick
            visible = (describe(sample[name]) for name in final_names)
            if any(value is not None and value != expected_value for value, expected_value in
                   zip(visible, expected[-1], strict=True)):
                raise ValueError(f'完成前发布了不同的结果，{case} @ {tick}')
    if done is None or (first_output is not None and done - first_output > 12):
        raise ValueError(f'定步扫描未在结果稳定后及时完成：{case}, {first_output=}, {done=}')
    return {'input': case, 'rounds': rounds, 'done_tick': done, 'first_output_tick': first_output,
            'outputs': dict(zip(final_names, expected[-1], strict=True))}


def audit_direct_scan(blueprint, report):
    profiles = tuple(((width,), False) for width in range(1, 5)) + (((1, 4, 2, 3), False), ((4, 1, 4, 1), True))
    evidence = []
    for seed, (pattern, adversarial) in enumerate(profiles):
        r = BatchReplay(blueprint, report, seed=seed, adversarial=adversarial)
        sequence = cycle(pattern)
        timing, steps = report['timing'], report['steps']
        cases = [_verify(r, sequence, case, timing, steps) for case in _CASES]
        for _ in _window(r, sequence, _CASES[2], 0, timing['reset_hold_ticks']):
            pass
        interrupt_at = timing['startup_ticks'] + timing['cycle_ticks']
        first_round = _expected(_CASES[2], steps)[1]
        observed_update = False
        for _, sample in _window(r, sequence, _CASES[2], 1, interrupt_at):
            if sample['done']:
                raise ValueError('预定中断前不应已发布完成位')
            observed_update |= tuple(describe(sample[f'state_{name}']) for name in
                                     ('remaining', 'valid', 'replay')) == first_round
        if not observed_update:
            raise ValueError('换单回放尚未执行第一轮真实更新')
        cases.append(dict(_verify(r, sequence, _CASES[1], timing, steps), interrupted_at=interrupt_at))
        evidence.append({'batch_pattern': pattern, 'adversarial': adversarial, 'backward_edges': r.backward_edges,
                         'feedback_components': [len(c) for c in r.feedback_components], 'feedback_flywires': r.feedback_flywires,
                         'order': r.order, 'ticks': r.tick, 'cases': cases})
    return evidence


def main():
    parser = argparse.ArgumentParser(description='逐刻对照五轮 direct_scan 原生蓝图')
    parser.add_argument('blueprint', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = json.loads(args.blueprint.with_suffix('.json').read_text(encoding='utf-8'))
    evidence = audit_direct_scan({'BP': _native_island(args.blueprint)}, report)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
