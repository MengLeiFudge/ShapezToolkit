"""建筑与岛定义 id 的本地目录，用来判断一个蓝图条目在目标版本还认不认。

1.2 的定义 id 有三种来源：
- 资产里的完整字符串，例如各 ``...InternalVariant``，在 ``resources.assets`` 中明文可见；
- 工厂按前缀和后缀现场拼接，例如 ``Rail_Forward``、``SpaceBelt_Lift2UpLeft``；
- 运行时衍生的后缀，镜像建筑加 ``Mirrored``，翻转岛加 ``_Flipped``。

规则来自 ``BuildingDefinitionFactory.FromMeta``、``TrainNavigationIslandDefinitionFactory.Suffixes``、
``SpacePathIslandDefinitionFactory.Create``、``DefinitionIdExtensions.IslandFlippedSuffix`` 与
``SpacePathDefinitionData`` 的 ``LiftDirectionAffix`` / ``LiftChunksByLayer``（均为 1.2.0-rc3）。
其余内容在压缩过的 addressable bundle 里，字节扫描看不到，需要 UnityPy 才能补全。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "buildings.json"
ASSETS_RELATIVE = Path("shapez 2_Data") / "resources.assets"

RAIL_PREFIX = "Rail"
SPACE_PATH_PREFIXES = ("SpaceBelt", "SpacePipe")
RAIL_SUFFIXES = (
    "_Forward",
    "_LeftTurn",
    "_RightTurn",
    "_LeftFwdSplitter",
    "_RightFwdSplitter",
    "_YSplitter",
    "_YSplitterFlipped",
    "_TripleSplitter",
    "_TripleSplitterFlipped",
    "_LeftFwdMerger",
    "_RightFwdMerger",
    "_YMerger",
    "_TripleMerger",
)
SPACE_PATH_SUFFIXES = (
    "_Forward",
    "_LeftTurn",
    "_RightTurn",
    "_LeftFwdSplitter",
    "_RightFwdSplitter",
    "_YSplitter",
    "_TripleSplitter",
    "_LeftFwdMerger",
    "_RightFwdMerger",
    "_YMerger",
    "_TripleMerger",
)
LIFT_AFFIXES = ("Forward", "Backward", "Left", "Right")
LIFT_LAYERS = (1, 2)
MIRRORED_SUFFIX = "Mirrored"
FLIPPED_SUFFIX = "_Flipped"

ASSET_PATTERN = re.compile(rb"[A-Za-z0-9_]*InternalVariant|(?:Layout|Foundation)_[A-Za-z0-9_]*")
CHUNK_SIZE = 8 << 20
CHUNK_OVERLAP = 128


class Catalog:
    """一份 id 目录：资产里明文出现的 id 与按工厂规则生成的 id。"""

    def __init__(self, asset_ids: set[str], game_version: str = "") -> None:
        self.asset_ids = asset_ids
        self.game_version = game_version
        self.generated_ids = generated_ids()

    def resolve(self, name: str) -> str:
        """返回 ``asset``、``generated`` 或 ``unknown``。"""
        if name in self.asset_ids:
            return "asset"
        if name in self.generated_ids:
            return "generated"
        candidates = _candidates(name)[1:]
        if any(candidate in self.asset_ids or candidate in self.generated_ids for candidate in candidates):
            return "generated"
        return "unknown"

    def unknown(self, names: list[str]) -> list[str]:
        """过滤出目录里完全解析不到的 id，保持输入顺序。"""
        seen: list[str] = []
        for name in names:
            if name not in seen and self.resolve(name) == "unknown":
                seen.append(name)
        return seen


def generated_ids() -> set[str]:
    """按 1.2 的工厂命名规则生成轨道、太空带、太空管的岛定义 id。"""
    ids: set[str] = set()
    for suffix in RAIL_SUFFIXES:
        ids.add(f"{RAIL_PREFIX}{suffix}")
    for prefix in SPACE_PATH_PREFIXES:
        for suffix in SPACE_PATH_SUFFIXES:
            ids.add(f"{prefix}{suffix}")
        for layer in LIFT_LAYERS:
            for direction in ("Up", "Down"):
                for affix in LIFT_AFFIXES:
                    ids.add(f"{prefix}_Lift{layer}{direction}{affix}")
    return ids


def scan_assets(path: Path) -> set[str]:
    """扫描 ``resources.assets`` 的明文 id，压缩 bundle 不在此列。"""
    found: set[str] = set()
    with path.open("rb") as handle:
        tail = b""
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            window = tail + chunk
            found.update(match.decode("ascii") for match in ASSET_PATTERN.findall(window))
            tail = window[-CHUNK_OVERLAP:]
    return found


def sync(game_dir: Path) -> Catalog:
    """从安装版抽取 id 并写回 ``data/buildings.json``。"""
    assets = game_dir / ASSETS_RELATIVE if game_dir.is_dir() else game_dir
    if not assets.is_file():
        raise FileNotFoundError(f"找不到 {assets}")
    version_file = game_dir / "version"
    game_version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else ""
    catalog = Catalog(scan_assets(assets), game_version)
    payload = {
        "game_version": catalog.game_version,
        "source": "shapez 2_Data/resources.assets 明文扫描，压缩 bundle 内的定义不在其中",
        "asset_ids": sorted(catalog.asset_ids),
        "generated_rules": "Rail/SpaceBelt/SpacePipe 前后缀与 Lift 规则见 catalog.py",
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return catalog


def load() -> Catalog:
    """读取已落盘的目录；缺失时返回只含生成规则的目录。"""
    if not DATA_PATH.is_file():
        return Catalog(set())
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return Catalog(set(payload.get("asset_ids", [])), str(payload.get("game_version", "")))


def _candidates(name: str) -> list[str]:
    """列出 id 本身与去掉运行时后缀后的候选，去重保序。"""
    candidates = [name]
    for suffix in (MIRRORED_SUFFIX, FLIPPED_SUFFIX):
        for candidate in list(candidates):
            if candidate.endswith(suffix):
                stripped = candidate[: -len(suffix)]
                if stripped not in candidates:
                    candidates.append(stripped)
    return candidates
