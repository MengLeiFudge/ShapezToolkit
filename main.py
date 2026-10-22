"""ShapezToolkit 的统一命令入口。"""

import argparse
import json
from pathlib import Path

from common.settings import MOD_DIR, PUZZLE_DIR, STEAM_GAME_DIR, TOKEN_FILE
from shapez1_mods.mods import sync_mods
from shapez1_mods.mod_library import clean_mods
from shapez1_mods.mod_publish import publish_mods
from shapez1_puzzles.puzzles import download_puzzle, refresh_token
from shapez1_puzzles.puzzle_library import export_puzzles, find_puzzles
from shapez1_tmam.tmam_verify import verify_saves


def build_parser() -> argparse.ArgumentParser:
    """按模组、谜题与 TMAM 分组定义命令，缺少必填参数时由 argparse 显示帮助。"""
    parser = argparse.ArgumentParser(description="Shapez 工具箱：模组同步、谜题资料与 TMAM 拆解、验证。")
    tools = parser.add_subparsers(dest="tool", required=True)

    mods = tools.add_parser("mods", help="一代模组")
    mod_commands = mods.add_subparsers(dest="command", required=True)
    mod_commands.add_parser("download", help="同步未废弃模组，每个模组保留一个当前版本")
    mod_commands.add_parser("clean", help="按已有清单整理本地包，清理重复、旧版和明确废弃包")
    mod_commands.add_parser("update", help="下载当前模组并通过 QQBot 同步到指定群文件夹")
    mod_commands.add_parser("publish", help="将已确认的本地模组通过 QQBot 同步到指定群文件夹")

    puzzles = tools.add_parser("puzzles", help="一代谜题下载、查询与导出")
    puzzle_commands = puzzles.add_subparsers(dest="command", required=True)
    puzzle_commands.add_parser("token", help="通过已登录的 Steam 获取并保存新 token")
    download = puzzle_commands.add_parser("download", help="用已有 token 下载指定谜题，首次使用时先获取 token")
    download.add_argument("codes", nargs="+", metavar="CODE", help="谜题数字 ID 或图形短代码，可填写多个")
    download.add_argument("--refresh-token", action="store_true", help="下载前主动获取并保存新 token")
    show = puzzle_commands.add_parser("show", help="按 ID 或短代码查询本地谜题，不联网")
    show.add_argument("code", metavar="CODE", help="谜题数字 ID 或图形短代码")
    export = puzzle_commands.add_parser("export", help="将普通本地谜题导出为 CSV，不联网")
    export.add_argument("--output", type=Path, default=PUZZLE_DIR / "catalog" / "puzzles.csv", help="输出 CSV 路径")
    tmam = tools.add_parser("tmam", help="一代 TMAM 图形拆解与存档电路验证")
    tmam_commands = tmam.add_subparsers(dest="command", required=True)
    verify = tmam_commands.add_parser("verify", help="按游戏 tick 规则穷举指定 TMAM 存档")
    verify.add_argument("--saves", type=Path, required=True, help="包含所选 TMAM 原始存档的目录")
    verify.add_argument("--output", type=Path, help="自定义报告根目录，按机器分目录；默认写到各机器的 verification 下")
    verify.add_argument("--machine", nargs="+", choices=("XianYu-20221129", "BugFix-20210622", "CTMAM"), default=("XianYu-20221129", "BugFix-20210622"), help="选择存档，默认 XianYu-20221129 BugFix-20210622；CTMAM 为 BugFix 旧名")
    verify.add_argument("--workers", type=int, default=8, help="并行进程数，1..32，默认 8")
    verify.add_argument("--max-ticks", type=int, default=4096, help="每阶段最大 tick 数；超时单独报告")
    solve = tmam_commands.add_parser("solve", help="用 XianYu-20221129 的逻辑拆解结构，输出部件与加工树，不查图形数据库")
    solve.add_argument("shape", type=int, help="16 位结构编号，1..65535，低四位为底层")
    solve.add_argument("--events", action="store_true", help="同时输出指令、模式和重试信号的变化 tick")
    solve.add_argument("--max-ticks", type=int, default=4096, help="每阶段最大 tick 数，默认 4096")
    return parser


def main() -> int:
    """分派命令并报告结果；错误返回非零退出码，不输出 token。"""
    args = build_parser().parse_args()
    try:
        if args.tool == "tmam":
            if args.command == "solve":
                from shapez1_tmam.xianyu_20221129.solver import XianYu20221129
                report = XianYu20221129(args.max_ticks).solve(args.shape, include_events=args.events)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return int(not report["success"])
            report = verify_saves(args.saves, args.output, args.workers, args.max_ticks, tuple(args.machine))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            for name, path in report["output_directories"].items():
                print(f"{name} 逐项验证结果：{path}")
            return int(any(machine["counts"].get(key, 0) for machine in report["machines"].values() for key in ("false_positive", "false_negative", "timeout")))
        if args.tool == "mods":
            if args.command == "clean":
                report = clean_mods(MOD_DIR)
                print(f"整理完成；重复 {report['duplicates']}，旧版 {report['obsolete']}，废弃 {report['retired']}，改名 {report['renamed']}。")
                return 0
            failed = 0
            if args.command in ("download", "update"):
                print(f"正在批量同步一代模组，保存位置：{MOD_DIR}")
                report = sync_mods(MOD_DIR)
                failed = report["failed"]
                print(f"下载 {report['downloaded']} 个，已有 {report['skipped']} 个，失败 {failed} 个，跳过废弃 {report['retired']} 个。")
                print(f"下载清单：{MOD_DIR / 'catalog' / 'download-state.json'}")
            else:
                clean_mods(MOD_DIR)
            if args.command in ("update", "publish"):
                print("正在同步群 1163635014 / s1-MOD-官方模组网站。")
                published = publish_mods(MOD_DIR)
                print(f"群文件同步完成：上传 {published['uploaded']}，未变化 {published['skipped']}，删除旧包 {published['deleted']}。")
            return 1 if failed else 0

        if args.command == "show":
            for path, puzzle in find_puzzles(args.code, PUZZLE_DIR):
                print(f"来源：{path}")
                print(json.dumps(puzzle, ensure_ascii=False, indent=2))
            return 0
        if args.command == "export":
            count = export_puzzles(PUZZLE_DIR, args.output)
            print(f"已导出 {count} 个谜题：{args.output}")
            return 0
        if args.command == "token" or args.refresh_token or not TOKEN_FILE.exists():
            print("正在获取一代谜题 token，请保持 Steam 登录。")
            refresh_token(STEAM_GAME_DIR, TOKEN_FILE)
            print(f"新 token 已保存：{TOKEN_FILE}")
        if args.command == "download":
            for code in args.codes:
                print(f"正在下载谜题：{code}")
                path = download_puzzle(code, TOKEN_FILE, PUZZLE_DIR)
                print(f"已保存：{path}")
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"操作失败：{exc}")
        return 1
    except KeyboardInterrupt:
        print("操作已取消。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
