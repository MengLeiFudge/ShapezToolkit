"""按 mod.io 网站的匿名浏览流程同步一代模组及本地清单。"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import quote, urlencode

from common.io import RequestError, download_file, file_matches, request_json, save_json
from .mod_library import clean_library, load_catalog, mod_filename, retirement_reason

WEBSITE_API = "https://mod.io/v1/games/@shapez/mods"
WEBSITE_HEADERS = {
    "Accept": "application/json",
    "X-Modio-Origin": "web",
    "Referer": "https://mod.io/g/shapez",
}


T = TypeVar("T")
MAX_ATTEMPTS = 4


def with_retries(operation: Callable[[], T], label: str, progress: Callable[[str], None]) -> T:
    """对临时网络或校验失败最多尝试四次，每次重新开始该项操作。"""
    for attempt in range(1, MAX_ATTEMPTS):
        try:
            return operation()
        except RequestError as exc:
            if not exc.retryable:
                raise
            delay = 2 ** attempt
            progress(f"重试：{label}；{exc} {delay} 秒后进行第 {attempt + 1}/{MAX_ATTEMPTS} 次尝试。")
            # 退避给网络和远端服务恢复时间；不重试认证、格式或本地磁盘错误。
            time.sleep(delay)
    return operation()


def iter_mods(progress: Callable[[str], None] = print) -> Iterator[dict[str, Any]]:
    """依次读取网站的公开模组分页，检查分页停滞和返回格式。"""
    offset = 0
    seen: set[int] = set()
    while True:
        query = urlencode({"_offset": offset, "_limit": 100, "_sort": "id"})
        page = with_retries(
            lambda: request_json(f"{WEBSITE_API}?{query}", WEBSITE_HEADERS),
            f"获取模组列表（offset={offset}）", progress,
        )
        items = page.get("data")
        count, total, actual = (page.get(key) for key in ("result_count", "result_total", "result_offset"))
        if (not isinstance(items, list) or type(count) is not int or type(total) is not int
                or type(actual) is not int or actual != offset or count != len(items)
                or total < 0 or count < 0 or (count == 0 and offset < total)):
            raise RequestError(f"网站模组分页格式不符合预期（offset={offset}），已停止同步。")
        for mod in items:
            if not isinstance(mod, dict) or type(mod.get("id")) is not int or mod["id"] <= 0:
                raise RequestError("网站返回了缺少有效 ID 的模组。")
            if mod["id"] in seen:
                raise RequestError("网站列表出现重复模组，分页可能发生变化，请重新运行。")
            seen.add(mod["id"])
            yield mod
        offset += count
        if offset >= total:
            return


def get_modfile(mod: dict[str, Any]) -> dict[str, Any]:
    """返回当前发布文件，必要时从模组详情补全下载元数据。"""
    file = mod.get("modfile")
    if file is None:
        name = mod.get("name_id")
        if not isinstance(name, str) or not name:
            raise RequestError("模组缺少网站名称，无法读取文件详情。")
        detail = request_json(f"{WEBSITE_API}/@{quote(name, safe='')}", WEBSITE_HEADERS)
        file = detail.get("modfile")
    if not isinstance(file, dict):
        raise RequestError("该模组没有可下载的当前发布文件。")
    return file


def file_metadata(file: dict[str, Any]) -> tuple[int, int, str, str]:
    """校验下载需要的文件 ID、大小、MD5 和地址。"""
    file_id, size = file.get("id"), file.get("filesize")
    hashes, download = file.get("filehash"), file.get("download")
    if type(file_id) is not int or file_id <= 0 or type(size) is not int or size <= 0:
        raise RequestError("模组文件缺少有效的 ID 或大小。")
    md5 = hashes.get("md5") if isinstance(hashes, dict) else None
    url = download.get("binary_url") if isinstance(download, dict) else None
    if not isinstance(md5, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", md5):
        raise RequestError("模组文件缺少有效 MD5，无法核对下载结果。")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RequestError("模组文件缺少有效的 HTTPS 下载地址。")
    return file_id, size, md5.lower(), url


def fresh_download_url(mod: dict[str, Any], file_id: int) -> str:
    """从网站文件详情获取指定文件的新下载地址，保持校验对象不变。"""
    name = mod.get("name_id")
    if not isinstance(name, str) or not name:
        raise RequestError("模组缺少网站名称，无法更新下载地址。")
    file = request_json(f"{WEBSITE_API}/@{quote(name, safe='')}/files/{file_id}", WEBSITE_HEADERS)
    actual_id, _, _, url = file_metadata(file)
    if actual_id != file_id:
        raise RequestError("网站返回了不同的模组文件，已停止本项下载。")
    return url


def sync_mod(mod: dict[str, Any], destination: Path, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """同步一个模组，完整的同版本本地文件直接复用。"""
    destination = destination.resolve()
    file = get_modfile(mod)
    file_id, size, md5, url = file_metadata(file)
    name = str(mod.get("name") or mod["id"])
    path = destination / "downloads" / mod_filename({"id": mod["id"], "name": name, "version": file.get("version")})
    local_size, local_md5 = size, md5
    reused = file_matches(path, size, md5)
    if not reused and previous and previous.get("file_id") == file_id and previous.get("md5") == md5:
        old_path = (destination / str(previous.get("path") or "")).resolve()
        if old_path.parent == (destination / "downloads").resolve():
            old_size = previous.get("local_bytes", previous.get("bytes"))
            old_md5 = previous.get("local_md5", previous.get("md5"))
            if file_matches(old_path, old_size, old_md5):
                path, reused, local_size, local_md5 = old_path, True, old_size, old_md5
    if not reused and path.exists():
        # 同名不同内容不能覆盖；新文件完整落地后由本地整理移走旧版。
        path = destination / "downloads/.pending" / f"{mod['id']}-{file_id}" / path.name
    if not reused:
        # 历史模组包没有 ID 文件名，按内容识别，避免迁移后重复下载相同文件。
        for candidate in sorted((destination / "downloads").glob("*.zip")):
            if candidate != path and file_matches(candidate, size, md5):
                path, reused = candidate, True
                break
    if not reused:
        expires = file["download"].get("date_expires")
        if isinstance(expires, (int, float)) and expires <= time.time() + 30:
            url = fresh_download_url(mod, file_id)
        try:
            download_file(url, path, size, md5)
        except RequestError as exc:
            if exc.status not in (401, 403):
                raise
            # 列表中的签名地址可能在排队期间过期，仅重新获取一次同文件地址。
            url = fresh_download_url(mod, file_id)
            download_file(url, path, size, md5)
    return {
        "id": mod["id"], "name": name, "summary": mod.get("summary"),
        "profile_url": mod.get("profile_url"), "tags": mod.get("tags"),
        "stats": mod.get("stats"), "file_id": file_id, "version": file.get("version"),
        "bytes": size, "md5": md5, "path": path.relative_to(destination).as_posix(),
        "local_bytes": local_size, "local_md5": local_md5,
        "status": "skipped" if reused else "downloaded",
    }


def sync_mods(destination: Path, progress: Callable[[str], None] = print) -> dict[str, Any]:
    """下载全部公开模组的当前文件，逐项保存结果；列表失败时保留已完成记录。"""
    destination = destination.resolve()
    state_file = destination / "catalog" / "download-state.json"
    state = load_catalog(destination)
    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "downloaded": 0, "skipped": 0, "failed": 0, "retired": 0,
        "listing_complete": False, "errors": [],
    }
    state["last_run"] = report
    save_json(state_file, state)
    try:
        for mod in iter_mods(progress):
            label = f"{mod['id']} {mod.get('name') or ''}"
            try:
                key = str(mod["id"])
                reason = retirement_reason(mod)
                if reason:
                    state["retired"][key] = {
                        **state["mods"].pop(key, {}), "id": mod["id"], "name": mod.get("name"),
                        "summary": mod.get("summary"), "reason": reason,
                    }
                    report["retired"] += 1
                    progress(f"跳过已废弃模组：{label}；{reason}")
                    save_json(state_file, state)
                    continue
                state["retired"].pop(key, None)
                previous = state["mods"].get(key)
                record = with_retries(lambda: sync_mod(mod, destination, previous), label, progress)
            except (RequestError, OSError, ValueError) as exc:
                report["failed"] += 1
                report["errors"].append({"id": mod["id"], "name": mod.get("name"), "error": str(exc)})
                progress(f"失败：{label}；{exc}")
            else:
                state["mods"][str(mod["id"])] = record
                report[record["status"]] += 1
                progress(f"{'已存在' if record['status'] == 'skipped' else '已下载'}：{label}")
            # 每项完成即保存；中断后可重新运行并核对已下载文件。
            save_json(state_file, state)
        report["listing_complete"] = True
    except (RequestError, OSError, ValueError) as exc:
        report["listing_error"] = str(exc)
        raise
    finally:
        report["cleanup"] = clean_library(destination, state, progress)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_json(state_file, state)
    return report
