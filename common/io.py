"""下载模块共用的网络读取、文件校验和原子写入。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import tempfile
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ShapezToolkit/1.0"
TIMEOUT = 30
MAX_JSON_BYTES = 32 * 1024 * 1024


class RequestError(RuntimeError):
    """携带 HTTP 状态码和重试分类的失败，不包含认证头或响应原文。"""

    def __init__(self, message: str, status: int | None = None, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable or status in (408, 425, 429, 500, 502, 503, 504)


def network_error(exc: Exception) -> RequestError:
    """保留网络底层原因，隐藏可能带签名的 URL；证书验证失败不重试。"""
    reason = exc.reason if isinstance(exc, URLError) else exc
    detail = re.sub(r"https?://\S+", "<地址>", str(reason)).replace("\n", " ").replace("\r", " ")
    return RequestError(
        f"网络连接失败（{type(reason).__name__}：{detail}）。",
        retryable=not isinstance(reason, ssl.SSLCertVerificationError),
    )


def request_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    """读取有大小上限的 JSON 对象，拒绝 HTTP 错误、HTML 和非对象响应。"""
    request = Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_JSON_BYTES + 1)
    except HTTPError as exc:
        exc.close()
        raise RequestError(f"服务器返回 HTTP {exc.code}。", exc.code) from None
    except (URLError, OSError, HTTPException) as exc:
        raise network_error(exc) from None
    if len(raw) > MAX_JSON_BYTES:
        raise RequestError("服务器 JSON 响应超过 32 MiB，已停止读取。")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError):
        raise RequestError("服务器没有返回有效 JSON，可能需要在网站处理访问验证。") from None
    if not isinstance(result, dict):
        raise RequestError("服务器响应不是 JSON 对象。")
    if result.get("error"):
        raise RequestError("服务器拒绝了请求，请检查访问权限或凭据。")
    return result


def save_json(path: Path, value: Any) -> None:
    """在同一目录写入临时文件后替换目标；失败时保留原文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def file_matches(path: Path, size: int, md5: str) -> bool:
    """按 mod.io 提供的大小与 MD5 核对本地文件是否完整。"""
    if not path.is_file() or path.stat().st_size != size:
        return False
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == md5


def download_file(url: str, path: Path, size: int, md5: str) -> None:
    """流式下载并校验大小和 MD5，完整后才替换目标文件。"""
    if not url.startswith("https://"):
        raise ValueError("模组下载地址必须使用 HTTPS。")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=TIMEOUT) as response:
            if not response.geturl().startswith("https://"):
                raise RequestError("模组下载被重定向到非 HTTPS 地址。")
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".part", delete=False) as stream:
                temporary = Path(stream.name)
                count = 0
                digest = hashlib.md5(usedforsecurity=False)
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > size:
                        raise RequestError("下载内容大于网站声明的文件大小。")
                    stream.write(chunk)
                    digest.update(chunk)
                stream.flush()
                os.fsync(stream.fileno())
        if count != size or digest.hexdigest() != md5:
            raise RequestError("下载文件的大小或 MD5 不匹配。", retryable=True)
        os.replace(temporary, path)
    except HTTPError as exc:
        exc.close()
        raise RequestError(f"下载服务器返回 HTTP {exc.code}。", exc.code) from None
    except (URLError, TimeoutError, ConnectionError, ssl.SSLError, HTTPException) as exc:
        raise network_error(exc) from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
