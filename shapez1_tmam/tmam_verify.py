"""一代 TMAM 的离散 tick 模拟与穷举报告；只模拟输出所依赖的电路。"""

import csv
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from .tmam_signals import FALSE, TRUE, describe, from_structure, operate, valid_structure


class CircuitModel:
    """固定电路拓扑。不同输入使用独立的保存状态，避免上一个案例污染下一个案例。"""

    def __init__(self, circuit: dict):
        """建立增量传播索引；跳过未变化的门不改变其逐 tick 延迟。"""
        self.circuit = circuit
        self.providers = circuit["networks"]
        self.gates = [(g["code"], g["inputs"], g["outputs"]) for g in circuit["gates"]]
        self.receivers = [[] for _ in self.providers]
        self.slot_nets = [[] for _ in circuit["initial"]]
        for net, providers in enumerate(self.providers):
            for slot in providers:
                self.slot_nets[slot].append(net)
        for gate, (_, inputs, _) in enumerate(self.gates):
            for net in inputs:
                if net >= 0:
                    self.receivers[net].append(gate)
        self.constants = {int(slot): value for slot, value in circuit["constants"].items()}

    def run(self, target: int, max_ticks: int = 4096, *, initial: list[int] | None = None, overrides: dict[int, int] | None = None, trace: bool = False, watch: tuple[int, ...] = ()) -> dict:
        """替换人工输入常量后推进到固定点或完整状态周期；超时单独报告。

        网络 -1 表示冲突，区别于无信号 0。任意输入冲突都令该门所有输出为空。
        一轮先汇总网络再计算门，因此后面的门不能读到本轮刚产生的新输出。
        Brent 检测保存完整检查点，哈希相同后仍比较全部引脚，避免哈希碰撞误判周期。
        """
        if max_ticks < 1:
            raise ValueError("max_ticks 必须为正整数")
        slots = list(initial if initial is not None else self.circuit["initial"])
        for slot, value in self.constants.items():
            slots[slot] = value
        slots[self.circuit["input"]] = target
        for slot, value in (overrides or {}).items():
            if slot not in self.constants:
                raise ValueError(f"只能修改常量或开关输出：{slot}")
            slots[slot] = value
        values = [0] * len(self.providers)
        dirty_nets = set(range(len(values)))
        dirty_gates = set(range(len(self.gates)))
        state_hash = 0
        for slot, value in enumerate(slots):
            state_hash ^= hash((slot, value))
        checkpoint, checkpoint_hash = slots.copy(), state_hash
        power, period = 1, 0
        history, conflict_ticks, conflicts = [], 0, 0
        events = []
        observed = tuple(slots[slot] for slot in watch)
        started = time.monotonic()
        status, cycle_start = "timeout", None
        for tick in range(1, max_ticks + 1):
            for net in dirty_nets:
                value = 0
                for slot in self.providers[net]:
                    candidate = slots[slot]
                    if candidate:
                        if value and value != candidate:
                            value = -1
                            break
                        value = candidate
                if value != values[net]:
                    values[net] = value
                    dirty_gates.update(self.receivers[net])
            active_conflicts = values.count(-1)
            conflicts += active_conflicts
            conflict_ticks += bool(active_conflicts)
            dirty_nets = set()
            for gate in dirty_gates:
                code, inputs, outputs = self.gates[gate]
                a = values[inputs[0]] if inputs[0] >= 0 else 0
                b = values[inputs[1]] if len(inputs) > 1 and inputs[1] >= 0 else 0
                result = (0,) * len(outputs) if a == -1 or b == -1 else operate(code, a, b)
                for slot, value in zip(outputs, result):
                    if slots[slot] != value:
                        state_hash ^= hash((slot, slots[slot])) ^ hash((slot, value))
                        slots[slot] = value
                        dirty_nets.update(self.slot_nets[slot])
            dirty_gates = set()
            output_values = tuple(slots[slot] for slot in self.circuit["outputs"])
            # 输出支路与真实导线一致地合并，不允许相互冲突的候选被算作成功。
            nonempty = set(output_values) - {0}
            output = next(iter(nonempty)) if len(nonempty) == 1 else -1 if nonempty else 0
            checked = any(slots[slot] == TRUE for slot in self.circuit["checks"])
            history.append((output, checked, active_conflicts))
            if watch:
                current = tuple(slots[slot] for slot in watch)
                if current != observed:
                    events.append((tick, current))
                    observed = current
            period += 1
            if not dirty_nets:
                status, cycle_start, period = "fixed", tick - 1, 1
                break
            if state_hash == checkpoint_hash and slots == checkpoint:
                status, cycle_start = "periodic", tick - period
                break
            if period == power:
                checkpoint, checkpoint_hash = slots.copy(), state_hash
                power *= 2
                period = 0
        cycle = history[cycle_start:] if cycle_start is not None else []
        success = bool(target) and bool(cycle) and all(output == target and checked for output, checked, _ in cycle)
        result = {
            "status": status, "success": success, "ticks": tick,
            "period": period if cycle else None, "cycle_start": cycle_start,
            "output": describe(history[-1][0]) if history[-1][0] >= 0 else "conflict",
            "check": history[-1][1], "conflict_ticks": conflict_ticks,
            "network_conflicts": conflicts, "cycle_conflicts": sum(c[2] for c in cycle),
            "transient_match": any(output == target and checked for output, checked, _ in history) if target else False,
            "seconds": time.monotonic() - started,
        }
        if watch:
            result["events"] = events
        if trace:
            result["final_slots"] = slots
            result["history"] = history
        return result


