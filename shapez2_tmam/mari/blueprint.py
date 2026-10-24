"""从指定 Mari 原包提取组合方程、端口来源和下发命令，不执行图形或门。

接线依据 BuildingBlueprint、BuildingIODataFactory、SignalNetworkSystem 和
PortSystem。仅接受已核对指纹的原包；布局变化必须重新核对坐标与竞争配对。
"""

import base64
import gzip
import hashlib
import json
import zipfile
from collections import defaultdict
from graphlib import TopologicalSorter
from pathlib import Path

from .ports import OPERATIONS, PORTS

ARCHIVE_SHA256 = "573cfd23dcd0149fd77279ce86287f19c04e1c3485d87b1a9b27ee4aaeeb89cd"
BLUEPRINT = "TMAM Brain Exo.spz2bp"
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))

# 同一输入母线上的多个输出端：以第一端代表外部输入，其余设为 Null。
# target 是 P60 的处理后目标。原包 replace-gaps 开关关闭时严格等于原目标；
# 开启该选项的反馈预处理不属于此组合边界。
BOUNDARIES = {
    (60, 14, 8, 2): "target",
    (60, 11, 7, 2): None,
    (59, 9, 5, 0): "iteration",
    (59, 14, 4, 0): None,
    (79, 29, -9, 0): "save_flood_color",
    (79, 29, 2, 0): "update_factory",
}


def _kind(entry: dict) -> str:
    """归一化建筑标识；镜像只影响几何，不重排输入或输出索引。"""
    return entry["T"].removesuffix("Mirrored").removesuffix("InternalVariant").replace("Default", "")


def _rotate(x: int, y: int, turns: int) -> tuple[int, int]:
    """将岛内端口坐标旋转到蓝图记录的建筑朝向。"""
    return ((x, y), (-y, x), (-x, -y), (y, -x))[turns]


