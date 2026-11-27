"""blueprint_web 的命令行：解析、升级与批量核对二代蓝图。

默认打印概览；``--decode`` 打印文档 JSON，``--upgrade`` 另存升级结果，
``--verify`` 对目录内全部蓝图做解析、往返与升级核对。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .codec import Blueprint, BlueprintError, decode, encode, summarize
from .upgrade import TARGET_FORMAT, TARGET_VERSION, UpgradeReport, upgrade

BLUEPRINT_SUFFIX = ".spz2bp"


def main(argv: list[str] | None = None) -> int:
    """按子模式分派；蓝图损坏时逐条报告并返回非零退出码。"""
    parser = argparse.ArgumentParser(prog="tmam2 web", description="解析、升级与核对二代蓝图（.spz2bp）。")
    parser.add_argument("paths", nargs="+", type=Path, metavar="PATH", help="蓝图文件或包含蓝图的目录")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--decode", action="store_true", help="打印解析后的文档 JSON")
    mode.add_argument("--upgrade", action="store_true", help="升级到本机最新游戏版本并另存")
    mode.add_argument("--verify", action="store_true", help="批量核对目录内蓝图的解析、往返与升级")
    parser.add_argument("--output-dir", type=Path, help="升级结果目录；默认写到输入文件旁的 upgraded/")
    args = parser.parse_args(argv)

    try:
        files = expand(args.paths)
    except OSError as exc:
        print(f"无法读取输入：{exc}")
        return 1
    if not files:
        print("没有找到 .spz2bp 文件。")
        return 1
    if args.verify:
        return verify(files)
    if args.decode:
        return show(files)
    return run_upgrade(files, args.output_dir)


def expand(paths: list[Path]) -> list[Path]:
    """展开文件与目录，目录按后缀递归收集并保持稳定顺序。"""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(item for item in path.rglob(f"*{BLUEPRINT_SUFFIX}") if item.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            raise OSError(f"路径不存在：{path}")
    return files


def show(files: list[Path]) -> int:
    """打印蓝图统计；单个文件时再打印完整文档树。"""
    failed = 0
    for path in files:
        try:
            blueprint = decode(path.read_text(encoding="utf-8"))
        except (BlueprintError, OSError) as exc:
            print(f"{path.name}：{exc}")
            failed += 1
            continue
        print(f"{path.name}：{json.dumps(summarize(blueprint), ensure_ascii=False)}")
        if len(files) == 1:
            print(json.dumps(blueprint.document, ensure_ascii=False, indent=2))
    if len(files) > 1:
        print("只输出统计；要看完整文档树就只传一个文件。")
    return int(bool(failed))


def run_upgrade(files: list[Path], output_dir: Path | None) -> int:
    """升级并另存，逐文件打印报告摘要。"""
    failed = 0
    for path in files:
        target_dir = output_dir or path.parent / "upgraded"
        try:
            blueprint = decode(path.read_text(encoding="utf-8"))
            upgraded, report = upgrade(blueprint)
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / path.name
            target.write_text(encode(upgraded), encoding="utf-8")
        except (BlueprintError, OSError) as exc:
            print(f"{path.name}：{exc}")
            failed += 1
            continue
        print(f"{path.name} → {target}：{_report_line(report)}")
    return int(bool(failed))


def verify(files: list[Path]) -> int:
    """批量核对解析、编解码往返与升级结果。"""
    parsed = roundtrip = upgraded_count = 0
    versions: dict[int, int] = {}
    formats: dict[int, int] = {}
    failures: list[str] = []
    for path in files:
        try:
            blueprint = decode(path.read_text(encoding="utf-8"))
            parsed += 1
            formats[blueprint.format_version] = formats.get(blueprint.format_version, 0) + 1
            versions[blueprint.version] = versions.get(blueprint.version, 0) + 1
            if decode(encode(blueprint, compresslevel=1)).document == blueprint.document:
                roundtrip += 1
            upgraded, _ = upgrade(blueprint)
            restored = decode(encode(upgraded, compresslevel=1))
            if restored.document != upgraded.document or restored.format_version != TARGET_FORMAT:
                failures.append(f"{path.name}：升级后回读不一致")
            elif upgraded.document.get("V") != TARGET_VERSION:
                failures.append(f"{path.name}：升级后版本号不是 {TARGET_VERSION}")
            else:
                upgraded_count += 1
        except (BlueprintError, OSError, ValueError) as exc:
            failures.append(f"{path.name}：{exc}")
    print(
        f"共 {len(files)} 个蓝图：解析 {parsed}，往返一致 {roundtrip}，"
        f"升级到 {TARGET_VERSION} / 封装 {TARGET_FORMAT} {upgraded_count}，失败 {len(failures)}"
    )
    print("封装分布：" + "，".join(f"{key}×{value}" for key, value in sorted(formats.items())))
    print("版本分布：" + "，".join(f"{key}×{value}" for key, value in sorted(versions.items())))
    for item in failures[:10]:
        print(f"失败：{item}")
    return int(bool(failures))


def _report_line(report: UpgradeReport) -> str:
    """把报告压成一行：应用了哪些步骤、还有哪些没实现。"""
    applied = [step.name for step in report.steps if step.status == "applied"]
    line = f"V {report.source_version} → {TARGET_VERSION}，应用 {len(applied)} 项"
    if report.unsupported:
        line += "；未实现 " + "、".join(step.name for step in report.unsupported)
    return line
