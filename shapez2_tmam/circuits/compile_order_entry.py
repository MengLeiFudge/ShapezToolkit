"""编译根订单的五层供料判定和尾针深度上界。"""

import argparse
from pathlib import Path

from .compile_pair_writer import _compile, _one
from .compiler_backend import _write_blueprint
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _local_wiring
from .compiler_backend.prefix_scan_wiring import _append
from .compiler_frontend import FrontendError


_ROWS = tuple(range(1701200, 1701205))
_ROW_UNKNOWN = tuple(range(1704660, 1704665))
_ROW_CRYSTAL = tuple(range(1704665, 1704668))
_NONEMPTY, _UNKNOWN, _BUDGET = range(1704670, 1704673)


def _parts():
    for z, channel in enumerate(_ROWS):
        outputs = {"unknown": _ROW_UNKNOWN[z]}
        if z >= 2:
            outputs["crystal"] = _ROW_CRYSTAL[z - 2]
        yield _compile("order_entry", {field: f"order_row_{field}" for field in outputs}, {"row": channel}, outputs)
    yield _one("order_entry", "order_nonempty", "nonempty", {f"row{z}": channel for z, channel in enumerate(_ROWS)}, _NONEMPTY)
    yield _one("order_entry", "order_unknown", "unknown", {f"u{z}": channel for z, channel in enumerate(_ROW_UNKNOWN)}, _UNKNOWN)
    yield _one("order_entry", "order_pin_budget", "budget", {f"z{z}": channel for z, channel in enumerate(_ROW_CRYSTAL, 2)}, _BUDGET)


def build():
    parts = tuple(_parts())
    document = parts[0][0]
    for part, _ in parts[1:]:
        _append(document, part["BP"]["Entries"])
    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    if receivers.keys() - senders.keys() != set(_ROWS) or any(count != 1 for count in senders.values()):
        raise ValueError("根订单确认的原生频道不符")
    holds = [report["settling"]["hold_signal_ticks"] for _, report in parts]
    report = {"inputs": {"rows": _ROWS}, "outputs": {"nonempty": _NONEMPTY, "unknown": _UNKNOWN, "budget": _BUDGET},
              "hold_signal_ticks": max(holds[:5]) + max(holds[5:]) + 12,
              "platforms": len(wiring.platforms), "building_entries": len(wiring.entries)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="导出四象限五层根订单筛选")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图输出路径")
    args = parser.parse_args()
    try:
        document, report = build()
        _write_blueprint(document, report, args.output)
    except FrontendError as error:
        parser.error(f"{error.filename}:{error.lineno}:{error.offset} {error.msg}")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
