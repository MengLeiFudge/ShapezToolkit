"""二代蓝图网页工具的公开入口：编解码、结构统计与版本升级。"""

from .codec import Blueprint, BlueprintError, build_custom_data, decode, encode, read_custom_data, summarize
from .upgrade import TARGET_FORMAT, TARGET_VERSION, UpgradeReport, upgrade

__all__ = [
    "Blueprint",
    "BlueprintError",
    "TARGET_FORMAT",
    "TARGET_VERSION",
    "UpgradeReport",
    "build_custom_data",
    "decode",
    "encode",
    "read_custom_data",
    "summarize",
    "upgrade",
]
