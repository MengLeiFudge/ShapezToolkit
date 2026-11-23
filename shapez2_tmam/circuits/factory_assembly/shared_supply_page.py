"""接通通用九道页的共用混合车供料。"""

import argparse
import json
from collections import Counter
from fractions import Fraction
from heapq import heappop, heappush
from itertools import count
from pathlib import Path
from random import Random

from ...mari.blueprint import DIRECTIONS
from ..circuit import encode_document
from ..freight_stage import approach_tracks
from ..production_line import check_jump
from ..slot_streams import SLOT_ROWS, SlotStreams
from ..work_lane import COLORS
from .crystal_feed import dye_intake
from .full_belt_sample import _add_reader
from .full_line_pages import _configure, _full_page
from .layout import STAGE_PITCH
from .recipe import MAX_STAGES
from .shared_supply import _base_segment, _bounds, _distribution
from .stage_pages import _document, _islands, _rail_links, _stats


_ROWS = (-12, -11, -10, -9, 8, 9, 10)
_RAW_ROWS = (-12, -11, -10, 8, 28, 29, 30)
_SIZE = 9


def _rotate(x, y, rotation):
    for _ in range(rotation):
        x, y = 19 - y, x
    return x, y


def _port(row, level, direction, sender):
    x, y = _rotate(37 if sender else -18, row, direction)
    return x, y, level, direction


def _position(obj):
    return obj.get('X', 0), obj.get('Y', 0)


def _port_connection(sender, receiver, out, incoming, kind):
    for board, point, side in ((sender, out, 'Sender'), (receiver, incoming, 'Receiver')):
        if not any(e['T'] == kind + 'Port' + side + 'InternalVariant'
                   and (e['X'], e['Y'], e['L'], e['R']) == point for e in board['B']['Entries']):
            raise ValueError(f'{_position(board)} 缺少 {kind} {side} 端口 {point}')
    x, y = _position(sender)
    a, b = _position(receiver)
    dx, dy = DIRECTIONS[out[3]]
    if (20 * (a - x) + incoming[0] - out[0], 20 * (b - y) + incoming[1] - out[1],
            incoming[2], incoming[3]) != (5 * dx, 5 * dy, out[2], out[3]):
        raise ValueError(f'端口 {_position(sender), out} 与 {_position(receiver), incoming} 的带管未对齐')


def _step(x, y, direction, size=1):
    dx, dy = DIRECTIONS[direction]
    return x + size * dx, y + size * dy


def _path(lane, start, finish, reserved, preference=0):
    x, y, z, direction = start
    a, b = _step(x, y, direction)
    initial = (a, b, z, direction)
    goal = (*_step(finish[0], finish[1], (finish[3] + 2) % 4), finish[2], finish[3])
    blocked = lane.occupied | reserved
    if initial[:3] in blocked or goal[:3] in blocked:
        raise ValueError(f'运输接点被占用 {start} → {finish}')
    def distance(state):
        return sum(abs(a - b) for a, b in zip(state[:2], goal[:2])) + int(state[2] != goal[2])
    parent = {initial: None}
    costs = {initial: 0}
    ordering = count()
    queue = [(distance(initial), 0, next(ordering), initial)]
    while queue:
        _, cost, _, state = heappop(queue)
        if cost != costs[state]:
            continue
        x, y, level, entering = state
        if state[:3] == goal[:3] and (entering - goal[3]) % 4 != 2:
            path = [(state, goal[3], level)]
            while parent[state] is not None:
                state, leaving, target = parent[state]
                path.append((state, leaving, target))
            return path[::-1]
        for rotation in (entering, (entering + 1 + 2 * preference) % 4, (entering - 1 - 2 * preference) % 4):
            u, v = _step(x, y, rotation)
            if not (-17 <= u <= 36 and -17 <= v <= 36):
                continue
            levels = (level, *(k for k in range(3) if k != level)) if entering == rotation else (level,)
            for target in levels:
                next_state = (u, v, target, rotation)
                new_cost = cost + 1 + int(rotation != entering) + int(target != level)
                if new_cost >= costs.get(next_state, 10**9) or (u, v, target) in blocked:
                    continue
                if any((x, y, k) in blocked for k in range(min(level, target), max(level, target) + 1)):
                    continue
                parent[next_state] = (state, rotation, target)
                costs[next_state] = new_cost
                heappush(queue, (new_cost + distance(next_state), new_cost, next(ordering), next_state))
    raise ValueError(f'台内运输无法接通 {start} → {finish}')


