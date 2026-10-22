"""Nabi v7f 的逐 tick 输出流审计；不把脉冲片段当作最终合成图形。"""

import csv
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from ..tmam_circuit import extract_circuit
from ..tmam_signals import FALSE, NULL, TRUE, describe, from_structure, operate, valid_structure
from ..tmam_verify import CircuitModel

NAME = "Nabi-v7f-20221128"
SAVE_SHA256 = "da4d9bb0a8080fbf7f4e914a828d6d92ac14040e7c80f2b68a43621ec83f001c"


def slot_at(circuit: dict, x: int, y: int) -> int:
    """定位布局中指定建筑的第一个输出引脚。"""
    suffix = f":0@{x},{y}"
    return next(i for i, label in enumerate(circuit["labels"]) if label.endswith(suffix))


class V7FAudit:
    """固定选择一个输入，关闭旋转，清空九组指令缓存后独立启动每个案例。"""

    def __init__(self, circuit: dict, max_ticks: int):
        self.circuit = circuit
        self.model = CircuitModel(circuit)
        self.max_ticks = max_ticks
        self.payload = slot_at(circuit, 32, -37)
        self.flag = slot_at(circuit, 32, -35)
        self.clear = slot_at(circuit, 35, -33)
        self.settings = {
            slot_at(circuit, 37, -28): FALSE,
            slot_at(circuit, 41, -28): FALSE,
        }
        # 测试图形选择器中只保留 (40,-20)；其他输入不得造成并线冲突。
        for slot in self.model.constants:
            x, y = map(int, circuit["labels"][slot].split("@")[1].split(","))
            if x >= 40 and x % 2 == 0 and y in (-28, -24, -20, -16):
                self.settings[slot] = TRUE if (x, y) == (40, -20) else FALSE
        self.disabled = {**self.settings, circuit["enable"]: FALSE, self.clear: TRUE}
        reset = self.model.run(NULL, max_ticks, overrides=self.disabled, trace=True)
        if reset["status"] != "fixed":
            raise RuntimeError("Nabi v7f 的输入关闭和缓存清除状态未稳定")
        self.reset = reset["final_slots"]

    def prepare(self, target: int) -> list[int]:
        """在关闭状态下等待选择器传播新目标，避免把切换输入的延迟算入解析。"""
        ready = self.model.run(target, self.max_ticks, initial=self.reset,
                               overrides=self.disabled, trace=True)
        if ready["status"] != "fixed":
            raise RuntimeError("Nabi v7f 更换输入后的关闭状态未稳定")
        return ready["final_slots"]

    def run(self, shape: int) -> tuple[dict, list[list], dict]:
        """返回审计行、每 tick 指令和原始模拟结果；候选堆叠不等同于完整解码。"""
        target = from_structure(shape)
        ready = self.prepare(target)
        result = self.model.run(target, self.max_ticks, initial=ready,
                                overrides={**self.settings, self.clear: FALSE}, trace=True,
                                watch=(self.payload, self.flag))
        # events 只记录变化，须展开持续区间；同一片段连续两 tick 是两条指令。
        commands = []
        previous_tick = 1
        previous = (ready[self.payload], ready[self.flag])
        for tick, values in [*result["events"], (result["ticks"] + 1, (NULL, NULL))]:
            if previous[0]:
                commands.extend((t, *previous) for t in range(previous_tick, tick))
            previous_tick, previous = tick, values
        final = result["final_slots"]
        retained = [(final[a], final[b]) for a, b in zip(
            self.circuit["outputs"][::2], self.circuit["outputs"][1::2])]
        expected = [(payload, flag) for _, payload, flag in reversed(commands[-9:])]
        expected.extend([(NULL, NULL)] * (9 - len(expected)))
        payload_matches = all(a[0] == b[0] for a, b in zip(retained, expected))
        flag_matches = all((a[1] > FALSE) == (b[1] > FALSE) for a, b in zip(retained, expected))
        # 明确标为候选：控制标志尚未解码，片段制造和实际物流也未建模。
        replay = NULL
        for _, payload, _ in reversed(commands):
            replay = payload if not replay else operate(50, replay, payload)[0]
        row = {
            "shape": shape, "shortcode": describe(target), "valid_input": valid_structure(shape),
            "status": result["status"], "ticks": result["ticks"], "period": result["period"],
            "command_count": len(commands), "true_flags": sum(flag == TRUE for _, _, flag in commands),
            "payload_cache_matches": payload_matches, "flag_cache_matches": flag_matches,
            "stack_replay": describe(replay), "stack_matches": bool(target) and replay == target,
            "conflict_ticks": result["conflict_ticks"], "cycle_conflicts": result["cycle_conflicts"],
        }
        return row, [[tick, describe(payload), describe(flag)] for tick, payload, flag in commands], result


