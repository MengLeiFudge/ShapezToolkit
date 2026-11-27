"""按依赖深度从输入侧到输出侧布置组合门。"""

from ..circuit import Circuit, Ref
from ._layout import _GATE_ROWS, _RADIO_ROWS, LayoutCapacityError, _RoutingError, _live_nodes, _place


_COLUMNS = range(8, 45, 6)
_LEVELS = range(3)


def layout_by_depth(circuit: Circuit, outputs: dict[int, Ref]) -> tuple[dict, int]:
    channels = circuit.channel_map()
    live = _live_nodes(circuit, channels, outputs)
    radios = [node for node in sorted(live) if circuit.gates[node].kind == "ControlledSignalReceiver"]
    gates = sorted(live - set(radios))
    if max(len(radios), len(outputs)) > len(_RADIO_ROWS) or len(gates) > len(_COLUMNS) * len(_GATE_ROWS) * len(_LEVELS):
        raise LayoutCapacityError("按依赖分列的布局超出单平台容量")

    # 同深度的门按其输入在平台上的行位置排列，避免早期比较门横跨输入侧。
    depths = dict.fromkeys(radios, 0)
    rows: dict[int, float] = dict(zip(radios, _RADIO_ROWS))
    used = {channels[ref] for ref in outputs.values()}
    for node in gates:
        sources = [arg for arg in circuit.gates[node].inputs if isinstance(arg, Ref)]
        depths[node] = 1 + max((depths[ref.node] for ref in sources), default=0)
        rows[node] = sum(rows[ref.node] for ref in sources) / len(sources) if sources else 25
        used.update(channels[ref] for ref in sources)

    ordered = sorted(gates, key=lambda node: (depths[node], rows[node]))
    placed = []
    sites = []
    columns = len(_COLUMNS)
    for i, x in enumerate(_COLUMNS):
        column = ordered[len(ordered) * i // columns:len(ordered) * (i + 1) // columns]
        placed.extend(sorted(column, key=rows.__getitem__))
        # 错开各层的门位，把每列的门均匀分到整列可用位置。
        grid = [(x + z, y + z, z) for y in _GATE_ROWS for z in _LEVELS]
        span = max(1, len(column) - 1)
        sites.extend(grid[round(j * (len(grid) - 1) / span)] for j in range(len(column)))
    try:
        return _place(circuit, channels, (radios, placed), used, sites, outputs)
    except _RoutingError as error:
        raise LayoutCapacityError(f"按依赖分列未布通 {len(gates)} 个门，{error}") from error
