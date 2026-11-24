"""收紧各行的直线段，保留器件占格和相邻线路的端口关系。"""

from collections import defaultdict
from heapq import heapify, heappop, heappush

from ..mari.blueprint import PORTS, _kind, _rotate
from .export_wiring_review import _building_cells


def compact_axis(entries, axis):
    along, across = ("X", "Y") if axis == 0 else ("Y", "X")
    rows = defaultdict(list)
    straight = defaultdict(dict)
    edges = defaultdict(lambda: ({}, {}))
    parent = list(range(len(entries)))
    lower = {}

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, entry in enumerate(entries):
        kind, turns = _kind(entry), entry["R"]
        if kind == "WireForward" and turns % 2 == axis:
            straight[entry[across], entry["L"]][entry[along]] = entry
            continue
        cells = tuple(_building_cells(entry, kind))
        lower[i] = min(pos[axis] for pos in cells)
        for pos in cells:
            rows[pos[1 - axis], pos[2]].append((pos[axis], i))
        for ports in PORTS[kind]:
            for direction, x, y, z in ports:
                if entry["T"].endswith("Mirrored"):
                    y, direction = -y, -direction % 4
                direction = (direction + turns) % 4
                if direction % 2 == axis:
                    continue
                offset = _rotate(x, y, turns)
                side = int(direction >= 2)
                edge = entry[across] + offset[1 - axis] - side, entry["L"] + z
                edges[edge][side][entry[along] + offset[axis]] = i

    constraints = []
    runs = []
    for row, cells in rows.items():
        cells.sort()
        wires = straight.get(row, {})
        for (a, i), (b, j) in zip(cells, cells[1:]):
            gap = b - a
            if gap == 1:
                parent[root(j)] = root(i)
            elif all(x in wires for x in range(a + 1, b)):
                constraints.append((i, j, gap - 1))
                runs.append((a, b, i, j, wires[a + 1]))
            else:
                constraints.append((i, j, gap - 2))

    # 跨行相接的端口共用位移。相对的空端口则至少错开一格。
    for forward, backward in edges.values():
        if not forward or not backward:
            continue
        for x in forward.keys() & backward.keys():
            parent[root(backward[x])] = root(forward[x])
        ordered = sorted((x, side, i) for side, ports in enumerate((forward, backward)) for x, i in ports.items())
        last = [None, None]
        for x, side, i in ordered:
            other = last[1 - side]
            if other is not None and other[0] < x:
                constraints.append((other[1], i, x - other[0] - 1))
            last[side] = x, i

    limits = {}
    for i, position in lower.items():
        group = root(i)
        limits[group] = min(position, limits.get(group, position))
    if not limits:
        return entries
    left = min(limits.values())
    shifts = {group: left - bound for group, bound in limits.items()}
    links = defaultdict(list)
    for i, j, slack in constraints:
        a, b = root(i), root(j)
        if a != b:
            links[a].append((b, slack))
    pending = [(-shift, group) for group, shift in shifts.items()]
    heapify(pending)
    while pending:
        distance, a = heappop(pending)
        if -distance != shifts[a]:
            continue
        for b, slack in links[a]:
            shift = -distance - slack
            if shift > shifts[b]:
                shifts[b] = shift
                heappush(pending, (-shift, b))

    packed = [{**entries[i], along: entries[i][along] + shifts[root(i)]} for i in lower]
    for a, b, i, j, wire in runs:
        packed.extend({**wire, along: x} for x in range(a + shifts[root(i)] + 1, b + shifts[root(j)]))
    return packed
