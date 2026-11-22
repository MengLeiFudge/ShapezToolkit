"""独立编译手写中间表示样例。"""

import argparse
from pathlib import Path

from . import _write_blueprint, export_program
from .examples import layer_program
from .timed import compile_fold


def main() -> int:
    parser = argparse.ArgumentParser(description="将手写逐层补料中间表示编译为原生蓝图和接口表")
    parser.add_argument("method", choices=("append_layer", "append_five", "append_five_timed"))
    parser.add_argument("--channel-base", required=True, type=int, help="公开接口的首个独占频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        if args.method == "append_five_timed":
            result = compile_fold(layer_program("append_layer"), 5, args.channel_base)
            report = _write_blueprint(*result, args.output)
        else:
            report = export_program(layer_program(args.method), args.channel_base, args.output)
    except ValueError as error:
        parser.error(str(error))
    print(f"已导出 {args.output}（{report['building_entries']} 个建筑）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
