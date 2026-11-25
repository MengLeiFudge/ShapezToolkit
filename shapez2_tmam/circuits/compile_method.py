"""将指定的 Python 方法或命名字段编译成游戏原生电路蓝图。"""

import argparse
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..mari.blueprint import Wiring, _kind
from .compiler_backend import _write_blueprint, compile_program
from .compiler_backend.fields import compile_fields
from .compiler_frontend import FrontendError, compile_field_methods, compile_method
from .factory_dense_layout import compact_combination
from .factory_local_flywire import shorten_local_wires, signal_depth
from .foundations import foundation_origin, foundation_tiles


def _named_options(parser, option, entries, convert: Callable[[str], Any] = str):
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


def _compact(document, report, *, left_rail=False):
    packed = compact_combination(document, left_rail=left_rail)
    compact, depth = shorten_local_wires(packed)
    platforms = compact["BP"]["Entries"]
    report["island_cells"] = sum(len(foundation_tiles(board["T"])) for board in platforms)
    if compact is document:
        return compact, report
    entries = [entry for board in platforms for entry in board["B"]["Entries"]]
    sizes = Counter(board["T"] for board in platforms)
    tiles = []
    for board in platforms:
        ox, oy = foundation_origin(board["T"])
        x, y = board.get("X", 0) + ox, board.get("Y", 0) + oy
        tiles.extend((x + dx, y + dy) for dx, dy in foundation_tiles(board["T"]))
    footprint = [max(axis) - min(axis) + 1 for axis in zip(*tiles)]
    report.update(platforms=len(platforms), platform_type=next(iter(sizes)) if len(sizes) == 1 else "mixed",
                  platform_sizes=dict(sizes), island_footprint_chunks=footprint, building_entries=len(entries),
                  buildings_by_layer=[sum(entry.get("L", 0) == z for entry in entries) for z in range(3)],
                  global_receivers=sum(_kind(entry) == "ControlledSignalReceiver" for entry in entries),
                  global_transmitters=sum(_kind(entry) == "ControlledSignalTransmitter" for entry in entries),
                  short_range_links=sum(_kind(entry) == "WireTransmitterSender" for entry in entries))
    if depth is None:
        depth = signal_depth(Wiring(compact["BP"]))
    ticks = 64 * (depth + 2)
    report["settling"].update(max_gate_depth=depth, hold_signal_ticks=ticks, hold_simulation_seconds=ticks / 12)
    return compact, report


def main() -> int:
    parser = argparse.ArgumentParser(description="按源码文件和顶层方法生成 Shapez 2 电路蓝图")
    parser.add_argument("source", type=Path, help="Python 源码文件")
    parser.add_argument("method", nargs="?", help="单方法模式的顶层方法名")
    parser.add_argument("--channel-base", type=int, help="单方法模式的首个公开信号频道")
    parser.add_argument("--field", action="append", default=[], metavar="字段=方法", help="指定输出字段及其值方法，可重复")
    parser.add_argument("--input-channel", action="append", default=[], metavar="参数=频道", help="指定输入参数的频道，可重复")
    parser.add_argument("--output-channel", action="append", default=[], metavar="字段=频道", help="指定输出字段的频道，可重复")
    parser.add_argument("--publish-when", action="append", default=[], metavar="字段=方法", help="指定字段的布尔发布方法，可重复")
    parser.add_argument("--left-rail", action="store_true", help="将单板组合方法的无线口沿左侧竖排")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    args = parser.parse_intermixed_args()
    fields, inputs, outputs, publish = {}, {}, {}, {}
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
            document, report = compile_fields(programs, input_channels=inputs, output_channels=outputs,
                                              publish_when=conditions)
        else:
            assert args.method is not None and args.channel_base is not None
            source = args.source.read_text(encoding="utf-8")
            program = compile_method(source, args.method, filename=str(args.source))
            document, report = compile_program(program, args.channel_base)
        report = _write_blueprint(*_compact(document, report, left_rail=args.left_rail), args.output)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, SyntaxError, ValueError) as error:
        parser.exit(2, f"编译 {target} 失败。{error}\n")
    print(f"已导出 {args.output}，占 {report['island_cells']} 岛格，{report['building_entries']} 个建筑条目。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
