# Python 方法编译前端

用 `compile_method(source, entry, filename=...)` 把一个 Python 源文件里的指定方法编译为 [`Program`](../compiler_contract.py)。`source` 是读取后的源码文本，`entry` 是顶层方法名，`filename` 用于定位诊断。编译时只读语法树，不导入源码。遇到不支持的写法会抛出 `FrontendError`，可用 `SyntaxError` 的文件、行号和列号字段呈现错误。

```python
from pathlib import Path

from shapez2_tmam.circuits.compiler_frontend import compile_method

path = Path("shapez2_tmam/synthesis/layer_methods.py")
program = compile_method(path.read_text(encoding="utf-8"), "append_five", filename=str(path))
```

| 用途 | 源码写法 |
|---|---|
| 类型 | 参数和返回值标注 `bool`、`int`、`Shape` 或 `Color`。图形与颜色可写 `\| None`，空值从赋值、返回、参数或比较的类型推断 |
| 局部状态 | 单变量赋值和带类型的局部变量。读取前必须在所有到达路径上赋值，一个变量始终保持相同类型 |
| 控制流 | `if`、`elif`、`else`，提前 `return`，短路 `and`、`or`，以及遍历同类型固定元组或字面量边界的 `range(stop)`、`range(start, stop)` |
| 只读表 | 可用整数索引读取非空的同类型固定元组。给元组命名时，在方法内定义一次。所有到达读取位置的路径都必须保证索引合法 |
| 字面量 | `True`、`False`，有符号 32 位整数，颜色单字符如 `"r"`，以及图形短代码如 `shape_literal("Cu------")` |
| 标量操作 | `not`，同类型 `==`、`!=`，对 `None` 的 `is`、`is not`，整数单次比较及可证明不溢出的加法 |
| 调用 | 同一文件的其他顶层方法，用固定位置参数调用，调用图必须无环。图形操作使用 [`BUILTINS`](../compiler_contract.py) 里的保留名称，如 `stack(lower, upper)` |

保留操作名在编译时绑定到共享合同。源码可以为纯 Python 调用提供同名实现，例如 `layer_methods.stack`，编译器使用合同里的签名与含义。自定义加工方法应使用其他名称。方法体只读参数、局部变量和可静态解析的调用，无需为蓝图摆放或时序传入参数。

`shape_literal` 是保留名称，参数是固定短代码。编译器按四象限五层规则校验图形，按 `COLORS` 校验颜色字符。Python 源码可定义同名函数，使直接调用时也得到 `Shape` 对象。颜色类型在 Python 中可写成 `Color = str`。校验规则定义在 [`synthesis/physics.py`](../../synthesis/physics.py)。

```python
from shapez2_tmam.synthesis.physics import Rules, Shape

Color = str


def shape_literal(code: str) -> Shape:
    return Rules().parse(code)


def is_order(item: Shape, dye: Color) -> bool:
    return item == shape_literal("Cu------") and dye == "r"


def material_order() -> bool:
    return is_order(shape_literal("Cu------"), "r")
```

循环用计数与回跳复用同一个循环体。固定元组在进入循环前取值，循环变量可赋值且不会改变迭代顺序。`max_block_visits` 按各基本块的访问预算求和，包含退出块，子调用的块访问单独计数。

编译器先用当前表达式和局部变量的已知区间检查加法与索引。需要进一步证明时，会沿基本块分析，把计数、赋值和分支约束带到下一轮。两条路径在同一步汇合时合并区间。输入和被调方法的整数返回值按完整的 32 位范围处理，直接整数比较可进一步缩小范围。每个方法最多分析 16,384 个块状态。范围越界或超出分析预算时，诊断指向需要证明的加法或索引。

只读表在定义时取值。长度为 `n` 的表允许 `-n` 到 `n - 1` 的索引，负索引按 Python 规则从末项向前数。动态查表将连续同值的索引合成一个区间，按区间数平分比较树，同一结果共用绑定块。下面的 `candidate_mask` 用比较限制来源槽位，再读取候选掩码。

```python
def candidate_mask(slot: int) -> int:
    masks = (0, 1, 3, 7)
    if 0 <= slot and slot < 4:
        return masks[slot]
    return 0
```

`advance_slots` 演示固定 20 槽的递增和回绕。它生成的中间表示含有运行时整数加法。导出时的运算支持见[原生蓝图编译器后端](../compiler_backend/README.md)。

```python
def advance_slots(advance: bool) -> int:
    slot = 0
    for _ in range(20):
        if advance:
            if slot < 19:
                slot = slot + 1
            else:
                slot = 0
    return slot
```
