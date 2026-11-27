"""把 0.0.9 的太空地下隧道改写成 1.2 的三层太空走线。

旧版隧道是成对的入口 / 出口岛，中间的地下通道不占区块，靠入口岛 `S` 里的
`ForwarderState.Length_S` 记录长度。1.2 删掉了这 4 个岛，改用太空层走线替代：
地面升到 z=1，横穿，再降回地面。

替换关系按 1.2 的岛定义几何确定（`SpacePathIslandDefinitionFactory`）：

- `{前缀}_Lift1Up{方向}`：占 z0 与 z1 同一列，输入在 z0 朝西，输出在 z1 朝东；
- `{前缀}_Forward`：占一个区块，输入朝西、输出朝东；
- `{前缀}_Lift1Down{方向}`：锚点在上层，占 z1 与 z0 同一列，输入在 z1 朝西，输出在 z0 朝东。

方向后缀按 `SpacePathDefinitionData.LiftDirectionAffix`：东 Forward、南 Right、西 Backward、北 Left；
`R` 取 `GridRotation`（东 0、南 1、西 2、北 3），即本地东对准流向。
"""

from __future__ import annotations

from typing import Any

TUNNEL_SUFFIXES = {
    "Layout_SpaceBeltTunnel_Entrance": ("SpaceBelt", "entrance"),
    "Layout_SpaceBeltTunnel_Exit": ("SpaceBelt", "exit"),
    "Layout_SpacePipeTunnel_Entrance": ("SpacePipe", "entrance"),
    "Layout_SpacePipeTunnel_Exit": ("SpacePipe", "exit"),
}
TUNNEL_IDS = frozenset(TUNNEL_SUFFIXES)

# 0.0.9 的太空带是自由连线的节点网，1.2 换成按区块相邻的 SpaceBelt_* 岛。
SPACE_NODE_IDS = frozenset({"Layout_SpaceBeltNode", "Layout_SpacePipeNode"})

# ChunkDirection：东 0、南 1、西 2、北 3；GridRotation 顺时针同号。
DIRECTION_VECTOR = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
DIRECTION_AFFIX = {0: "Forward", 1: "Right", 2: "Backward", 3: "Left"}


def migrate_tunnels(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """把隧道入口 / 出口换成升降段与太空段。

    返回 ``(新条目, 每条改写的说明, 未处理原因)``。原列表不被修改。
    找不到配对、轴向不直、跨度为零或目标区块已被占用时，保持原样并给出原因。
    """
    tunnels = [entry for entry in entries if entry.get("T") in TUNNEL_IDS]
    if not tunnels:
        return entries, [], []

    occupied = {
        (entry.get("X"), entry.get("Y"), entry.get("Z", 0)) for entry in entries if entry.get("T") not in TUNNEL_IDS
    }
    remaining = [entry for entry in entries if entry.get("T") not in TUNNEL_IDS]
    replacements: list[dict[str, Any]] = []
    problems: list[str] = []
    used: set[int] = set()

    for index, entrance in enumerate(tunnels):
        if index in used:
            continue
        prefix, role = TUNNEL_SUFFIXES[entrance["T"]]
        if role != "entrance":
            problems.append(f"出口 ({entrance.get('X')}, {entrance.get('Y')}) 没有配对的入口，原样保留")
            remaining.append(entrance)
            continue
        match = _find_exit(entrance, tunnels, used, prefix)
        if match is None:
            problems.append(f"入口 ({entrance.get('X')}, {entrance.get('Y')}) 没有同轴的出口")
            remaining.append(entrance)
            continue

        exit_index, exit_entry, direction, span = match
        plan = _route(prefix, entrance, exit_entry, direction, span)
        blocked = [coord for coord in plan["occupied"] if coord in occupied]
        if blocked:
            problems.append(
                f"入口 ({entrance.get('X')}, {entrance.get('Y')}) 的替代走线要占用的区块已被其他岛占用：{blocked[:3]}"
            )
            remaining.append(entrance)
            remaining.append(exit_entry)
            used.add(exit_index)
            continue

        used.add(exit_index)
        new_entries = plan["entries"]
        remaining.extend(new_entries)
        occupied.update(plan["occupied"])
        replacements.append(
            {
                "entrance": (entrance.get("X"), entrance.get("Y")),
                "exit": (exit_entry.get("X"), exit_entry.get("Y")),
                "direction": direction,
                "span": span,
                "ids": [entry["T"] for entry in new_entries],
            }
        )

    return remaining, replacements, problems


def _find_exit(
    entrance: dict[str, Any], tunnels: list[dict[str, Any]], used: set[int], prefix: str
) -> tuple[int, dict[str, Any], int, int] | None:
    """按轴向与距离找最近的出口，返回 (下标, 条目, 方向, 跨度)。"""
    origin = (entrance.get("X"), entrance.get("Y"))
    if not all(isinstance(value, int) for value in origin):
        return None
    best: tuple[int, dict[str, Any], int, int] | None = None
    for index, candidate in enumerate(tunnels):
        if index in used or candidate is entrance:
            continue
        if TUNNEL_SUFFIXES[candidate["T"]] != (prefix, "exit"):
            continue
        delta = (candidate.get("X", 0) - origin[0], candidate.get("Y", 0) - origin[1])
        direction, span = _axis_of(delta)
        if direction is None:
            continue
        if best is None or span < best[3]:
            best = (index, candidate, direction, span)
    return best


def _axis_of(delta: tuple[int, int]) -> tuple[int | None, int]:
    """把位移折算成轴向与跨度；斜向或零位移返回 (None, 0)。"""
    for direction, vector in DIRECTION_VECTOR.items():
        span = delta[0] * vector[0] + delta[1] * vector[1]
        if span <= 0:
            continue
        if (vector[0] * span, vector[1] * span) == delta:
            return direction, span
    return None, 0


def _route(
    prefix: str, entrance: dict[str, Any], exit_entry: dict[str, Any], direction: int, span: int
) -> dict[str, Any]:
    """给出替代走线的条目与其占用的区块。"""
    affix = DIRECTION_AFFIX[direction]
    vector = DIRECTION_VECTOR[direction]
    x, y = entrance["X"], entrance["Y"]
    entries: list[dict[str, Any]] = [{"X": x, "Y": y, "Z": 0, "R": direction, "T": f"{prefix}_Lift1Up{affix}"}]
    occupied = [(x, y, 0), (x, y, 1)]
    for step in range(1, span):
        cell = (x + vector[0] * step, y + vector[1] * step, 1)
        entries.append({"X": cell[0], "Y": cell[1], "Z": 1, "R": direction, "T": f"{prefix}_Forward"})
        occupied.append(cell)
    entries.append(
        {
            "X": exit_entry["X"],
            "Y": exit_entry["Y"],
            "Z": 1,
            "R": direction,
            "T": f"{prefix}_Lift1Down{affix}",
        }
    )
    occupied.extend([(exit_entry["X"], exit_entry["Y"], 1), (exit_entry["X"], exit_entry["Y"], 0)])
    return {"entries": entries, "occupied": occupied}


def find_space_nodes(entries: list[dict[str, Any]]) -> list[tuple[Any, Any]]:
    """列出旧版太空节点网的节点坐标。"""
    return [(entry.get("X"), entry.get("Y")) for entry in entries if entry.get("T") in SPACE_NODE_IDS]
