"""旧版节点网、列车生产器与 1.2 里改过布局的配置。

三块内容都只针对身份或字节布局真的变了的条目：

- 0.0.9 的 `Layout_RailNode` / `Layout_SpaceBeltNode` / `Layout_SpacePipeNode` 是自由连线的节点，
  按相邻关系换成 1.2 的网格岛（直行、转向、分流、汇合）；
- 列车生产器的岛原点在 1117 后移了一格，旧蓝图要把坐标补回去；
- `ControlledSignalReceiver` 的配置在 1102 从「int 索引 + byte 有效位」换成通道 uid，
  `ExchangeLayerFilterConfig` 在 1131 从「阻挡层号列表」换成位掩码。
"""

from __future__ import annotations

import base64
from typing import Any

NODE_FAMILIES = {
    "Layout_RailNode": ("Rail", 0),
    "Layout_SpaceBeltNode": ("SpaceBelt", 1),
    "Layout_SpacePipeNode": ("SpacePipe", 1),
}
# 节点网的端点会接上同类岛或站台，这些也算连接面。
NEIGHBOUR_PREFIXES = {
    "Rail": ("Rail_", "Layout_Train"),
    "SpaceBelt": ("SpaceBelt_", "Layout_SpaceBeltTunnel"),
    "SpacePipe": ("SpacePipe_", "Layout_SpacePipeTunnel"),
}

# 本地方向编号：东 0、南 1、西 2、北 3；集合为该岛占用的连接面。
SHAPES: dict[str, frozenset[int]] = {
    "_Forward": frozenset({2, 0}),
    "_LeftTurn": frozenset({2, 3}),
    "_RightTurn": frozenset({2, 1}),
    "_LeftFwdSplitter": frozenset({2, 3, 0}),
    "_RightFwdSplitter": frozenset({2, 0, 1}),
    "_YSplitter": frozenset({2, 3, 1}),
    "_LeftFwdMerger": frozenset({2, 1, 0}),
    "_RightFwdMerger": frozenset({2, 3, 0}),
    "_YMerger": frozenset({3, 1, 0}),
    "_TripleSplitter": frozenset({2, 3, 0, 1}),
    "_TripleMerger": frozenset({2, 3, 1, 0}),
}
# 每座岛在本地坐标系下的 (输入面, 输出面) 集合：东 0、南 1、西 2、北 3。
# 旧节点的 `C` 里正好按「从哪侧进、往哪侧出」记录，所以可以直接对表，不必猜流向。
PAIR_SHAPES: dict[str, frozenset[tuple[int, int]]] = {
    "_Forward": frozenset({(2, 0)}),
    "_LeftTurn": frozenset({(2, 3)}),
    "_RightTurn": frozenset({(2, 1)}),
    "_LeftFwdSplitter": frozenset({(2, 3), (2, 0)}),
    "_RightFwdSplitter": frozenset({(2, 0), (2, 1)}),
    "_YSplitter": frozenset({(2, 3), (2, 1)}),
    "_LeftFwdMerger": frozenset({(2, 0), (1, 0)}),
    "_RightFwdMerger": frozenset({(2, 0), (3, 0)}),
    "_YMerger": frozenset({(3, 0), (1, 0)}),
    "_TripleSplitter": frozenset({(2, 3), (2, 0), (2, 1)}),
    "_TripleMerger": frozenset({(2, 0), (3, 0), (1, 0)}),
}
# 没有连线数据时只能按连接面兜底，这时分流与汇合无从区分，统一取分流。

