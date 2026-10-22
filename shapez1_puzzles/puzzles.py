"""一代谜题认证与下载；仅 refresh_token 会启动 Steam 认证流程。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from common.io import RequestError, request_json, save_json

API_URL = "https://api.shapez.io/v1"
API_KEY = "d5c54aaa491f200709afff082c153ef2"
RESULT_PREFIX = "SHAPEZ_AUTH_RESULT "


def refresh_token(game_dir: Path, token_file: Path) -> None:
    """通过已登录的 Windows Steam 获取新 token；成功后替换凭据，失败保留原值。"""
    if os.name != "nt":
        raise RuntimeError("请在 Windows 的 Python 中运行获取程序，使用本机已登录的 Steam。")
    game_dir = game_dir.resolve()
    executable = game_dir / "shapezio.exe"
    native_dir = game_dir / "resources/app.asar.unpacked/node_modules/shapez.io-private-artifacts/steam"
    if not executable.is_file() or not (native_dir / "greenworks.js").is_file():
        raise FileNotFoundError(f"没有找到一代游戏或 Steam 组件，请检查 common/settings.py 中的 STEAM_GAME_DIR：{game_dir}")
    if (game_dir / "steam_appid.txt").read_text(encoding="utf-8").strip() != "1318690":
        raise RuntimeError(f"{game_dir} 不是预期的 shapez 一代安装目录。")
    environment = os.environ.copy()
    environment.update(ELECTRON_RUN_AS_NODE="1", SteamAppId="1318690", SteamGameId="1318690")
    # 游戏自带 Electron 与 Greenworks 的原生 ABI 一致；Node 模式不会创建游戏窗口。
    helper = Path(__file__).with_name("steam_login.cjs")
    try:
        result = subprocess.run(
            [str(executable), str(helper)], cwd=game_dir, env=environment,
            capture_output=True, timeout=55, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("获取 token 超时，已结束认证进程，原 token 保持不变。") from None
    messages = [line[len(RESULT_PREFIX):] for line in result.stdout.decode("utf-8", errors="replace").splitlines()
                if line.startswith(RESULT_PREFIX)]
    if len(messages) != 1:
        raise RuntimeError("认证组件未返回结果，请确认游戏安装完整且支持 Electron 的 Node 模式。")
    try:
        response = json.loads(messages[0])
    except ValueError:
        raise RuntimeError("认证组件返回了无效数据，原 token 保持不变。") from None
    if not isinstance(response, dict):
        raise RuntimeError("认证组件返回格式不正确，原 token 保持不变。")
    if result.returncode != 0 or response.get("ok") is not True:
        raise RuntimeError(response.get("error") or "认证失败，原 token 保持不变。")
    token = response.get("token")
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise RuntimeError("认证组件未返回有效 token，原 token 保持不变。")
    save_json(token_file, {"token": token, "obtained_at": datetime.now(timezone.utc).isoformat()})


def download_puzzle(code: str, token_file: Path, destination: Path) -> Path:
    """用已有 token 下载一个谜题，code 为数字 ID 或图形短代码，返回本地 JSON 路径。"""
    code = str(code).strip()
    if not code or len(code) > 200 or re.fullmatch(r"[A-Za-z0-9:_-]+", code) is None:
        raise ValueError("谜题标识必须是数字 ID 或游戏提供的图形短代码。")
    try:
        credentials = json.loads(token_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError("尚未保存 token，请运行 python main.py puzzles token。") from None
    except (ValueError, UnicodeError):
        raise RuntimeError(f"凭据文件格式无效，请重新获取 token：{token_file}") from None
    token = credentials.get("token") if isinstance(credentials, dict) else None
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise RuntimeError(f"凭据文件缺少有效 token，请重新获取：{token_file}")
    try:
        puzzle = request_json(f"{API_URL}/puzzles/download/{quote(code, safe='')}", {
            "Accept": "application/json", "x-api-key": API_KEY, "x-token": token,
        })
    except RequestError as exc:
        if exc.status in (401, 403):
            raise RuntimeError("谜题下载认证被拒绝，请运行 python main.py puzzles token 后重试。") from None
        raise
    if not isinstance(puzzle.get("game"), dict) or not isinstance(puzzle.get("meta"), dict):
        raise RequestError("服务器返回的数据不包含有效的谜题 game/meta 对象，未保存。")
    # Windows 文件名不允许冒号；摘要保留不同短代码的区分，避免替换字符引起碰撞。
    name = code if code.isdecimal() else hashlib.sha256(code.encode("utf-8")).hexdigest()[:24]
    path = destination / f"p.{name}.json"
    save_json(path, puzzle)
    return path
