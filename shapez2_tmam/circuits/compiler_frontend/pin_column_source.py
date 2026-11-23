"""把顶针单列来源的固定模式展开成可编译的 Python 方法。"""

import argparse
from pathlib import Path

from ...synthesis.pin_patterns import SOURCE_PATTERNS


def _all(terms):
    parts = tuple(dict.fromkeys(term for term in terms if term != "True"))
    if "False" in parts:
        return "False"
    return "True" if not parts else parts[0] if len(parts) == 1 else "(" + " & ".join(parts) + ")"


def _any(terms):
    parts = tuple(dict.fromkeys(term for term in terms if term != "False"))
    if "True" in parts:
        return "True"
    return "False" if not parts else parts[0] if len(parts) == 1 else "(" + " | ".join(parts) + ")"


def _not(term):
    if term == "True":
        return "False"
    if term == "False":
        return "True"
    return f"(not {term})"


def _at_least(end, count):
    if count <= 0:
        return "True"
    return "False" if count > end else f"count_{end}_{count}"


def _exact(end, count):
    return _all((_at_least(end, count), _not(_at_least(end, count + 1))))


def _pattern_condition(kept, crystals):
    occupied = set(kept) | set(crystals)
    pins = []
    for row in crystals:
        if row and row - 1 not in occupied:
            below = max((z for z in occupied if z < row), default=-1)
            if below not in kept:
                return "False"
            pins.append(_not(f"pin_{kept.index(below)}"))
    if any(not set(range(lower + 1, upper)) <= occupied for lower in crystals for upper in crystals):
        return "False"

    for rank, row in enumerate(kept):
        if row and row - 1 not in occupied:
            pins.append(_not(f"pin_{rank}"))
        if row and any(z > row for z in crystals):
            prefix = _all(f"pin_{i}" for i in range(rank)) if set(range(row)) <= set(kept) else "False"
            pins.append(_any((_not(f"pin_{rank}"), prefix)))

    # 同一保留掩码共用落点与穿晶判定，同一晶体掩码共用强制晶体判定。
    positions = [_at_least(min(row + 2, 5), rank + 1) for rank, row in enumerate(kept)]
    for row in range(4):
        before = sum(z < row for z in kept)
        positions.append(_any((_not(f"forced_{row}"), _exact(row + 1, before))))
    forced = [_not(f"forced_{row}") for row in range(4) if row not in crystals]
    forced.extend(f"(forced_{row} == forced_{row + 1})"
                  for row in range(3) if row in crystals and row + 1 in crystals)
    return _all((_all(positions), _all(forced), _all(pins)))


def _selection():
    lines = []
    for row in range(4, -1, -1):
        lines.append(f"row_{row} = unstack_upper(word)")
        if row:
            lines.append("word = unstack_lower(word)")
    for row in range(5):
        lines.append(f'needle_{row} = row_{row} == shape_literal("Su------")')
        ordinary = f'(row_{row} == shape_literal("Ru------"))'
        retained = _any((ordinary, f"needle_{row}")) if row else ordinary
        lines.append(f"retained_{row} = {retained}")
        for count in range(1, row + 2):
            needed = _all((_at_least(row, count - 1), f"retained_{row}"))
            lines.append(f"count_{row + 1}_{count} = " + _any((_at_least(row, count), needed)))
    for row in range(4):
        lines.append(f'forced_{row} = row_{row + 1} == shape_literal("Wu------")')
        witnesses = (_all((f"needle_{z}", _exact(z, row))) for z in range(1, 5) if row <= z)
        lines.append(f"pin_{row} = " + _any(witnesses))
    lines.extend(f"slot_{slot} = slot == {slot}" for slot in range(20))

    selected = []
    for ground, buckets in enumerate(SOURCE_PATTERNS):
        for count, patterns in enumerate(buckets):
            if not patterns:
                continue
            bucket = f"bucket_{ground}_{count}"
            floor = "needle_0" if ground else "(not needle_0)"
            lines.append(f"{bucket} = " + _all((floor, _exact(5, count))))
            for slot, (keep_mask, crystal_mask) in enumerate(patterns):
                kept = tuple(row for row in range(4) if keep_mask & (1 << row))
                crystals = tuple(row for row in range(4) if crystal_mask & (1 << row))
                condition = _pattern_condition(kept, crystals)
                if condition == "False":
                    continue
                name = f"selected_{ground}_{count}_{slot}"
                lines.append(f"{name} = " + _all((bucket, f"slot_{slot}", condition)))
                selected.append((name, kept, crystals))
    lines.append('valid = ' + _all(('(row_0 != shape_literal("Wu------"))', _any(name for name, _, _ in selected))))
    return lines, selected


def _mask_body(selected, field):
    lines = []
    for row in range(4):
        chosen = _any(pattern[0] for pattern in selected if row in pattern[field])
        lines.extend((f"bit_{row} = 0", f"if {chosen}:", f"    bit_{row} = {1 << row}"))
    lines.append("return (bit_0 + bit_1) + (bit_2 + bit_3)")
    return lines


def _material_body(selected, row):
    crystals = _any(name for name, _, rows in selected if row in rows)
    by_rank = [
        _any(name for name, kept, _ in selected if row in kept and kept.index(row) == rank)
        for rank in range(row + 1)
    ]
    has_pin = _any(_all((chosen, f"pin_{rank}")) for rank, chosen in enumerate(by_rank))
    ordinary = _any(_all((chosen, _not(f"pin_{rank}"))) for rank, chosen in enumerate(by_rank))
    return [f"if {crystals}:", "    return 3", f"if {has_pin}:", "    return 2",
            f"if {ordinary}:", "    return 1", "return 0"]


def generate_pin_column_source(mode: str = "materials") -> str:
    """生成共用词形和槽号输入的四层材料或两份掩码方法。"""
    selection, selected = _selection()
    blocks = [
        '"""顶针单列候选结构，按 SOURCE_PATTERNS 的原槽序。"""',
        "from shapez2_tmam.synthesis.physics import Shape\n"
        "from shapez2_tmam.synthesis.shape_methods import shape_literal, unstack_lower, unstack_upper",
    ]

    def append(name, result, body):
        head = f"def {name}(word: Shape, slot: int) -> {result}:"
        blocks.append(head + "\n" + "\n".join(f"    {line}" for line in (*selection, *body)))

    append("valid", "bool", ["return valid"])
    invalid = ["if not valid:", "    return -1"]
    if mode == "masks":
        for field, name in enumerate(("keep", "crystals"), 1):
            append(name, "int", [*invalid, *_mask_body(selected, field)])
    elif mode == "materials":
        for row in range(4):
            append(f"material_{row}", "int", [*invalid, *_material_body(selected, row)])
    else:
        raise ValueError("输出模式须为 materials 或 masks")
    return "\n\n\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成顶针单列定址的可编译源码")
    parser.add_argument("--mode", choices=("materials", "masks"), default="materials", help="输出材料或掩码方法")
    parser.add_argument("--output", required=True, type=Path, help="生成的 Python 源码路径")
    args = parser.parse_args()
    try:
        args.output.write_text(generate_pin_column_source(args.mode), encoding="utf-8")
    except OSError as error:
        parser.exit(2, f"写入 {args.output} 失败。{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
