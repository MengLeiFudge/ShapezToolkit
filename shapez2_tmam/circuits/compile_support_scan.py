"""导出复用同行支撑传播板的四象限五层 K/G 检查。"""

import argparse
from pathlib import Path

from ..synthesis.shape_methods import shape_literal
from .circuit import Literal
from .compile_pair_writer import _one
from .compiler_backend import _write_blueprint
from .compiler_backend.confirmed_call import _register, build as build_confirmed_call
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _compare, _gate, _local_wiring
from .compiler_backend.prefix_scan_wiring import _append
from .compiler_frontend import FrontendError
from .local_module import Module


_STEP, _ROW, _NEIGHBOR, _DOWN, _CHECK = range(1704400, 1704405)
_ENABLE, _SETTLED, _DONE, _GROUNDED, _OPTIONAL, _NEXT, _VALID, _NEXT_VALID = range(1704410, 1704418)
_ROWS = range(1704420, 1704425)
_MARKS = range(1704425, 1704430)
_ADDRESS, _ACK, _OPCODE, _HAS_PACKET, _CONFIRMED, _REQUEST = range(1704430, 1704436)
_CLOCK, _COMMIT = 1704460, 1704463
_SEED_INPUTS = {"row": 1703840, "added": 1703841, "reached": 1703842, "previous": 1703843,
                "down": _DOWN, "pin_seed": 1703845}


def _select(row, index, out):
    return _one("dense_input", "dense_input_row", "row", {**{f"row{i}": ch for i, ch in enumerate(row)}, "level": index}, out)


def _cursor():
    board = Module({"step": _STEP, "enable": _ENABLE, "settled": _SETTLED})
    board.lookup("step", "successor", ((i, min(i + 1, 16)) for i in range(17)))
    done = _compare(board, "terminal", "step", 16)
    active = _gate(board, "And", "advance", "enable", "settled")
    _gate(board, "If", "next", "successor", active)
    board.outputs = {"next": _NEXT, _gate(board, "And", "done", "enable", done): _DONE}
    return board


def _config():
    board = Module({"row": _ROW, "down": _DOWN, "grounded": _GROUNDED,
                    "neighbor_mark": 1703858, "old_mark": 1703857})
    ground = _compare(board, "ground", "row", 0)
    regular = _gate(board, "Not", "not_ground", ground)
    _gate(board, "If", "source", "neighbor_mark", regular)
    _gate(board, "If", "source", Literal(shape_literal("CuCuCuCu")), ground)
    board.outputs = {"source": 1703842, ground: 1703854,
                     _gate(board, "If", "old", "old_mark", "down"): 1703843,
                     _gate(board, "Not", "pin_seed", "grounded"): 1703845}
    return board


def _optional_top():
    board = Module({"row": _ROW, "optional": _OPTIONAL})
    top = _compare(board, "top", "row", 4)
    board.outputs = {_gate(board, "And", "optional_top", top, "optional"): 1703855}
    return board


def _write_mark(index, channel):
    board = Module({"enable": _ENABLE, "selected": _ROW, "checking": _CHECK, "commit": _COMMIT,
                    "new": 1703860, "old": channel})
    selected = _compare(board, "selected_row", "selected", index)
    propagate = _gate(board, "Not", "not_check", "checking")
    update = _gate(board, "And", "update_row", selected, propagate)
    load = _gate(board, "And", "load", "commit", update)
    keep = _gate(board, "Not", "keep_old", load)
    _gate(board, "If", "data", "new", _gate(board, "And", "write", "enable", load))
    _gate(board, "If", "data", "old", _gate(board, "And", "keep", "enable", keep))
    board.outputs = {"data": channel}
    return board


def _valid_update():
    board = Module({"checking": _CHECK, "valid": _VALID, "row_ok": 1703856})
    check_ok = _gate(board, "Or", "check_ok", _gate(board, "Not", "not_check", "checking"), "row_ok")
    board.outputs = {_gate(board, "And", "next_valid", "valid", check_ok): _NEXT_VALID}
    return board


