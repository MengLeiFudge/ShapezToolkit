"""一代电路信号与图形操作；保留形状和颜色，不把控制指令降为占用位。"""

from functools import lru_cache

# null、false、true 是三个不同的信号；冲突单独存储在网络状态中。
NULL, FALSE, TRUE = 0, 1, 2
COLORS = "ur g b y p c w".replace(" ", "")
COLOR_NAMES = ("uncolored", "red", "green", "blue", "yellow", "purple", "cyan", "white")
SHAPES = "CRSW"
LAYER_BITS = 24
LAYER_MASK = (1 << LAYER_BITS) - 1


def from_key(key: str) -> int:
    """将短代码编码为六位角块序列；最高位记录层数，保留空层以检查非法输入。"""
    layers = key.split(":")
    if not 1 <= len(layers) <= 4 or any(len(layer) != 8 for layer in layers):
        raise ValueError(f"无效图形代码：{key}")
    value = 1 << (len(layers) * LAYER_BITS)
    for z, layer in enumerate(layers):
        for q in range(4):
            part = layer[q * 2:q * 2 + 2]
            if part != "--":
                cell = SHAPES.index(part[0]) * 8 + COLORS.index(part[1]) + 1
                value |= cell << (z * LAYER_BITS + q * 6)
    return value


def to_key(value: int) -> str | None:
    """输出图形短代码；非图形返回 None。"""
    if value < 1 << LAYER_BITS:
        return None
    layers = []
    for z in range((value.bit_length() - 1) // LAYER_BITS):
        layer = []
        for q in range(4):
            cell = (value >> (z * LAYER_BITS + q * 6)) & 63
            layer.append("--" if not cell else SHAPES[(cell - 1) // 8] + COLORS[(cell - 1) % 8])
        layers.append("".join(layer))
    return ":".join(layers)


def from_saved(item: dict | None) -> int:
    """读取存档中的 null、布尔、颜色或图形值，拒绝未知类型。"""
    if item is None:
        return NULL
    kind, data = item["$"], item["data"]
    if kind == "boolean_item":
        return TRUE if data else FALSE
    if kind == "color":
        return 3 + COLOR_NAMES.index(data)
    if kind == "shape":
        return from_key(data)
    raise ValueError(f"不支持的信号类型：{kind}")


def describe(value: int) -> str | None:
    """将信号转换为报告可读值。"""
    if value == NULL:
        return None
    if value < 3:
        return "true" if value == TRUE else "false"
    if value < 11:
        return COLOR_NAMES[value - 3]
    return to_key(value)


def structure(value: int) -> int:
    """提取四层占用位，低四位为底层，角顺序为右上、右下、左下、左上。"""
    if value < 1 << LAYER_BITS:
        return 0
    body = value ^ (1 << (value.bit_length() - 1))
    return sum(1 << q for q in range(16) if (body >> (q * 6)) & 63)


def from_structure(shape: int) -> int:
    """将 16 位结构转换成无色圆形；0 表示断开输入，空中间层原样保留。"""
    if not 0 <= shape <= 65535:
        raise ValueError("结构编号必须在 0..65535 内")
    if not shape:
        return NULL
    layers = (shape.bit_length() + 3) // 4
    return (1 << (layers * LAYER_BITS)) | sum(1 << (q * 6) for q in range(16) if shape & (1 << q))


def valid_structure(shape: int) -> bool:
    """游戏常量输入要求至少一层，且每层至少有一个角。"""
    return bool(shape) and all((shape >> z) & 15 for z in range(0, shape.bit_length(), 4))


@lru_cache(maxsize=262144)
def operate(code: int, a: int, b: int = NULL) -> tuple[int, ...]:
    """执行一个门的纯运算；调用方在进入前处理输入网络冲突。"""
    if code == 32:
        return (TRUE if a > FALSE and b > FALSE else FALSE,)
    if code == 34:
        return (TRUE if a <= FALSE else FALSE,)
    if code == 35:
        return (TRUE if (a > FALSE) != (b > FALSE) else FALSE,)
    if code == 36:
        return (TRUE if a > FALSE or b > FALSE else FALSE,)
    if code in (38, 60):
        return (b if a > FALSE else NULL,)
    if code == 46:
        return (NULL if not a or not b else TRUE if a == b else FALSE,)
    if a < 1 << LAYER_BITS:
        return (NULL, NULL) if code in (42, 43, 45) else (NULL,)
    count = (a.bit_length() - 1) // LAYER_BITS
    layers = [(a >> (i * LAYER_BITS)) & LAYER_MASK for i in range(count)]
    if code == 43:
        cell = a & 63
        if not cell:
            return (NULL, NULL)
        plain = (cell - 1) // 8 * 8 + 1
        full = (1 << LAYER_BITS) | sum(plain << (q * 6) for q in range(4))
        return (3 + (cell - 1) % 8, full)
    if code == 44:
        layers = [((layer << 6) & LAYER_MASK) | (layer >> 18) for layer in layers]
    elif code == 45:
        lower = (a & ((1 << ((count - 1) * LAYER_BITS)) - 1)) | (1 << ((count - 1) * LAYER_BITS)) if count > 1 else NULL
        return (lower, layers[-1] | (1 << LAYER_BITS))
    elif code == 42:
        results = []
        for mask in (LAYER_MASK ^ 4095, 4095):
            half = [layer & mask for layer in layers if layer & mask]
            results.append((1 << (len(half) * LAYER_BITS)) | sum(layer << (z * LAYER_BITS) for z, layer in enumerate(half)) if half else NULL)
        return tuple(results)
    elif code == 50:
        if b < 1 << LAYER_BITS:
            return (NULL,)
        top_count = (b.bit_length() - 1) // LAYER_BITS
        top = [(b >> (i * LAYER_BITS)) & LAYER_MASK for i in range(top_count)]
        heights = [max((z for z, layer in enumerate(layers) if (layer >> (q * 6)) & 63), default=-1) for q in range(4)]
        bottoms = [next((z for z, layer in enumerate(top) if (layer >> (q * 6)) & 63), 4) for q in range(4)]
        offset = max(0, 1 - min(bottoms[q] - heights[q] for q in range(4)))
        layers.extend([0] * max(0, offset + top_count - count))
        for z, layer in enumerate(top):
            layers[offset + z] |= layer
        layers = layers[:4]
    elif code == 51:
        if not 3 <= b < 11:
            return (NULL,)
        layers = [sum((((((layer >> (q * 6)) & 63) - 1) // 8 * 8 + b - 2) << (q * 6)) if (layer >> (q * 6)) & 63 else 0 for q in range(4)) for layer in layers]
    else:
        raise ValueError(f"未知逻辑门建筑代码：{code}")
    return ((1 << (len(layers) * LAYER_BITS)) | sum(layer << (z * LAYER_BITS) for z, layer in enumerate(layers)),)
