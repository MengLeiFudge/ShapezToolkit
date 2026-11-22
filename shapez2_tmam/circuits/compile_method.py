"""将指定的 Python 方法编译成游戏原生电路蓝图。"""

import argparse
from pathlib import Path

from .compiler_backend import export_program
from .compiler_frontend import FrontendError, compile_method


def main() -> int:
    parser = argparse.ArgumentParser(description="按源码文件和方法名生成 Shapez 2 电路蓝图")
    parser.add_argument("source", type=Path, help="Python 源码文件")
    parser.add_argument("method", help="源码中的顶层方法名")
    parser.add_argument("--channel-base", required=True, type=int, help="首个公开信号频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        source = args.source.read_text(encoding="utf-8")
        program = compile_method(source, args.method, filename=str(args.source))
        report = export_program(program, args.channel_base, args.output)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"编译 {args.source} 中的 {args.method} 失败。{error}\n")
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