class Wiring:
    """保存几何网络及静态驱动源；未知建筑和未配对核心端口不默认为空。"""

    def __init__(self, blueprint: dict):
        self.platforms = blueprint["Entries"]
        self.entries = [(pi, entry) for pi, platform in enumerate(self.platforms)
                        for entry in platform.get("B", {}).get("Entries", [])]
        self.sites = [(pi, e.get("X", 0), e.get("Y", 0), e.get("L", 0)) for pi, e in self.entries]
        self.lookup = {site: i for i, site in enumerate(self.sites)}
        if len(self.lookup) != len(self.entries):
            raise ValueError("Mari 主控存在重复建筑坐标")
        self.parent = []
        self.pins = {}
        self.drivers = defaultdict(list)
        self.short_ports = {}
        self._source_cache = {}
        self._connect_pins()
        self._pair_short_ports()

    def _find(self, node: int) -> int:
        """并查集返回导线分量，路径压缩不改变电气连接。"""
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def _connect_pins(self):
        """按相邻朝向端口合并导线；桥的两对端口分别成网。"""
        positions = defaultdict(list)
        terminals = []
        for i, (pi, entry) in enumerate(self.entries):
            kind = _kind(entry)
            if kind not in PORTS:
                raise ValueError(f"缺少端口定义：{entry['T']}，位置 {self.sites[i]}")
            platform = self.platforms[pi]
            pin_groups = []
            for category, ports in enumerate(PORTS[kind]):
                nodes = []
                for port, (direction, x, y, z) in enumerate(ports):
                    if entry["T"].endswith("Mirrored"):
                        y, direction = -y, -direction % 4
                    turns = entry.get("R", 0)
                    x, y = _rotate(x, y, turns)
                    pivot = (x + entry.get("X", 0) + 20 * platform.get("X", 0),
                             y + entry.get("Y", 0) + 20 * platform.get("Y", 0),
                             z + entry.get("L", 0) + 20 * platform.get("Z", 0),
                             (direction + turns) % 4)
                    node = len(self.parent)
                    self.parent.append(node)
                    terminals.append((i, category, port))
                    positions[pivot].append(node)
                    nodes.append(node)
                pin_groups.append(nodes)
                if category == 2:
                    groups = (nodes[:2], nodes[2:]) if kind == "WireBridge" else (nodes,)
                    for group in groups:
                        for node in group[1:]:
                            self.parent[self._find(node)] = self._find(group[0])
            self.pins[i] = pin_groups
        for (x, y, z, direction), nodes in positions.items():
            dx, dy = DIRECTIONS[direction]
            for node in nodes:
                for other in positions.get((x + dx, y + dy, z, (direction + 2) % 4), ()):
                    a, b = terminals[node][1], terminals[other][1]
                    if a == 2 or b == 2 or {a, b} == {0, 1}:
                        self.parent[self._find(node)] = self._find(other)
        for node, (i, category, port) in enumerate(terminals):
            if category == 0:
                self.drivers[self._find(node)].append((i, port))

    def _pair_short_ports(self):
        """恢复单候选与原包四处竞争配对，拒绝其他未核对的竞争布局。"""
        senders, receivers = {}, {}
        for i, (pi, entry) in enumerate(self.entries):
            kind = _kind(entry)
            if kind not in ("WireTransmitterSender", "WireTransmitterReceiver"):
                continue
            platform = self.platforms[pi]
            position = (entry.get("X", 0) + 20 * platform.get("X", 0),
                        entry.get("Y", 0) + 20 * platform.get("Y", 0),
                        entry.get("L", 0) + 20 * platform.get("Z", 0), entry.get("R", 0))
            (senders if kind == "WireTransmitterSender" else receivers)[position] = i
        resolved = {(pi, 11, 3, 0): (pi, 7, 3, 0) for pi in (2, 12)}
        resolved.update({(pi, 9, 2, 0): (pi, 4, 2, 0) for pi in (2, 12)})
        for (x, y, z, direction), receiver in receivers.items():
            dx, dy = DIRECTIONS[direction]
            candidates = [senders[(x - gap * dx, y - gap * dy, z, direction)]
                          for gap in range(5, 1, -1) if (x - gap * dx, y - gap * dy, z, direction) in senders]
            if len(candidates) == 1:
                self.short_ports[receiver] = candidates[0]
            elif len(candidates) > 1:
                site = self.sites[receiver]
                if site not in resolved or self.lookup[resolved[site]] not in candidates:
                    raise ValueError(f"未核对的短距端口竞争：{site}")
                self.short_ports[receiver] = self.lookup[resolved[site]]
        if len(set(self.short_ports.values())) != len(self.short_ports):
            raise ValueError("同一短距发送器分配到了多个接收器，需按 PortSystem 重新核对")

    def _direct_sources(self, i: int, port: int) -> list[tuple[int, int]]:
        """返回输入端所在导线分量的直接输出端引用。"""
        return self.drivers[self._find(self.pins[i][1][port])]

    def sources(self, i: int, port: int) -> tuple[tuple[int, int], ...]:
        """穿过短距传输，返回稳定状态下驱动此输入的非导线输出端。"""
        if (i, port) in self._source_cache:
            return self._source_cache[i, port]
        pending = list(self._direct_sources(i, port))
        visited, result = set(), set()
        while pending:
            source = pending.pop()
            if source in visited:
                continue
            visited.add(source)
            index, _ = source
            if _kind(self.entries[index][1]) == "WireTransmitterReceiver":
                if index not in self.short_ports:
                    raise ValueError(f"依赖闭包包含未配对的短距接收器：{self.sites[index]}")
                pending.extend(self._direct_sources(self.short_ports[index], 0))
            else:
                result.add(source)
        self._source_cache[i, port] = tuple(sorted(result))
        return self._source_cache[i, port]


