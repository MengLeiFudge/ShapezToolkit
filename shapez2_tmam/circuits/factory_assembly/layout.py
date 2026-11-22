"""装配六槽通用工段，并给制作和配料提供同一张车厢端口表。"""

from dataclasses import asdict, dataclass

from ..freight_stage import CARS, add_machine_dyes, freight_stage
from ..layer_factory import slot_bridge
from ..production_line import check_jump, product_exit
from ..production_stage import build_stage
from ..quarter_gather import QUADRANTS
from ..slot_streams import SLOT_ROWS, SlotStreams
from ..stock_selector import SOURCES
from ..work_lane import A_X
from .changeover import controls
from .recipe import BASE, CRYSTAL, MAX_STAGES, Production

STAGE_PITCH = 18
SHAPE_ROWS = {cargo: y for cargo, (y, _) in zip('CRSW', SOURCES)}
PRIMARY_ROWS = (28, 29, 30, 31)


@dataclass(frozen=True)
class CargoPort:
    station: str
    wagon: int
    kind: str
    layer: int
    cargo: str
    rows: tuple[int, ...]


def cargo_ports() -> tuple[CargoPort, ...]:
    ports = []
    for group, quadrant in enumerate(QUADRANTS):
        for wagon, (kind, layers) in enumerate(CARS, 1):
            for layer, cargo in enumerate(layers):
                if cargo is None:
                    continue
                rows = PRIMARY_ROWS if kind == 'Fluids' else (SHAPE_ROWS[cargo],)
                ports.append(CargoPort(f'q{quadrant}', 3 * group + wagon, kind, layer, cargo, rows))
    for layer, cargo in enumerate(CARS[2][1]):
        ports.append(CargoPort('crystal', 1, 'Fluids', layer, cargo, PRIMARY_ROWS))
    return tuple(ports)


def _check_footprints(islands: list[dict]) -> None:
    occupied = set()
    for obj in islands:
        x, y, z = (obj.get(axis, 0) for axis in ('X', 'Y', 'Z'))
        if obj['T'] == 'Foundation_3x3':
            offsets = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        elif obj['T'].startswith(('Layout_TrainLoader_', 'Layout_TrainUnloader_')):
            offsets = [(0, 0), (1 if obj['T'].endswith('_Flipped') else -1, 0)]
        else:
            offsets = [(0, 0)]
        for a, b in offsets:
            tile = x + a, y + b, z
            if tile in occupied:
                raise ValueError(f'六槽装配的区块相交 {tile}')
            occupied.add(tile)


def crystal_loading(cargo: str) -> dict:
    port = next((p for p in cargo_ports() if p.station == 'crystal' and p.cargo == cargo), None)
    if port is None:
        raise ValueError(f'结晶车原料须为 r、g 或 b，收到 {cargo!r}')
    lane = SlotStreams()
    lift = ('PipeForward', 'PipeUpForward', 'Pipe2UpForward')[port.layer]
    for row in port.rows:
        lane.put('FluidPortReceiver', -18, row, config='AA==')
        lane.straight(-17, 0, row, pipe=True)
        lane.put(lift, 0, row)
        lane.straight(1, 37, row, port.layer, pipe=True)
        lane.put('FluidPortSender', 37, row, port.layer, config='KAAAAAA=')
    islands = [lane.finish()]
    for x, kind in ((-3, 'Unloader_Fluids_Flipped'), (3, 'Loader_Fluids')):
        islands.extend(({'T': 'Layout_TrainWaitStation', 'X': x, 'Y': 0, 'R': 3},
                        {'T': 'Layout_Train' + kind, 'X': x, 'Y': 1, 'R': 3}))
    _check_footprints(islands)
    return {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': islands}}


def assemble(count: int, *, packet_tag: int,
             fixed_orders: tuple[Production, ...] | None = None) -> tuple[dict, dict]:
    if type(count) is not int or not 1 <= count <= MAX_STAGES:
        raise ValueError(f'工段数须在 1 至 {MAX_STAGES} 之间')
    base_stages = crystal_stages = range(count)
    if fixed_orders is not None:
        if not fixed_orders or any(len(order.stages) > count for order in fixed_orders):
            raise ValueError('精简工道需要至少一份已回放且不超过工段容量的固定配方')
        base_stages = {s.index for order in fixed_orders for s in order.stages if s.opcode == BASE}
        crystal_stages = {s.index for order in fixed_orders for s in order.stages if s.opcode == CRYSTAL}
    islands = []
    stations = []
    bridge = slot_bridge()
    previous = None
    for index in range(count):
        x = STAGE_PITCH * index
        base, crystal = index in base_stages, index in crystal_stages
        if base:
            stage = freight_stage(index, machine_dyes=crystal, stream=True)['BP']['Entries']
        else:
            stage = build_stage(index, stream=True)['BP']['Entries']
            take, receive, work = stage[:3]
            for row in SLOT_ROWS:
                check_jump(take, receive, row, 0)
            for level in (0, 1):
                check_jump(take, work, A_X, 1, level)
            if crystal:
                add_machine_dyes(stage)
        for obj in stage:
            obj['X'] = obj.get('X', 0) + x
        take, receive = stage[:2]
        if previous is not None:
            for offset in range(previous['X'] + 3, x, 3):
                relay = dict(bridge, X=offset)
                for row in SLOT_ROWS:
                    check_jump(previous, relay, row, 0)
                islands.append(relay)
                previous = relay
            for row in SLOT_ROWS:
                check_jump(previous, take, row, 0)
        islands.extend(stage)
        previous = receive
        station = {'stage': index}
        if base:
            station['base_head'] = x - 12, -17
        if crystal:
            station['crystal_head'] = x - 9, 3
        stations.append(station)
    assert previous is not None
    outlet = product_exit()
    outlet['X'] = previous['X'] + 3
    for row in SLOT_ROWS:
        check_jump(previous, outlet, row, 0)
    islands.append(outlet)
    islands.extend(controls(count, packet_tag))
    _check_footprints(islands)
    document = {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': islands}}
    return document, {'stations': stations, 'load': [asdict(port) for port in cargo_ports()],
                      'output': {'platform': (outlet['X'], 0, 0), 'east_y': SLOT_ROWS[-1], 'level': 0}}