SHAPE_PREFERENCE = (
    "_Forward",
    "_LeftTurn",
    "_RightTurn",
    "_LeftFwdSplitter",
    "_RightFwdSplitter",
    "_YSplitter",
    "_LeftFwdMerger",
    "_YMerger",
    "_TripleSplitter",
)
# 1.2 轨道岛的连接器按「先去重的输入面、再去重的输出面」排列
# （`TrainNavigationIslandDefinitionFactory.ComputeConnections`），
# 颜色掩码就按这个顺序写。本地方向：东 0、南 1、西 2、北 3。
RAIL_CONNECTOR_ORDER: dict[str, tuple[int, ...]] = {
    "_Forward": (2, 0),
    "_LeftTurn": (2, 3),
    "_RightTurn": (2, 1),
    "_LeftFwdSplitter": (2, 0, 3),
    "_RightFwdSplitter": (2, 0, 1),
    "_YSplitter": (2, 1, 3),
    "_LeftFwdMerger": (2, 3, 0),
    "_RightFwdMerger": (2, 1, 0),
    "_YMerger": (3, 1, 0),
    "_TripleSplitter": (2, 0, 1, 3),
    "_TripleMerger": (1, 2, 3, 0),
}
DIRECTION_STEP = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
PAIR_ORDER = tuple(PAIR_SHAPES)

SPACE_PATH_CONFIG_FLAG = 20
RAIL_CONFIG_FLAG = 10
RAIL_COLOR_COUNT = 7
ALL_RAIL_COLORS = (1 << RAIL_COLOR_COUNT) - 1
PRODUCER_PREFIX = "Layout_TrainProducer_"
PRODUCER_OFFSET_GATE = 1117
STATE_DROP_GATE = 1138
SIGNAL_RECEIVER_PREFIX = "ControlledSignalReceiverInternalVariant"
SIGNAL_RECEIVER_GATE = 1102
EXCHANGE_FILTER_GATE = 1131
EXCHANGE_FILTER_INTRODUCED = 1116
EXCHANGE_FILTER_HOSTS = ("Loader", "Unloader", "Transfer")
RANDOM_OPERATOR_SHAPE_TYPE = 2
BLOB_INT_BYTES = 4


