"""将基础料车卸货与四角选料合到同一排平台。"""

from ..assembled_stage import assembled_stage
from ..freight_stage import CARS, approach_tracks
from ..layer_supply import STOCK_CHANNEL, ordering
from ..production_line import check_jump
from ..production_stage import build_stage
from ..quarter_gather import QUADRANTS
from ..slot_stream_ports import trace, transport_paths
from ..slot_streams import SLOT_ROWS, SlotStreams
from ..stock_selector import SOURCES, stock_selector
from ..work_lane import A_X
from .crystal_feed import dye_intake


HEAD = (-9, -17)
_Q0_GROUP = QUADRANTS.index(0)
PLAIN_WAGONS = (3 * _Q0_GROUP + 1, 3 * _Q0_GROUP + 2)


def build_base_stage(index: int) -> list[dict]:
    islands = assembled_stage(index, stream=True)['BP']['Entries']
    boards = {(e.get('X', 0), e.get('Y', 0)): e for e in islands if not e.get('Z', 0) and 'B' in e}
    pipes = dye_intake(corner=True)['B']['Entries']
    station_x, station_y = HEAD
    islands.append({'T': 'Layout_TrainWaitStation', 'X': station_x, 'Y': station_y, 'R': 3})
    for i in range(len(QUADRANTS)):
        y = station_y + 2 + 3 * i
        selector = boards[station_x + 3, y]
        prep = boards[station_x + 6, y]
        lane = SlotStreams()
        stock = [e for e in selector['B']['Entries'] if not e['T'].startswith(('FluidPort', 'Pipe'))]
        for entry in (*stock, *pipes):
            kind, _, mirrored = entry['T'].partition('InternalVariant')
            lane.put(kind, entry['X'], entry['Y'], entry['L'], entry['R'], mirrored=bool(mirrored),
                     config=entry.get('C'))
        selector['B']['Entries'] = lane.entries
        check_jump(selector, prep, 9, 0)
        for row in (-12, -11, -10, -9, 8, 9, 10, 11):
            check_jump(selector, prep, row, 0, 1 if row == 11 else 2, fluid=True)
        for j, (kind, _) in enumerate(CARS):
            islands.append({'T': 'Layout_TrainUnloader_' + kind + '_Flipped', 'X': station_x,
                            'Y': y + j - 1, 'R': 3})
    islands.extend(dict(track, X=track['X'] + 3) for track in approach_tracks(machine_dyes=False))
    return islands


def build_plain_base_stage(index: int) -> list[dict]:
    islands = build_stage(index, north_base=True, stream=True)['BP']['Entries']
    take, receive, work = islands[:3]
    for row in SLOT_ROWS:
        check_jump(take, receive, row, 0)
    for level in (0, 1):
        check_jump(take, work, A_X, 1, level)

    station_x, station_y = HEAD
    y = station_y + 2 + 3 * _Q0_GROUP
    stock_channel = STOCK_CHANNEL + 8 * index
    selector = stock_selector(stock_channel)
    selector.update(X=station_x + 3, Y=y)
    selector['B']['Entries'] = [e for e in selector['B']['Entries'] if not e['T'].startswith(('FluidPort', 'Pipe'))]
    control = ordering(1_600_076 + 32 * index, 0, stock_channel, stock_channel + 1)
    control.update(X=selector['X'], Y=y, Z=1)
    islands.extend((selector, control))
    for row, level in SOURCES:
        trace(transport_paths(selector), (-17, row, level, 2), {(37, 9, 0, 2)}, set())

    previous = selector
    for x in (-3, 0, 3):
        lane = SlotStreams()
        lane.put('BeltPortReceiver', -18, 9, config='AA==')
        end = 30 if x == 3 else 37
        lane.straight(-17, end, 9)
        if x == 3:
            lane.put('BeltDefaultLeft', end, 9, mirrored=True)
            for yy in range(10, 37):
                lane.put('BeltDefaultForward', end, yy, rotation=1)
            lane.put('BeltPortSender', end, 37, rotation=1, config='KAAAAAA=')
            exit_port = (end, 37, 0, 3)
        else:
            lane.put('BeltPortSender', end, 9, config='KAAAAAA=')
            exit_port = (end, 9, 0, 2)
        island = lane.finish()
        island.update(X=x, Y=y)
        trace(transport_paths(island), (-17, 9, 0, 2), {exit_port}, set())
        check_jump(previous, island, 9, 0)
        islands.append(island)
        previous = island
    lane = SlotStreams()
    lane.put('BeltPortReceiver', 30, -18, rotation=1, config='AA==')
    for yy in range(-17, 37):
        lane.put('BeltDefaultForward', 30, yy, rotation=1)
    lane.put('BeltPortSender', 30, 37, rotation=1, config='KAAAAAA=')
    final = lane.finish()
    final.update(X=3, Y=y + 3)
    trace(transport_paths(final), (30, -17, 0, 3), {(30, 37, 0, 3)}, set())
    check_jump(previous, final, 30, 1)
    check_jump(final, receive, 30, 1)
    islands.append(final)

    islands.append({'T': 'Layout_TrainWaitStation', 'X': station_x, 'Y': station_y, 'R': 3})
    for wagon, (kind, _) in enumerate(CARS * len(QUADRANTS), 1):
        if wagon in PLAIN_WAGONS:
            station = 'Layout_TrainUnloader_Shapes_Flipped'
        else:
            spacer = 'Shape' if kind == 'Shapes' else 'Fluid'
            station = 'Layout_TrainSpacerStraight' + spacer
        islands.append({'T': station, 'X': station_x, 'Y': station_y + wagon, 'R': 3})
    islands.extend(dict(track, X=track['X'] + 3) for track in approach_tracks(machine_dyes=False))
    return islands
