"""从四个 Python 前缀更新方法生成共用的时序扫描蓝图。"""

import argparse
from pathlib import Path

from ..synthesis import row_support
from .compiler_backend import _write_blueprint
from .compiler_backend.timed import compile_state_fold
from .compiler_frontend import FrontendError, compile_method


def main() -> int:
    parser = argparse.ArgumentParser(description="从实际求解方法生成四象限五层的堆叠前缀扫描电路")
    parser.add_argument("--channel-base", required=True, type=int, help="首个公开信号频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    path = Path(row_support.__file__)
    try:
        source = path.read_text(encoding="utf-8")
        methods = {f"h{q}": compile_method(source, f"stack_scan_q{q}", filename=str(path)) for q in range(4)}
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
