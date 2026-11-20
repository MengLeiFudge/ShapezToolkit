"""管理一代模组的本地命名、最新版清单和可恢复清理。"""

from __future__ import annotations

import hashlib
import html
import json
import re
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.io import save_json


def load_catalog(destination: Path) -> dict[str, Any]:
    """读取下载清单，缺失时建立空结构，损坏时停止而不覆盖。"""
    path = destination / "catalog/download-state.json"
    if not path.exists():
        return {"mods": {}, "retired": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("mods"), dict):
        raise ValueError(f"下载清单结构无效：{path}")
    state.setdefault("retired", {})
    if not isinstance(state["retired"], dict):
        raise ValueError(f"废弃模组清单结构无效：{path}")
    return state


def retirement_reason(mod: dict[str, Any]) -> str:
    """仅识别模组自身明确的弃用或失效声明，不以更新时间或请求失败推断。"""
    title = html.unescape(str(mod.get("name") or ""))
    marker = r"deprecated|obsolete|discontinued|abandoned|not longer working|no longer works|已废弃|已弃用|停止维护"
    match = re.search(rf"\b(?:{marker})\b", title, re.IGNORECASE)
    if match:
        return f"名称标记：{match.group()}"
    for tag in mod.get("tags") or []:
        value = str(tag.get("name", "")) if isinstance(tag, dict) else str(tag)
        if re.fullmatch(marker, value.strip(), re.IGNORECASE):
            return f"标签：{value}"
    text = str(mod.get("summary") or "") + "\n" + str(mod.get("description_plaintext") or "")
    for sentence in re.split(r"[.!?。！？\n]+", html.unescape(text)):
        sentence = sentence.strip()
        if re.match(r"^(?:(?:this mod|it) (?:is|has been) )?(?:now )?(?:deprecated|obsolete|discontinued|abandoned)\b", sentence, re.IGNORECASE):
            return f"作者说明：{sentence}"
    return ""


def mod_filename(mod: dict[str, Any]) -> str:
    """生成名称_版本.zip；网站 ID 保留在清单中。"""
    name = html.unescape(str(mod.get("name") or mod["id"]))
    version = str(mod.get("version") or "unversioned")
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", f"{name}_{version}")
    return (stem.strip(" .")[:160] or str(mod["id"])) + ".zip"


def archive_info(path: Path) -> dict[str, Any]:
    """读取 ZIP 内文件的 SHA-256；不解压到磁盘，也不执行模组代码。"""
    entries = []
    with zipfile.ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 1024 ** 3:
            raise ValueError("ZIP 展开内容超过 1 GiB，无法自动整理")
        for item in archive.infolist():
            if item.is_dir():
                continue
            digest = hashlib.sha256()
            with archive.open(item) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            entries.append((item.filename, item.file_size, digest.hexdigest()))
    if not entries:
        raise ValueError("ZIP 中没有文件")
    digest, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            md5.update(chunk)
    return {
        "path": path, "bytes": path.stat().st_size, "sha256": digest.hexdigest(), "md5": md5.hexdigest(),
        "content": hashlib.sha256(json.dumps(sorted(entries), ensure_ascii=False).encode()).hexdigest(),
    }


