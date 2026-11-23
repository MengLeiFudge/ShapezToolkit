"""生成分开布置的顶针单列解码、模式查表与结构校验。"""

import argparse
from pathlib import Path

from ...synthesis.pin_patterns import SOURCE_PATTERNS
from .pin_column_source import _all, _any, _not


_MARKERS = ("Cu------", "Ru------", "Su------", "Wu------")
_ROWS = tuple(f"z{row}" for row in range(5))


def _function(name, args, result, lines):
    return f"def {name}({args}) -> {result}:\n" + "\n".join(f"    {line}" for line in lines)


def _decoder():
    args = "word: Shape"
    yield _function("_kind", "row: Shape | None", "int", [
        line for value, code in enumerate(_MARKERS[1:], 1)
        for line in (f'if row == shape_literal("{code}"):', f"    return {value}")
    ] + ["return 0"])
    for row, name in enumerate(_ROWS):
        yield _function(f"read_{name}", args, "int", ["word = unstack_lower(word)"] * (4 - row)
                        + ["return _kind(unstack_upper(word))"])
    lines = list(_prefix("target", _retained()))
    lines.extend(("retained = 0", *(line for count in range(1, 6)
                                     for line in (f"if {_exact('target', 5, count)}:",
                                                  f"    retained = {count}"))))
    args = ", ".join(f"{name}: int" for name in _ROWS)
    yield _function("find_bucket", args, "int", [*lines,
                    "if retained == 5:", "    return -1",
                    "if z0 == 2:", "    return retained + 5", "return retained"])
    reads = ", ".join(f"read_{name}(word)" for name in _ROWS)
    yield _function("bucket", "word: Shape", "int", [f"return find_bucket({reads})"])


def _lookup():
    # 每个槽的形状常量可在四个象限各存一个桶的候选。所有标记都是实心普通材料。
    patterns = {5 * floor + count: slots for floor, buckets in enumerate(SOURCE_PATTERNS)
                for count, slots in enumerate(buckets) if slots}
    keys = tuple(patterns)
    groups = [keys[start:start + 4] for start in range(0, len(keys), 4)]
    body = []
    for group, group_keys in enumerate(groups):
        lines = []
        for slot in range(max(len(patterns[key]) for key in group_keys)):
            choices = [patterns[key][slot] if slot < len(patterns[key]) else None for key in group_keys]
            rows = []
            for row in range(4):
                parts = []
                for choice in choices:
                    if choice is None:
                        parts.append("--")
                        continue
                    keep, crystals = choice
                    value = 1 if keep & (1 << row) else 3 if crystals & (1 << row) else 0
                    parts.append(_MARKERS[value][:2])
                rows.append("".join(parts).ljust(8, "-"))
            code = ":".join(rows)
            lines.extend((f"if slot == {slot}:", f'    return shape_literal("{code}")'))
        yield _function(f"pack_{group}", "slot: int", "Shape | None", [*lines, "return None"])
        body.append(f"if {_any(f'(bucket == {key})' for key in group_keys)}:")
        body.append(f"    packed = group_{group}")
        rotations = ("packed", "rotate_ccw(packed)", "rotate_ccw(rotate_ccw(packed))", "rotate_cw(packed)")
        for key, rotated in zip(group_keys, rotations):
            body.extend((f"    if bucket == {key}:", f"        return _isolate({rotated})"))
        body.append("    return None")
    yield _function("_isolate", "packed: Shape | None", "Shape | None",
                    ["return rotate_ccw(cut_front(rotate_cw(cut_front(packed))))"])
    args = ", ".join(["bucket: int", *(f"group_{i}: Shape | None" for i in range(len(groups)))])
    yield _function("select_pattern", args, "Shape | None", [*body, "return None"])
    packs = ", ".join(f"pack_{i}(slot)" for i in range(len(groups)))
    yield _function("pattern", "bucket: int, slot: int", "Shape | None",
                    [f"return select_pattern(bucket, {packs})"])


def _at_least(name, end, rank):
    if rank == 0:
        return "True"
    return "False" if rank > end else f"{name}_{end}_{rank}"


