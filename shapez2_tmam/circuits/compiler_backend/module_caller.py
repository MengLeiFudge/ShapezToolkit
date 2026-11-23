"""按接口表重复调用定步模块并保持每次调用的结果。"""

import argparse
import base64
import gzip
import json
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from ...mari.blueprint import Wiring, _kind
from ...mari.ports import PORTS
from ...mari.signals import decode_constant
from ...synthesis.physics import Rules
from ..circuit import Literal, constant
from ..circuit_packing import stack_platforms
from ..compiler_contract import ValueType
from ..local_module import Module
from . import _write_blueprint


_RADIO_TICKS = 12
_MAX_CALLS = 4
_MAX_DELAY_STEPS = 128
_RADIO_RECEIVER = "ControlledSignalReceiverInternalVariant"
_RADIO_TRANSMITTER = "ControlledSignalTransmitterInternalVariant"


def _gate(module: Module, kind: str, name: str, *args, config: str | None = None) -> str:
    module.gate(f"LogicGate{kind}", args, (name,), config)
    return name


def _any(module: Module, name: str, signals: tuple[str, ...]) -> str:
    first, *rest = signals
    for i, signal in enumerate(rest):
        first = _gate(module, "Or", f"{name}_or_{i}", first, signal)
    return first


def _compare(module: Module, name: str, left, right, config: str = "AQ==") -> str:
    return _gate(module, "Compare", name, left, right, config=config)


def _advance(enable: int, phase: int, done: int, reset_tap: int, sample_tap: int, phases: tuple) -> Module:
    module = Module({"enable": enable, "phase": phase, "done": done, "reset_tap": reset_tap,
                     "sample_tap": sample_tap})
    last = phases[-1][-1] + 1
    module.lookup("phase", "next", ((i, min(i + 1, last)) for i in range(last + 1)))
    modes = []
    for index, name in enumerate(("reset", "running")):
        matches = tuple(_compare(module, f"{name}_{i}", "phase", group[index]) for i, group in enumerate(phases))
        modes.append(_any(module, name, matches))
    reset, running = modes
    reset_ready = _gate(module, "And", "reset_ready", _compare(module, "reset_elapsed", "reset_tap", "phase"),
                        _compare(module, "done_cleared", "done", 0))
    sample_ready = _gate(module, "And", "sample_ready", _compare(module, "sample_elapsed", "sample_tap", "phase"),
                         _compare(module, "callee_done", "done", 1))
    wait_reset = _gate(module, "And", "wait_reset", reset, _gate(module, "Not", "reset_pending", reset_ready))
    wait_sample = _gate(module, "And", "wait_sample", running,
                        _gate(module, "Not", "sample_pending", sample_ready))
    waiting = _gate(module, "Or", "waiting", wait_reset, wait_sample)
    enabled = _compare(module, "enabled", "enable", 1)
    _gate(module, "If", "state", "next", _gate(module, "And", "advance", enabled,
                                               _gate(module, "Not", "ready", waiting)))
    _gate(module, "If", "state", "phase", _gate(module, "And", "hold", enabled, waiting))
    _gate(module, "If", "state", 0, _gate(module, "Not", "disabled", enabled))
    module.outputs = {"state": phase}
    return module


def _control(phase: int, run: int, done: int, phases: tuple, active: tuple, captures: tuple) -> tuple[Module, ...]:
    module = Module({"phase": phase})
    capture_board = module if len(phases) <= 3 else Module({"phase": phase})
    running = []
    for i, (reset, start, capture) in enumerate(phases):
        before_end = _compare(module, f"before_end_{i}", "phase", capture, "BQ==")
        _gate(module, "And", f"active_{i}", before_end, _compare(module, f"after_reset_{i}", "phase", reset, "Ag=="))
        running.append(_gate(module, "And", f"running_{i}", before_end,
                             _compare(module, f"after_start_{i}", "phase", start, "Ag==")))
        _compare(capture_board, f"capture_{i}", "phase", capture)
    _compare(module, "done", "phase", phases[-1][-1] + 1)
    module.outputs = {_any(module, "run", tuple(running)): run, "done": done,
                      **{f"active_{i}": channel for i, channel in enumerate(active)}}
    capture_board.outputs.update({f"capture_{i}": channel for i, channel in enumerate(captures)})
    return (module,) if capture_board is module else (module, capture_board)


