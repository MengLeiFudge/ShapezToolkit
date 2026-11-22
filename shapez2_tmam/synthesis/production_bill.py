"""从四象限制造树展开每件成品的物料需求，固定货种与配料站的层位相对应。"""

from collections import Counter
from fractions import Fraction

from .physics import EMPTY, PIN
from .recipe import Recipe


# 原生 PainterDefault / CrystalGeneratorDefault 的 ConsumptionPerItemInLiters。
PAINT_LITERS = 10
CRYSTAL_LITERS = 20
# 两个等容混合腔。白色采用红 + 青，青采用绿 + 蓝。
PRIMARY = {"r": "rrrr", "g": "gggg", "b": "bbbb", "y": "rrgg",
           "c": "ggbb", "m": "rrbb", "w": "rrgb"}
SHAPE_LOADS = (("C", "R", "S"), ("W", None, None))
FLUID_LOADS = (("r", "g", "b"),)


def production_bill(recipe: Recipe) -> dict:
    if recipe.height != 5 or len(recipe.result.layers[0]) != 4:
        raise ValueError("整厂用料需要四象限五层配方")
    steps = list(recipe.steps())
    raw = Counter()
    paint = Counter()
    work = Counter()
    layers = []
    labels = [step["result"][p:p+2] for step in steps if step["operation"] == "base" for p in range(0, 8, 2)]
    blanks = Counter(label[0] for label in labels if label not in (PIN, EMPTY))
    blank = max(sorted(blanks), key=blanks.get) if blanks else "C"
    pigments = Counter(step["parameter"] for step in steps if step["operation"] == "crystal")
    pigments.update(label[1] for label in labels if label not in (PIN, EMPTY) and label[1] != 'u')
    # 优先用配方本来就需要的单色做牺牲塔；其余颜色按相同混合比例出料。
    used = Counter()
    for color, count in pigments.items():
        for source in PRIMARY[color]:
            used[source] += count
    pin_color = max("rgb", key=lambda source: used[source])
    for step in steps:
        op = step["operation"]
        if op != "base":
            work[op] += 1
            if op == "crystal":
                paint[step["parameter"]] += CRYSTAL_LITERS
            continue
        row = tuple(step["result"][p:p+2] for p in range(0, 8, 2))
        direct = len(set(row)) == 1
        orders = []
        for q, cell in enumerate(row[:1] if direct else row):
            part, color = cell
            kind = blank if cell in (EMPTY, PIN) else part
            raw[kind] += 1
            if cell == PIN:
                work.update({"pin": 6, "crystal": 1})
                paint[pin_color] += CRYSTAL_LITERS
            elif cell == EMPTY:
                work.update({"cut": 1, "rotate": 1})
            elif color != 'u':
                paint[color] += PAINT_LITERS
                work["paint"] += 1
            orders.append({"q": q, "cell": cell, "blank": kind,
                           "line": "pin" if cell == PIN else ("empty-front" if q < 2 else "empty-back")
                           if cell == EMPTY else "ordinary"})
        if not direct:
            work.update({"swap": 3, "rotate": 2})
        layers.append({"step": step["id"], "mode": "direct" if direct else "quarters", "orders": orders})
    primary = Counter()
    for color, liters in paint.items():
        for source in PRIMARY[color]:
            primary[source] += Fraction(liters, 4)
    return {"raw_items_per_product": dict(sorted(raw.items())), "prepared_dye_liters_per_product": dict(sorted(paint.items())),
            "primary_liters_per_product": {k: float(v) for k,v in sorted(primary.items())},
            "operations_per_product": dict(sorted(work.items())), "pin_color": pin_color,
            "base_orders": layers, "shape_train_layers": SHAPE_LOADS, "fluid_train_layers": FLUID_LOADS}
