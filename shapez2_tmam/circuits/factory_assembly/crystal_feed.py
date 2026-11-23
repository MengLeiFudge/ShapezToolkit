"""把混合车卸货和染料管路合装到加工台西侧。"""

from ..freight_stage import approach_tracks
from ..production_line import check_jump
from ..slot_streams import SlotStreams
from ..wagon_intake import intake


HEAD = (-6, 3)
_ROUTES = ((2, (-12, -11, -10, -9)), (1, (8, 9, 10)))


def dye_intake(*, corner: bool = False) -> dict:
    feed = intake(dyes_only=True)
    pipework = feed['B']['Entries']
    # 染料已在西边混好。从东边的七条出料管直接转向加工台对应行。
    cuts = {(28 + i, level): 26 + i for level, rows in _ROUTES for i in range(len(rows))}
    kept = []
    for entry in pipework:
        x, y, level = (entry[axis] for axis in ('X', 'Y', 'L'))
        if (y, level) in cuts and x >= cuts[y, level]:
            continue
        if (y, level) == (31, 1) and x >= 33:
            continue
        if corner:
            if (level == 0 and y == 12 and 6 <= x <= 9) or (x, y, level) == (9, 13, 0):
                continue
        else:
            if level == 0 and (x == 9 and 13 <= y <= 31 or y == 31 and 10 <= x <= 32):
                continue
            if (x, y, level) == (9, 12, 0):
                entry = dict(entry, T='PipeForwardInternalVariant')
        kept.append(entry)

    lane = SlotStreams()
    for level, rows in _ROUTES:
        for i, row in enumerate(rows):
            source, turn = 28 + i, 26 + i
            lane.put('PipeLeft', turn, source, level)
            for y in range(row + 1, source):
                lane.put('PipeForward', turn, y, level, 3)
            lane.put('PipeLeft', turn, row, level, 3, mirrored=True)
            lane.straight(turn + 1, 33, row, level, pipe=True)
            lane.put('PipeUpForward' if level == 1 else 'PipeForward', 33, row, level)
            lane.straight(34, 37, row, 2, pipe=True)
            lane.put('FluidPortSender', 37, row, 2, config='KAAAAAA=')
    if corner:
        # 绕开整片选料的两个常量位，保留南侧的制针红管。
        lane.put('PipeLeft', 6, 12, mirrored=True)
        lane.put('PipeLeft', 6, 13, rotation=1)
        lane.straight(7, 9, 13, pipe=True)
        lane.put('PipeCross', 9, 13)
        lane.put('PipeLeft', 9, 12, rotation=3, mirrored=True)
        lane.put('PipeLeft', 33, 31, 1)
        for y in range(12, 31):
            lane.put('PipeForward', 33, y, 1, 3)
        lane.put('PipeLeft', 33, 11, 1, 3, mirrored=True)
        lane.straight(34, 37, 11, 1, pipe=True)
        lane.put('FluidPortSender', 37, 11, 1, config='KAAAAAA=')
    entries = kept + lane.entries
    if len({(e['X'], e['Y'], e['L']) for e in entries}) != len(entries):
        raise ValueError('卸料台的染料管路重叠')
    feed['B']['Entries'] = entries
    return feed


def add_crystal_feed(stage: list[dict]) -> None:
    feed = dye_intake()
    x, y = HEAD
    feed.update(X=x + 3, Y=y)
    for _, rows in _ROUTES:
        for row in rows:
            check_jump(feed, stage[2], row, 0, 2, fluid=True)
    stage.extend((feed, {'T': 'Layout_TrainWaitStation', 'X': x, 'Y': y, 'R': 3},
                  {'T': 'Layout_TrainUnloader_Fluids_Flipped', 'X': x, 'Y': y + 1, 'R': 3}))
    stage.extend(dict(track, X=track['X'] + 3) for track in approach_tracks(corner_stock=False))
