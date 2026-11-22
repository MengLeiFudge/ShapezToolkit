"""将指定的 Python 方法或命名字段编译成游戏原生电路蓝图。"""

import argparse
from pathlib import Path

from .compiler_backend import export_program
from .compiler_backend.fields import export_fields
from .compiler_frontend import FrontendError, compile_field_methods, compile_method


def _named_options(parser, option, entries, convert=str):
    items = {}
    for entry in entries:
        name, equal, value = entry.partition("=")
        if not equal or not name.isidentifier() or not value:
            parser.error(f"{option} 需要 名称=值，收到 {entry!r}")
        if name in items:
            parser.error(f"{option} 重复指定了 {name!r}")
        try:
            items[name] = convert(value)
        except ValueError:
            parser.error(f"{option} 的频道须为整数，收到 {value!r}")
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="按源码文件和顶层方法生成 Shapez 2 电路蓝图")
    parser.add_argument("source", type=Path, help="Python 源码文件")
    parser.add_argument("method", nargs="?", help="单方法模式的顶层方法名")
    parser.add_argument("--channel-base", type=int, help="单方法模式的首个公开信号频道")
    parser.add_argument("--field", action="append", default=[], metavar="字段=方法", help="指定输出字段及其值方法，可重复")
    parser.add_argument("--input-channel", action="append", default=[], metavar="参数=频道", help="指定输入参数的频道，可重复")
    parser.add_argument("--output-channel", action="append", default=[], metavar="字段=频道", help="指定输出字段的频道，可重复")
    parser.add_argument("--publish-when", action="append", default=[], metavar="字段=方法", help="指定字段的布尔发布方法，可重复")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_intermixed_args()
    if args.field:
        if args.method is not None or args.channel_base is not None:
            parser.error("--field 不能和单方法名或 --channel-base 一起使用")
        fields = _named_options(parser, "--field", args.field)
        inputs = _named_options(parser, "--input-channel", args.input_channel, int)
        outputs = _named_options(parser, "--output-channel", args.output_channel, int)
        publish = _named_options(parser, "--publish-when", args.publish_when)
        if outputs.keys() != fields.keys():
            parser.error("--output-channel 须为每个 --field 指定一个频道")
    else:
        if args.input_channel or args.output_channel or args.publish_when:
            parser.error("输入、输出频道和发布方法须和 --field 一起使用")
        if args.method is None or args.channel_base is None:
            parser.error("请指定顶层方法名和 --channel-base，或用 --field 指定输出字段")

    target = f"{args.source} 中的命名字段" if args.field else f"{args.source} 中的 {args.method}"
    try:
        if args.field:
            programs, conditions = compile_field_methods(args.source, fields, publish_when=publish)
            report = export_fields(programs, args.output, input_channels=inputs, output_channels=outputs,
                                   publish_when=conditions)
        else:
            source = args.source.read_text(encoding="utf-8")
            program = compile_method(source, args.method, filename=str(args.source))
            report = export_program(program, args.channel_base, args.output)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, SyntaxError, ValueError) as error:
        parser.exit(2, f"编译 {target} 失败。{error}\n")
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
