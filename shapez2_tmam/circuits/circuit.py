"""将信号门网表布置为带平台、无线连线的原生二代蓝图。

默认每门一块1x1平台；装箱版复制固定常量，并可合并允许的组合门。端口均静态核对，兼容多驱动可共用频道。
这里编译生产电路，不运行游戏、门级模拟或目标求解。
"""

import base64
import gzip
import json
import struct
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass

from .circuit_packing import pack_components, stack_platforms
from ..mari.blueprint import Wiring
from ..mari.ports import PORTS
from ..synthesis.physics import Shape


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


def encode_document(document: dict, *, format_version: int = 4) -> str:
    """编码已经完成静态接线核对的生产蓝图，固定压缩时间戳。"""
    if format_version not in (4, 5):
        raise ValueError(f"不支持的蓝图格式 {format_version}")
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    body = base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii")
    metadata = "[]_2" if format_version == 5 else ""
    return f"SHAPEZ2-{format_version}-{body}{metadata}$"


def _place_pair(gate: Gate, provider: Gate, source: Ref, output_channel: int, channels: dict[Ref, int],
                fixed: dict[Ref, str], place: Callable[[str, int, int, int, str | None], int]
                ) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """二门固定模板；返回每个输入的预期提供者，由调用者检查占地与最终接线。"""
    links = []
    direction = PORTS[gate.kind][1][gate.inputs.index(source)][0]
    vx, vy = _DIRECTIONS[direction]
    turns = (direction + 2) % 4
    child_x, child_y = 11 + 4 * vx, 11 + 4 * vy
    child = place(provider.kind, child_x, child_y, turns, provider.config)
    parent = place(gate.kind, 11, 11, 0, gate.config)
    for distance in (1, 2, 3):
        place("WireForward", 11 + distance * vx, 11 + distance * vy, turns, None)
    for current, index, x, y, rotation in ((provider, child, child_x, child_y, turns), (gate, parent, 11, 11, 0)):
        for port, value in enumerate(current.inputs):
            if index == parent and value == source:
                links.append(((parent, port), (child, 0)))
                continue
            facing = (PORTS[current.kind][1][port][0] + rotation) % 4
            dx, dy = _DIRECTIONS[facing]
            toward = (facing + 2) % 4
            config = constant(value.value) if isinstance(value, Literal) else fixed.get(value)
            if config is not None:
                sender = place("ConstantSignal", x + dx, y + dy, toward, config)
            else:
                assert isinstance(value, Ref)
                rx, ry = x + 4 * dx, y + 4 * dy
                sender = place("ControlledSignalReceiver", rx, ry, toward, None)
                cx, cy = _DIRECTIONS[(toward + 3) % 4]
                control = place("ConstantSignal", rx + 2 * cx, ry + 2 * cy, (toward + 1) % 4, constant(channels[value]))
                links.append(((sender, 0), (control, 0)))
                for distance in (1, 2):
                    place("WireForward", x + distance * dx, y + distance * dy, toward, None)
            links.append(((index, port), (sender, 0)))
    transmitter = place("ControlledSignalTransmitter", 13, 11, 0, None)
    control = place("ConstantSignal", 13, 9, 1, constant(output_channel))
    links.extend((((transmitter, 0), (control, 0)), ((transmitter, 1), (parent, 0))))
    return links


