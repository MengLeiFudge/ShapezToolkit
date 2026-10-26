"""将信号门网表布置为带平台、无线连线的原生二代蓝图。

默认每门一块1x1平台；装箱版就地复制固定常量，再平移门组件。端口均静态核对，显式兼容多驱动可共用频道。
这里编译生产电路，不运行游戏、门级模拟或目标求解。
"""

import base64
import gzip
import json
import math
import struct
from collections import deque
from dataclasses import dataclass

from .mari.blueprint import Wiring
from .mari.ports import PORTS
from .synthesis.physics import Shape


@dataclass(frozen=True)
class Ref:
    """网表内一个门的输出引用，port 使用游戏原始输出索引。"""

    node: int
    port: int = 0


@dataclass(frozen=True)
class Literal:
    """输入端附近直接放置的常量；颜色使用 color:r 等编码。"""

    value: int | str | Shape | None


@dataclass(frozen=True)
class Gate:
    """一个使用已核对原生端口类型的门，config 是蓝图 C 字段。"""

    kind: str
    inputs: tuple[Ref | Literal, ...] = ()
    config: str | None = None


def constant(value: int | str | Shape | None) -> str:
    """序列化 SignalSerializer 常量，不混淆整数零、空信号和图形。"""
    if value is None:
        data = b"\x01"
    elif isinstance(value, int):
        if not -(1 << 31) <= value < 1 << 31:
            raise ValueError("整数信号必须是有符号 32 位整数")
        data = {0: b"\x04", 1: b"\x05"}.get(value)
        if data is None:
            data = b"\x03" + struct.pack("<i", value)
    elif isinstance(value, Shape):
        key = value.to_key().encode("ascii")
        data = b"\x06\x01\x01" + struct.pack("<H", len(key)) + key
    elif value.startswith("color:") and len(value) == 7 and value[-1] in "urgbcmyw":
        data = b"\x07\x01" + value[-1].encode("ascii")
    else:
        raise ValueError(f"未知信号常量：{value!r}")
    return base64.b64encode(data).decode("ascii")


_TYPES = {
    "ConstantSignal": "ConstantSignalDefaultInternalVariant",
    "WireForward": "WireDefaultForwardInternalVariant",
    "WireLeft": "WireDefaultLeftInternalVariant",
    "VirtualAnalyzer": "VirtualAnalyzerDefaultInternalVariant",
    "VirtualCrystalGenerator": "VirtualCrystalGeneratorDefaultInternalVariant",
    "VirtualHalfCutter": "VirtualHalfCutterDefaultInternalVariant",
    "VirtualHalvesSwapper": "VirtualHalvesSwapperDefaultInternalVariant",
    "VirtualPainter": "VirtualPainterDefaultInternalVariant",
    "VirtualPinPusher": "VirtualPinPusherDefaultInternalVariant",
    "VirtualRotator": "VirtualRotatorDefaultInternalVariant",
    "VirtualRotatorCCW": "VirtualRotatorCCWInternalVariant",
    "VirtualStacker": "VirtualStackerDefaultInternalVariant",
    "VirtualUnstacker": "VirtualUnstackerDefaultInternalVariant",
}
_DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))
_SUPPORTED = (set(_TYPES) - {"WireForward", "WireLeft"}) | {
    "ControlledSignalReceiver", "LogicGateIf", "LogicGateNot", "LogicGateAnd",
    "LogicGateOr", "LogicGateXOr", "LogicGateCompare",
}


def encode_document(document: dict) -> str:
    """编码已经完成静态接线核对的生产蓝图，固定压缩时间戳。"""
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "SHAPEZ2-4-" + base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii") + "$"


