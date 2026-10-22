"""将已确认的本地一代模组交给 QQBot，同步固定群文件夹。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from common.io import save_json
from .mod_library import mod_filename

PUBLISH_URL = "http://127.0.0.1:8080/admin/api/artifacts/shapez1-mods"


def publish_mods(destination: Path, progress=print) -> dict[str, Any]:
    """顺序同步当前清单，失败即保存进度并停止；重跑由机器人状态去重。

    机器人拥有群文件 ID、上传中状态和旧版清理记录。本地不推断远端上传
    是否成功，也不自动重试可能已经产生群文件的请求。
    """
    destination = destination.resolve()
    manifest = json.loads((destination / "catalog/current-mods.json").read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or not isinstance(manifest.get("mods"), list) or not isinstance(manifest.get("retired"), list)):
        raise ValueError("当前模组清单无效，请先执行 mods clean 或 mods download。")
    requests = []
    seen = set()
    for item in manifest["mods"] + manifest["retired"]:
        if not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] <= 0 or item["id"] in seen:
            raise ValueError("模组清单中存在无效或重复 ID，请重新生成清单。")
        seen.add(item["id"])
    for item in manifest["mods"]:
        path = (destination / str(item.get("path") or "")).resolve()
        if path.parent != destination / "downloads" or not path.is_file():
            raise ValueError(f"模组 {item['id']} 的文件不在 downloads 中或已缺失，请重新生成清单。")
        requests.append({"id": item["id"], "file_id": item["file_id"], "path": str(path),
                         "name": mod_filename(item), "sha256": item["sha256"]})
    requests.extend({"id": item["id"], "retired": True} for item in manifest["retired"])
    report: dict[str, Any] = {"started_at": datetime.now(timezone.utc).isoformat(),
                              "uploaded": 0, "skipped": 0, "deleted": 0, "results": []}
    report_path = destination / "catalog/qqbot-last-run.json"
    opener = build_opener(ProxyHandler({}))
    try:
        for item in requests:
            progress(f"正在同步群文件：{item['id']} {item.get('name', '清理已跟踪的废弃包')}")
            request = Request(PUBLISH_URL, data=json.dumps(item, ensure_ascii=False).encode("utf-8"),
                              headers={"Content-Type": "application/json"}, method="POST")
            try:
                # 单个上传最多 900 秒；额外时间留给目录查询、确认及旧版删除。
                with opener.open(request, timeout=1100) as response:
                    raw = response.read(65537)
                if len(raw) > 65536:
                    raise RuntimeError("QQBot 响应超过大小限制。")
                result = json.loads(raw)
                if (not isinstance(result, dict) or result.get("ok") is not True or result.get("id") != item["id"]
                        or any(type(result.get(key)) is not int or result[key] < 0 for key in ("uploaded", "skipped", "deleted"))):
                    raise RuntimeError("QQBot 未返回有效同步结果，不能确认上传状态。")
            except HTTPError as exc:
                with exc:
                    raw = exc.read(65536)
                try:
                    detail = str(json.loads(raw).get("detail") or f"HTTP {exc.code}")
                except (ValueError, AttributeError):
                    detail = f"HTTP {exc.code}"
                raise RuntimeError(f"模组 {item['id']} 同步失败：{detail}") from None
            except (URLError, OSError, HTTPException) as exc:
                raise RuntimeError(f"无法完成 QQBot 同步：{exc}；请确认云栖已启动，结果不确定时不要手工重复上传。") from None
            report["results"].append(result)
            for key in ("uploaded", "skipped", "deleted"):
                report[key] += result[key]
            save_json(report_path, report)
        report["complete"] = True
    except (RuntimeError, ValueError, OSError) as exc:
        report["error"] = str(exc)
        raise
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_json(report_path, report)
    return report