def extract(archive: Path) -> dict:
    """提取六候选共用的有向无环方程；不求值、不推进时钟或模拟实体物流。"""
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Mari 原包指纹不匹配；需重新核对布局，不沿用固定端口坐标")
    with zipfile.ZipFile(archive) as package:
        text = package.read(BLUEPRINT).decode("utf-8").strip()
    if not text.startswith("SHAPEZ2-4-") or not text.endswith("$"):
        raise ValueError("需要 SHAPEZ2-4 格式的 Mari 主控蓝图")
    document = json.loads(gzip.decompress(base64.b64decode(text[10:-1], validate=True)))
    wiring = Wiring(document["BP"])
    roots = {}
    check = wiring.lookup[(79, 8, 2, 0)]
    roots["processed_target"] = wiring.sources(check, 0)
    roots["result"] = wiring.sources(check, 1)
    roots["equal"] = ((check, 0),)
    observations = {
        "corner_1": ((80, 4, 31, 0), 0), "corner_2": ((80, 5, 31, 0), 0),
        "corner_3": ((80, 6, 31, 0), 0), "corner_4": ((80, 7, 31, 0), 0),
        "hybrid_1": ((80, 27, 6, 0), 1), "hybrid_2": ((80, 22, 6, 0), 1),
        "hybrid_3": ((80, 26, 6, 1), 1), "hybrid_4": ((80, 21, 6, 1), 1),
        "hybrid_5": ((80, 17, 6, 0), 1),
        "swap_order": ((80, 21, 19, 1), 1), "pin_claw": ((80, 25, 12, 0), 1),
    }
    for name, (site, port) in observations.items():
        roots[name] = wiring.sources(wiring.lookup[site], port)
    commands = []
    for i, (pi, entry) in enumerate(wiring.entries):
        if pi in (25, 39, 57, 76, 86) and _kind(entry) == "ControlledSignalTransmitter":
            name = f"P{pi}({entry.get('X', 0)},{entry.get('Y', 0)},{entry.get('L', 0)})"
            roots[name + ".channel"] = wiring.sources(i, 0)
            roots[name + ".payload"] = wiring.sources(i, 1)
            commands.append(name)
    dependencies = {}
    pending = [i for sources in roots.values() for i, _ in sources]
    while pending:
        i = pending.pop()
        if i in dependencies:
            continue
        sources = () if wiring.sites[i] in BOUNDARIES else tuple(
            source for port in range(len(wiring.pins[i][1])) for source in wiring.sources(i, port))
        dependencies[i] = {source for source, _ in sources}
        pending.extend(dependencies[i])
    order = tuple(TopologicalSorter(dependencies).static_order())
    slots, nodes = {}, []
    for i in order:
        site = wiring.sites[i]
        entry = wiring.entries[i][1]
        kind = _kind(entry)
        inputs = []
        config = None
        if site in BOUNDARIES:
            operation, config = "input", BOUNDARIES[site]
        elif kind == "ConstantSignal":
            operation, config = "constant", entry["C"]
        elif kind == "Button":
            operation = "integer"
            raw = base64.b64decode(entry["C"], validate=True)
            if raw not in (b"\x00", b"\x01"):
                raise ValueError(f"未知开关配置：{site}")
            config = raw[0]
        elif kind in OPERATIONS:
            operation = OPERATIONS[kind]
            if operation == "compare":
                raw = base64.b64decode(entry["C"], validate=True)
                if len(raw) != 1 or raw[0] not in range(1, 7):
                    raise ValueError(f"未知比较器配置：{site}")
                config = raw[0]
            inputs = [[slots[source] for source in wiring.sources(i, port)]
                      for port in range(len(wiring.pins[i][1]))]
        else:
            raise ValueError(f"核心包含未实现的建筑：{kind}，{site}")
        outputs = []
        for port in range(len(wiring.pins[i][0])):
            slots[i, port] = len(slots)
            outputs.append(slots[i, port])
        nodes.append({"site": site, "op": operation, "config": config, "inputs": inputs, "outputs": outputs})
    return {"archive_sha256": ARCHIVE_SHA256, "blueprint": BLUEPRINT,
            "nodes": nodes, "roots": {name: [slots[source] for source in sources] for name, sources in roots.items()},
            "commands": commands, "slots": len(slots)}


def export(archive: Path, destination: Path):
    """保存可审查的方程源，每个建筑一行，并保留蓝图坐标。"""
    program = extract(archive)
    nodes = program.pop("nodes")
    header = json.dumps(program, ensure_ascii=False, separators=(",", ":"))
    rows = ",\n".join(json.dumps(node, ensure_ascii=False, separators=(",", ":")) for node in nodes)
    destination.write_text(header[:-1] + ',"nodes":[\n' + rows + "\n]}\n", encoding="utf-8")
