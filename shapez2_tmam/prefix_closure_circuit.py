"""四象限零Pin首轮的两列支撑见证及追加块强制闭包。"""

from dataclasses import dataclass

from .circuit import Ref
from .corner_program import CornerProgram
from .prefix_search import PrefixSearch, height_value


@dataclass(frozen=True)
class PrefixClosure:
    """当前切向的一轮结果；初值保留全部C，无C时保留完整地面层。"""

    initial: tuple[Ref, ...]
    next_values: tuple[Ref, ...]
    changed: Ref
    impossible: Ref


def prefix_closure(program: CornerProgram, finder: PrefixSearch, direction: Ref) -> PrefixClosure:
    """静态生成强制补格通路；由调用者推进寄存器，不在此执行搜索。"""
    target, current = finder.target, finder.columns
    has_crystal = program.or_(*(cell.crystal for column in target for cell in column))
    minimum = tuple(tuple(program.and_(valid[height], program.not_(program.or_(*valid[:height])))
                          for height in range(6)) for valid in finder.valid_heights)
    initial = tuple(program.pick(has_crystal, height_value(program, minimum[q]), target[q][0].occupied)
                    for q in range(4))
    forced = [[program.zero for _ in range(5)] for _ in range(4)]
    failures = []
    for first in range(4):
        pair = (first, (first + 1) % 4)
        selected = direction if first % 2 else program.not_(direction)
        links = (program.zero, *(program.or_(*(program.and_(target[q][z].crystal,
                 target[q][z - 1].crystal) for q in pair)) for z in range(1, 5)))
        same = tuple(tuple(program.and_(*links[min(z, r) + 1:max(z, r) + 1])
                           for r in range(5)) for z in range(5))
        eligible = tuple(tuple(program.one if z == 0 else program.or_(
            program.and_(program.not_(links[z]), target[q][z - 1].occupied), target[q][z - 1].pin)
            for q in pair) for z in range(5))
        ordinary = tuple(tuple(program.and_(target[q][z].occupied, program.not_(target[q][z].pin),
                                            program.not_(target[q][z].crystal), eligible[z][i])
                               for i, q in enumerate(pair)) for z in range(5))
        active = tuple(program.or_(*(program.and_(current[q][z].occupied,
                                    program.not_(current[q][z].pin)) for q in pair)) for z in range(5))
        seeds = tuple(program.or_(*(program.and_(current[q][z].occupied,
                                   program.not_(current[q][z].pin), eligible[z][i])
                                   for i, q in enumerate(pair))) for z in range(5))
        supported = tuple(program.or_(*(program.and_(same[z][r], seeds[r]) for r in range(5))) for z in range(5))
        bad = tuple(program.and_(active[z], program.not_(supported[z])) for z in range(5))
        candidates = tuple(program.or_(*(program.and_(same[z][r], program.or_(*ordinary[r]))
                                         for r in range(5))) for z in range(5))
        failures.append(program.and_(selected, program.or_(*(program.and_(bad[z], program.not_(candidates[z]))
                                                             for z in range(5)))))
        for i, q in enumerate(pair):
            for z in range(5):
                lowest = program.and_(ordinary[z][i], program.not_(program.or_(*(
                    program.and_(same[z][r], ordinary[r][i]) for r in range(z)))))
                add = program.and_(selected, lowest, program.or_(*(
                    program.and_(same[z][r], bad[r]) for r in range(5))))
                forced[q][z] = program.or_(forced[q][z], add)
    for z in range(5):
        ordinary = tuple(program.and_(finder.required_delta[q][z], program.not_(target[q][z].pin)) for q in range(4))
        below = tuple(target[q][z - 1].occupied if z else program.one for q in range(4))
        supported = tuple(program.and_(ordinary[q], below[q]) for q in range(4))
        for _ in range(3):
            supported = tuple(program.or_(supported[q], program.and_(ordinary[q], program.or_(
                supported[(q - 1) % 4], supported[(q + 1) % 4]))) for q in range(4))
        for q in range(4):
            bad = program.and_(finder.required_delta[q][z],
                               program.not_(program.pick(target[q][z].pin, below[q], supported[q])))
            forced[q][z] = program.or_(forced[q][z], bad)
    additions = tuple(tuple(program.and_(forced[q][z], finder.delta[q][z]) for z in range(5)) for q in range(4))
    changed = program.or_(*(cell for column in additions for cell in column))
    next_values = []
    for q, old in enumerate(finder.values):
        highest = tuple(program.and_(additions[q][z], program.not_(program.or_(*additions[q][z + 1:]))) for z in range(5))
        value = height_value(program, highest, first=1)
        next_values.append(program.pick(program.or_(*additions[q]), value, old))
    return PrefixClosure(initial, tuple(next_values), changed, program.or_(*failures))