def migrate_nodes(
    entries: list[dict[str, Any]], counters: dict[str, int]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """把节点网换成 1.2 的网格岛，返回 (新条目, 改写说明, 未处理原因)。"""
    if not any(entry.get("T") in NODE_FAMILIES for entry in entries):
        return entries, [], []

    notes: list[str] = []
    problems: list[str] = []
    occupied = _occupied_cells(entries)
    result: list[dict[str, Any]] = []
    for entry in entries:
        family = NODE_FAMILIES.get(entry.get("T"))
        if family is None:
            result.append(entry)
            continue
        prefix, layer = family
        connections = _connections(entry)
        pairs = frozenset((src, dst) for src, dst, _ in connections)
        sides = frozenset(side for pair in pairs for side in pair) or _neighbour_sides(entry, entries, prefix)
        if not sides:
            problems.append(f"孤立节点 ({entry.get('X')}, {entry.get('Y')}) 没有同网邻居，已丢弃")
            continue
        shape = _match_pairs(pairs) if pairs else None
        if shape is None and not pairs:
            shape = _match_shape(sides)
        if shape is None:
            problems.append(
                f"节点 ({entry.get('X')}, {entry.get('Y')}) 的连线 {sorted(pairs) if pairs else sorted(sides)} "
                "在 1.2 没有对应岛，已丢弃"
            )
            continue
        name, rotation = shape
        if (_coord(entry, "X"), _coord(entry, "Y"), layer) in occupied:
            problems.append(f"节点 ({entry.get('X')}, {entry.get('Y')}) 的目标区块已被其他条目占用，已丢弃")
            continue
        converted: dict[str, Any] = {
            "X": _coord(entry, "X"),
            "Y": _coord(entry, "Y"),
            "Z": layer,
            "R": rotation,
            "T": f"{prefix}{name}",
        }
        if prefix == "Rail":
            converted["C"] = _rail_config(name, rotation, connections)
        result.append(converted)
        counters["node"] += 1
        if not pairs:
            notes.append(f"({entry.get('X')}, {entry.get('Y')}) 没有连线数据，按相邻面推的岛型，需实机确认")
    return result, notes, problems


def _rail_config(name: str, rotation: int, connections: list[tuple[int, int, int | None]]) -> str:
    """按岛连接器顺序写颜色掩码，掩码取原来经过这一侧的连线的并集。

    旧数据是「每条连线一个掩码」，1.2 是「每个连接器一个掩码」；连线两端的掩码语义一致，
    同侧有多条连线时取并集，取不到就按全色放行。
    """
    masks = []
    for side in RAIL_CONNECTOR_ORDER[name]:
        source = (side + rotation) % 4
        mask = 0
        for src, dst, src_mask in connections:
            if src_mask and source in (src, dst):
                mask |= src_mask
        masks.append(mask or ALL_RAIL_COLORS)
    payload = bytes([len(masks)]) + b"".join(mask.to_bytes(BLOB_INT_BYTES, "little") for mask in masks)
    return _encode(payload)


def _occupied_cells(entries: list[dict[str, Any]]) -> set[tuple[int, int, int]]:
    """非节点条目占掉的区块；升降段跨两层，上下各留一格。"""
    occupied: set[tuple[int, int, int]] = set()
    for entry in entries:
        if entry.get("T") in NODE_FAMILIES:
            continue
        cell = (_coord(entry, "X"), _coord(entry, "Y"), _coord(entry, "Z"))
        occupied.add(cell)
        if "_Lift" in str(entry.get("T")):
            occupied.update({(cell[0], cell[1], cell[2] + 1), (cell[0], cell[1], cell[2] - 1)})
    return occupied


def _coord(entry: dict[str, Any], key: str) -> int:
    """蓝图 JSON 省略默认值，缺失的坐标就是 0。"""
    value = entry.get(key)
    return value if isinstance(value, int) else 0


def _connections(entry: dict[str, Any]) -> list[tuple[int, int, int | None]]:
    """旧节点的 `C` 记着每条连线的进出口方向，解成 (输入面, 输出面, 颜色掩码) 列表。

    太空节点每条连线 2 字节，轨道节点每条 2 字节方向加 4 字节颜色掩码；解不出来就返回空表。
    """
    payload = _decode(entry.get("C"))
    if payload is None or len(payload) < 2:
        return []
    flag = payload[0]
    if flag == SPACE_PATH_CONFIG_FLAG:
        stride, has_mask = 2, False
    elif flag == RAIL_CONFIG_FLAG:
        stride, has_mask = 2 + BLOB_INT_BYTES, True
    else:
        return []
    count = payload[1]
    if len(payload) != 2 + stride * count:
        return []
    result = []
    for index in range(count):
        base = 2 + stride * index
        mask = int.from_bytes(payload[base + 2 : base + 2 + BLOB_INT_BYTES], "little") if has_mask else None
        result.append((payload[base], payload[base + 1], mask))
    return result


def _match_pairs(pairs: frozenset[tuple[int, int]]) -> tuple[str, int] | None:
    """按连线对找岛，顺带定出流向与旋转。"""
    for suffix in PAIR_ORDER:
        pattern = PAIR_SHAPES[suffix]
        if len(pattern) != len(pairs):
            continue
        for rotation in range(4):
            if frozenset(((side + rotation) % 4, (out + rotation) % 4) for side, out in pattern) == pairs:
                return suffix, rotation
    return None


def _neighbour_sides(entry: dict[str, Any], entries: list[dict[str, Any]], prefix: str) -> frozenset[int]:
    """按同层邻居判断四个连接面。"""
    x, y = _coord(entry, "X"), _coord(entry, "Y")
    layer = entry.get("Z")
    sides = set()
    for direction, (dx, dy) in DIRECTION_STEP.items():
        for other in entries:
            if other is entry:
                continue
            if _coord(other, "X") != x + dx or _coord(other, "Y") != y + dy or other.get("Z") != layer:
                continue
            name = other.get("T")
            if not isinstance(name, str):
                continue
            accepted = NEIGHBOUR_PREFIXES[prefix]
            if name in NODE_FAMILIES or any(name.startswith(item) for item in accepted):
                sides.add(direction)
                break
    return frozenset(sides)


def _match_shape(sides: frozenset[int]) -> tuple[str, int] | None:
    """找能以某个旋转覆盖这些连接面的岛，返回 (后缀, 旋转)。"""
    for suffix in SHAPE_PREFERENCE:
        pattern = SHAPES[suffix]
        for rotation in range(4):
            if frozenset((side - rotation) % 4 for side in sides) == pattern:
                return suffix, rotation
    return None


def shift_producers(entries: list[dict[str, Any]], version: int, counters: dict[str, int]) -> None:
    """1117 之前的列车生产器原点后移了一格，把坐标补回去。"""
    if version >= PRODUCER_OFFSET_GATE:
        return
    for entry in entries:
        name = entry.get("T")
        if not isinstance(name, str) or not name.startswith(PRODUCER_PREFIX):
            continue
        rotation = entry.get("R")
        if not isinstance(rotation, int):
            continue
        entry["X"] = entry.get("X", 0) + _rotate_offset((-1, 0), rotation)[0]
        entry["Y"] = entry.get("Y", 0) + _rotate_offset((-1, 0), rotation)[1]
        counters["producer"] += 1


def _rotate_offset(offset: tuple[int, int], rotation: int) -> tuple[int, int]:
    """把本地方向的偏移按岛屿顺时针旋转折算到全局。"""
    x, y = offset
    for _ in range(rotation % 4):
        x, y = -y, x
    return x, y


def drop_island_state(entries: list[dict[str, Any]], version: int, counters: dict[str, int]) -> None:
    """旧版本写的岛状态布局与 1.2 不一致，全部清空，由游戏重建。"""
    if version >= STATE_DROP_GATE:
        return
    for entry in entries:
        if entry.get("S"):
            entry.pop("S", None)
            counters["state"] += 1


def rewrite_configs(entries: list[dict[str, Any]], version: int, counters: dict[str, int], notes: list[str]) -> None:
    """按 1102 与 1131 两个分叉改写配置字节串。"""
    for entry in entries:
        name = entry.get("T")
        payload = _decode(entry.get("C"))
        if payload is None or not isinstance(name, str):
            continue
        if version < SIGNAL_RECEIVER_GATE and name.startswith(SIGNAL_RECEIVER_PREFIX):
            rewritten = _rewrite_signal_receiver(payload)
            if rewritten is None:
                notes.append(f"{name} 的配置长度 {len(payload)} 不是旧的 5 字节布局，保持原样")
            else:
                entry["C"] = _encode(rewritten)
                counters["signal"] += 1
            continue
        hosts = name.startswith("Layout_Train") and any(host in name for host in EXCHANGE_FILTER_HOSTS)
        if hosts and EXCHANGE_FILTER_INTRODUCED <= version < EXCHANGE_FILTER_GATE:
            rewritten = _rewrite_exchange_filter(payload)
            if rewritten is not None:
                entry["C"] = _encode(rewritten)
                counters["exchange"] += 1


def _rewrite_signal_receiver(payload: bytes) -> bytes | None:
    """旧布局是 int 索引加一个有效位，新布局是通道 uid。"""
    if len(payload) != BLOB_INT_BYTES + 1:
        return None
    index = int.from_bytes(payload[:BLOB_INT_BYTES], "little")
    valid = payload[BLOB_INT_BYTES]
    uid = (RANDOM_OPERATOR_SHAPE_TYPE << 24) | (index if valid == 1 else 0)
    return uid.to_bytes(BLOB_INT_BYTES, "little", signed=False)


def _rewrite_exchange_filter(payload: bytes) -> bytes | None:
    """旧布局是层号列表，新布局是位掩码。"""
    if len(payload) < 2 * BLOB_INT_BYTES or (len(payload) - BLOB_INT_BYTES) % BLOB_INT_BYTES:
        return None
    count = int.from_bytes(payload[:BLOB_INT_BYTES], "little")
    if not 1 <= count <= 8 or len(payload) != BLOB_INT_BYTES * (count + 1):
        return None
    mask = 0
    for offset in range(count):
        start = BLOB_INT_BYTES * (offset + 1)
        layer = int.from_bytes(payload[start : start + BLOB_INT_BYTES], "little")
        if not 0 <= layer < 32:
            return None
        mask |= 1 << layer
    return mask.to_bytes(BLOB_INT_BYTES, "little")


def _decode(text: Any) -> bytes | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        return base64.b64decode(text + "=" * (-len(text) % 4))
    except ValueError:
        return None


def _encode(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii").rstrip("=")