class Circuit:
    """原生门网表及频道分配；导出时核对每个端口的真实几何驱动源。"""

    def __init__(self, channel_base: int = 1_000_000):
        """分配一段低于 2^24 的正整数频道；使用者须为实例保留这段频道。"""
        self.gates: list[Gate] = []
        self.wire_methods = False
        self.method_ranges: list[tuple[range, tuple[Ref, ...]]] = []
        self.channel_base = channel_base
        self.aliases: list[tuple[Ref, ...]] = []
        self.local_nodes: set[int] = set()
        self.fixed_local_pairs: dict[int, int] | None = None
        self.retained_nodes: frozenset[int] | None = None
        self.retained_outputs: tuple[Ref, ...] = ()

    def add(self, kind: str, *inputs: Ref | Literal, config: str | None = None) -> Ref:
        """添加一个门，返回输出零；其他出口用 Ref(node, port) 指定。"""
        if self.retained_nodes is not None:
            raise ValueError("登记导出依赖后不能再添加门")
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

    def retain_outputs(self, outputs: tuple[Ref, ...]) -> None:
        """完成网表后仅导出公开输出的依赖闭包；保留全部原Ref及频道编号。"""
        if self.retained_nodes is not None:
            raise ValueError("导出依赖不能重复登记")
        channels = self.channel_map()
        if any(output not in channels for output in outputs):
            raise ValueError("导出终点引用了不存在的输出")
        self.local_pairs(protected=outputs)
        writers: dict[int, set[int]] = {}
        for ref, channel in channels.items():
            writers.setdefault(channel, set()).add(ref.node)
        for gate in self.gates:
            if gate.kind == "ControlledSignalReceiver":
                source = gate.inputs[0]
                if not isinstance(source, Literal) or not isinstance(source.value, int):
                    raise ValueError("动态选频接收器不能静态裁剪导出依赖")
        pending = [node for output in outputs for node in writers[channels[output]]]
        retained: set[int] = set()
        while pending:
            node = pending.pop()
            if node in retained:
                continue
            retained.add(node)
            gate = self.gates[node]
            for source in gate.inputs:
                if isinstance(source, Ref):
                    pending.extend(writers[channels[source]] - retained)
            if gate.kind == "ControlledSignalReceiver":
                source = gate.inputs[0]
                assert isinstance(source, Literal) and isinstance(source.value, int)
                pending.extend(writers.get(source.value, set()) - retained)
        self.retained_nodes = frozenset(retained)
        self.retained_outputs = outputs

    def gate_counts(self) -> dict[str, int]:
        """实际导出的逻辑门分类；原节点编号与频道分配不受裁剪影响。"""
        return dict(sorted(Counter(gate.kind for node, gate in enumerate(self.gates)
                                   if self.retained_nodes is None or node in self.retained_nodes).items()))

    def _max_depth(self, changing: tuple[Ref, ...] | None = None,
                   outputs: tuple[Ref, ...] | None = None, *, trace: list[Ref] | None = None) -> int:
        """频道DAG加权路径；固定局部边权为0，其余为1；trace记录实际门路径。"""
        channels = self.channel_map()
        if changing is not None and any(source not in channels for source in changing):
            raise ValueError("变化源引用了不存在的输出")
        if outputs is not None and any(output not in channels for output in outputs):
            raise ValueError("传播终点引用了不存在的输出")
        origins = set(channels.values()) if changing is None else {channels[source] for source in changing}
        dependencies: dict[int, dict[int, int]] = {channel: {} for channel in channels.values()}
        local = self.local_pairs() if self.fixed_local_pairs is not None else {}
        writers: dict[tuple[int, int], Ref] = {}
        for index, gate in enumerate(self.gates):
            incoming: dict[int, int] = {}
            for source in gate.inputs:
                if isinstance(source, Ref):
                    weight = int(local.get(index) != source.node)
                    channel = channels[source]
                    incoming[channel] = max(incoming.get(channel, 0), weight)
            if gate.kind == "ControlledSignalReceiver":
                control = gate.inputs[0]
                if not isinstance(control, Literal) or not isinstance(control.value, int):
                    raise ValueError("动态选频接收器不适用此组合传播上界")
                if control.value in dependencies:
                    incoming[control.value] = 1
            for port in range(len(PORTS[gate.kind][0])):
                output = Ref(index, port)
                channel = channels[output]
                for source, weight in incoming.items():
                    if source not in dependencies[channel] or weight > dependencies[channel][source]:
                        dependencies[channel][source] = weight
                        if trace is not None:
                            writers[channel, source] = output
        remaining = {channel: len(sources) for channel, sources in dependencies.items()}
        consumers: dict[int, list[int]] = {channel: [] for channel in dependencies}
        for channel, sources in dependencies.items():
            for source in sources:
                consumers[source].append(channel)
        queue = deque(channel for channel, count in remaining.items() if count == 0)
        depths = {channel: int(channel in origins) for channel in queue}
        previous: dict[int, int] = {}
        while queue:
            source = queue.popleft()
            for channel in consumers[source]:
                candidate = depths[source] + dependencies[channel][source] if depths[source] else 0
                current = depths.get(channel, int(channel in origins))
                if candidate > current:
                    previous[channel] = source
                depths[channel] = max(current, candidate)
                remaining[channel] -= 1
                if remaining[channel] == 0:
                    queue.append(channel)
        if len(depths) != len(dependencies) or any(remaining.values()):
            raise ValueError("反馈电路没有本组合传播上界")
        selected = depths if outputs is None else {channels[output]: depths[channels[output]] for output in outputs}
        end = max(selected, key=lambda channel: (depths[channel], -channel), default=None)
        if trace is not None:
            trace.clear()
            representatives = {channel: output for output, channel in channels.items()}
            if changing is not None:
                representatives.update((channels[source], source) for source in changing)
            channel = end
            while channel is not None and depths[channel]:
                source = previous.get(channel)
                trace.append(writers[channel, source] if source is not None else representatives[channel])
                channel = source
            trace.reverse()
        return depths[end] if end is not None else 0

    def changing_depth(self, changing: tuple[Ref, ...], outputs: tuple[Ref, ...] | None = None,
                       *, trace: list[Ref] | None = None) -> int:
        """变化源计一级，可限制终点；其他输入须稳定，反馈和动态选频仍拒绝。"""
        return self._max_depth(changing, outputs, trace=trace)

    def settling_bound(self) -> dict:
        """按全部频道依赖计算保守保持期，不忽略任何输入的变化。"""
        depth = self._max_depth()
        ticks = 64 * (depth + 2)
        return {"max_gate_depth": depth, "hold_signal_ticks": ticks,
                "hold_simulation_seconds": ticks / 12,
                "conditions": "本机Hybrid或AlwaysHighUPS模式的常速连续推进，每批最多4信号tick；频道独占、接线及配置固定。调试单步、模式切换、强制低UPS和快进不适用。",
                "proof": "4q5l/signal-timing.md；含外部收发与启动余量，非墙钟时间。"}

    def freeze_local_pairs(self, protected: tuple[Ref, ...]) -> None:
        """保护后续锁存器复用的输出，并固定用于压缩布局计时的局部配对。"""
        if self.fixed_local_pairs is not None:
            raise ValueError("局部计时配对不能重复固定")
        self.fixed_local_pairs = self.local_pairs(protected=protected)

    def local_pairs(self, *, protected: tuple[Ref, ...] = ()) -> dict[int, int]:
        """选择私有组合门，或逐项核对已经用于时序计算的固定配对。"""
        kinds = {"LogicGateAnd", "LogicGateOr", "LogicGateXOr", "LogicGateCompare", "LogicGateIf", "LogicGateNot"}
        uses = Counter(source for gate in self.gates for source in gate.inputs if isinstance(source, Ref))
        aliased = {reference for group in self.aliases for reference in group}
        public = set(protected) | set(self.retained_outputs)
        channels = self.channel_map()
        received = {gate.inputs[0].value for gate in self.gates if gate.kind == "ControlledSignalReceiver"
                    and isinstance(gate.inputs[0], Literal)}

        method_nodes = {node for nodes, _ in self.method_ranges for node in nodes}

        def eligible(node: int, port: int, source: Ref | Literal) -> bool:
            gate = self.gates[node]
            return (isinstance(source, Ref) and source.port == 0 and source.node in self.local_nodes
                    and node not in method_nodes and source.node not in method_nodes
                    and source.node < node and uses[source] == 1 and source not in aliased and source not in public
                    and channels[source] not in received and self.gates[source.node].kind in kinds
                    and PORTS[gate.kind][1][port] in ((2, 0, 0, 0), (3, 0, 0, 0)))

        pairs: dict[int, int] = {}
        used: set[int] = set()
        if self.fixed_local_pairs is not None:
            for node, child in self.fixed_local_pairs.items():
                if (node not in self.local_nodes or node in used or child in used or self.gates[node].kind not in kinds
                        or not any(source == Ref(child) and eligible(node, port, source)
                                   for port, source in enumerate(self.gates[node].inputs))):
                    raise ValueError("用于时序计算的固定局部配对不再满足私有接线条件")
                used.update((node, child))
            return {node: child for node, child in self.fixed_local_pairs.items()
                    if self.retained_nodes is None or node in self.retained_nodes}
        for node in sorted(self.local_nodes, reverse=True):
            gate = self.gates[node]
            if node in used or gate.kind not in kinds:
                continue
            for port, source in enumerate(gate.inputs):
                if isinstance(source, Ref) and source.node not in used and eligible(node, port, source):
                    pairs[node] = source.node
                    used.update((node, source.node))
                    break
        return {node: child for node, child in pairs.items()
                if self.retained_nodes is None or node in self.retained_nodes}

    def building_counts(self, *, packed: bool = False) -> dict[str, int]:
        """按网表及固定模板统计非线缆建筑；不分配坐标、平台或执行走线。"""
        if self.fixed_local_pairs is not None and not packed:
            raise ValueError("按局部连接计时的网表必须使用固定配对统计建筑")
        pairs = self.local_pairs() if packed else {}
        absorbed = set(pairs.values())
        aliased = {reference for group in self.aliases for reference in group}
        fixed = {Ref(node) for node, gate in enumerate(self.gates)
                 if packed and gate.kind == "ConstantSignal" and gate.config is not None and Ref(node) not in aliased}
        counts = Counter(self.gate_counts())
        for node, gate in enumerate(self.gates):
            if self.retained_nodes is not None and node not in self.retained_nodes:
                continue
            for source in gate.inputs:
                if isinstance(source, Ref) and node in pairs and source == Ref(pairs[node]):
                    continue
                # 每个外部输入有一份常量：字面量、就地常量或接收器频道。
                counts["ConstantSignal"] += 1
                if isinstance(source, Ref) and source not in fixed:
                    counts["ControlledSignalReceiver"] += 1
            if node not in absorbed:
                outputs = len(PORTS[gate.kind][0])
                counts["ControlledSignalTransmitter"] += outputs
                counts["ConstantSignal"] += outputs
        return dict(sorted(counts.items()))

    def document(self, *, packed: bool = False) -> dict:
        """生成原生 Island 蓝图文档，同时核对实际占地和信号网络。"""
        if self.fixed_local_pairs is not None and not packed:
            raise ValueError("按局部连接计时的电路必须导出为固定配对的压缩布局")
        channels = self.channel_map()
        platforms: list[dict] = []
        expected = []
        aliased = {reference for group in self.aliases for reference in group}
        pairs = self.local_pairs() if packed else {}
        absorbed = set(pairs.values())
        fixed_values = {Ref(node): gate.config for node, gate in enumerate(self.gates)
                        if gate.kind == "ConstantSignal" and Ref(node) not in aliased and gate.config is not None}
        method_nodes = {node for nodes, _ in self.method_ranges for node in nodes}
        if method_nodes and not packed:
            raise ValueError("本地方法需要3×3平台布局")
        for i, gate in enumerate(self.gates):
            if i in method_nodes or i in absorbed or (self.retained_nodes is not None and i not in self.retained_nodes):
                continue
            component = len(platforms)
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
                lower, upper = (2, 17) if packed else (3, 16)
                if occupied & footprint or any(not lower <= a <= upper or not lower <= b <= upper
                                               for a, b, _ in footprint):
                    raise ValueError(f"平台 {i} 建筑占地冲突或越界：{kind}@({x},{y})")
                occupied.update(footprint)
                entry = {"X": x, "Y": y, "R": turns, "T": _TYPES.get(kind, kind + "InternalVariant")}
                if config is not None:
                    entry["C"] = config
                entries.append(entry)
                return len(entries) - 1

            if i in pairs:
                links = _place_pair(gate, self.gates[pairs[i]], Ref(pairs[i]), channels[Ref(i)], channels, fixed_values, place)
                expected.extend(((component, local, port), (component, sender, sport))
                                for (local, port), (sender, sport) in links)
                platforms.append({"T": "Foundation_1x1", "B": {
                    "$type": "Building", "BinaryVersion": 1137, "Entries": entries}})
                continue
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
                    expected.append(((component, gate_index, port), (component, sender, 0)))
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
                expected.append(((component, receiver, 0), (component, control, 0)))
                expected.append(((component, gate_index, port), (component, receiver, 0)))
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
                expected.append(((component, transmitter, 0), (component, control, 0)))
                expected.append(((component, transmitter, 1), (component, gate_index, port)))
            platforms.append({"X": component % 12, "Y": component // 12, "T": "Foundation_1x1", "B": {
                "$type": "Building", "BinaryVersion": 1137, "Entries": entries}})
        if packed:
            platforms, mapping = pack_components(platforms)
            expected = [((mapping[pi][0], mapping[pi][1] + local, port),
                         (mapping[si][0], mapping[si][1] + slocal, sport))
                        for (pi, local, port), (si, slocal, sport) in expected]
        if method_nodes:
            from .wired_module import method_platforms
            platforms.extend(method_platforms(self, channels))
            stack_platforms(platforms)
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
