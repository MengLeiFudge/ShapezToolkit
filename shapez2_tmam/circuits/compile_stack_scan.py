"""从 Python 求解方法生成原层读取和堆叠前缀扫描。"""

import argparse
from pathlib import Path

from ..synthesis import column_scan, direct_stack, row_support, shape_methods
from .compiler_backend import _write_blueprint
from .compiler_backend.fields import compile_fields
from .compiler_backend.timed import compile_state_fold, compile_state_steps
from .compiler_frontend import FrontendError, compile_method


def main() -> int:
    parser = argparse.ArgumentParser(description="从实际求解方法生成四象限五层电路")
    parser.add_argument("--channel-base", required=True, type=int, help="首个公开信号频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--read-rows", action="store_true", help="生成从原始图形读取所选两层的电路")
    modes.add_argument("--check-direct", action="store_true", help="生成纯堆叠的层材料检查和回放电路")
    modes.add_argument("--read-column", action="store_true", help="生成 q0 列材料读取与列 A 判定电路")
    args = parser.parse_args()
    if args.read_rows:
        path = Path(shape_methods.__file__)
        entries = {field: f"row_scan_{field}" for field in ("remaining", "top", "below")}
    elif args.check_direct:
        path = Path(direct_stack.__file__)
        entries = {field: f"direct_scan_{field}" for field in ("remaining", "valid", "replay")}
    elif args.read_column:
        path = Path(column_scan.__file__)
        entries = {field: f"column_scan_{field}" for field in ("remaining", "word", "height")}
    else:
        path = Path(row_support.__file__)
        entries = {f"h{q}": f"stack_scan_q{q}" for q in range(4)}
    try:
        source = path.read_text(encoding="utf-8")
        methods = {field: compile_method(source, method, filename=str(path)) for field, method in entries.items()}
        if args.check_direct or args.read_column:
            document, report = compile_state_steps(methods, 5, args.channel_base)
        else:
            document, report = compile_state_fold(methods, 5, args.channel_base, round_values=(5, 4, 3, 2, 1))
        if args.read_column:
            column_rule = compile_method(source, "column_word_admissible", filename=str(path))
            rule_document, rule_report = compile_fields(
                {"column_a": column_rule},
                input_channels={"word": report["outputs"]["result_word"]["channel"]},
                output_channels={"column_a": report["reserved_channels"][1] + 1},
            )
            rule_output = args.output.with_name(f"{args.output.stem}-admissible.spz2bp")
            _write_blueprint(rule_document, rule_report, rule_output)
            print(f"已导出 {rule_output}，共 {rule_report['platforms']} 块平台。")
        _write_blueprint(document, report, args.output)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"扫描电路编译失败。{error}\n")
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