def _pack_platforms(platforms: list[dict], bounds: list[tuple[int, int, int, int]]) -> tuple[list[dict], dict[int, tuple[int, int]]]:
    """按行高和余宽复用旧平台空位，组件间留一格，边缘留两格。"""
    packed: list[dict] = []
    mapping = {}
    rows: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    vertical: dict[int, list[tuple[int, int]]] = {}
    order = sorted(range(len(platforms)), key=lambda i: (-(bounds[i][3] - bounds[i][1]),
                                                        -(bounds[i][2] - bounds[i][0]), i))
    for index in order:
        left, bottom, right, top = bounds[index]
        width, height = right - left + 1, top - bottom + 1
        if width > 16 or height > 16:
            raise ValueError("门组件矩形超出平台16×16格内部范围")
        row_key = min((key for key in rows if key[0] >= height and key[1] >= width + 1), default=None)
        if row_key is not None:
            row_height, remaining = row_key
            platform, x, y = rows[row_key].pop()
            if not rows[row_key]:
                del rows[row_key]
        else:
            space = min((space for space in vertical if space >= height + 1), default=None)
            if space is None:
                platform, y, space = len(packed), 2, 17
                packed.append({"T": "Foundation_1x1", "B": {
                    "$type": "Building", "BinaryVersion": 1137, "Entries": []}})
            else:
                platform, y = vertical[space].pop()
                if not vertical[space]:
                    del vertical[space]
            free = space - height - 1
            if free >= 2:
                vertical.setdefault(free, []).append((platform, y + height + 1))
            x, row_height, remaining = 2, height, 17
        entries = packed[platform]["B"]["Entries"]
        mapping[index] = platform, len(entries)
        entries.extend({**entry, "X": entry["X"] + x - left, "Y": entry["Y"] + y - bottom}
                       for entry in platforms[index]["B"]["Entries"])
        remaining -= width + 1
        if remaining >= 2:
            rows.setdefault((row_height, remaining), []).append((platform, x + width + 1, y))
    # 方阵缩短蓝图边长；每岛内仍留两格边缘，不产生跨岛本地连接。
    width = max(1, math.isqrt(max(0, len(packed) - 1)) + 1)
    for index, platform in enumerate(packed):
        platform.update(X=index % width, Y=index // width)
    return packed, mapping


class Circuit:
    """原生门网表及频道分配；导出时核对每个端口的真实几何驱动源。"""

    def __init__(self, channel_base: int = 1_000_000):
        """分配一段低于 2^24 的正整数频道；使用者须为实例保留这段频道。"""
        self.gates: list[Gate] = []
        self.channel_base = channel_base
        self.aliases: list[tuple[Ref, ...]] = []

    def add(self, kind: str, *inputs: Ref | Literal, config: str | None = None) -> Ref:
        """添加一个门，返回输出零；其他出口用 Ref(node, port) 指定。"""
        if kind not in _SUPPORTED or len(inputs) != len(PORTS[kind][1]):
            raise ValueError(f"不支持的门或输入数量：{kind}")
        index = len(self.gates)
        self.gates.append(Gate(kind, inputs, config))
        return Ref(index)

    def channel_map(self) -> dict[Ref, int]:
        """确定全部输出的频道；显式别名要求非空驱动互斥或具有相同值。"""
        refs = [Ref(i, port) for i, gate in enumerate(self.gates) for port in range(len(PORTS[gate.kind][0]))]
        channels = {ref: self.channel_base + i for i, ref in enumerate(refs)}
        if self.channel_base < 1 or self.channel_base + len(refs) >= 1 << 24:
            raise ValueError("内部频道范围必须落在 1～16777215")
        aliased = set()
        for group in self.aliases:
            if len(group) != len(set(group)) or aliased.intersection(group):
                raise ValueError("输出总线别名组必须互不重叠，且组内引用不得重复")
            aliased.update(group)
            if not group or any(ref not in channels for ref in group):
                raise ValueError("输出总线别名引用了不存在的输出")
            channel = channels[group[0]]
            for ref in group:
                channels[ref] = channel
        for gate in self.gates:
            for source in gate.inputs:
                if isinstance(source, Ref) and source not in channels:
                    raise ValueError(f"门输入引用了不存在的输出：{source}")
        return channels

    def _max_depth(self, changing: tuple[Ref, ...] | None = None,
                   outputs: tuple[Ref, ...] | None = None) -> int:
        """频道DAG最长路径；指定源时，未被变化源触及的路径深度为零。"""
        channels = self.channel_map()
        if changing is not None and any(source not in channels for source in changing):
            raise ValueError("变化源引用了不存在的输出")
        if outputs is not None and any(output not in channels for output in outputs):
            raise ValueError("传播终点引用了不存在的输出")
        origins = set(channels.values()) if changing is None else {channels[source] for source in changing}
        dependencies: dict[int, set[int]] = {channel: set() for channel in channels.values()}
        for index, gate in enumerate(self.gates):
            incoming = {channels[source] for source in gate.inputs if isinstance(source, Ref)}
            if gate.kind == "ControlledSignalReceiver":
                control = gate.inputs[0]
                if not isinstance(control, Literal) or not isinstance(control.value, int):
                    raise ValueError("动态选频接收器不适用此组合传播上界")
                if control.value in dependencies:
                    incoming.add(control.value)
            for port in range(len(PORTS[gate.kind][0])):
                dependencies[channels[Ref(index, port)]].update(incoming)
        remaining = {channel: len(sources) for channel, sources in dependencies.items()}
        consumers: dict[int, list[int]] = {channel: [] for channel in dependencies}
        for channel, sources in dependencies.items():
            for source in sources:
                consumers[source].append(channel)
        queue = deque(channel for channel, count in remaining.items() if count == 0)
        depths = {channel: int(channel in origins) for channel in queue}
        while queue:
            source = queue.popleft()
            for channel in consumers[source]:
                candidate = depths[source] + 1 if depths[source] else 0
                depths[channel] = max(depths.get(channel, int(channel in origins)), candidate)
                remaining[channel] -= 1
                if remaining[channel] == 0:
                    queue.append(channel)
        if len(depths) != len(dependencies) or any(remaining.values()):
            raise ValueError("反馈电路没有本组合传播上界")
        selected = depths.values() if outputs is None else (depths[channels[output]] for output in outputs)
        return max(selected, default=0)

    def changing_depth(self, changing: tuple[Ref, ...], outputs: tuple[Ref, ...] | None = None) -> int:
        """变化源计一级，可限制终点；其他输入须稳定，反馈和动态选频仍拒绝。"""
        return self._max_depth(changing, outputs)

    def settling_bound(self) -> dict:
        """按全部频道依赖计算保守保持期，不忽略任何输入的变化。"""
        depth = self._max_depth()
        ticks = 64 * (depth + 2)
        return {"max_gate_depth": depth, "hold_signal_ticks": ticks,
                "hold_simulation_seconds": ticks / 12,
                "conditions": "本机Hybrid或AlwaysHighUPS模式的常速连续推进，每批最多4信号tick；频道独占、接线及配置固定。调试单步、模式切换、强制低UPS和快进不适用。",
                "proof": "4q5l/signal-timing.md；含外部收发与启动余量，非墙钟时间。"}

    def document(self, *, packed: bool = False) -> dict:
        """生成原生 Island 蓝图文档，同时核对实际占地和信号网络。"""
        channels = self.channel_map()
        platforms: list[dict] = []
        bounds: list[tuple[int, int, int, int]] = []
        expected = []
        aliased = {reference for group in self.aliases for reference in group}
        for i, gate in enumerate(self.gates):
            entries = []
            occupied = set()

            def place(kind: str, x: int, y: int, turns: int = 0, config: str | None = None) -> int:
                """按 resources.assets 的 Tiles 核对旋转后实际三维占地。"""
                if kind in ("ControlledSignalReceiver", "ControlledSignalTransmitter"):
                    tiles = [(a, b, z) for a in (-1, 0, 1) for b in (-1, 0, 1) for z in range(3)]
                elif kind == "VirtualHalvesSwapper":
                    tiles = [(0, -1, 0), (0, 0, 0)]
                else:
                    tiles = [(0, 0, 0)]
                footprint = set()
                for a, b, z in tiles:
                    a, b = ((a, b), (-b, a), (-a, -b), (b, -a))[turns]
                    footprint.add((x + a, y + b, z))
                if occupied & footprint or any(not 2 <= a <= 17 or not 2 <= b <= 17 for a, b, _ in footprint):
                    raise ValueError(f"平台 {i} 建筑占地冲突或越界：{kind}@({x},{y})")
                occupied.update(footprint)
                entry = {"X": x, "Y": y, "R": turns, "T": _TYPES.get(kind, kind + "InternalVariant")}
                if config is not None:
                    entry["C"] = config
                entries.append(entry)
                return len(entries) - 1

            gate_index = place(gate.kind, 10, 10, config=gate.config)
            for port, source in enumerate(gate.inputs):
                direction, dx, dy, _ = PORTS[gate.kind][1][port]
                fixed = None
                if packed and isinstance(source, Ref) and source.port == 0 and source not in aliased:
                    provider = self.gates[source.node]
                    if provider.kind == "ConstantSignal":
                        fixed = provider.config
                if isinstance(source, Literal) or fixed is not None:
                    config = constant(source.value) if isinstance(source, Literal) else fixed
                    vx, vy = _DIRECTIONS[direction]
                    sender = place("ConstantSignal", 10 + dx + vx, 10 + dy + vy,
                                   (direction + 2) % 4, config)
                    expected.append(((i, gate_index, port), (i, sender, 0)))
                    continue
                channel = channels[source]
                if (direction, dx, dy) == (2, 0, 0):
                    receiver = place("ControlledSignalReceiver", 6, 10)
                    control = place("ConstantSignal", 6, 8, 1, constant(channel))
                    for x in (8, 9):
                        place("WireForward", x, 10)
                elif (direction, dx, dy) == (3, 0, 0):
                    receiver = place("ControlledSignalReceiver", 10, 6, 1)
                    control = place("ConstantSignal", 12, 6, 2, constant(channel))
                    for y in (8, 9):
                        place("WireForward", 10, y, 1)
                elif (direction, dx, dy) == (1, 0, 0):
                    receiver = place("ControlledSignalReceiver", 10, 14, 3)
                    control = place("ConstantSignal", 8, 14, 0, constant(channel))
                    for y in (11, 12):
                        place("WireForward", 10, y, 1)
                elif (direction, dx, dy) == (2, 0, -1):
                    receiver = place("ControlledSignalReceiver", 8, 4, 1)
                    control = place("ConstantSignal", 10, 4, 2, constant(channel))
                    for y in (6, 7, 8):
                        place("WireForward", 8, y, 1)
                    place("WireLeft", 8, 9, 1)
                    place("WireForward", 9, 9)
                else:
                    raise ValueError(f"没有布局的门输入：{gate.kind}:{port}")
                expected.append(((i, receiver, 0), (i, control, 0)))
                expected.append(((i, gate_index, port), (i, receiver, 0)))
            for port, (direction, dx, dy, _) in enumerate(PORTS[gate.kind][0]):
                if direction == 0 and dy == 0:
                    if gate.kind in ("VirtualHalvesSwapper", "VirtualAnalyzer", "VirtualUnstacker"):
                        place("WireForward", 11, 10)
                        dx += 1
                    transmitter = place("ControlledSignalTransmitter", 12 + dx, 10)
                    control = place("ConstantSignal", 12 + dx, 8, 1, constant(channels[Ref(i, port)]))
                elif (direction, dx, dy) == (3, 0, 0):
                    transmitter = place("ControlledSignalTransmitter", 10, 8, 3)
                    control = place("ConstantSignal", 8, 8, 0, constant(channels[Ref(i, port)]))
                elif (direction, dx, dy) == (0, 0, -1):
                    place("WireLeft", 11, 9)
                    place("WireForward", 11, 8, 1)
                    transmitter = place("ControlledSignalTransmitter", 11, 6, 3)
                    control = place("ConstantSignal", 9, 6, 0, constant(channels[Ref(i, port)]))
                else:
                    raise ValueError(f"没有布局的门输出：{gate.kind}:{port}")
                expected.append(((i, transmitter, 0), (i, control, 0)))
                expected.append(((i, transmitter, 1), (i, gate_index, port)))
            platforms.append({"X": i % 12, "Y": i // 12, "T": "Foundation_1x1", "B": {
                "$type": "Building", "BinaryVersion": 1137, "Entries": entries}})
            bounds.append((min(x for x, _, _ in occupied), min(y for _, y, _ in occupied),
                           max(x for x, _, _ in occupied), max(y for _, y, _ in occupied)))
        if packed:
            platforms, mapping = _pack_platforms(platforms, bounds)
            expected = [((mapping[pi][0], mapping[pi][1] + local, port),
                         (mapping[si][0], mapping[si][1] + slocal, sport))
                        for (pi, local, port), (si, slocal, sport) in expected]
        blueprint = {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}
        wiring = Wiring(blueprint)
        indices = {}
        offset = 0
        for pi, platform in enumerate(platforms):
            for local in range(len(platform["B"]["Entries"])):
                indices[pi, local] = offset + local
            offset += len(platform["B"]["Entries"])
        for (pi, local, port), (si, slocal, sport) in expected:
            sources = wiring.sources(indices[pi, local], port)
            if sources != ((indices[si, slocal], sport),):
                raise ValueError(f"平台 {pi} 的 {local}:{port} 接线不符合网表，实际来源 {sources}")
        return {"V": 1137, "BP": blueprint}

    def encode(self, *, packed: bool = False) -> str:
        """编译网表并编码为 SHAPEZ2-4，压缩时间戳固定以保持结果可复核。"""
        return encode_document(self.document(packed=packed))