def _exact(name, end, rank):
    return _all((_at_least(name, end, rank), _not(_at_least(name, end, rank + 1))))


def _prefix(name, terms):
    for row, term in enumerate(terms):
        for rank in range(1, row + 2):
            existing = _at_least(name, row, rank)
            added = _all((term, _at_least(name, row, rank - 1)))
            yield f"{_at_least(name, row + 1, rank)} = {_any((existing, added))}"


def _bound(left, end, right, limit):
    return _all(_any((_not(_at_least(left, end, rank)), _at_least(right, limit, rank)))
                for rank in range(1, end + 1))


def _same(left, end, right, limit):
    return _all((_bound(left, end, right, limit), _bound(right, limit, left, end)))


def _retained():
    return ["(z0 == 1)", *(f"((z{i} == 1) | (z{i} == 2))" for i in range(1, 5))]


def _validation():
    lines = ["present = pattern is not None"]
    for row in range(3, -1, -1):
        lines.extend((f"pattern_{row} = unstack_upper(pattern)",
                      f'keep_{row} = pattern_{row} == shape_literal("{_MARKERS[1]}")',
                      f'crystal_{row} = pattern_{row} == shape_literal("{_MARKERS[3]}")',
                      f"occupied_{row} = keep_{row} | crystal_{row}"))
        if row:
            lines.append("pattern = unstack_lower(pattern)")
    # 前缀是否达到指定格数用布尔信号表示，供落点和穿晶条件共用。
    lines.extend(_prefix("target", _retained()))
    lines.extend(_prefix("kept", [f"keep_{i}" for i in range(4)]))
    for rank in range(4):
        witnesses = (_all((f"(z{row} == 2)", _exact("target", row, rank)))
                     for row in range(max(1, rank), 5))
        lines.append(f"needle_{rank} = {_any(witnesses)}")
    checks = ["present", "(z0 != 3)", "(occupied_0 == (z0 == 2))", _same("target", 5, "kept", 4)]
    for row in range(4):
        witnesses = (_all((f"needle_{rank}", _exact("kept", row, rank))) for rank in range(row + 1))
        lines.append(f"pin_{row} = " + _all((f"keep_{row}", _any(witnesses))))
        lines.append(f"forced_{row} = z{row + 1} == 3")
        checks.append(_any((_not(f"keep_{row}"), _bound("kept", row + 1, "target", row + 2))))
        same_before = _same("kept", row, "target", row + 1)
        checks.append(_any((_not(f"forced_{row}"), _all((f"crystal_{row}", same_before)))))
    args = ", ".join(["pattern: Shape | None", *(f"{name}: int" for name in _ROWS)])
    yield _function("fit_low", args, "bool", [*lines, "return " + _all(checks[:8])])
    yield _function("fit_high", args, "bool", [*lines, "return " + _all(checks[8:])])
    call = "pattern, " + ", ".join(_ROWS)
    yield _function("fit", args, "bool", [f"return fit_low({call}) & fit_high({call})"])
    for row in range(4):
        yield _function(f"restore_{row}", args, "int", [
            *lines, f"if crystal_{row}:", "    return 3", f"if pin_{row}:", "    return 2",
            f"if keep_{row}:", "    return 1", "return 0",
        ])

    lines = ["ordinary_below_0 = False", "pins_below_0 = True"]
    checks = ["low", "high"]
    for row in range(4):
        lines.extend((f"occupied_{row} = m{row} != 0", f"pin_{row} = m{row} == 2",
                      f"crystal_{row} = m{row} == 3", f"forced_{row} = z{row + 1} == 3"))
    for row in range(4):
        if row:
            below = row - 1
            checks.extend((f"((not pin_{row}) | occupied_{below})",
                           f"((not crystal_{row}) | occupied_{below} | ordinary_below_{row})",
                           f"((not (crystal_{below} & crystal_{row})) | (forced_{below} == forced_{row}))"))
        if 0 < row < 3:
            above = _any(f"crystal_{z}" for z in range(row + 1, 4))
            below = _any(f"crystal_{z}" for z in range(row))
            checks.extend((_any((f"occupied_{row}", _not(below), _not(above))),
                           _any((_not(f"pin_{row}"), _not(above), f"pins_below_{row}"))))
        if row < 3:
            lines.extend((f"ordinary_below_{row + 1} = (m{row} == 1) | "
                          f"((not occupied_{row}) & ordinary_below_{row})",
                          f"pins_below_{row + 1} = pins_below_{row} & pin_{row}"))
    inputs = [*(f"m{i}: int" for i in range(4)), *(f"z{i}: int" for i in range(1, 5)),
              "low: bool", "high: bool"]
    args = ", ".join(inputs)
    yield _function("supported", args, "bool", [*lines, "return " + _all(checks)])
    call = ", ".join(spec.split(":")[0] for spec in inputs)
    for row in range(4):
        yield _function(f"publish_{row}", args, "int", [
            f"if supported({call}):", f"    return m{row}", "return -1",
        ])

    args = ", ".join(["pattern: Shape | None", *(f"{name}: int" for name in _ROWS)])
    call = "pattern, " + ", ".join(_ROWS)
    lines = [f"m{i} = restore_{i}({call})" for i in range(4)]
    collected = ", ".join([*(f"m{i}" for i in range(4)), *_ROWS[1:],
                           f"fit_low({call})", f"fit_high({call})"])
    yield _function("valid", args, "bool", [*lines, f"return supported({collected})"])
    for row in range(4):
        yield _function(f"material_{row}", args, "int", [*lines, f"return publish_{row}({collected})"])


def generate_pin_column_stages() -> str:
    blocks = [
        '"""顶针单列来源分段方法。"""',
        "from shapez2_tmam.synthesis.physics import Shape\n"
        "from shapez2_tmam.synthesis.shape_methods import (cut_front, rotate_ccw, rotate_cw, "
        "shape_literal, unstack_lower, unstack_upper)",
        *_decoder(), *_lookup(), *_validation(),
    ]
    return "\n\n\n".join(blocks) + "\n"


def pin_column_stage_plan(channel_base: int):
    """按模块返回字段方法、输入频道和输出频道。"""
    rows = {name: channel_base + 2 + i for i, name in enumerate(_ROWS)}
    bucket = channel_base + 7
    groups = {f"group_{i}": channel_base + 8 + i for i in range(3)}
    pattern = channel_base + 11
    fits = {"low": channel_base + 12, "high": channel_base + 13}
    materials = {f"m{i}": channel_base + 14 + i for i in range(4)}
    final = {f"material_{i}": channel_base + 19 + i for i in range(4)}
    checker = {"pattern": pattern, **rows}
    yield "read", {name: f"read_{name}" for name in rows}, {"word": channel_base}, rows
    yield "bucket", {"bucket": "find_bucket"}, rows, {"bucket": bucket}
    for i, (name, channel) in enumerate(groups.items()):
        yield f"pack_{i}", {name: f"pack_{i}"}, {"slot": channel_base + 1}, {name: channel}
    yield "pattern", {"pattern": "select_pattern"}, {"bucket": bucket, **groups}, {"pattern": pattern}
    for name, channel in fits.items():
        yield f"fit_{name}", {name: f"fit_{name}"}, checker, {name: channel}
    for label, indices in (("lower", range(3)), ("upper", range(3, 4))):
        fields = {f"m{i}": f"restore_{i}" for i in indices}
        yield f"restore_{label}", fields, checker, {name: materials[name] for name in fields}
    inputs = {**materials, **{name: rows[name] for name in _ROWS[1:]}, **fits}
    outputs = {"valid": channel_base + 18, **final}
    yield "materials", {"valid": "supported", **{name: f"publish_{i}" for i, name in enumerate(final)}}, inputs, outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="生成顶针单列查表与结构校验源码")
    parser.add_argument("--output", required=True, type=Path, help="生成的 Python 源码路径")
    args = parser.parse_args()
    try:
        args.output.write_text(generate_pin_column_stages(), encoding="utf-8")
    except OSError as error:
        parser.exit(2, f"写入 {args.output} 失败。{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
