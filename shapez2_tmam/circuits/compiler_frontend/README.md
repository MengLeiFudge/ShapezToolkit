# Python 方法编译前端

用 `compile_method(source, entry, filename=...)` 把指定的 Python 方法编译为 [`Program`](../compiler_contract.py)。`source` 是源码文本，`entry` 是入口文件中的顶层方法名，`filename` 用于定位诊断和相对导入。编译器用语法树解析涉及的源码。`FrontendError` 提供 `SyntaxError` 的文件、行号和列号字段。

```python
from pathlib import Path

from shapez2_tmam.circuits.compiler_frontend import compile_method

path = Path("shapez2_tmam/synthesis/layer_methods.py")
program = compile_method(path.read_text(encoding="utf-8"), "append_five", filename=str(path))
```

## 编译共享输入的多个字段

`compile_field_methods(path, methods, publish_when=...)` 从一个文件读取多个顶层方法。`methods` 将字段名映射到值方法名。可选的 `publish_when` 为字段指定返回 `bool` 的发布方法。所有方法的参数顺序、名称和类型须一致。

```python
from pathlib import Path

from shapez2_tmam.circuits.compiler_frontend import compile_field_methods

path = Path("shapez2_tmam/synthesis/direct_recipe.py")
programs, conditions = compile_field_methods(path, {
    "opcode": "direct_recipe_opcode",
    "a": "direct_recipe_lower",
    "b": "direct_recipe_upper",
    "destination": "direct_recipe_destination",
})
```

将两张映射分别传给后端 `fields.compile_fields` 的 `programs` 和 `publish_when`。上例的 `conditions` 为空。若要单独控制下料槽的发布，可在同一文件定义下面的方法，再传入 `publish_when={"a": "publish_lower"}`。

```python
def publish_lower(address: int, length: int) -> bool:
    return 0 <= direct_recipe_lower(address, length)
```

## 支持的 Python 语法

| 用途 | 源码写法 |
|---|---|
| 类型 | 参数和返回值标注 `bool`、`int`、`Shape` 或 `Color`。图形与颜色可写 `\| None`，空值从赋值、返回、参数或比较的类型推断 |
| 局部状态 | 单变量赋值和带类型的局部变量。读取前必须在所有到达路径上赋值，一个变量始终保持相同类型 |
| 控制流 | `if`、`elif`、`else`，提前 `return`，短路 `and`、`or`，定长 `for` 和定步长 `while`。循环体可用 `break`、`continue` |
| 只读表 | 可用整数索引读取非空的同类型固定元组。给元组命名时，可在方法内定义一次，或直接在同文件顶层用一个赋值定义字面量元组。所有到达读取位置的路径都必须保证索引合法 |
| 字面量 | `True`、`False`，有符号 32 位整数，颜色单字符如 `"r"`，以及图形短代码如 `shape_literal("Cu------")` |
| 标量操作 | `not`，布尔 `&`、`\|`，同类型 `==`、`!=`，对 `None` 的 `is`、`is not`，整数单次比较及可证明不溢出的加法与减字面量 |
| 调用 | 以固定位置参数调用同文件顶层方法，或用 `from .模块 import 方法` 导入调用，支持 `as` 别名。调用图必须无环。图形操作使用共享合同中 `BUILTINS` 的保留名称 |

布尔 `&` 和 `|` 会求值两侧，再生成对应的逻辑门。用比较结果作操作数时加括号，例如 `(z0 == 0) & (z1 == 2)`。`and` 和 `or` 按 Python 规则短路。

例如相邻的 `assembly.py` 可以用 `from .layer_methods import append_layer as append` 再调用 `append(lower, upper)`。编译时将 `assembly.py` 的实际路径传给 `filename`。按入口可达的调用查找同包源码，跨文件方法以模块路径区分。同名顶层绑定和调用环会定位到冲突定义和触发调用的位置。

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

循环用计数与回跳复用同一个循环体。`for` 可遍历同类型固定元组或字面量边界的 `range(stop)`、`range(start, stop)`。固定元组在进入循环前取值。`break` 退出最内层循环，`continue` 进入最内层循环的下一轮检查。循环后读取的局部变量须在自然结束和所有 `break` 路径上已经赋值。`max_block_visits` 按各基本块的访问预算求和，包含退出块，子调用的块访问单独计数。

`while` 将编译期已知的整数游标与字面量用 `<`、`<=`、`>` 或 `>=` 比较。循环体顶层有一个固定步长更新，可用 `slot += 1`、`slot -= 1` 或 `slot = slot + 1`。步长须朝着结束边界推进，包含最后一次更新在内的游标值都须在有符号 32 位范围内。`continue` 须在游标更新之后执行。

```python
def first_slot(wanted: int) -> int:
    masks = (1, 4, 2, 8)
    slot = 0
    while slot < 4:
        if masks[slot] == wanted:
            break
        slot += 1
    return slot
```

编译器先用当前表达式和局部变量的已知区间检查整数运算与索引。整数减字面量（如 `cells[r - 1]`）沿用加法的有符号 32 位范围检查。需要进一步证明时，会沿基本块分析，把计数、赋值和分支约束带到下一轮。同一步汇合的路径合并区间。整数输入按完整的 32 位范围处理，直接比较可进一步缩小范围。

编译器合并各条可达返回路径上的整数区间，并把结果传到同文件和相对导入的调用处。例如，`target_height(target)` 的返回范围为 0～5，加 1 后为 1～6。每个方法最多分析 16,384 个块状态。无法在预算内推导的返回值按完整的 32 位区间处理。无法证明整数运算或索引安全时，诊断指向该表达式。

只读表在定义时取值。同文件的方法可以共用顶层表，表元素须直接写成字面量。长度为 `n` 的表允许 `-n` 到 `n - 1` 的索引，负索引按 Python 规则从末项向前数。动态查表将连续同值的索引合成一个区间，按区间数平分比较树，同一结果共用绑定块。

下面的 `candidate_mask` 用比较限制来源槽位，再读取共享的候选掩码。

```python
MASKS = (0, 1, 3, 7)


def candidate_mask(slot: int) -> int:
    if 0 <= slot and slot < 4:
        return MASKS[slot]
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
