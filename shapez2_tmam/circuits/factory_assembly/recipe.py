"""按六槽指令回放目标，并记录各工段的实际物品流。"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ...synthesis.physics import EMPTY, Rules, Shape
from ..slot_streams import SLOT_ROWS
from ..work_lane import COLORS

MAX_STAGES = 971
BASE = 14
CRYSTAL = 10
BINARY = (7, 8, 9)
OPCODES = (*range(1, 11), BASE)


@dataclass(frozen=True)
class Stage:
    index: int
    opcode: int
    operands: tuple[int, ...]
    destination: int
    result: Shape
    color: str | None = None
    discarded: Shape | None = None


@dataclass(frozen=True)
class Production:
    target: Shape
    stages: tuple[Stage, ...]
    product_slot: int


def _slot(value: object) -> int:
    if type(value) is not int or not 0 <= value < len(SLOT_ROWS):
        raise ValueError(f"槽号须为 0 至 {len(SLOT_ROWS) - 1} 的整数，收到 {value!r}")
    return value


def _process(rules: Rules, opcode: int, used: tuple[Shape, ...],
             color: str | None) -> tuple[Shape | None, Shape | None]:
    a = used[0]
    if opcode in (1, 2, 3):
        return rules.rotate(a, (1, -1, 2)[opcode - 1]), None
    if opcode in (4, 5):
        keep = opcode - 4
        halves = rules.cut(a)
        return halves[keep], halves[1 - keep]
    if opcode == 6:
        return rules.pin(a), None
    if opcode == 7:
        return rules.stack(a, used[1]), None
    if opcode in (8, 9):
        keep = opcode - 8
        halves = rules.swap(a, used[1])
        return halves[keep], halves[1 - keep]
    assert opcode == CRYSTAL and color is not None
    return rules.crystal(a, color), None


def replay(target: str, packets: Iterable[Mapping[str, object]]) -> Production:
    rules = Rules(4, 5)
    expected = rules.parse(target)
    if any('cu' in row for row in expected.layers):
        raise ValueError('未着色晶体的实体供料尚未界定')
    live: dict[int, Shape] = {}
    stages = []
    for index, packet in enumerate(packets):
        if index >= MAX_STAGES:
            raise ValueError(f'工段数超过 {MAX_STAGES}')
        try:
            opcode = packet['opcode']
            if type(opcode) is not int or opcode not in OPCODES:
                raise ValueError(f'未知制作操作号 {opcode!r}')
            destination = _slot(packet['destination'])
            color = None
            discarded = None
            if opcode == BASE:
                operands = ()
                base = packet['base']
                if not isinstance(base, str):
                    raise ValueError('操作 14 需要基础单层短代码')
                result = rules.parse(base)
                if len(result.layers) != 1 or any(cell[0] == 'c' for cell in result.layers[0]):
                    raise ValueError('基础料须为非空且不含晶体的单层')
            else:
                operands = (_slot(packet['a']),)
                if opcode in BINARY:
                    operands += (_slot(packet['b']),)
                    if operands[0] == operands[1]:
                        raise ValueError('两个操作数须来自不同的槽')
                missing = tuple(i for i in operands if i not in live)
                if missing:
                    raise ValueError(f'操作数槽为空 {missing}')
                if opcode == CRYSTAL:
                    signal = packet['color']
                    if not isinstance(signal, str) or signal not in tuple('color:' + c for c in COLORS):
                        raise ValueError('操作 10 需要 color:r/g/b/c/m/y/w 中的一种信号')
                    color = signal[-1]
                result, discarded = _process(rules, opcode, tuple(live[i] for i in operands), color)
            if destination in live and destination not in operands:
                raise ValueError(f'目的槽 {destination} 已有未消费物品')
            if result is None:
                raise ValueError('所选产物出口为空')
            for i in operands:
                del live[i]
            live[destination] = result
            stages.append(Stage(index, opcode, operands, destination, result, color, discarded))
        except KeyError as error:
            raise ValueError(f'工段 {index} 缺少字段 {error.args[0]}') from error
        except ValueError as error:
            raise ValueError(f'工段 {index} {error}') from error
    if len(live) != 1:
        raise ValueError(f'回放结束须恰剩一个成品槽，实际剩余 {tuple(live)}')
    product_slot, result = next(iter(live.items()))
    if result != expected:
        raise ValueError(f'回放产物 {result.to_key()} 与目标 {target} 不同')
    return Production(expected, tuple(stages), product_slot)
