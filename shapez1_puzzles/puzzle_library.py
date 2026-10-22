"""一代本地谜题查询与 CSV 导出，不依赖 Steam 或网络。"""

from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any


COLUMNS = (
    "序号ID", "短代码ShortKey", "谜题名称Title", "作者Author", "查看次数Downloads",
    "完成次数Completions", "完成率CompletionRate", "平均时间AverageTime", "喜欢个数Likes",
    "宽Width", "高Height", "分离Splitter", "切割Cutter", "旋转Rotater", "堆叠Stacker",
    "混色Mixer", "上色Painter", "垃圾桶Trash", "传送带Belt", "隧道Tunnel",
)
BUILDINGS = (
    "balancer", "cutter", "rotater", "stacker", "mixer", "painter", "trash", "belt", "underground_belt",
)


def _read_library(destination: Path, include_deleted: bool = False) -> Iterator[tuple[Path, dict[str, Any]]]:
    """同一 ID 优先采用最新下载，随后读取普通归档和可选的已删除归档。"""
    if not destination.is_dir():
        raise FileNotFoundError(f"本地谜题目录不存在：{destination}")
    downloads = sorted(destination.glob("p.*.json"), key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
    groups = [downloads, sorted((destination / "common").glob("*.json"))]
    if include_deleted:
        groups.append(sorted((destination / "puzzles_deleted").glob("*.json")))
    seen: set[int] = set()
    for paths in groups:
        for path in paths:
            try:
                puzzle = json.loads(path.read_text(encoding="utf-8-sig"))
            except (ValueError, UnicodeError) as exc:
                raise ValueError(f"谜题 JSON 无法读取：{path}；{exc}") from exc
            if not isinstance(puzzle, dict) or not isinstance(puzzle.get("meta"), dict) or not isinstance(puzzle.get("game"), dict):
                raise ValueError(f"谜题缺少 game/meta 对象：{path}")
            identity = puzzle["meta"].get("id")
            if type(identity) is not int or identity < 0:
                raise ValueError(f"谜题缺少有效的数字 ID：{path}")
            if identity not in seen:
                seen.add(identity)
                yield path, puzzle


def find_puzzles(code: str, destination: Path) -> list[tuple[Path, dict[str, Any]]]:
    """按 ID 或短代码返回本地匹配项及来源；短代码可能对应多个谜题。"""
    code = code.strip()
    if not code:
        raise ValueError("请输入谜题数字 ID 或图形短代码。")
    identity = int(code) if code.isascii() and code.isdecimal() else None
    matches = []
    for path, puzzle in _read_library(destination, include_deleted=True):
        meta = puzzle["meta"]
        if (identity is not None and identity == meta["id"]) or code == meta.get("shortKey"):
            matches.append((path, puzzle))
    if not matches:
        raise ValueError(f"本地没有找到谜题：{code}")
    return sorted(matches, key=lambda match: match[1]["meta"]["id"])


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _csv_row(puzzle: dict[str, Any], path: Path) -> list[Any]:
    meta, game = puzzle["meta"], puzzle["game"]
    bounds = game.get("bounds")
    excluded = game.get("excludedBuildings", [])
    if not isinstance(bounds, dict) or not isinstance(excluded, list):
        raise ValueError(f"谜题边界或禁用建筑格式无效：{path}")
    downloads, completions = meta.get("downloads"), meta.get("completions")
    rate = f"{completions / downloads:.2%}" if _number(downloads) and downloads > 0 and _number(completions) else ""
    average = meta.get("averageTime")
    duration = ""
    if _number(average):
        hours, remaining = divmod(int(average), 3600)
        minutes, seconds = divmod(remaining, 60)
        duration = (f"{hours}h" if hours else "") + (f"{minutes}m" if minutes else "") + f"{seconds}s"
    return [
        meta["id"], meta.get("shortKey", ""), meta.get("title", ""), meta.get("author", ""),
        downloads if _number(downloads) else "", completions if _number(completions) else "", rate, duration,
        meta.get("likes", ""), bounds.get("w", ""), bounds.get("h", ""),
        *("×" if building in excluded else "√" for building in BUILDINGS),
    ]


def export_puzzles(destination: Path, output: Path) -> int:
    """导出普通谜题的 20 列 CSV，按 ID 排序；失败保留原输出文件。"""
    if output.suffix.lower() != ".csv":
        raise ValueError("导出文件必须使用 .csv 扩展名。")
    rows = [_csv_row(puzzle, path) for path, puzzle in _read_library(destination)]
    if not rows:
        raise ValueError(f"没有可导出的本地谜题：{destination}")
    rows.sort(key=lambda row: row[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="", dir=output.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream)
            writer.writerow(COLUMNS)
            writer.writerows(rows)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return len(rows)
