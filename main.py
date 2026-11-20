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
    nabi = tmam_commands.add_parser("verify-v7f", help="审计 Nabi v7f 的全部结构、逐 tick 指令和缓存")
    nabi.add_argument("--save", type=Path, required=True, help="TMAM-Nabi-20221128 的原始存档文件")
    nabi.add_argument("--output", type=Path, help="新的报告目录；默认保存到 Nabi 目录的 verification 下")
    nabi.add_argument("--workers", type=int, default=8, help="并行进程数，1..32，默认 8")
    nabi.add_argument("--max-ticks", type=int, default=4096, help="每阶段最大 tick 数，默认 4096")
    solve = tmam_commands.add_parser("solve", help="用 XianYu-20221129 的逻辑拆解结构，输出部件与加工树，不查图形数据库")
    solve.add_argument("shape", type=int, help="16 位结构编号，1..65535，低四位为底层")
    solve.add_argument("--events", action="store_true", help="同时输出指令、模式和重试信号的变化 tick")
    solve.add_argument("--max-ticks", type=int, default=4096, help="每阶段最大 tick 数，默认 4096")
    tmam2 = tools.add_parser("tmam2", help="二代 TMAM 通用合成、原生电路编译、Mari 模型与论文排版")
    tmam2_commands = tmam2.add_subparsers(dest="command", required=True)
    synth2 = tmam2_commands.add_parser("synth", help="按通用偶数象限合成器输出制造证书或六槽指令")
    synth2.add_argument("target", help="保留原层号的图形短代码")
    synth2.add_argument("--quadrants", type=int, default=4, help="偶数象限数，至少 2，默认 4")
    synth2.add_argument("--height", type=int, default=5, help="整个制造过程的层数上限，至少 2，默认 5")
    synth2.add_argument("--complete", action="store_true", help="启用完整四象限五层尾部搜索")
    synth2.add_argument("--instructions", action="store_true", help="另导出四/六象限五层的六寄存器消费式指令")
    mari2 = tmam2_commands.add_parser("mari", aliases=["solve"], help="按 Mari 六候选逻辑计算虚拟重建和工厂指令（兼容旧名 solve）")
    mari2.add_argument("shape", help="四象限、最多五层的完整图形短代码")
    mari2.add_argument("--iteration", type=int, choices=range(1, 7), help="只计算指定候选；默认依次选择最小匹配编号")
    bp2 = tmam2_commands.add_parser("blueprint", help="编译二代原生电路蓝图或导出静态网表报告")
    bp2.add_argument("targets", nargs="*", metavar="NAME", help="预设蓝图名称（不带 .spz2bp 后缀）")
    bp2.add_argument("--list", action="store_true", help="列出全部预设蓝图目标")
    bp2.add_argument("--all", action="store_true", help="按预设频道重新编译全部 24 份蓝图")
    bp2.add_argument("--reports", action="store_true", help="更新 shapez2_tmam/reports/ 下的静态网表报告")
    bp2.add_argument("--output-dir", type=Path, help="自定义蓝图输出目录")
    paper2 = tmam2_commands.add_parser("paper", help="将二代 TMAM 理论 Markdown 排版为 A4 PDF")
    paper2.add_argument("--source", type=Path, help="理论 Markdown 源文件路径")
    paper2.add_argument("--output", type=Path, help="导出 PDF 路径")
    paper2.add_argument("--all", action="store_true", help="重新排版全部四篇正文论文与附录")
    return parser


def main() -> int:
    """分派命令并报告结果；错误返回非零退出码，不输出 token。"""
    args = build_parser().parse_args()
    try:
        if args.tool == "tmam2":
            if args.command == "synth":
                from shapez2_tmam.synthesis.__main__ import main as synth_main
                argv = ["--quadrants", str(args.quadrants), "--height", str(args.height)]
                if args.complete:
                    argv.append("--complete")
                if args.instructions:
                    argv.append("--instructions")
                argv.extend(["--", args.target])
                return synth_main(argv)
            if args.command == "blueprint":
                from shapez2_tmam.circuits.__main__ import BLUEPRINT_DIR, main as circuits_main
                argv = []
                if args.list:
                    argv.append("--list")
                if args.all:
                    argv.append("--all")
                if args.reports:
                    argv.append("--reports")
                if args.output_dir is not None:
                    argv.extend(["--output-dir", str(args.output_dir)])
                else:
                    argv.extend(["--output-dir", str(BLUEPRINT_DIR)])
                argv.extend(args.targets)
                return circuits_main(argv)
            if args.command == "paper":
                import importlib.util
                pdf_script = Path(__file__).resolve().parent / "shapez2_tmam/docs/papers/build_paper_pdf.py"
                spec = importlib.util.spec_from_file_location("build_paper_pdf", pdf_script)
                assert spec is not None and spec.loader is not None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                argv = []
                if args.all:
                    argv.append("--all")
                if args.source is not None:
                    argv.extend(["--source", str(args.source)])
                if args.output is not None:
                    argv.extend(["--output", str(args.output)])
                return module.main(argv)
            from shapez2_tmam.mari import Mari, Shape
            machine = Mari()
            target = Shape.from_key(args.shape)
            candidate = machine.candidate(target, args.iteration) if args.iteration else machine.solve(target)
            report = candidate.as_dict() if candidate is not None else {"target": target.to_key(), "matched": False}
            report["status"] = "matched" if report["matched"] else "mismatch" if args.iteration else "no_candidate"
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return int(not report["matched"])
        if args.tool == "tmam":
            if args.command == "verify-v7f":
                from shapez1_tmam.nabi_20221128.verify_v7f import verify_v7f
                report = verify_v7f(args.save, args.output, args.workers, args.max_ticks)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                print("审计完成；候选堆叠结果不代表完整指令语义已经验证通过。")
                return 0
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