def audit_range(circuit: dict, feasible: set[int], start: int, stop: int,
                max_ticks: int, destination: Path) -> dict:
    """扫描一个编号区间；独立保存完整指令，避免只看最后一次输出。"""
    audit = V7FAudit(circuit, max_ticks)
    counts = Counter()
    with destination.with_suffix(".csv").open("w", encoding="utf-8", newline="") as stream, \
            destination.with_suffix(".jsonl").open("w", encoding="utf-8") as events:
        writer = None
        for shape in range(start, stop):
            row, commands, _ = audit.run(shape)
            row["feasible"] = shape in feasible
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)
            events.write(json.dumps({"shape": shape, "commands": commands}, ensure_ascii=False) + "\n")
            group = "feasible" if shape in feasible else "impossible" if row["valid_input"] else "invalid"
            counts[f"{group}.{row['status']}"] += 1
            for key in ("stack_matches", "payload_cache_matches", "flag_cache_matches"):
                counts[f"{group}.{key}.{row[key]}"] += 1
            if row["true_flags"]:
                counts[f"{group}.has_true_flag"] += 1
    return {"start": start, "stop": stop, "counts": dict(counts)}


def summarize_failures(destination: Path) -> dict:
    """从全量 CSV 提取确定的无输出案例与缓存丢标志案例，不把候选堆叠差异当漏解。"""
    with (destination / "results.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    empty = {int(row["shape"]) for row in rows
             if row["feasible"] == "True" and int(row["command_count"]) == 0}
    lost = [row for row in rows if row["feasible"] == "True" and row["flag_cache_matches"] == "False"]
    all_rotations = set()
    for shape in empty:
        rotated = shape
        orbit = {shape}
        for _ in range(3):
            rotated = ((rotated << 1) & 0xEEEE) | ((rotated >> 3) & 0x1111)
            orbit.add(rotated)
        if orbit <= empty:
            all_rotations.add(shape)
    for filename, selected in (
        ("no_output_shapes.txt", [row for row in rows if int(row["shape"]) in empty]),
        ("flag_loss_shapes.txt", lost),
        ("no_output_all_rotations.txt", [row for row in rows if int(row["shape"]) in all_rotations]),
    ):
        (destination / filename).write_text("".join(row["shortcode"] + "\n" for row in selected), encoding="utf-8")
    return {"feasible_no_output": len(empty), "feasible_flag_loss": len(lost),
            "feasible_no_output_in_all_rotations": len(all_rotations),
            "max_ticks_observed": max(int(row["ticks"]) for row in rows),
            "max_commands_observed": max(int(row["command_count"]) for row in rows)}


def verify_v7f(save: Path, destination: Path | None = None, workers: int = 8,
               max_ticks: int = 4096) -> dict:
    """全量审计已定位的原始存档；输出证据，不宣称候选重放已验证完整指令语义。"""
    if not 1 <= workers <= 32 or max_ticks < 1:
        raise ValueError("workers 必须在 1..32，max_ticks 必须为正整数")
    if hashlib.sha256(save.read_bytes()).hexdigest() != SAVE_SHA256:
        raise ValueError("存档与已分析的 Nabi v7f 不一致，须先核对布局和输入输出坐标")
    destination = destination or Path(__file__).parent / "verification" / datetime.now().strftime("v7f-%Y%m%d-%H%M%S")
    if destination.exists():
        raise FileExistsError(f"报告目录已存在：{destination}")
    database = Path(__file__).parent.parent / "data/shapes/shapes.json"
    feasible = set(json.loads(database.read_text(encoding="utf-8")))
    if len(feasible) != 48432 or any(not valid_structure(shape) for shape in feasible):
        raise ValueError("图形对照库不是预期的 48432 个合法结构")
    circuit = extract_circuit(save, NAME)
    destination.mkdir(parents=True)
    parts = destination / "parts"
    parts.mkdir()
    (destination / "circuit.json").write_text(json.dumps(circuit, ensure_ascii=False), encoding="utf-8")
    started = time.monotonic()
    counts = Counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs = [pool.submit(audit_range, circuit, feasible, start, start + 1024,
                            max_ticks, parts / f"{start:05d}") for start in range(0, 65536, 1024)]
        for done, future in enumerate(as_completed(jobs), 1):
            counts.update(future.result()["counts"])
            print(f"Nabi v7f {done * 1024}/65536，已用 {time.monotonic() - started:.1f}s", flush=True)
    with (destination / "results.csv").open("w", encoding="utf-8", newline="") as target, \
            (destination / "commands.jsonl").open("w", encoding="utf-8") as commands:
        writer = csv.writer(target)
        for start in range(0, 65536, 1024):
            with (parts / f"{start:05d}.csv").open(encoding="utf-8", newline="") as source:
                reader = csv.reader(source)
                header = next(reader)
                if start == 0:
                    writer.writerow(header)
                writer.writerows(reader)
            with (parts / f"{start:05d}.jsonl").open(encoding="utf-8") as source:
                for line in source:
                    commands.write(line)
    report = {
        "machine": NAME, "save_sha256": circuit["save_sha256"],
        "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        "gates": len(circuit["gates"]), "networks": len(circuit["networks"]),
        "slots": len(circuit["initial"]), "max_ticks": max_ticks, "workers": workers,
        "scope": "电路 tick、输出流和九组缓存；逆序堆叠是候选重放，未证明完整控制标志语义或实体制造",
        "protocol": "关启动、关两处旋转、只选一个目标、清空缓存；输入稳定后取消清除并启动",
        "counts": dict(sorted(counts.items())), "seconds": time.monotonic() - started,
        "findings": summarize_failures(destination),
        "directory": str(destination),
    }
    (destination / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