def clean_library(destination: Path, state: dict[str, Any], progress: Callable[[str], None] = print) -> dict[str, Any]:
    """保留每个已确认模组的当前包；重复、旧版及废弃包移至恢复目录。"""
    destination = destination.resolve()
    downloads = destination / "downloads"
    state.setdefault("retired", {})
    for key, record in list(state["mods"].items()):
        reason = retirement_reason(record)
        if reason:
            state["retired"][key] = {**record, "reason": reason}
            del state["mods"][key]
    records = {**state["mods"], **state["retired"]}
    infos: dict[Path, dict[str, Any]] = {}
    report: dict[str, Any] = {"duplicates": 0, "obsolete": 0, "retired": 0, "renamed": 0, "unreadable": [], "unmanaged": []}
    packages = [*downloads.glob("*.zip"), *downloads.glob(".pending/*/*.zip")]
    for path in sorted(packages):
        try:
            infos[path] = archive_info(path)
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
            report["unreadable"].append({"name": path.name, "error": str(exc)})
            progress(f"保留无法读取的文件：{path.name}；{exc}")

    # 清单指向并通过校验的文件才算已落地的当前版本；更新失败时不删除旧版。
    current: dict[str, dict[str, Any]] = {}
    owners: dict[Path, set[str]] = {path: set() for path in infos}
    for key, record in records.items():
        relative = Path(str(record.get("path") or ""))
        path = (destination / relative).resolve()
        if path in infos:
            owners[path].add(key)
            expected = record.get("local_md5") or record.get("md5")
            if key in state["mods"] and infos[path]["md5"] == expected:
                current[key] = infos[path]
    # ID 前缀可准确归属旧文件；普通名称仅在唯一匹配时归属。
    for path in infos:
        if owners[path]:
            continue
        prefix = re.match(r"^(\d+)_\d+_", path.name)
        if prefix and prefix[1] in records:
            owners[path].add(prefix[1])
            continue
        candidates = []
        for key, record in records.items():
            name = html.unescape(str(record.get("name") or ""))
            stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
            if stem and html.unescape(path.name).casefold().startswith(stem.casefold() + "_"):
                candidates.append(key)
        if len(candidates) == 1:
            owners[path].add(candidates[0])

    groups: dict[str, list[dict[str, Any]]] = {}
    for info in infos.values():
        groups.setdefault(info["content"], []).append(info)
    removed: dict[Path, str] = {}
    kept: list[tuple[dict[str, Any], list[str]]] = []
    for content, group in groups.items():
        active = [key for key, info in current.items() if info["content"] == content]
        ids = set().union(*(owners[item["path"]] for item in group))
        if ids and not active and ids.issubset(state["retired"]):
            for item in group:
                removed[item["path"]] = "retired"
            continue
        if ids and not active and all(key in current or key in state["retired"] for key in ids):
            for item in group:
                removed[item["path"]] = "obsolete"
            continue
        preferred = [current[key] for key in active]
        keeper = min(preferred or group, key=lambda item: (item["bytes"], item["path"].name))
        kept.append((keeper, active))
        if not active:
            report["unmanaged"].append(keeper["path"].name)
        for item in group:
            if item["path"] != keeper["path"]:
                removed[item["path"]] = "duplicates"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    # 重复、旧版及废弃包移入所属数据目录的 trash 下保留恢复清单。
    trash = destination / "trash" / f"mods-{stamp}"
    moves = []
    for path, reason in removed.items():
        moves.append({"source": str(path), "target": str(trash / path.relative_to(downloads)), "reason": reason, "sha256": infos[path]["sha256"]})
        report[reason] += 1
    reserved = {path.name.casefold() for path in downloads.iterdir() if path not in removed} if downloads.exists() else set()
    for info, active in kept:
        old = info["path"]
        if active:
            key = sorted(active, key=int)[0]
            name = mod_filename(state["mods"][key])
            if old.parent == downloads:
                reserved.discard(old.name.casefold())
            if name.casefold() in reserved:
                raise ValueError(f"模组文件名冲突，未执行清理：{name}")
            reserved.add(name.casefold())
            target = old if old.parent == downloads and name.casefold() == old.name.casefold() else downloads / name
            if target != old:
                moves.append({"source": str(old), "target": str(target), "reason": "renamed", "sha256": info["sha256"]})
                report["renamed"] += 1
            info["final_path"] = target
            for owner in active:
                state["mods"][owner].update(
                    path=target.relative_to(destination).as_posix(), local_md5=info["md5"],
                    local_bytes=info["bytes"], sha256=info["sha256"], content_sha256=info["content"],
                )
    if moves:
        trash.mkdir(parents=True)
        save_json(trash / "moves.json", {"moves": moves})
        old_catalog = destination / "catalog/download-state.json"
        if old_catalog.exists():
            save_json(trash / "catalog-before.json", json.loads(old_catalog.read_text(encoding="utf-8")))
        for move in moves:
            source, target = Path(move["source"]), Path(move["target"])
            if target.exists():
                raise FileExistsError(f"目标已存在，未覆盖：{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
        progress(f"本地整理：重复 {report['duplicates']}，旧版 {report['obsolete']}，废弃包 {report['retired']}，改名 {report['renamed']}。")
        report["recovery_path"] = str(trash)
    if report["unmanaged"]:
        progress(f"保留 {len(report['unmanaged'])} 个尚无当前版本记录的历史包，不列入上传清单。")
    state["last_cleanup"] = report
    save_json(destination / "catalog/download-state.json", state)
    # 上传端读取稳定 ID 和内容哈希；文件名仅用于展示，未确认的历史包不进入上传清单。
    publish = []
    for key in sorted(current, key=int):
        record = state["mods"][key]
        publish.append({field: record.get(field) for field in (
            "id", "file_id", "name", "version", "path", "sha256", "content_sha256", "local_bytes",
        )})
    save_json(destination / "catalog/current-mods.json", {
        "schema_version": 1, "mods": publish,
        "retired": [{"id": item["id"], "name": item["name"], "reason": item["reason"]} for item in state["retired"].values()],
    })
    return report


def clean_mods(destination: Path, progress: Callable[[str], None] = print) -> dict[str, Any]:
    """根据已保存清单整理本地文件，不联网。"""
    return clean_library(destination, load_catalog(destination), progress)