def _arguments(active: tuple[int, ...], sources: tuple[int | Literal, ...], output: int) -> Module:
    inputs = {f"active_{i}": channel for i, channel in enumerate(active)}
    inputs.update({f"source_{i}": ch for i, ch in enumerate(sources) if isinstance(ch, int)})
    module = Module(inputs)
    for i, source in enumerate(sources):
        _gate(module, "If", "argument", f"source_{i}" if isinstance(source, int) else source, f"active_{i}")
    module.outputs = {"argument": output}
    return module


def _result(enable: int, capture: int, result: int, output: int) -> Module:
    module = Module({"enable": enable, "capture": capture, "result": result, "stored": output})
    enabled = _compare(module, "enabled", "enable", 1)
    load = _gate(module, "And", "load", enabled, "capture")
    keep = _gate(module, "And", "keep", enabled, _gate(module, "Not", "outside_capture", "capture"))
    _gate(module, "If", "latched", "result", load)
    _gate(module, "If", "latched", "stored", keep)
    module.outputs = {"latched": output}
    return module


def _copy(source: int, target: int) -> Module:
    module = Module({"source": source})
    _gate(module, "If", "copy", "source", 1)
    module.outputs = {"copy": target}
    return module


def _check_channel(channel: int) -> None:
    if type(channel) is not int or not 1 <= channel < 1 << 24:
        raise ValueError(f"频道必须在 1～16777215 内，收到 {channel!r}")


def _interface(report: dict) -> tuple[dict, dict, tuple[int, int], tuple[int, int]]:
    try:
        inputs, outputs = report["inputs"], report["outputs"]
        timing = report["timing"]
        first, last = report["reserved_channels"]
        waits = timing["reset_hold_signal_ticks"], timing["start_to_sample_signal_ticks"]
        ports = (*inputs.values(), *outputs.values())
        if (report["schedule"] != "bounded_fold" or inputs["run"]["type"] != "bool"
                or outputs["done"]["type"] != "bool" or timing["channel_signal_ticks"] != _RADIO_TICKS):
            raise ValueError("需要 12 tick 频道和布尔 run/done 的定步模块接口表")
        names = [port["channel"] for port in ports]
        for port in ports:
            ValueType(port["type"])
        for channel in (first, last, *names):
            _check_channel(channel)
        if first > last or len(names) != len(set(names)) or any(not first <= ch <= last for ch in names):
            raise ValueError("定步模块的公开频道须独占且位于保留范围内")
        if any(type(wait) is not int or not 1 <= wait <= _RADIO_TICKS * _MAX_DELAY_STEPS for wait in waits):
            raise ValueError(f"复位和采样时间须为 1～{_RADIO_TICKS * _MAX_DELAY_STEPS} 个信号 tick")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("定步模块接口表缺少有效的端口或计时字段") from error
    return inputs, outputs, (first, last), waits


def _literal(value, type_name: str) -> Literal:
    type_ = ValueType(type_name)
    if type_ is ValueType.BOOL and (type(value) is bool or type(value) is int and value in (0, 1)):
        return Literal(int(value))
    if type_ is ValueType.INT and type(value) is int:
        constant(value)
        return Literal(value)
    if type_ is ValueType.SHAPE and (value is None or isinstance(value, str)):
        return Literal(Rules().parse(value) if value is not None else None)
    if type_ is ValueType.COLOR and (value is None or isinstance(value, str)):
        color = "color:" + value if value is not None else None
        constant(color)
        return Literal(color)
    raise ValueError(f"参数 {value!r} 与类型 {type_name} 不符")


