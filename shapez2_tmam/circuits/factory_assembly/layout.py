"""装配六槽通用工段，并给制作和配料提供同一张车厢端口表。"""

from dataclasses import asdict, dataclass

from ...synthesis.direct_recipe import direct_recipe_length, direct_recipe_opcode
from ..freight_stage import CARS, add_machine_dyes, freight_stage
from ..layer_factory import slot_bridge
from ..production_line import check_jump, product_exit
from ..production_stage import build_stage
from ..quarter_gather import QUADRANTS
from ..slot_stream_ports import trace, transport_paths
from ..slot_streams import SLOT_ROWS, SlotStreams
from ..stock_selector import SOURCES
from ..work_lane import A_X, OUT_X
from .changeover import controls
from .interface import recipe_interface
from .recipe import BASE, CRYSTAL, MAX_STAGES, Production

STAGE_PITCH = 18
SHAPE_ROWS = {cargo: y for cargo, (y, _) in zip('CRSW', SOURCES)}
PRIMARY_ROWS = (28, 29, 30, 31)
DIRECT_STACK_STAGES = direct_recipe_length(5)


@dataclass(frozen=True)
class CargoPort:
    station: str
    wagon: int
    kind: str
    layer: int
    cargo: str
    rows: tuple[int, ...]


def cargo_ports(*, machine_dyes: bool = True) -> tuple[CargoPort, ...]:
    ports = []
    for group, quadrant in enumerate(QUADRANTS):
        for wagon, (kind, layers) in enumerate(CARS, 1):
            for layer, cargo in enumerate(layers):
                if cargo is None:
                    continue
                rows = PRIMARY_ROWS if kind == 'Fluids' else (SHAPE_ROWS[cargo],)
                ports.append(CargoPort(f'q{quadrant}', 3 * group + wagon, kind, layer, cargo, rows))
    if machine_dyes:
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


def _stack_lane() -> dict:
    lane = SlotStreams()
    groups = (-9, 24)
    rows = tuple(center + dy for center in groups for dy in (-6, 0, 6))
    branch_x, split_x, machine_x = A_X - 3, A_X + 3, 10
    for level in (0, 1):
        lane.put('BeltPortReceiver', A_X, -18, level, 1, config='AA==')
        lane.put('Splitter1To2L', A_X, -17, level, 1, mirrored=True)
        for x in range(branch_x + 1, A_X):
            lane.put('BeltDefaultForward', x, -17, level, 2)
        lane.put('BeltDefaultLeft', branch_x, -17, level, 2)
        for x, start, center in ((A_X, -16, groups[0]), (branch_x, -16, groups[1])):
            for y in range(start, center):
                lane.put('BeltDefaultForward', x, y, level, 1)
            lane.put('BeltDefaultLeft', x, center, level, 1)
            lane.straight(x + 1, split_x, center, level)
            lane.put('Splitter1To3', split_x, center, level)
            for dy, rotation in ((-1, 3), (1, 1)):
                for step in range(1, 6):
                    lane.put('BeltDefaultForward', split_x, center + dy * step, level, rotation)
                lane.put('BeltDefaultLeft', split_x, center + dy * 6, level, rotation, mirrored=dy < 0)
    for row in rows:
        for level in (0, 1):
            lane.straight(split_x + 1, machine_x, row, level)
        lane.put('StackerStraight', machine_x, row)
        lane.straight(machine_x + 1, OUT_X, row)
    lane.put('BeltDefaultLeft', OUT_X, rows[0], mirrored=True)
    for y in range(rows[0] + 1, rows[-1]):
        if y in rows:
            lane.put('Merger2To1L', OUT_X, y, rotation=1, mirrored=True)
        else:
            lane.put('BeltDefaultForward', OUT_X, y, rotation=1)
    lane.put('Merger2To1L', OUT_X, rows[-1])
    lane.straight(OUT_X + 1, 37, rows[-1])
    lane.put('BeltPortSender', 37, 30, config='KAAAAAA=')
    island = lane.finish()
    island['Y'] = 3
    paths = transport_paths(island)
    for level in (0, 1):
        start = (A_X, -17, level, 3)
        for center, direction in zip(groups, (1, 2)):
            paths[start] = ((A_X, -17, level, direction),)
            for dy, outlet in ((-6, 3), (0, 0), (6, 1)):
                paths[split_x, center, level, 2] = ((split_x, center, level, outlet),)
                trace(paths, start, {(machine_x, center + dy, level, 2)}, set())
    for row in rows:
        trace(paths, (machine_x + 1, row, 0, 2), {(37, rows[-1], 0, 2)}, set())
    return island


def assemble(count: int, *, packet_tag: int,
             fixed_orders: tuple[Production, ...] | None = None, handoff: bool = False) -> tuple[dict, dict]:
    if type(count) is not int or not 1 <= count <= MAX_STAGES:
        raise ValueError(f'工段数须在 1 至 {MAX_STAGES} 之间')
    base_stages = crystal_stages = range(count)
    if fixed_orders is not None:
        if not fixed_orders or any(len(order.stages) > count for order in fixed_orders):
            raise ValueError('精简工道需要至少一份已回放且不超过工段容量的固定配方')
        base_stages = {s.index for order in fixed_orders for s in order.stages if s.opcode == BASE}
        crystal_stages = {s.index for order in fixed_orders for s in order.stages if s.opcode == CRYSTAL}
    return _assemble(count, packet_tag, base_stages, crystal_stages, handoff=handoff)


def assemble_direct_stack(*, packet_tag: int) -> tuple[dict, dict]:
    count = DIRECT_STACK_STAGES
    opcodes = tuple(direct_recipe_opcode(i, count) for i in range(count))
    base_stages = {i for i, opcode in enumerate(opcodes) if opcode == BASE}
    document, interfaces = _assemble(count, packet_tag, base_stages, (), direct_stack=True)
    for station, opcode in zip(interfaces['stations'], opcodes):
        station['opcode'] = opcode
    interfaces['recipe']['supported_lengths'] = [direct_recipe_length(height) for height in range(1, 6)]
    return document, interfaces


def _assemble(count, packet_tag, base_stages, crystal_stages, *, direct_stack=False, handoff=False):
    islands = []
    stations = []
    bridge = slot_bridge()
    previous = None
    for index in range(count):
        x = STAGE_PITCH * index
        base, crystal = index in base_stages, index in crystal_stages
        if base:
            stage = freight_stage(index, machine_dyes=crystal, stream=True)['BP']['Entries']
            if direct_stack:
                # 基础料从北口领入，只保留六槽台、译码、存储和供货路线。
                stage = stage[:2] + stage[3:6] + stage[9:]
        else:
            stage = build_stage(index, stream=True)['BP']['Entries']
            if direct_stack:
                stage[2] = _stack_lane()
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
    islands.extend(controls(count, packet_tag, handoff=handoff))
    _check_footprints(islands)
    document = {'V': 1137, 'BP': {'$type': 'Island', 'BinaryVersion': 1137, 'Entries': islands}}
    return document, {'stations': stations,
                      'load': [asdict(port) for port in cargo_ports(machine_dyes=not direct_stack)],
                      'recipe': recipe_interface(count, packet_tag),
                      'output': {'platform': (outlet['X'], 0, 0), 'east_y': SLOT_ROWS[-1], 'level': 0}}
