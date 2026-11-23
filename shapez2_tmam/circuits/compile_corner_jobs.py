"""从制角方法编译子步骤参数和共用写入调用。"""

from .compiler_backend import _write_blueprint
from .compiler_backend.confirmed_call import build as build_confirmed_call
from .compiler_backend.method_sequence import _radio_channels
from .compiler_backend.module_caller import _compare, _gate, _local_wiring
from .compiler_backend.prefix_scan_wiring import _append
from .local_module import Module


_PHASE, _NEXT, _SETTLED, _CONFIRMED, _HAS_CALL = range(1702640, 1702645)
_ADDRESS, _REQUEST, _ACK, _OPCODE = range(1702645, 1702649)
_ENABLE, _DONE = 1702052, 1702053
_SELECTOR, _RUN, _CALL_DONE = 1701636, 1701637, 1701638


def _parts(fields, single, column):
    phase = {"phase": _PHASE}
    main = {**phase, "main": 1701692}
    for name, inputs, outputs in (
        ("dense", main, {"destination": 1701404, "scratch": 1701405}),
        ("append", main, {"lower": 1701651, "upper": 1701652}),
        ("release", main, {"main": 1701662, "support": 1701663, "far": 1701664, "upper": 1701665}),
    ):
        yield f"corner-job-{name}", fields("corner_jobs", {k: f"corner_{name}_{k}" for k in outputs}, inputs, outputs)
    yield "corner-job-direction", single("corner_jobs", "corner_column_ccw", "ccw", {"column": column}, 1700678)
    for name, method, inputs, channel in (
        ("selector", "corner_job_selector", {"suspended": 1700579, "highest": 1700588, "pins": 1701623,
                                             "far": 1701622, "counterclockwise": 1700678}, _SELECTOR),
        ("dense-role", "corner_dense_role", {"suspended": 1700579}, 1701650),
        ("append-mode", "corner_append_mode", {"suspended": 1700579}, 1701657),
        ("append-initial", "corner_append_initial", {"main": 1701692, "highest": 1700588}, 1701653),
        ("release-stage", "corner_release_stage", {"suspended": 1700579}, 1701660),
    ):
        yield f"corner-job-{name}", single("corner_jobs", method, "result", {**phase, **inputs}, channel)
    yield "corner-job-successor", single("corner_jobs", "corner_job_successor", "next", phase, 1702664)
    yield "corner-job-cursor", fields(
        "corner_jobs", {"next": "corner_job_next", "done": "corner_job_done"},
        {**phase, "enable": _ENABLE, "settled": _SETTLED, "selector": _SELECTOR, "confirmed": _CONFIRMED,
         "successor": 1702664},
        {"next": _NEXT, "done": _DONE},
    )
    yield "corner-job-clock", _clock()


def export(output_dir, fields, single, column):
    document = {"V": 1137, "BP": {"$type": "Island", "BinaryVersion": 1137, "Entries": []}}
    reports = {}
    for name, (board, table) in _parts(fields, single, column):
        _write_blueprint(board, table, output_dir / f"{name}.spz2bp")
        entries = board["BP"]["Entries"]
        if document["BP"]["Entries"]:
            _append(document, entries)
        else:
            document["BP"]["Entries"].extend(entries)
        reports[name] = table
    wiring = _local_wiring(document["BP"])
    receivers, senders = _radio_channels(wiring)
    if any(count > 1 for count in senders.values()):
        raise ValueError("制角排程有重复发射频道")
    report = {"inputs": sorted(receivers.keys() - senders.keys()), "outputs": sorted(senders),
              "timing": reports["corner-job-clock"]["timing"], "platforms": len(wiring.platforms),
              "building_entries": len(wiring.entries)}
    _write_blueprint(document, report, output_dir / "corner-jobs.spz2bp")


def _clock():
    document, report = build_confirmed_call(
        enable=_ENABLE, address=_ADDRESS, ack=_ACK, finished=_DONE, opcode=_OPCODE,
        settled=_SETTLED, has_packet=_HAS_CALL, confirmed=_CONFIRMED, request=_REQUEST,
        states={"phase": (_PHASE, _NEXT, 0)}, settle_ticks=6400, update_ticks=1600, channel_base=1702650,
    )
    board = Module({"phase": _PHASE, "done": _CALL_DONE, "selector": _SELECTOR, "request": _REQUEST})
    cleared = _compare(board, "cleared", "done", 0)
    started = _compare(board, "started", "request", 0, "Ag==")
    idle = _compare(board, "idle", "selector", 0)
    selected = _gate(board, "Not", "selected", idle)
    finished = _compare(board, "finished", "done", 1)
    confirmed = _gate(board, "And", "confirmed", started, finished)
    board.outputs = {_gate(board, "If", "address", "phase", cleared): _ADDRESS,
                     _gate(board, "If", "opcode", 1, selected): _OPCODE,
                     started: _RUN,
                     _gate(board, "If", "ack", "request", confirmed): _ACK}
    _append(document, board.layout()["BP"]["Entries"])
    return document, report