def build_calls(
    interface: dict, calls: list[dict], channel_base: int, *, result_names: tuple[str, ...] | None = None,
) -> tuple[dict, dict]:
    """编译按顺序执行的定步模块调用，各组参数可来自频道或字面量。"""
    inputs, outputs, callee_channels, waits = _interface(interface)
    parameters = {name: port for name, port in inputs.items() if name != "run"}
    results = {name: port for name, port in outputs.items() if name != "done"}
    if result_names is not None:
        selected = set(result_names)
        if not selected or len(selected) != len(result_names) or selected - results.keys():
            available = ", ".join(results) or "无"
            raise ValueError(f"回读字段须为互不重复的结果名。可选字段为 {available}")
        results = {name: port for name, port in results.items() if name in selected}
    if not isinstance(calls, list) or not 1 <= len(calls) <= _MAX_CALLS:
        raise ValueError(f"一次调度需要 1～{_MAX_CALLS} 组调用参数")
    arguments = []
    external = set()
    for call in calls:
        if not isinstance(call, dict) or call.keys() != parameters.keys():
            raise ValueError("每组调用须给出接口表中除 run 外的全部输入")
        args = {}
        for name, spec in call.items():
            if isinstance(spec, dict) and spec.keys() == {"channel"}:
                channel = spec["channel"]
                _check_channel(channel)
                external.add(channel)
                args[name] = channel
            elif isinstance(spec, dict) and spec.keys() == {"literal"}:
                args[name] = _literal(spec["literal"], parameters[name]["type"])
            else:
                raise ValueError(f"参数 {name} 须指定 channel 或 literal")
        arguments.append(args)

    reset_steps, sample_steps = ((wait + _RADIO_TICKS - 1) // _RADIO_TICKS for wait in waits)
    delay_count = max(reset_steps, sample_steps)
    phases = tuple((i * 3 + 1, i * 3 + 2, i * 3 + 3) for i in range(len(calls)))
    width = 3 + 2 * len(calls) + delay_count + len(calls) * len(results)
    _check_channel(channel_base)
    last = channel_base + width - 1
    _check_channel(last)
    callee_first, callee_last = callee_channels
    if (channel_base <= callee_last and last >= callee_first
            or any(channel_base <= ch <= last or callee_first <= ch <= callee_last for ch in external)):
        raise ValueError("调用器、定步模块和参数源的频道范围须互不重叠")
    numbers = iter(range(channel_base, last + 1))
    enable, phase, done = next(numbers), next(numbers), next(numbers)
    active = tuple(next(numbers) for _ in calls)
    captures = tuple(next(numbers) for _ in calls)
    delays = tuple(next(numbers) for _ in range(delay_count))
    result_ports = [{name: {"channel": next(numbers), "type": port["type"]} for name, port in results.items()}
                    for _ in calls]
    modules = [_advance(enable, phase, outputs["done"]["channel"], delays[reset_steps - 1],
                        delays[sample_steps - 1], phases),
               *_control(phase, inputs["run"]["channel"], done, phases, active, captures)]
    modules.extend(_copy(source, target) for source, target in zip((phase, *delays), delays))
    modules.extend(_arguments(active, tuple(args[name] for args in arguments), port["channel"])
                   for name, port in parameters.items())
    for capture, stored in zip(captures, result_ports, strict=True):
        modules.extend(_result(enable, capture, results[name]["channel"], port["channel"])
                       for name, port in stored.items())
    platforms = [module.layout()["BP"]["Entries"][0] for module in modules]
    stack_platforms(platforms)
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": platforms}}
    _local_wiring(document["BP"])
    port_report = {
        "schedule": "repeated_bounded_fold",
        "inputs": {"enable": {"channel": enable, "type": "bool"}},
        "outputs": {"done": {"channel": done, "type": "bool"}, "calls": result_ports},
        "calls": calls,
        "callee": {"inputs": inputs, "outputs": outputs, "reserved_channels": list(callee_channels)},
        "reserved_channels": [channel_base, last],
        "phase_channel": phase,
        "timing": {
            "channel_signal_ticks": _RADIO_TICKS,
            "reset_hold_signal_ticks": (delay_count + 4) * _RADIO_TICKS,
            "callee_reset_wait_signal_ticks": reset_steps * _RADIO_TICKS,
            "callee_sample_wait_signal_ticks": sample_steps * _RADIO_TICKS,
            "conditions": interface["timing"]["conditions"],
            "protocol": "先将 enable 保持为 0 达到复位时间，再将整组参数与 enable=1 保持到 done=1。"
                        "此时读取各组结果。下次调用先把 enable 置为 0 并再次等待复位。",
        },
        "platforms": len(platforms),
        "building_entries": sum(len(board["B"]["Entries"]) for board in platforms),
    }
    return document, port_report


def _local_wiring(blueprint: dict) -> Wiring:
    wiring = Wiring(blueprint)
    dependencies = {}
    for i, (_, entry) in enumerate(wiring.entries):
        ports = PORTS.get(_kind(entry))
        if ports and ports[1]:
            dependencies[i] = {source for port in range(len(ports[1])) for source, _ in wiring.sources(i, port)}
    try:
        TopologicalSorter(dependencies).prepare()
    except CycleError as error:
        raise ValueError("原生本地接线存在反馈环，无法使用固定频道延迟") from error
    return wiring


def _attach_callee(document: dict, report: dict, path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text.startswith("SHAPEZ2-4-") or not text.endswith("$"):
        raise ValueError("需要 SHAPEZ2-4 格式的定步原生蓝图")
    blueprint = json.loads(gzip.decompress(base64.b64decode(text[10:-1], validate=True)))["BP"]
    wiring = Wiring(blueprint)
    rx, tx = set(), set()
    first, last = report["callee"]["reserved_channels"]
    for i, (_, entry) in enumerate(wiring.entries):
        kind = entry["T"]
        if kind in (_RADIO_RECEIVER, _RADIO_TRANSMITTER):
            (source, _), = wiring.sources(i, 0)
            channel = decode_constant(wiring.entries[source][1]["C"])
            if type(channel) is not int or not first <= channel <= last:
                raise ValueError("定步蓝图包含接口表以外的无线频道")
            (rx if kind == _RADIO_RECEIVER else tx).add(channel)
    if (report["callee"]["inputs"]["run"]["channel"] not in rx
            or any(port["channel"] not in tx for port in report["callee"]["outputs"].values())):
        raise ValueError("实际定步蓝图未接通接口表的 run 或结果频道")
    boards = document["BP"]["Entries"]
    offset = 3 + max(p.get("X", 0) for p in boards) - min(p.get("X", 0) for p in wiring.platforms)
    boards.extend({**p, "X": p.get("X", 0) + offset} for p in wiring.platforms)
    _local_wiring(document["BP"])
    report["callee"]["platforms"] = len(wiring.platforms)
    report["platforms"] = len(boards)
    report["building_entries"] += len(wiring.entries)


def main() -> int:
    parser = argparse.ArgumentParser(description="从接口表生成重复调用定步模块的原生蓝图")
    parser.add_argument("interface", type=Path, help="定步模块的 JSON 接口表")
    parser.add_argument("calls", type=Path, help="按顺序列出每次调用的 JSON 参数")
    parser.add_argument("--channel-base", type=int, required=True, help="调用器的首个独占频道")
    parser.add_argument("--callee", type=Path, help="合装定步模块的原生蓝图")
    parser.add_argument("--result", action="append", help="只锁存指定结果字段，可重复指定")
    parser.add_argument("--output", type=Path, required=True, help="原生 .spz2bp 输出路径")
    args = parser.parse_args()
    try:
        interface = json.loads(args.interface.read_text(encoding="utf-8"))
        calls = json.loads(args.calls.read_text(encoding="utf-8"))
        result_names = tuple(args.result) if args.result is not None else None
        document, report = build_calls(interface, calls, args.channel_base, result_names=result_names)
        if args.callee:
            _attach_callee(document, report, args.callee)
        _write_blueprint(document, report, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
