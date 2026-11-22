"""按预设频道与配置清单编译二代原生电路蓝图及静态网表报告。"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from unittest.mock import patch

from .factory_book import TRAIN_BOOK, WORKSHOP_BOOK

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_DIR = PACKAGE_ROOT / "blueprints"
REPORT_DIR = PACKAGE_ROOT / "reports"

# 名称 -> (模块名, 默认参数列表)
BLUEPRINT_TARGETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "cell-at-4q5l": ("cell_at", ()),
    "column-scan-4q5l": ("column_step", ("--scan",)),
    "column-step-4q5l": ("column_step", ()),
    "quarter-order-4q5l": ("quarter_order", ()),
    "layer-recipe-4q5l": ("layer_recipe", ()),
    "operation-core-4q5l": ("operation_core", ("--quadrants", "4", "--channel-base", "1000000")),
    "operation-core-6q5l": ("operation_core", ("--quadrants", "6", "--channel-base", "1001000")),
    "noncrystal-4q5l": ("noncrystal_circuit", ("--quadrants", "4", "--channel-base", "1002000")),
    "noncrystal-6q5l": ("noncrystal_circuit", ("--quadrants", "6", "--channel-base", "1004000")),
    "decoder-4q5l": ("decoder_circuit", ("--channel-base", "1006000")),
    "half-4q5l": ("half_circuit", ("--channel-base", "1008000")),
    "scan-4q5l": ("scan_circuit", ("--channel-base", "1011000")),
    "signal-register": ("register_circuit", ("--channel-base", "1012000")),
    "four-phase-clock": ("sequential_circuit", ("--channel-base", "1013000")),
    "iterative-scanner-4q5l": ("iterative_scanner", ("--channel-base", "1014000")),
    "material-half-4q5l": ("material_half_circuit", ("--channel-base", "1016000")),
    "pin-column-4q5l": ("pin_column_circuit", ("--channel-base", "1019000")),
    "pin-column-iterator-4q5l": ("pin_column_iterator", ("--channel-base", "1022000")),
    "recipe-processor-4q5l": ("recipe_processor", ("--channel-base", "1025000")),
    "recipe-processor-6q5l": ("recipe_processor", ("--quadrants", "6")),
    "automatic-half-4q5l": ("half_synthesizer", ("--channel-base", "1028000")),
    "startpoint-4q5l": ("startpoint_circuit", ("--channel-base", "1061000")),
    "s-tail-4q5l": ("startpoint_circuit", ("--s-tail", "--channel-base", "1094000")),
    "tagged-goal-4q5l": ("tagged_goal_circuit", ("--channel-base", "1127000")),
    "pin-image-4q5l": ("pin_image_circuit", ("--channel-base", "1144000")),
    "tagged-leaf-4q5l": ("startpoint_circuit", ("--tagged-goal", "--channel-base", "1161000")),
    "pin-source-4q5l": ("pin_source_circuit", ("--channel-base", "1194000")),
    "full-tail-4q5l": ("full_solver_circuit", ("--channel-base", "1211000")),
    "full-tail-packed-4q5l": ("full_solver_circuit", ("--pack",)),
    "factory-control-4q5l": ("full_solver_circuit", ("--pack", "--factory")),
}

# 按游戏蓝图库的目录分册。同一模块的四、六象限版本放在一起。
CIRCUIT_BOOKS = {
    "目标取格": ("cell_at",),
    "列判据": ("column_step",),
    "基础料订单": ("quarter_order",),
    "逐层配方": ("layer_recipe",),
    "完整主控": ("full_solver_circuit",),
    "扫描与时序": ("scan_circuit", "iterative_scanner", "register_circuit", "sequential_circuit", "decoder_circuit"),
    "起点与半形": ("half_circuit", "material_half_circuit", "half_synthesizer", "startpoint_circuit", "noncrystal_circuit"),
    "顶针逆推": ("pin_column_circuit", "pin_column_iterator", "pin_image_circuit", "pin_source_circuit", "tagged_goal_circuit"),
    "加工与指令": ("operation_core", "recipe_processor"),
}
BOOK_BY_MODULE = {module: Path("电路", book) for book, modules in CIRCUIT_BOOKS.items() for module in modules}

BOOK_BY_TARGET = {name: BOOK_BY_MODULE[module] for name, (module, _) in BLUEPRINT_TARGETS.items()}
for section, books in (("实体", WORKSHOP_BOOK), ("火车", TRAIN_BOOK)):
    for name, book in books.items():
        BLUEPRINT_TARGETS[name] = ("factory_book", (name,))
        BOOK_BY_TARGET[name] = Path(section, book)

for cargo, book in (("shapes", "图形"), ("fluids", "染料")):
    for role in ("depot", "load", "unload"):
        name = f"mixed-{cargo}-{role}"
        BLUEPRINT_TARGETS[name] = ("proportioning", (cargo, role))
        BOOK_BY_TARGET[name] = Path("配料", book)

for section in ("stock", "quarters", "paint", "palette"):
    name = f"base-{section}-4q5l"
    BLUEPRINT_TARGETS[name] = ("base_workshop", (section,))
    BOOK_BY_TARGET[name] = Path("实体", "基础单层")

REPORT_TARGETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "full-tail-4q5l": ("full_solver_circuit", ("--report-only",)),
    "full-tail-packed-4q5l": ("full_solver_circuit", ("--report-only", "--pack")),
}


def run_module_main(module_name: str, args: list[str]) -> int:
    """按给定参数运行指定电路模块的 CLI 入口。"""
    module = importlib.import_module(f"{__package__}.{module_name}")
    with patch.object(sys, "argv", [f"shapez2_tmam.circuits.{module_name}", *args]):
        return int(module.main() or 0)


def compile_blueprints(names: list[str], output_dir: Path = BLUEPRINT_DIR) -> int:
    """编译指定名称列表的原生电路蓝图。"""
    for name in names:
        if name not in BLUEPRINT_TARGETS:
            raise ValueError(f"未知蓝图目标：{name}（可用 --list 查看全部预设名称）")
        module_name, extra_args = BLUEPRINT_TARGETS[name]
        output = output_dir / BOOK_BY_TARGET[name] / f"{name}.spz2bp"
        code = run_module_main(module_name, [*extra_args, "--output", str(output)])
        if code != 0:
            return code
    return 0


def compile_reports(output_dir: Path = REPORT_DIR) -> int:
    """生成完整四象限尾部网表统计与理论时序报告。"""
    for name, (module_name, extra_args) in REPORT_TARGETS.items():
        output = output_dir / f"{name}.json"
        code = run_module_main(module_name, [*extra_args, "--output", str(output)])
        if code != 0:
            return code
    return 0


def main(argv: list[str] | None = None) -> int:
    """列出或批量编译预设蓝图与静态网表报告。"""
    parser = argparse.ArgumentParser(description="编译二代 TMAM 原生纯电路蓝图与静态网表报告")
    parser.add_argument("targets", nargs="*", metavar="NAME", help="要编译的蓝图名称（不带 .spz2bp 后缀）")
    parser.add_argument("--list", action="store_true", help="列出全部预设蓝图名称与对应模块")
    parser.add_argument("--all", action="store_true", help="按功能分册重新编译全部蓝图")
    parser.add_argument("--reports", action="store_true", help="生成 reports/ 下的两份完整网表统计报告")
    parser.add_argument("--output-dir", type=Path, default=BLUEPRINT_DIR, help="蓝图输出目录（默认 shapez2_tmam/blueprints）")
    args = parser.parse_args(argv)

    if args.list:
        for name, (module_name, extra_args) in BLUEPRINT_TARGETS.items():
            flags = " ".join(extra_args) or "(默认参数)"
            print(f"{name:28s} {BOOK_BY_TARGET[name].as_posix()}  {module_name} [{flags}]")
        return 0

    if not args.all and not args.reports and not args.targets:
        parser.print_help()
        return 1

    if args.reports:
        code = compile_reports()
        if code != 0:
            return code

    selected = list(BLUEPRINT_TARGETS) if args.all else args.targets
    if selected:
        return compile_blueprints(selected, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