def verify_range(circuit: dict, feasible: set[int], start: int, stop: int, max_ticks: int, destination: Path) -> dict:
    """逐个验证半开编号范围，保存完整 CSV；非法常量编码仍运行，但单独归类。"""
    model = CircuitModel(circuit)
    # 人工操作流程：关启动开关，等待稳定，改输入并等待稳定，再开开关。
    # 保存结果寄存器允许保留旧值，启动脉冲负责清理；不能直接把寄存器全部清零。
    disabled = {circuit["enable"]: FALSE}
    reset = model.run(circuit["initial"][circuit["input"]], max_ticks, overrides=disabled, trace=True)
    if reset["status"] != "fixed":
        raise RuntimeError(f"{circuit['name']} 关闭启动开关后未稳定：{reset['status']}")
    counts = Counter()
    started = time.monotonic()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = ("shape", "valid_input", "expected", "success", "status", "ticks", "period", "output", "check", "conflict_ticks", "network_conflicts", "cycle_conflicts", "transient_match")
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for shape in range(start, stop):
            target = from_structure(shape)
            ready = model.run(target, max_ticks, initial=reset["final_slots"], overrides=disabled, trace=True)
            if ready["status"] != "fixed":
                raise RuntimeError(f"{circuit['name']} 输入 {shape} 的关闭状态未稳定")
            result = model.run(target, max_ticks, initial=ready["final_slots"])
            valid, expected = valid_structure(shape), shape in feasible
            result.update(shape=shape, valid_input=valid, expected=expected)
            writer.writerow(result)
            if not valid:
                category = "invalid_input"
            elif result["status"] == "timeout":
                category = "timeout"
            elif result["success"]:
                category = "true_positive" if expected else "false_positive"
            else:
                category = "false_negative" if expected else "true_negative"
            counts[category] += 1
            if (shape - start + 1) % 256 == 0:
                stream.flush()
    return {"name": circuit["name"], "start": start, "stop": stop, "counts": dict(counts), "seconds": time.monotonic() - started}

