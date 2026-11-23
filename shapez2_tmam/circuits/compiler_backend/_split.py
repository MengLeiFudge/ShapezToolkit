"""组合网表在两个同岛层平台之间的有向切分。"""

from collections import defaultdict
from graphlib import TopologicalSorter
from heapq import heapify, heappop, heappush

from ..circuit import Circuit, Ref
from ._layout import (LayoutCapacityError, _EdgeLinks, _GATE_CAPACITY, _RADIO_ROWS, _assemble,
                      _layout_platform, _live_nodes)


# 每个缺口有四行，每行可在三个建筑层放短距口。坐标基准与 _Board 一致。
_EDGE_SLOTS = tuple((start + row, level) for row in (2, 3, 1, 4) for level in range(3)
                    for start in (24, 4, 44))


def layout_two_platforms(circuit: Circuit, outputs: dict[int, Ref], *,
                         retain_inputs: bool = True) -> tuple[dict, int]:
    """把互斥总线的全部驱动放在同一块板上，再从板间单向传递合并后的值。"""
    channels = circuit.channel_map()
    live = _live_nodes(circuit, channels, outputs, retain_inputs=retain_inputs)
    radios = {i for i in live if circuit.gates[i].kind == "ControlledSignalReceiver"}
    if (len(radios) > len(_RADIO_ROWS) or len(outputs) > 2 * len(_RADIO_ROWS)
            or len(live) - len(radios) > 2 * _GATE_CAPACITY):
        raise LayoutCapacityError("组合门网超过相邻两块三层平台的容量")
    owners = {i: i for i in live}
    for group in circuit.aliases:
        if group[0].node in live:
            owners.update((ref.node, group[0].node) for ref in group)
    groups = defaultdict(list)
    inputs = defaultdict(set)
    for i in sorted(live):
        owner = owners[i]
        groups[owner].append(i)
        inputs[owner].update(channels[arg] for arg in circuit.gates[i].inputs if isinstance(arg, Ref))
    providers = {net: owners[ref.node] for ref, net in channels.items() if ref.node in live}
    deps = {owner: {providers[net] for net in inputs[owner]} for owner in groups}
    sorter = TopologicalSorter(deps)
    sorter.prepare()
    ready = list(sorter.get_ready())
    heapify(ready)
    ordered = []
    # 同时就绪的门保持降级顺序，避免把原本相邻的方法体打散。
    while ready:
        owner = heappop(ready)
        if owner not in radios:
            ordered.append(owner)
        sorter.done(owner)
        for next_owner in sorter.get_ready():
            heappush(ready, next_owner)
    if len(ordered) < 2:
        raise LayoutCapacityError("组合网表没有可用的前馈切口")

    cuts = []
    left = set(radios)
    for owner in ordered[:-1]:
        left.update(groups[owner])
        right = live - left
        west_gates = len(left) - len(radios)
        if max(west_gates, len(right)) > _GATE_CAPACITY:
            continue
        nets = sorted({net for i in right for net in inputs[owners[i]] if providers[net] in left})
        if len(nets) <= len(_EDGE_SLOTS):
            # 两板容量相同，用较满一侧的门数估算拥塞，另给跨板线留出布线余量。
            peak_gates = max(west_gates, len(right))
            cuts.append((peak_gates + 10 * len(nets), len(nets), len(left), left.copy(), right, nets))

    last_error = None
    for _, _, _, left, right, nets in sorted(cuts)[:4]:
        slots = dict(zip(nets, _EDGE_SLOTS))
        west = {channel: ref for channel, ref in outputs.items() if ref.node in left}
        east = {channel: ref for channel, ref in outputs.items() if ref.node in right}
        try:
            a = _layout_platform(circuit, channels, left, west, _EdgeLinks({}, slots))
            b = _layout_platform(circuit, channels, right, east, _EdgeLinks(slots, {}))
        except LayoutCapacityError as error:
            last_error = error
        else:
            return _assemble([a, b])
    if last_error is not None:
        raise LayoutCapacityError(f"相邻两平台的前馈切口未布通，{last_error}") from last_error
    raise LayoutCapacityError(f"没有同时满足门数和 {len(_EDGE_SLOTS)} 对短距口上限的前馈切口")