def _lay(lane, kind, path):
    fluid = kind == 'Fluid'
    for (x, y, level, entering), leaving, target in path:
        if target != level:
            delta = abs(level - target)
            if fluid:
                lane.put('PipeUpForward' if delta == 1 else 'Pipe2UpForward', x, y, min(level, target),
                         leaving if level < target else (leaving + 2) % 4)
            else:
                lane.put(f'Lift{delta}{"Up" if target > level else "Down"}Forward', x, y, level, leaving)
        elif entering == leaving:
            lane.put('PipeForward' if fluid else 'BeltDefaultForward', x, y, level, leaving)
        else:
            lane.put('PipeLeft' if fluid else 'BeltDefaultLeft', x, y, level, entering,
                     mirrored=(leaving - entering) % 4 == 1)


def _adapter(routes, x, y):
    # 端口内侧各留一格，避免先铺的线路占用后铺线路的入口。
    def reserve(port, sender):
        return (*_step(*port[:2], (port[3] + (2 if sender else 0)) % 4), port[2])
    triggers = [(reserve(start, False), reserve(end, True)) for _, start, end in routes]
    ends = {point for pair in triggers for point in pair}
    base = SlotStreams()
    for kind, start, end in routes:
        base.put(kind + 'PortReceiver', *start, config='AA==')
        base.put(kind + 'PortSender', *end, config='KAAAAAA=')
    right = sorted(range(len(routes)), key=lambda i: (routes[i][2][3], routes[i][2][2], routes[i][2][1]))
    nearest = sorted(range(len(routes)), key=lambda i: sum(abs(a - b) for a, b in zip(*triggers[i])))
    rng = Random(931)
    extra = [rng.sample(range(len(routes)), len(routes)) for _ in range(36)] if len(routes) > 7 else []
    preferences = (right, right[::-1], nearest, nearest[::-1], list(range(len(routes))), *extra)
    for preference in (0, 1):
        for order in preferences:
            lane = SlotStreams()
            lane.entries = base.entries.copy()
            lane.occupied = base.occupied.copy()
            try:
                for i in order:
                    kind, start, end = routes[i]
                    _lay(lane, kind, _path(lane, start, end, ends - set(triggers[i]), preference))
                return dict(lane.finish(), X=x, Y=y)
            except ValueError as error:
                last = error
    raise ValueError(f'换向台 {(x, y)} {last}')


def _route_bundle(start, end, start_direction, end_direction, level, blocked, reserved, span, weight):
    first = (*_step(*start, start_direction, 3), start_direction, level)
    last = _step(*end, (end_direction + 2) % 4, 3)
    if first[:2] == end and start_direction == end_direction:
        return []
    serial = count()
    queue = [(0, 0, next(serial), first)]
    parents = {first: None}
    costs = {first: 0}
    while queue:
        _, cost, _, state = heappop(queue)
        if cost != costs[state]:
            continue
        x, y, entering, current = state
        if (x,y,current) in reserved or (x,y) in blocked:
            continue
        if (x,y) == last and (entering-end_direction) % 4 != 2:
            steps = [(*state, end_direction, current)]
            while parents[state] is not None:
                old = state
                state = parents[state]
                steps.append((*state, old[2], old[3]))
            if len(_cells(steps)) == sum(abs(floor-target)+1 for _,_,_,floor,_,target in steps):
                return steps[::-1]
        for leaving in (entering, (entering + 1) % 4, (entering + 3) % 4):
            a,b = _step(x,y,leaving,3)
            if not (span[0] <= a <= span[1] and -120 <= b <= 54) or (a,b) in blocked:
                continue
            levels = range(3) if leaving == entering else (current,)
            for target in levels:
                candidate = a,b,leaving,target
                if (a,b,target) in reserved:
                    continue
                here = [(x,y,z) for z in range(min(current,target),max(current,target)+1)]
                if any(p in reserved for p in here):
                    continue
                new = cost + 3 + (leaving != entering) + 4*(target != current) + sum(weight(p) for p in here)
                if new >= costs.get(candidate, 10**9):
                    continue
                costs[candidate] = new
                parents[candidate] = state
                estimate = abs(a-last[0]) + abs(b-last[1])
                heappush(queue,(new+estimate,new,next(serial),candidate))
    raise ValueError(f'跨岛束 {start} → {end} 未接通')


