"""二代蓝图封装串的读写，格式 1..5 全部支持。

封装串形如 ``SHAPEZ2-<格式号>-<base64(gzip(JSON))><追加数据>_<追加数据长度>$``，
追加数据是自定义元数据的 JSON 数组，格式 5 起蓝图图标也从 ``BP.Icon`` 搬到这里。
导出公式见 ``Game.Core.Blueprint.Exporter.BlueprintExporter.Export``（1.2.0-rc3）。
"""

from __future__ import annotations

import base64
import binascii
import gzip
import io
import json
from dataclasses import dataclass
from typing import Any

PREFIX = "SHAPEZ2-"
SUFFIX = "$"
FORMAT_MIN = 1
FORMAT_LATEST = 5
BLUEPRINT_KINDS = ("Island", "Building")


class BlueprintError(ValueError):
    """封装串无法解析或重建时抛出，消息直接指向损坏的位置。"""


@dataclass
class Blueprint:
    """一份解析后的蓝图：文档树、封装格式号与追加数据原文。

    文档保持游戏导出的原样（``V`` 是语义版本，``BP`` 是蓝图本体），
    追加数据按原文保存，重建时不再归一化，避免无损信息被改写。
    """

    document: dict[str, Any]
    format_version: int
    custom_data: str = ""

    @property
    def version(self) -> int:
        """文档语义版本，对应游戏内 ``GameVersion`` 枚举值。"""
        value = self.document.get("V", 0)
        return value if isinstance(value, int) else 0

    @property
    def body(self) -> dict[str, Any]:
        """蓝图本体 ``BP``；缺失或类型不对时返回空字典。"""
        body = self.document.get("BP")
        return body if isinstance(body, dict) else {}

    @property
    def kind(self) -> str:
        """``Island`` 或 ``Building``；未标注时按条目形状推断。"""
        kind = self.body.get("$type")
        if kind in BLUEPRINT_KINDS:
            return str(kind)
        return "Island" if any("B" in entry or "S" in entry for entry in self.entries) else "Building"

    @property
    def entries(self) -> list[dict[str, Any]]:
        """本层条目列表，过滤掉非字典项。"""
        entries = self.body.get("Entries")
        if not isinstance(entries, list):
            return []
        return [entry for entry in entries if isinstance(entry, dict)]


def decode(text: str) -> Blueprint:
    """解析封装串，损坏时抛 :class:`BlueprintError`。"""
    stripped = text.strip()
    if not stripped.startswith(PREFIX):
        raise BlueprintError(f"缺少前缀 {PREFIX}")
    if not stripped.endswith(SUFFIX):
        raise BlueprintError(f"缺少结尾 {SUFFIX}")
    head, separator, tail = stripped[len(PREFIX) : -len(SUFFIX)].partition("-")
    if not separator or not head.isdigit():
        raise BlueprintError("格式号缺失或不是整数")
    format_version = int(head)
    if not FORMAT_MIN <= format_version <= FORMAT_LATEST:
        raise BlueprintError(f"格式号 {format_version} 不在 {FORMAT_MIN}..{FORMAT_LATEST} 之间")
    payload, custom_data = _split_appended(tail)
    return Blueprint(document=_decompress(payload), format_version=format_version, custom_data=custom_data)


def encode(blueprint: Blueprint, compresslevel: int = 9) -> str:
    """按保存的格式号与追加数据重建封装串。

    gzip 时间戳固定便于比对；``compresslevel`` 与游戏一致取 9，
    只做内容核对时可降到 1，大蓝图能快一个数量级。
    """
    text = json.dumps(blueprint.document, ensure_ascii=False, separators=(",", ":"))
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=compresslevel, mtime=0) as stream:
        stream.write(text.encode("utf-8"))
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    custom_data = blueprint.custom_data
    appended = f"{custom_data}_{len(custom_data)}" if custom_data else ""
    return f"{PREFIX}{blueprint.format_version}-{payload}{appended}{SUFFIX}"


def read_custom_data(blueprint: Blueprint) -> list[dict[str, Any]]:
    """把追加数据解析成元数据项列表，形状为 ``{"Type": ..., "Content": ...}``。"""
    text = blueprint.custom_data.strip()
    if not text:
        return []
    try:
        items = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BlueprintError(f"追加数据不是 JSON：{exc.msg}") from exc
    if not isinstance(items, list):
        raise BlueprintError("追加数据不是 JSON 数组")
    return [item for item in items if isinstance(item, dict)]


def build_custom_data(items: list[dict[str, Any]]) -> str:
    """把元数据项列表编码回追加数据原文。"""
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


def summarize(blueprint: Blueprint) -> dict[str, Any]:
    """统计蓝图规模，供命令行核对与页面概览使用。"""
    islands = 0
    buildings = 0
    configs = 0
    kinds: dict[str, int] = {}
    layers: list[int] = []
    for entry in blueprint.entries:
        nested = entry.get("B")
        if isinstance(nested, dict):
            islands += 1
            for building in nested.get("Entries", []):
                if isinstance(building, dict):
                    buildings += 1
                    configs += "C" in building
                    layer = building.get("L")
                    if isinstance(layer, int):
                        layers.append(layer)
        else:
            buildings += 1
            configs += "C" in entry
            layer = entry.get("L")
            if isinstance(layer, int):
                layers.append(layer)
        name = entry.get("T")
        if isinstance(name, str):
            kinds[name] = kinds.get(name, 0) + 1
    return {
        "format": blueprint.format_version,
        "version": blueprint.version,
        "kind": blueprint.kind,
        "entries": len(blueprint.entries),
        "islands": islands,
        "buildings": buildings,
        "configs": configs,
        "layers": [min(layers), max(layers) + 1] if layers else [0, 0],
        "kinds": dict(sorted(kinds.items())),
    }


def _split_appended(tail: str) -> tuple[str, str]:
    """按结尾的 ``_<长度>`` 切出 base64 与追加数据；格式 1..4 没有追加数据。"""
    index = tail.rfind("_")
    if index < 0:
        return tail, ""
    length_text = tail[index + 1 :]
    if not length_text.isdigit():
        return tail, ""
    length = int(length_text)
    start = index - length
    if start < 0:
        raise BlueprintError("声明的追加数据长度超过剩余长度")
    custom_data = tail[start:index]
    payload = tail[:start]
    if not payload:
        raise BlueprintError("缺少 base64 内容")
    try:
        items = json.loads(custom_data)
    except json.JSONDecodeError as exc:
        raise BlueprintError(f"追加数据不是 JSON：{exc.msg}") from exc
    if not isinstance(items, list):
        raise BlueprintError("追加数据不是 JSON 数组")
    return payload, custom_data


def _decompress(payload: str) -> dict[str, Any]:
    """把 base64+gzip+JSON 还原成文档字典。"""
    compact = "".join(payload.split())
    try:
        raw = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BlueprintError(f"base64 解码失败：{exc}") from exc
    try:
        unpacked = gzip.decompress(raw)
    except (OSError, EOFError) as exc:
        raise BlueprintError(f"gzip 解压失败：{exc}") from exc
    try:
        document = json.loads(unpacked)
    except json.JSONDecodeError as exc:
        raise BlueprintError(f"蓝图 JSON 解析失败：{exc}") from exc
    if not isinstance(document, dict):
        raise BlueprintError("蓝图 JSON 顶层不是对象")
    return document
