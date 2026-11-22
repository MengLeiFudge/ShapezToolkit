"""按已回放的配方核算每件成品的加工、物品和液体流量。"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import ceil

from ...synthesis.physics import EMPTY, PIN
from ...synthesis.production_bill import CRYSTAL_LITERS, PAINT_LITERS, PRIMARY
from .layout import CargoPort, cargo_ports
from .recipe import BASE, CRYSTAL, Production

WORK_MACHINES = {
    1: ('RotatorOneQuad',), 2: ('RotatorOneQuadCCW',), 3: ('RotatorHalf',),
    4: ('CutterHalf',), 5: ('RotatorHalf', 'CutterHalf', 'RotatorHalf'),
    6: ('PinPusherDefault',), 7: ('StackerStraight',),
    8: ('HalvesSwapperDefault',), 9: ('HalvesSwapperDefault',), 10: ('CrystalGeneratorDefault',),
}
# 车厢的 28～31 行沿用 wagon_intake 的四条独立原色支路。
DYE_ROWS = {
    'r': {'r': 28}, 'g': {'g': 31}, 'b': {'b': 31},
    'c': {'g': 28, 'b': 29}, 'm': {'r': 29, 'b': 28},
    'y': {'r': 30, 'g': 29}, 'w': {'r': 31, 'g': 30, 'b': 30}, 'pin': {'r': 28},
}


@dataclass(frozen=True)
class Demand:
    stage: int
    path: str
    resource: str
    per_product: Fraction
    unit: str
    port: CargoPort | None = None
    row: int | None = None


@dataclass(frozen=True)
class TrainDelivery:
    interval_seconds: Fraction
    # 已送进每条站场缓冲的有效货量，按车厢号、建筑层和西侧带行索引。
    payload: Mapping[tuple[int, int, int], Fraction]


@dataclass(frozen=True)
class Capacity:
    demand: Demand
    required_per_second: Fraction
    available_per_second: Fraction | None
    train_per_second: Fraction | None


def demands(production: Production) -> tuple[Demand, ...]:
    ports = {(p.station, p.cargo): p for p in cargo_ports()}
    output: list[Demand] = []
    for stage in production.stages:
        index = stage.index

        def machine(path, kind, amount=1, unit='item'):
            output.append(Demand(index, path, kind, Fraction(amount), unit))

        def cargo(path, kind, row, amount, unit):
            port = ports[path, kind]
            output.append(Demand(index, path, kind, Fraction(amount), unit, port, row))

        def dye(path, color, liters):
            blend = 'r' if color == 'pin' else color
            ingredients = Counter(PRIMARY[blend])
            for kind, parts in ingredients.items():
                cargo(path, kind, DYE_ROWS[color][kind], Fraction(liters * parts, 4), 'liter')
            if blend == 'w':
                machine(path + '/cyan', 'MixerDefault', Fraction(liters, 2), 'liter')
            if len(ingredients) > 1:
                machine(path + '/' + blend, 'MixerDefault', liters, 'liter')

        machine('slot_stream', 'belt')
        if stage.opcode != BASE:
            for i, kind in enumerate(WORK_MACHINES[stage.opcode], 1):
                machine(f'work/{i}', kind)
            if stage.opcode == CRYSTAL:
                assert stage.color is not None
                dye('crystal', stage.color, CRYSTAL_LITERS)
            continue
        row = stage.result.layers[0]
        direct = len(set(row)) == 1
        for q, cell in enumerate(row[:1] if direct else row):
            path = f'q{q}'
            kind = 'C' if cell in (EMPTY, PIN) else cell[0]
            port = ports[path, kind]
            cargo(path, kind, port.rows[0], 1, 'item')
            if cell == PIN:
                for i in range(1, 7):
                    machine(f'{path}/pin/{i}', 'PinPusherDefault')
                machine(path + '/pin', 'CrystalGeneratorDefault')
                dye(path, 'pin', CRYSTAL_LITERS)
            elif cell == EMPTY:
                machine(path, 'CutterHalf')
                machine(path, 'RotatorOneQuadCCW' if q < 2 else 'RotatorOneQuad')
            elif cell[1] != 'u':
                machine(path, 'PainterDefault')
                dye(path, cell[1], PAINT_LITERS)
        if not direct:
            for part in ('first', 'second', 'final'):
                machine('join/' + part, 'HalvesSwapperDefault')
            for part in ('first', 'second'):
                machine('join/' + part, 'RotatorOneQuadCCW')
    return tuple(output)


def check_capacity(production: Production, belt_items_per_second: Fraction,
                   rates: Mapping[str, Fraction],
                   deliveries: Mapping[tuple[int, str], TrainDelivery]) -> tuple[Capacity, ...]:
    target = Fraction(belt_items_per_second)
    if target <= 0 or any(rate < 0 for rate in rates.values()):
        raise ValueError('目标带速须为正数，现场供给和加工率须为非负数')
    for delivery in deliveries.values():
        if delivery.interval_seconds <= 0 or any(amount < 0 for amount in delivery.payload.values()):
            raise ValueError('列车到站间隔须为正数，卸入缓冲的货量须为非负数')
    capacity = []
    for demand in demands(production):
        port = demand.port
        resource = demand.resource
        train_rate = None
        if port is not None:
            resource = 'pipe' if demand.unit == 'liter' else 'belt'
            service = 'crystal' if port.station == 'crystal' else 'base'
            train = deliveries.get((demand.stage, service))
            if train is not None and demand.row is not None:
                payload = train.payload.get((port.wagon, port.layer, demand.row))
                if payload is not None:
                    train_rate = Fraction(payload) / Fraction(train.interval_seconds)
        available = rates.get(resource)
        capacity.append(Capacity(demand, target * demand.per_product,
                                 None if available is None else Fraction(available), train_rate))
    return tuple(capacity)


def parallel_lines(capacity: tuple[Capacity, ...]) -> int | None:
    if not capacity:
        raise ValueError('并联数需要至少一项产能记录')
    required_lines = 1
    for row in capacity:
        rates = (row.available_per_second,) if row.demand.port is None else (
            row.available_per_second, row.train_per_second)
        if any(rate is None or rate <= 0 for rate in rates):
            return None
        for rate in rates:
            assert rate is not None
            required_lines = max(required_lines, ceil(row.required_per_second / rate))
    return required_lines