def verify_saves(save_dir: Path, destination: Path | None, workers: int = 8, max_ticks: int = 4096,
                 machines: tuple[str, ...] = ("XianYu-20221129", "BugFix-20210622")) -> dict:
    """并行验证所选存档的全部编号，合并逐项结果与来源摘要。"""
    import hashlib
    from concurrent.futures import ProcessPoolExecutor, as_completed

    from .tmam_circuit import extract_circuit

    if not 1 <= workers <= 32 or max_ticks < 1:
        raise ValueError("workers 必须在 1..32 内，max_ticks 必须为正整数")
    machines = tuple("BugFix-20210622" if name == "CTMAM" else name for name in machines)
    sources = {
        "XianYu-20221129": ("xianyu_20221129", "savegame-916dcc85ebaf5438a5e23cb79d344e2fc28ef2c8.bin"),
        "BugFix-20210622": ("bugfix_20210622", "savegame-3c4c1c08fc4161406e4353e25f06c4b92e824b48.bin"),
    }
    database = Path(__file__).resolve().parent / "data/shapes/shapes.json"
    feasible = set(json.loads(database.read_text(encoding="utf-8")))
    if any(not valid_structure(shape) for shape in feasible):
        raise ValueError("对照集合包含非法结构编码")
    if not machines or len(set(machines)) != len(machines) or any(name not in sources for name in machines):
        raise ValueError("请选择不重复的 TMAM 名称：XianYu-20221129、BugFix-20210622（旧名 CTMAM）")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directories = {
        name: (destination / sources[name][0] if destination is not None
               else Path(__file__).resolve().parent / sources[name][0] / "verification" / stamp)
        for name in machines
    }
    for path in directories.values():
        if (path / "summary.json").exists():
            raise FileExistsError(f"结果目录已有报告，请选择新的目录：{path}")
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    circuits = {name: extract_circuit(save_dir / sources[name][1], name) for name in machines}
    for name, circuit in circuits.items():
        baseline = CircuitModel(circuit).run(circuit["initial"][circuit["input"]], max_ticks)
        if not baseline["success"] or baseline["status"] != "fixed":
            raise RuntimeError(f"{name} 未能复现存档保存的稳定输出：{baseline}")
        (directories[name] / f"{name}-circuit.json").write_text(json.dumps(circuit, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "scope": "拆解与虚拟合成电路；未模拟传送带、实体加工和出货",
        "protocol": "从保存状态关启动开关至固定点，修改输入至固定点，再打开启动开关",
        "max_ticks": max_ticks, "workers": workers, "feasible_count": len(feasible),
        "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        "machines": {},
        "output_directories": {name: str(path) for name, path in directories.items()},
    }
    started = time.monotonic()
    jobs = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for name, circuit in circuits.items():
            for start in range(0, 65536, 1024):
                path = directories[name] / "parts" / f"{name}-{start:05d}.csv"
                future = pool.submit(verify_range, circuit, feasible, start, start + 1024, max_ticks, path)
                jobs.append(future)
        reports = []
        completed = Counter()
        for future in as_completed(jobs):
            report = future.result()
            reports.append(report)
            completed[report["name"]] += report["stop"] - report["start"]
            print(f"{report['name']} {completed[report['name']]}/65536，已用 {time.monotonic() - started:.1f}s", flush=True)
    for name, circuit in circuits.items():
        counts = Counter()
        for report in reports:
            if report["name"] == name:
                counts.update(report["counts"])
        with (directories[name] / f"{name}.csv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.writer(target)
            for start in range(0, 65536, 1024):
                with (directories[name] / "parts" / f"{name}-{start:05d}.csv").open(encoding="utf-8", newline="") as source:
                    reader = csv.reader(source)
                    header = next(reader)
                    if start == 0:
                        writer.writerow(header)
                    writer.writerows(reader)
        summary["machines"][name] = {"counts": dict(counts), "save_sha256": circuit["save_sha256"], "gates": len(circuit["gates"]), "networks": len(circuit["networks"])}
    summary["seconds"] = time.monotonic() - started
    for name, path in directories.items():
        report = {**summary, "machines": {name: summary["machines"][name]},
                  "output_directories": {name: str(path)}}
        (path / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary
