"""把旧版二代蓝图升级到本机最新游戏版本。

规则全部来自逐版本反编译，数据在 ``data/migration.json``：岛定义改名与互换的版本门、
岛条目 ``Z`` 字段的引入点、``BinaryVersion`` 的存废、图标搬进追加数据的时机。
文档级迁移只改已经确定的部分，未实现的字节串迁移按 ``gaps`` 以 unsupported 列进报告。
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .codec import Blueprint, BlueprintError, build_custom_data, read_custom_data

DATA_PATH = Path(__file__).resolve().parent / "data" / "migration.json"
RULES: dict[str, Any] = json.loads(DATA_PATH.read_text(encoding="utf-8"))
TARGET_VERSION: int = int(RULES["target"]["document_version"])
TARGET_FORMAT: int = int(RULES["target"]["format_version"])
ICON_TYPE: str = str(RULES["icon"]["type"])


@dataclass(frozen=True)
class Step:
    """一条升级步骤的结果，``status`` 取 applied、skipped 或 unsupported。"""

    name: str
    status: str
    detail: str = ""


@dataclass
class UpgradeReport:
    """升级报告：源版本与逐条步骤，未实现的项单独归入 unsupported。"""

    source_version: int
    source_format: int
    steps: list[Step] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        """追加一条步骤记录。"""
        self.steps.append(Step(name, status, detail))

    @property
    def unsupported(self) -> list[Step]:
        """尚未实现、需要人工确认的步骤。"""
        return [step for step in self.steps if step.status == "unsupported"]

    def as_dict(self) -> dict[str, Any]:
        """转成可直接打印的字典。"""
        return {
            "source_version": self.source_version,
            "source_format": self.source_format,
            "target_version": TARGET_VERSION,
            "target_format": TARGET_FORMAT,
            "steps": [{"name": step.name, "status": step.status, "detail": step.detail} for step in self.steps],
            "unsupported": [step.name for step in self.unsupported],
        }


def upgrade(source: Blueprint) -> tuple[Blueprint, UpgradeReport]:
    """升级到目标版本与封装格式，返回新蓝图与报告；不改动传入对象。"""
    if source.version > TARGET_VERSION:
        raise BlueprintError(f"蓝图版本 {source.version} 高于本工具支持的 {TARGET_VERSION}")
    document = copy.deepcopy(source.document)
    body = document.get("BP")
    if not isinstance(body, dict):
        raise BlueprintError("蓝图缺少 BP 本体")
    report = UpgradeReport(source_version=source.version, source_format=source.format_version)
    counters: Counter[str] = Counter()
    renamed: Counter[str] = Counter()
    custom_data = _migrate_icon(source, body, counters)
    _migrate_entries(body, source.version, counters, renamed)
    _stamp_versions(body)
    document["V"] = TARGET_VERSION
    _report_steps(source, custom_data, counters, renamed, report)
    _report_gaps(body, source.version, counters, report, source.kind == "Island")
    return Blueprint(document=document, format_version=TARGET_FORMAT, custom_data=custom_data), report


def _migrate_icon(source: Blueprint, body: dict[str, Any], counters: Counter[str]) -> str:
    """把根蓝图的内嵌图标搬进追加数据，并清掉各层已经失效的 Icon 字段。"""
    items = [item for item in read_custom_data(source) if not _is_icon_item(item)]
    icon = body.pop("Icon", None)
    if isinstance(icon, dict) and icon.get("Data"):
        content = json.dumps(icon, ensure_ascii=False, separators=(",", ":"))
        items.append({"Type": ICON_TYPE, "Content": content})
        counters["icon"] += 1
    for entry in _entries(body):
        nested = entry.get("B")
        if isinstance(nested, dict):
            nested.pop("Icon", None)
    return build_custom_data(items)


def _migrate_entries(
    body: dict[str, Any], version: int, counters: Counter[str], renamed: Counter[str], island_level: bool = True
) -> None:
    """按版本门改写条目：岛定义改名与互换、岛条目缺失的 Z、建筑负层号与配置计数。"""
    renames = {str(rule["old"]): (str(rule["new"]), int(rule["gate"])) for rule in RULES["island_renames"]}
    swaps = [(str(rule["first"]), str(rule["second"]), int(rule["gate"])) for rule in RULES["island_swaps"]]
    z_gate = int(RULES["island_entry_defaults"]["z_gate"])
    z_value = int(RULES["island_entry_defaults"]["z_value"])
    for entry in _entries(body):
        name = entry.get("T")
        if island_level and isinstance(name, str):
            if name in renames and version < renames[name][1]:
                entry["T"] = renames[name][0]
                renamed[f"{name} → {renames[name][0]}"] += 1
            for first, second, gate in swaps:
                if version < gate and entry.get("T") == first:
                    entry["T"] = second
                    counters["swap"] += 1
                    break
        if island_level and "Z" not in entry and version < z_gate:
            entry["Z"] = z_value
            counters["z"] += 1
        layer = entry.get("L")
        if isinstance(layer, int) and layer < 0:
            entry["L"] = 0
            counters["layer"] += 1
        counters["configs"] += "C" in entry or bool(entry.get("S"))
        nested = entry.get("B")
        if isinstance(nested, dict):
            _migrate_entries(nested, version, counters, renamed, island_level=False)


def _stamp_versions(body: dict[str, Any]) -> None:
    """标好本体类型，并按 1.2 的序列化类去掉已经取消的 BinaryVersion。"""
    body.setdefault("$type", "Island" if any("B" in entry for entry in _entries(body)) else "Building")
    body.pop("BinaryVersion", None)
    for nested in _bodies(body)[1:]:
        nested.setdefault("$type", "Building")
        nested.pop("BinaryVersion", None)


def _report_steps(
    source: Blueprint,
    custom_data: str,
    counters: Counter[str],
    renamed: Counter[str],
    report: UpgradeReport,
) -> None:
    """把累计的改动写成报告步骤。"""
    if source.format_version == TARGET_FORMAT:
        report.add("format", "skipped", f"已是封装 {TARGET_FORMAT}")
    else:
        report.add("format", "applied", f"封装 {source.format_version} → {TARGET_FORMAT}")
    if counters["icon"]:
        report.add("icon", "applied", "内嵌图标搬到追加数据")
    elif custom_data != source.custom_data:
        report.add("icon", "applied", "清掉失效的图标条目")
    else:
        report.add("icon", "skipped", "没有内嵌图标")
    for pair, count in sorted(renamed.items()):
        report.add("rename", "applied", f"{pair}（{count} 个）")
    if not renamed:
        report.add("rename", "skipped", "没有需要改名的岛")
    if counters["swap"]:
        report.add("swap", "applied", f"轨合并器左右互换 {counters['swap']} 个")
    if counters["z"]:
        report.add("entry_z", "applied", f"补齐缺失的 Z 字段：{counters['z']} 个条目")
    else:
        report.add("entry_z", "skipped", "条目已有层号")
    if counters["layer"]:
        report.add("layer", "applied", f"负层号钳到 0：{counters['layer']} 个条目")
    report.add("version", "applied", f"V {source.version} → {TARGET_VERSION}")


def _report_gaps(
    body: dict[str, Any], version: int, counters: Counter[str], report: UpgradeReport, is_island: bool
) -> None:
    """把尚未实现的迁移逐条标成 unsupported，不静默吞掉。"""
    gaps = {str(gap["id"]): gap for gap in RULES["gaps"]}
    island_entries = _entries(body) if is_island else []
    triggers = {
        "legacy_island_config": version <= int(gaps["legacy_island_config"]["gate"])
        and any("C" in entry for entry in island_entries),
        "island_config_blob": version < int(gaps["island_config_blob"]["gate"])
        and any(entry.get("S") for entry in island_entries),
        "train_producer_offset": version < int(gaps["train_producer_offset"]["gate"]) and bool(island_entries),
        "config_blob": version < TARGET_VERSION and counters["configs"] > 0,
    }
    for name, triggered in triggers.items():
        if triggered:
            report.add(name, "unsupported", str(gaps[name]["detail"]))
    pending = [
        f"{branch['gate']} {branch['name']}" for branch in RULES["data_branches"] if version < int(branch["gate"])
    ]
    if pending and counters["configs"]:
        report.add("data_branches", "unsupported", "待实现的字节串分叉：" + "、".join(pending))


def _entries(body: dict[str, Any]) -> list[dict[str, Any]]:
    """取出本层条目，过滤掉非字典项。"""
    entries = body.get("Entries")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _bodies(body: dict[str, Any]) -> list[dict[str, Any]]:
    """遍历根蓝图与全部内嵌建筑蓝图的本体。"""
    bodies = [body]
    for entry in _entries(body):
        nested = entry.get("B")
        if isinstance(nested, dict):
            bodies.extend(_bodies(nested))
    return bodies


def _is_icon_item(item: dict[str, Any]) -> bool:
    """判断追加数据项是否是蓝图图标。"""
    return str(item.get("Type", "")).startswith("BlueprintIcon")