def _parts():
    for name, channel in (("row", _ROW), ("neighbor", _NEIGHBOR), ("down", _DOWN), ("check", _CHECK)):
        yield f"control-{name}", _one("support_schedule", f"support_scan_{name}", name, {"step": _STEP}, channel)
    for name, rows, index, out in (("row", _ROWS, _ROW, 1703840), ("neighbor", _ROWS, _NEIGHBOR, 1703841),
                                  ("mark", _MARKS, _ROW, 1703857), ("neighbor-mark", _MARKS, _NEIGHBOR, 1703858)):
        yield name, _select(rows, index, out)
    for i, side in enumerate(("front", "back")):
        yield f"seed-{side}", _one("support_rows", f"support_seed_{side}", "reached", _SEED_INPUTS, 1703847 + i)
        yield f"spread-{side}", _one("support_rows", f"support_spread_{side}", "reached",
                                    {"row": 1703840, "seed": 1703846}, 1703849 + i)
    yield "join-seed", _one("support_rows", "support_join_halves", "row", {"front": 1703847, "back": 1703848}, 1703846)
    yield "join-mark", _one("support_rows", "support_join_halves", "row", {"front": 1703849, "back": 1703850}, 1703860)
    yield "check-row", _one("support_rows", "support_row_accepted", "accepted",
                           {"row": 1703840, "below": 1703841, "reached": 1703857,
                            "ground": 1703854, "optional": 1703855}, 1703856)


def build():
    parts = dict(_parts())
    ticks = {name: report["settling"]["hold_signal_ticks"] for name, (_, report) in parts.items()}
    select = max(ticks[name] for name in ("row", "neighbor", "mark", "neighbor-mark"))
    propagation = (max(ticks["seed-front"], ticks["seed-back"]) + ticks["join-seed"]
                   + max(ticks["spread-front"], ticks["spread-back"]) + ticks["join-mark"])
    settle = max(ticks["control-row"], ticks["control-neighbor"], ticks["control-down"], ticks["control-check"]) + select
    settle += max(propagation, ticks["check-row"]) + 768
    document, clock = build_confirmed_call(
        enable=_ENABLE, address=_ADDRESS, ack=_ACK, finished=_DONE, opcode=_OPCODE, settled=_SETTLED,
        has_packet=_HAS_PACKET, confirmed=_CONFIRMED, request=_REQUEST, states={"step": (_STEP, _NEXT, 0)},
        settle_ticks=settle, update_ticks=768, channel_base=_CLOCK,
    )
    for board, _ in parts.values():
        _append(document, board["BP"]["Entries"])
    modules = (_cursor(), _config(), _optional_top(), _valid_update(), _register(_ENABLE, _COMMIT, _VALID, _NEXT_VALID, 1),
               *(_write_mark(i, ch) for i, ch in enumerate(_MARKS)))
    for module in modules:
        _append(document, module.layout()["BP"]["Entries"])
    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    inputs = {"enable": _ENABLE, "grounded": _GROUNDED, "optional_top": _OPTIONAL, "rows": tuple(_ROWS)}
    public_inputs = {_ENABLE, _GROUNDED, _OPTIONAL, *_ROWS}
    if any(n != 1 for n in senders.values()) or receivers.keys() - senders.keys() != public_inputs | {_ADDRESS, _ACK, _OPCODE}:
        raise ValueError("支撑检查的实际原生收发与接口不符")
    report = {"inputs": inputs, "outputs": {"done": _DONE, "accepted": _VALID, "reached_rows": tuple(_MARKS)},
              "timing": clock["timing"], "platforms": len(wiring.platforms), "building_entries": len(wiring.entries)}
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="编译四象限五层的 K/G 支撑行扫描")
    parser.add_argument("--output", type=Path, required=True, help="原生蓝图路径")
    args = parser.parse_args()
    try:
        document, report = build()
        _write_blueprint(document, report, args.output)
    except FrontendError as error:
        parser.error(f"{error.filename}:{error.lineno}:{error.offset} {error.msg}")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"已导出 {args.output}，共 {report['platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
