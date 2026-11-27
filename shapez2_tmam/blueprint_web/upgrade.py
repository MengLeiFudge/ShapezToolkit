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

from . import catalog as catalog_module
from . import legacy, tunnels
from .codec import Blueprint, BlueprintError, build_custom_data, read_custom_data

DATA_PATH = Path(__file__).resolve().parent / "data" / "migration.json"
RULES: dict[str, Any] = json.loads(DATA_PATH.read_text(encoding="utf-8"))
TARGET_VERSION: int = int(RULES["target"]["document_version"])
TARGET_FORMAT: int = int(RULES["target"]["format_version"])
ICON_TYPE: str = str(RULES["icon"]["type"])
_CATALOG: catalog_module.Catalog | None = None


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
    _migrate_space_tunnels(body, source.version, report)
    notes: list[str] = []
    problems: list[str] = []
    _migrate_legacy(body, source.version, counters, notes, problems)
    _stamp_versions(body)
    document["V"] = TARGET_VERSION
    _report_steps(source, custom_data, counters, renamed, report)
    _report_legacy(counters, problems, report)
    _report_notes(notes, report)
    _report_gaps(body, source.version, report, source.kind == "Island")
    _check_catalog(body, report)
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


def _migrate_space_tunnels(body: dict[str, Any], version: int, report: UpgradeReport) -> None:
    """把旧版太空地下隧道换成 1.2 的三层太空走线。"""
    converted = 0
    problems: list[str] = []
    for node in _bodies(body):
        entries = _entries(node)
        if not any(entry.get("T") in tunnels.TUNNEL_IDS for entry in entries):
            continue
        replaced, replacements, issues = tunnels.migrate_tunnels(entries, version)
        node["Entries"] = replaced
        converted += len(replacements)
        problems.extend(issues)
    if converted:
        report.add("space_tunnel", "applied", f"{converted} 处地下隧道改成升降段与 z=1 太空段")
    if problems:
        report.add("space_tunnel", "unsupported", "；".join(problems[:4]))
    if not converted and not problems:
        report.add("space_tunnel", "skipped", "没有旧版地下隧道")


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


def _migrate_legacy(
    body: dict[str, Any], version: int, counters: Counter[str], notes: list[str], problems: list[str]
) -> None:
    """节点网换成网格岛、生产器坐标补偏移、清空旧岛状态、改写两处分叉配置。"""
    for node in _bodies(body):
        entries = _entries(node)
        if not entries:
            continue
        replaced, node_notes, node_problems = legacy.migrate_nodes(entries, counters)
        if replaced is not entries:
            node["Entries"] = replaced
        notes.extend(node_notes)
        problems.extend(node_problems)
        legacy.shift_producers(_entries(node), version, counters)
        legacy.drop_island_state(_entries(node), version, counters)
        legacy.rewrite_configs(_entries(node), version, counters, notes)


def _report_legacy(counters: Counter[str], problems: list[str], report: UpgradeReport) -> None:
    """把 legacy 迁移的结果写成报告步骤。"""
    if counters["node"]:
        detail = f"{counters['node']} 个旧节点换成网格岛"
        if counters["node_kept"]:
            detail += f"，{counters['node_kept']} 个连接面数对不上仍保留原样"
        report.add("node_network", "applied", detail)
    else:
        report.add("node_network", "skipped", "没有旧版节点网")
    if problems:
        report.add("node_network", "unsupported", "；".join(problems[:4]))
    if counters["producer"]:
        report.add("producer_offset", "applied", f"{counters['producer']} 个列车生产器坐标后移一格")
    else:
        report.add("producer_offset", "skipped", "没有需要补偏移的生产器")
    if counters["state"]:
        report.add("island_state", "applied", f"清空 {counters['state']} 个旧岛状态，交给游戏重建")
    else:
        report.add("island_state", "skipped", "没有旧岛状态")
    if counters["signal"]:
        report.add("signal_channel", "applied", f"{counters['signal']} 个受控信号接收器的通道换成 uid")
    else:
        report.add("signal_channel", "skipped", "没有旧式通道配置")
    if counters["exchange"]:
        report.add("exchange_filter", "applied", f"{counters['exchange']} 个交换层筛选改成位掩码")
    else:
        report.add("exchange_filter", "skipped", "没有旧式交换层筛选")


def _report_notes(notes: list[str], report: UpgradeReport) -> None:
    """把需要人工确认的推测写进报告。"""
    if notes:
        preview = "；".join(notes[:3])
        report.add("needs_review", "unsupported", f"{len(notes)} 处按推测改写，需实机确认：{preview}")


def _report_gaps(body: dict[str, Any], version: int, report: UpgradeReport, is_island: bool) -> None:
    """把尚未实现的迁移逐条标成 unsupported，不静默吞掉。"""
    gaps = {str(gap["id"]): gap for gap in RULES["gaps"]}
    island_entries = _entries(body) if is_island else []
    legacy_gap = gaps.get("legacy_island_config")
    if legacy_gap and version <= int(legacy_gap["gate"]) and any("C" in entry for entry in island_entries):
        report.add("legacy_island_config", "unsupported", str(legacy_gap["detail"]))


def _check_catalog(body: dict[str, Any], report: UpgradeReport) -> None:
    """用本机 1.2 的 id 目录核对条目，解析不到的 id 单列出来。"""
    names = [name for name in _all_names(body) if isinstance(name, str)]
    catalog = _catalog()
    unknown = catalog.unknown(names)
    if unknown:
        preview = "、".join(unknown[:6]) + ("…" if len(unknown) > 6 else "")
        removed = [name for name in unknown if catalog.resolve(name) == "removed"]
        detail = f"{len(unknown)} 个 id 在本机可读资源里找不到：{preview}"
        if removed:
            detail += f"（其中 {len(removed)} 个是 1.2 已移除的定义，其余可能藏在压缩 bundle 里）"
        report.add("catalog", "unsupported", detail)
    else:
        report.add("catalog", "skipped", "全部 id 都能在本机 1.2 目录里解析")


def _all_names(body: dict[str, Any]) -> list[Any]:
    """收集本层与内嵌建筑蓝图的全部 T。"""
    names: list[Any] = []
    for node in _bodies(body):
        names.extend(entry.get("T") for entry in _entries(node))
    return names


def _catalog() -> catalog_module.Catalog:
    """惰性读取 id 目录，避免每次升级重复解析 JSON。"""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = catalog_module.load()
    return _CATALOG


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
