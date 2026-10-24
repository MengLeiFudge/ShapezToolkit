"""Mari 六种固定候选的 Python 组合模型，保留每个门的原蓝图坐标。

该模型计算默认关闭 gap replacement 时的目标拆解与下发指令。
六候选全部不匹配只表示 Mari 此次没有解，不能据此宣布目标不可制作。
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .assembly import assemble
from .shapes import Shape
from .signals import Signal, decode_constant, describe, merge, operate


@dataclass(frozen=True)
class Command:
    """一处主控发射器的频道和有效载荷；位置使用蓝图平台索引。"""

    source: str
    channel: Signal
    payload: Signal

    def as_dict(self) -> dict:
        """给出可追到蓝图的下发信号记录。"""
        return {"source": self.source, "channel": describe(self.channel), "payload": describe(self.payload)}


@dataclass(frozen=True)
class Candidate:
    """一个固定候选的重建结果与指令；matched 是虚拟相等，不是成品回传。"""

    iteration: int
    target: Shape
    result: Signal
    equal_signal: Signal
    commands: tuple[Command, ...]
    parts: tuple[tuple[str, Signal], ...]

    @property
    def matched(self) -> bool:
        """同时检查比较门与图形值，拒绝将空值或 Conflict 相等当作目标成功。"""
        return self.equal_signal == 1 and self.result == self.target

    def as_dict(self) -> dict:
        """输出当前候选的结论和原机指令，不声称实体加工已通过。"""
        return {"iteration": self.iteration, "target": self.target.to_key(),
                "result": describe(self.result), "matched": self.matched,
                "parts": {name: describe(value) for name, value in self.parts},
                "commands": [command.as_dict() for command in self.commands]}


class Mari:
    """拓扑顺序求值具名方程，候选之间没有共享的可变寄存器状态。"""

    def __init__(self):
        path = Path(__file__).with_name("equations.json")
        program = json.loads(path.read_text(encoding="utf-8"))
        self.nodes = program["nodes"]
        self.roots = program["roots"]
        self.commands = program["commands"]
        self.slot_count = program["slots"]
        self.archive_sha256 = program["archive_sha256"]
        self.constants = {}
        self.locations = {}
        defined = set()
        for node in self.nodes:
            if any(slot not in defined for net in node["inputs"] for slot in net):
                raise ValueError(f"方程不是拓扑顺序：{node['site']}")
            if any(slot in defined or not 0 <= slot < self.slot_count for slot in node["outputs"]):
                raise ValueError(f"方程输出编号重复或越界：{node['site']}")
            defined.update(node["outputs"])
            self.locations[tuple(node["site"])] = node["outputs"]
            if node["op"] == "constant":
                self.constants[node["outputs"][0]] = decode_constant(node["config"])
            elif node["op"] == "integer":
                self.constants[node["outputs"][0]] = node["config"]
        if defined != set(range(self.slot_count)) or any(
                slot not in defined for net in self.roots.values() for slot in net):
            raise ValueError("方程输出或观察端引用不完整")

    def _evaluate(self, target: Shape, iteration: int, save_flood_color: bool) -> list[Signal]:
        """每个门只在其全部输入已定义后求值；同线合并先于门运算。"""
        if iteration not in range(1, 7):
            raise ValueError("Mari 候选编号必须为 1～6")
        # 指令求值主动打开下发门，返回开启更新时会发送的载荷；不连接游戏。
        inputs = {"target": target, "iteration": iteration,
                  "save_flood_color": int(save_flood_color), "update_factory": 1, None: None}
        values: list[Signal] = [None] * self.slot_count
        for slot, value in self.constants.items():
            values[slot] = value
        for node in self.nodes:
            operation = node["op"]
            if operation in ("constant", "integer"):
                continue
            if operation == "input":
                outputs = (inputs[node["config"]],)
            else:
                args = tuple(merge(values[slot] for slot in net) for net in node["inputs"])
                outputs = operate(operation, args, node["config"] or 0)
            if len(outputs) != len(node["outputs"]):
                raise ValueError(f"门的输出数与端口表不符：{node['site']}")
            for slot, value in zip(node["outputs"], outputs):
                values[slot] = value
        return values

    def candidate(self, target: Shape, iteration: int, *, save_flood_color: bool = True) -> Candidate:
        """固定编号后计算重建图形和 51 路指令；默认保留原包的节省颜色选项。"""
        values = self._evaluate(target, iteration, save_flood_color)
        signals = {name: merge(values[slot] for slot in net) for name, net in self.roots.items()}
        assembled = assemble(tuple(signals[f"corner_{i}"] for i in range(1, 5)),
                             tuple(signals[f"hybrid_{i}"] for i in range(1, 6)),
                             signals["swap_order"], signals["pin_claw"])
        if assembled != signals["result"]:
            raise RuntimeError("P80 的逐门结果与具名拼合表达式不一致")
        commands = tuple(Command(name, signals[name + ".channel"], signals[name + ".payload"])
                         for name in self.commands)
        parts = tuple((name, value) for name, value in signals.items()
                      if name.startswith(("corner_", "hybrid_")) or name in ("swap_order", "pin_claw"))
        return Candidate(iteration, target, signals["result"], signals["equal"], commands, parts)

    def solve(self, target: Shape, *, save_flood_color: bool = True) -> Candidate | None:
        """按原成功记录的优先级选择最小匹配编号；没有匹配时返回 None。"""
        for iteration in range(1, 7):
            candidate = self.candidate(target, iteration, save_flood_color=save_flood_color)
            if candidate.matched:
                return candidate
        return None

    def inspect(self, target: Shape, iteration: int, sites: tuple[tuple[int, int, int, int], ...],
                *, save_flood_color: bool = True) -> dict:
        """读取指定原蓝图坐标的所有输出端，便于逐式推导中间结果。"""
        values = self._evaluate(target, iteration, save_flood_color)
        return {str(site): [describe(values[slot]) for slot in self.locations[site]] for site in sites}
