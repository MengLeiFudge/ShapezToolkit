"""将基础料车卸货与四角选料合到同一排平台。"""

from ..assembled_stage import assembled_stage
from ..freight_stage import CARS, approach_tracks
from ..production_line import check_jump
from ..quarter_gather import QUADRANTS
from ..slot_streams import SlotStreams
from .crystal_feed import dye_intake


HEAD = (-9, -17)


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