def _cells(steps):
    return {(x,y,z) for x,y,_,floor,_,target in steps
            for z in range(min(floor,target),max(floor,target)+1)}


def _rows(kinds):
    return _RAW_ROWS if kinds[0] == 'Belt' else _ROWS


def _relay(kinds, level, entering, leaving, x, y):
    lane = SlotStreams()
    for row, kind in zip(_rows(kinds), kinds, strict=True):
        start = _port(row, level, entering, False)
        end = _port(row, level, leaving, True)
        lane.put(kind + 'PortReceiver', *start, config='AA==')
        lane.put(kind + 'PortSender', *end, config='KAAAAAA=')
        position = _step(*start[:2], entering)
        last = _step(*end[:2], (leaving + 2) % 4)
        dx, dy = DIRECTIONS[entering]
        turn = (last[0], position[1]) if dx else (position[0], last[1])
        direction = entering
        path = []
        while position != last:
            if position == turn:
                path.append(((*position, level, entering), leaving, level))
                direction = leaving
            else:
                path.append(((*position, level, direction), direction, level))
            position = _step(*position, direction)
        path.append(((*last, level, leaving), leaving, level))
        _lay(lane, kind, path)
    return dict(lane.finish(), X=x, Y=y)


def _occupied(entries):
    result = set()
    for obj in entries:
        if obj.get('Z', 0):
            continue
        x, y = _position(obj)
        if obj['T'] == 'Foundation_3x3':
            result.update((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        else:
            result.add((x, y))
            if obj['T'].startswith('Layout_TrainUnloader_'):
                result.add((x+1, y))
    return result


def _cleanout(entries, start, page):
    islands = _islands(_document(entries))
    returned = []
    for address in range(start, start + _SIZE):
        x = address * STAGE_PITCH
        base = islands[x+3, -3, 0]
        work = islands[x, 3, 0]
        returned.append({'stage': address, 'base': _add_reader(base, (30,34,0), 1),
                         'work': _add_reader(work, (34,30,0), 0),
                         'stack': page['stack'][address]['readers']})
    outlet = islands[page['output']['island']]
    return {'reset_phase': 3, 'reset_min_signal_ticks': 128,
            'fixed_cargo_may_remain': True, 'returns': returned,
            'slot_exit': [_add_reader(outlet, (34,row,0), 0) for row in SLOT_ROWS]}


def _branches(entries, requests):
    occupied = _occupied(entries)
    low = min(x for x, _ in occupied) // 3 * 3 - 30
    high = max(x for x, _ in occupied) // 3 * 3 + 30
    blocked = {(x,y) for x in range(low,high+1,3) for y in range(-120,55,3)
               if any((x+dx,y+dy) in occupied for dx in (-1,0,1) for dy in (-1,0,1))}
    positions = [(_position(start), _position(end), first, last, level)
                 for start,end,first,last,level,_,_ in requests]
    ends = [{(*_step(*a, first, 3), z)} for a,_,first,_,z in positions]
    reserved = set().union(*ends)
    order = sorted(range(len(requests)), key=lambda i: sum(abs(a-b) for a,b in zip(*positions[i][:2])), reverse=True)
    usage, history = Counter(), Counter()
    plan = {}
    for attempt in range(32):
        if attempt:
            reroute = [i for i in order if any(usage[p] > 1 for p in _cells(plan[i]))]
        else:
            reroute = order
        penalty = 18 + attempt * 4
        def weight(p):
            return penalty * usage[p] + history[p]
        for i in reroute:
            usage.subtract(_cells(plan.get(i, ())))
            a,b,first,last,level = positions[i]
            steps = _route_bundle(a,b,first,last,level,blocked,reserved - ends[i],(low,high),weight)
            plan[i] = steps
            usage.update(_cells(steps))
        conflicts = [p for p,n in usage.items() if n > 1]
        if not conflicts:
            break
        for p in conflicts:
            history[p] += 6
    else:
        raise ValueError(f'共用供料还有 {len(conflicts)} 个重叠的跨岛接点')
    planes, paths = {}, []
    for i, (start,end,first,last,level,kinds,sinks) in enumerate(requests):
        steps = plan[i]
        previous, facing, floor = start, first, level
        for x,y,entering,floor,leaving,target in steps:
            if floor == target:
                board = _relay(kinds, floor, entering, leaving, x, y)
            else:
                board = _adapter([(kind, _port(row, floor, entering, False), _port(row, target, leaving, True))
                                  for row, kind in zip(_rows(kinds),kinds,strict=True)], x, y)
            for row, kind in zip(_rows(kinds), kinds, strict=True):
                _port_connection(previous, board, _port(row, floor, facing, True), _port(row, floor, entering, False), kind)
            if (x,y) in planes:
                planes[x,y]['B']['Entries'].extend(board['B']['Entries'])
            else:
                planes[x,y] = board
            previous, facing = board, leaving
        arrival = steps[-1][-1] if steps else level
        if arrival != level:
            replacement = _adapter([(kind, _port(row, arrival, last, False), sink)
                                    for row,kind,sink in zip(_rows(kinds),kinds,sinks,strict=True)], *_position(end))
            end['B'] = replacement['B']
        for row, kind in zip(_rows(kinds), kinds, strict=True):
            _port_connection(previous, end, _port(row, arrival, facing, True), _port(row, arrival, last, False), kind)
        paths.append([(*_position(start), level), *((x,y,floor) for x,y,_,floor,_,_ in steps), (*_position(end), arrival)])
    entries.extend(planes.values())
    return paths


def _move(entries, x, y):
    return [dict(e, X=e.get('X',0) + x, Y=e.get('Y',0) + y) for e in entries]


def _raw_selector(board):
    # 每色只接一条固定原色管，在原四条用途支路之前分流。
    entries = []
    for e in board['B']['Entries']:
        x,y,z,r = (e[k] for k in ('X','Y','L','R'))
        if e['T'] == 'FluidPortReceiverInternalVariant' and x == -18 and 29 <= y <= 31:
            continue
        if e['T'] == 'PipeForwardInternalVariant' and x == -17 and 28 <= y <= 31 and r == 0:
            entries.append(dict(e, T='PipeCrossInternalVariant'))
        else:
            entries.append(e)
    board['B'] = dict(board['B'], Entries=entries)


_RAW_KINDS = ('Belt',) * 4 + ('Fluid',) * 3
_DYE_KINDS = ('Fluid',) * 7


def _feed_request(start, end, direction, level, kinds, sinks=None):
    if sinks is None:
        sinks = [_port(row,level,0,True) for row in _rows(kinds)]
    return start, end, direction, 0, level, kinds, sinks


def _base_groups(entries, start, rate, headway):
    requests, stations, channels = [], [], []
    selectors = _islands(_document(entries))
    templates = {}
    def made(routes, x, y):
        key = tuple(routes)
        if key not in templates:
            templates[key] = _adapter(routes, x, y)
        return dict(templates[key], X=x, Y=y)
    for i in (0, 4, 8):
        count = min(4, _SIZE - i)
        raw, station = _base_segment(start + i, rate, headway)
        dx = STAGE_PITCH * (start + i) - 18
        dy = -33
        moved = _move(raw, dx, dy)
        entries.extend(moved)
        head_x, head_y, _ = station['head']
        head = (head_x + dx, head_y + dy)
        stations.append({'first': start + i, 'count': count, 'head': (*head, 0)})
        for g in range(4):
            raw_y = head_y + 2 + 3*g
            x, y = head[0] + 3, raw_y + dy
            old = next(e for e in moved if _position(e) == (x, y))
            raw_lanes, lane_sets = [], []
            for j in range(count):
                address = start + i + j
                x_at = address * STAGE_PITCH
                row_at = raw_y
                selector = selectors[x_at - 6, row_at, 0]
                _raw_selector(selector)
                direction = 0 if j == 0 else 1
                floor = j % 3
                raw_outlets = [o for o in station['outlets'] if o['address'] == address and o['island'][1] == raw_y]
                assert len(raw_outlets) == 7
                target_x = x_at - 9
                outputs = [o['outlet'][1:] if o['unit'] == 'item' else (28, o['outlet'][2]) for o in raw_outlets]
                # 图形入口使用原四个固定货层行，卸货行只是本组支路编号。
                outputs = [(row - j if k < 4 else row, level) for k, (row, level) in enumerate(outputs)]
                raw_lanes.append([(kind, (-18, o['outlet'][1], o['outlet'][2], 0), _port(row, floor, direction, True))
                                  for kind, o, row in zip(_RAW_KINDS, raw_outlets, _RAW_ROWS, strict=True)])
                receiver = made([(kind, _port(row, floor, 0, False), _port(target, level, 0, True))
                                     for kind, row, (target,level) in zip(_RAW_KINDS, _RAW_ROWS, outputs, strict=True)],
                                    target_x, row_at)
                entries.append(receiver)
                for kind, (target, level) in zip(_RAW_KINDS, outputs, strict=True):
                    check_jump(receiver, selector, target, 0, level, fluid=kind == 'Fluid')
                lane_sets.append((receiver, direction, floor, [_port(row,z,0,True) for row,z in outputs]))
                channels.append({'stage': address, 'quadrant': raw_outlets[0]['quadrant'],
                                 'raw': (x,y,0), 'selector': (x_at-6,row_at,0), 'receiver': (target_x,row_at,0),
                                 'ports': [{'cargo': o['cargo'], 'wagon': o['wagon'], 'unload': o['inlet'],
                                            'selector_inlet': (-18,row,level), 'required_per_second': o['max_per_second']}
                                           for o, (row,level) in zip(raw_outlets, outputs, strict=True)]})
            # 每台剥离一地址，其余卸货行同层直通下一台。各象限逐行错开。
            ahead = 1 if count == 1 else 1 + (count + 1) * (3 - g)
            previous = old
            for step in range(1, ahead):
                relay = dict(old, X=x + 3*step)
                entries.append(relay)
                previous = relay
            for step, j in enumerate(reversed(range(count)), ahead):
                routes = [(kind, port, end if k == j else (37, port[1], port[2], 0))
                          for k, lanes in enumerate(raw_lanes[:j+1]) for kind, port, end in lanes]
                split = made(routes, x + 3*step, y)
                for kind, port, _ in routes:
                    check_jump(previous, split, port[1], 0, port[2], fluid=kind == 'Fluid')
                entries.append(split)
                previous = split
                receiver, direction, floor, sinks = lane_sets[j]
                requests.append(_feed_request(split, receiver, direction, floor, _RAW_KINDS, sinks))
            channels[-count:] = list(reversed(channels[-count:]))
    return requests, stations, channels


def _crystal_groups(entries, start):
    stations, requests, channels = [], [], []
    for i in (0, 2, 4, 6, 8):
        count = min(2, _SIZE - i)
        x = (start + i) * STAGE_PITCH - 9
        y = 15
        feed = dict(_distribution() if count == 2 else dye_intake(), X=x, Y=y)
        head = x - 3, y
        entries += [feed, {'T':'Layout_TrainWaitStation', 'X':head[0], 'Y':y,'R':3},
                    {'T':'Layout_TrainUnloader_Fluids_Flipped', 'X':head[0], 'Y':y+1,'R':3}]
        entries += _move(approach_tracks(corner_stock=False), x+6, y-3)
        stations.append({'first': start+i, 'count': count, 'head': (*head, 0)})
        for j in range(count):
            address = start + i + j
            x_at = STAGE_PITCH * address
            work = next(e for e in entries if _position(e) == (x_at,3) and e.get('Z',0) == 0)
            adapter = _relay(_DYE_KINDS, 2, 0, 0, x_at-3,3)
            entries.append(adapter)
            for row in _ROWS:
                check_jump(adapter, work, row, 0, 2, fluid=True)
            requests.append(_feed_request(feed, adapter, 0 if j == 0 else 3, 2, _DYE_KINDS))
            channels.append({'stage': address, 'feed': (x,y,0), 'adapter': (x_at-3,3,0),
                             'work': (x_at,3,0), 'colors_by_row': dict(zip(_ROWS, COLORS, strict=True))})
    return requests, stations, channels


def _strip_stations(document, page):
    remove = set()
    for rail in page['rails']:
        x,y = rail['head']
        base = rail['service'] == 'base'
        count = 12 if base else 1
        remove.update((x,y+i) for i in range(count+1))
        tracks = approach_tracks(machine_dyes=not base, corner_stock=base)
        remove.update(_position(e) for e in _move(tracks, x + (12 if base else 9), 0))
        if not base:
            remove.add((x+3,y))
    return [e for e in document['BP']['Entries'] if e.get('Z',0) or _position(e) not in remove]


def build(start, belt_rate, unload_belt, pipe_rate, headway):
    if (not 0 <= start <= MAX_STAGES - _SIZE or min(belt_rate, unload_belt, headway) <= 0
            or pipe_rate is not None and pipe_rate <= 0):
        raise ValueError('需要连续九道地址，带速、管速和到站间隔须为正数')
    _, _, all_stations = _configure(start + _SIZE, None, True)
    baseline, page = _full_page(all_stations[start:], terminal=False, universal=True)
    baseline_stats = _stats(baseline)
    entries = _strip_stations(baseline, page)
    base_requests, base_stops, base_ports = _base_groups(entries, start, belt_rate, headway)
    crystal_requests, crystal_stops, crystal_ports = _crystal_groups(entries, start)
    routes = _branches(entries, base_requests + crystal_requests)
    changeover = _cleanout(entries, start, page)
    document = _document(entries)
    stats = _stats(document)
    islands = _islands(document)
    for service, stops in (('base',base_stops), ('crystal',crystal_stops)):
        for stop in stops:
            stop['rails'] = _rail_links(islands, stop['head'][:2], service)
    report = {'window': (start, start + _SIZE), 'six_slots': {'input': page['input'], 'output': page['output']},
              'baseline': baseline_stats, 'shared': stats, 'delta': {k: stats[k] - n for k,n in baseline_stats.items()},
              'base_stops': base_stops, 'crystal_stops': crystal_stops,
              'base_contacts': [{**port, 'route': path} for port,path in zip(base_ports, routes[:len(base_ports)], strict=True)],
              'crystal_contacts': [{**port, 'route': path} for port,path in zip(crystal_ports,routes[len(base_ports):],strict=True)],
              'stack': page['stack'], 'belt_items_per_second': str(belt_rate),
              'unload_belt_items_per_second': str(unload_belt),
              'shared_pipe_liters_per_second': None if pipe_rate is None else str(pipe_rate),
              'headway_seconds': str(headway), 'capacity': _bounds(belt_rate,unload_belt,pipe_rate,headway),
              'capacity_checks': {'base_item_each_belt_per_second': str(belt_rate),
                                  'base_item_full_wagon_layer_per_second': str(4*belt_rate),
                                  'base_pin_each_pipe_liters_per_second': str(20*belt_rate),
                                  'base_paint_each_pipe_liters_per_second': str(10*belt_rate),
                                  'single_crystal_branch_liters_per_second': str(20*belt_rate),
                                  'paired_crystal_shared_pipe_liters_per_second': str(40*belt_rate),
                                  'base_belt_rate_meets_target': unload_belt >= belt_rate,
                                  'paired_crystal_pipe_rate_meets_target': None if pipe_rate is None else
                                  pipe_rate >= 40*belt_rate},
              'changeover': changeover}
    return document, report


def main():
    parser = argparse.ArgumentParser(description='导出接完共用混合车供料的通用九道页')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--belt-rate', type=Fraction, default=Fraction(2))
    parser.add_argument('--unload-belt', type=Fraction, default=Fraction(2))
    parser.add_argument('--pipe-rate', type=Fraction)
    parser.add_argument('--headway', type=Fraction, default=Fraction(60))
    args = parser.parse_args()
    try:
        if args.output.suffix != '.spz2bp':
            raise ValueError('--output 需要 .spz2bp 路径')
        document, report = build(args.start,args.belt_rate,args.unload_belt,args.pipe_rate,args.headway)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encode_document(document)+'\n',encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    except (OSError,ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
