"""从 Python 求解方法生成原层读取和堆叠前缀扫描。"""

import argparse
from pathlib import Path

from ..synthesis import row_support, shape_methods
from .compiler_backend import _write_blueprint
from .compiler_backend.timed import compile_state_fold
from .compiler_frontend import FrontendError, compile_method


def main() -> int:
    parser = argparse.ArgumentParser(description="从实际求解方法生成四象限五层的堆叠前缀扫描电路")
    parser.add_argument("--channel-base", required=True, type=int, help="首个公开信号频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    parser.add_argument("--read-rows", action="store_true", help="生成从原始图形读取所选两层的电路")
    args = parser.parse_args()
    if args.read_rows:
        path = Path(shape_methods.__file__)
        entries = {field: f"row_scan_{field}" for field in ("remaining", "top", "below")}
    else:
        path = Path(row_support.__file__)
        entries = {f"h{q}": f"stack_scan_q{q}" for q in range(4)}
    try:
        source = path.read_text(encoding="utf-8")
        methods = {field: compile_method(source, method, filename=str(path)) for field, method in entries.items()}
        document, report = compile_state_fold(methods, 5, args.channel_base, round_values=(5, 4, 3, 2, 1))
        _write_blueprint(document, report, args.output)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"堆叠前缀扫描编译失败。{error}\n")
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
