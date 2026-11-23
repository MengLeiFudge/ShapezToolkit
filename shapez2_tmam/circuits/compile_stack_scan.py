"""从 Python 求解方法生成原层读取和堆叠前缀扫描。"""

import argparse
from pathlib import Path

from ..synthesis import (column_build, column_scan, crystal_support, cut_cursor, direct_stack,
                         paired_tail, pin_labels, row_support, shape_methods)
from .circuit_packing import stack_platforms
from .compiler_backend import _write_blueprint
from .compiler_backend.confirmed_call import build as build_confirmed_call
from .compiler_backend.fields import compile_fields
from .compiler_backend.timed import compile_state_fold, compile_state_steps
from .compiler_frontend import FrontendError, compile_method
from .local_module import Module


def _choose_cut(base: int, output: Path) -> int:
    path = Path(cut_cursor.__file__)
    source = path.read_text(encoding="utf-8")
    entries = {"next": "next_cut_phase", "opcode": "cut_event_opcode",
               **{field: f"cut_{field}" for field in ("start", "alternate", "chosen", "exhausted", "terminal",
                                                      "address")}}
    methods = {field: compile_method(source, method, filename=str(path)) for field, method in entries.items()}
    event = compile_method(source, "cut_event", filename=str(path))
    inputs = {"phase": base, "enable": base + 1, "settled": base + 2, "confirmed": base + 11,
              "done": 1700765, "has_prefix": 1700897}
    outputs = {"next": base + 3, "chosen": base + 4, "exhausted": base + 5, "terminal": base + 6,
               "address": base + 7, "opcode": base + 9, "start": 1700930, "alternate": 1700871}
    choice, report = compile_fields(methods, input_channels=inputs, output_channels=outputs,
                                    publish_when={"opcode": event})
    # 判定相位重新计时，确认事件之前的空回合不改变切向状态。
    clock, clock_report = build_confirmed_call(
        enable=inputs["enable"], address=outputs["address"], ack=base + 8, finished=outputs["terminal"],
        opcode=outputs["opcode"], settled=inputs["settled"], has_packet=base + 10, confirmed=inputs["confirmed"],
        request=base + 12, states={"phase": (inputs["phase"], outputs["next"], 0)},
        settle_ticks=1536, update_ticks=report["settling"]["hold_signal_ticks"], channel_base=base + 16,
    )
    ack = Module({"request": base + 12})
    ack.gate("LogicGateIf", ("request", 1), ("ack",))
    ack.outputs = {"ack": base + 8}
    board = ack.layout()["BP"]["Entries"][0]
    platforms = clock["BP"]["Entries"]
    platforms.append(board)
    stack_platforms(platforms)
    clock_report["platforms"] += 1
    clock_report["building_entries"] += len(board["B"]["Entries"])
    clock_output = output.with_name(f"{output.stem}-clock.spz2bp")
    _write_blueprint(clock, clock_report, clock_output)
    _write_blueprint(choice, report, output)
    print(f"已导出 {output} 和 {clock_output}，共 {report['platforms'] + clock_report['platforms']} 块平台。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="从实际求解方法生成四象限五层电路")
    parser.add_argument("--channel-base", required=True, type=int, help="首个公开信号频道")
    parser.add_argument("--output", required=True, type=Path, help="原生 .spz2bp 输出路径")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--read-rows", action="store_true", help="生成从原始图形读取所选两层的电路")
    modes.add_argument("--check-direct", action="store_true", help="生成纯堆叠的层材料检查和回放电路")
    modes.add_argument("--read-column", action="store_true", help="生成 q0 列材料读取与列 A 判定电路")
    modes.add_argument("--build-dense-column", action="store_true", help="生成紧柱逐层回放与完工电路")
    modes.add_argument("--close-prefix", action="store_true", help="生成双半形前缀的五轮逐层闭包")
    modes.add_argument("--read-prefix-column", action="store_true", help="生成已闭合前缀的 q0 列材料读取电路")
    modes.add_argument("--seed-crystal-half", action="store_true", help="生成两列半形的含晶支撑预处理")
    modes.add_argument("--append-paired-tail", action="store_true", help="生成双半形尾料的五轮筛选和堆叠")
    modes.add_argument("--restore-pin-label", action="store_true", help="按保序序号读回顶针前态原料的原色标签")
    modes.add_argument("--choose-cut", action="store_true", help="生成复用同一闭包的双切向选择器")
    args = parser.parse_args()
    if args.choose_cut:
        try:
            return _choose_cut(args.channel_base, args.output)
        except FrontendError as error:
            parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
        except (OSError, ValueError) as error:
            parser.exit(2, f"切向选择电路编译失败。{error}\n")
    if args.restore_pin_label:
        path = Path(pin_labels.__file__)
        entries = {field: f"retained_{field}" for field in ("rank", "label")}
    elif args.append_paired_tail:
        path = Path(paired_tail.__file__)
        entries = {field: f"tail_{field}_step" for field in ("replay", "mask")}
    elif args.seed_crystal_half:
        path = Path(crystal_support.__file__)
        entries = {field: f"seed_{field}" for field in ("required", "candidate", "supported")}
    elif args.close_prefix:
        path = Path(row_support.__file__)
        entries = {f"h{q}": f"prefix_scan_q{q}" for q in range(4)}
    elif args.read_rows:
        path = Path(shape_methods.__file__)
        entries = {field: f"row_scan_{field}" for field in ("remaining", "top", "below")}
    elif args.check_direct:
        path = Path(direct_stack.__file__)
        entries = {field: f"direct_scan_{field}" for field in ("remaining", "valid", "replay")}
    elif args.build_dense_column:
        path = Path(column_build.__file__)
        entries = {field: f"dense_column_{field}" for field in ("source", "pending")}
    elif args.read_column or args.read_prefix_column:
        path = Path(column_scan.__file__)
        stem = "column_prefix" if args.read_prefix_column else "column_scan"
        entries = {field: f"{stem}_{field}" for field in ("remaining", "word", "height")}
    else:
        path = Path(row_support.__file__)
        entries = {f"h{q}": f"stack_scan_q{q}" for q in range(4)}
    try:
        source = path.read_text(encoding="utf-8")
        methods = {field: compile_method(source, method, filename=str(path)) for field, method in entries.items()}
        if args.seed_crystal_half:
            document, report = compile_state_steps(methods, 5, args.channel_base,
                                                   held_inputs=("low_word", "high_word", "high_height"),
                                                   round_values=(5, 4, 3, 2, 1))
        elif args.read_prefix_column:
            document, report = compile_state_steps(methods, 5, args.channel_base, held_inputs=("prefix_height",))
        elif args.check_direct or args.read_column:
            document, report = compile_state_steps(methods, 5, args.channel_base)
        elif args.restore_pin_label:
            document, report = compile_state_fold(methods, 5, args.channel_base, round_values=(0, 1, 2, 3, 4))
        elif args.build_dense_column or args.append_paired_tail:
            document, report = compile_state_fold(methods, 5, args.channel_base)
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
        if args.build_dense_column:
            finish = compile_method(source, "dense_column_finish", filename=str(path))
            finish_document, finish_report = compile_fields(
                {"result": finish},
                input_channels={field: report["outputs"][f"result_{field}"]["channel"]
                                for field in ("source", "pending")},
                output_channels={"result": report["reserved_channels"][1] + 1},
            )
            finish_output = args.output.with_name(f"{args.output.stem}-finish.spz2bp")
            _write_blueprint(finish_document, finish_report, finish_output)
            print(f"已导出 {finish_output}，共 {finish_report['platforms']} 块平台。")
        _write_blueprint(document, report, args.output)
    except FrontendError as error:
        parser.exit(2, f"{error.filename}:{error.lineno}:{error.offset} {error.msg}\n")
    except (OSError, ValueError) as error:
        parser.exit(2, f"扫描电路编译失败。{error}\n")
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
