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

## 生成顶针单列候选方法

```sh
python -m shapez2_tmam.circuits.compiler_frontend.pin_column_source --output pin_column.py
```

也可调用 `pin_column_source.generate_pin_column_source()` 取得源码文本。各入口接收 `(word: Shape, slot: int)`。`word` 是 `column_scan` 的五层材料字，由底到顶用 `Cu------`、`Ru------`、`Su------`、`Wu------` 分别表示空、普通材料、针、晶体。`slot` 沿用 `SOURCE_PATTERNS` 的 0～19 槽序。见[固定模式表](../../synthesis/pin_patterns.py)。

| 生成模式 | 入口 | 结果 |
|---|---|---|
| `materials`（默认） | `material_0` 到 `material_3` | 前态从底到顶四格，`0` 为空，`1` 为普通材料，`2` 为针，`3` 为晶体 |
| `masks` | `keep`、`crystals` | 两个四位掩码，最低位对应前态底层。`keep` 标记普通材料或针，`crystals` 标记全部晶体 |
| 两种模式 | `valid` | 该槽是否通过单列结构筛选 |

空余、越界或结构不合的槽使各整数方法返回 `-1`，`valid` 返回 `False`。槽位为 0 或材料为 0 都可能合法。普通材料和晶体的具体标签由调用方从原行读取。

把同一模式的字段一起传给 `compile_field_methods`，再做组合编译，可共享材料解析和候选判定。若总线要求无效槽发空信号，为各字段指定 `publish_when` 方法 `valid`。

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

## 顶针单列定址

在仓库根目录生成一份可供 Python 和编译器读取的源码。

```powershell
py -m shapez2_tmam.circuits.compiler_frontend.pin_column_source --mode materials --output pin_column.py
```

方法共用 `word: Shape` 和 `slot: int`。`word` 为 `column_scan` 的五层单列材料字，使用 q0 的 `Cu`、`Ru`、`Su`、`Wu` 分别标记空格、普通件、针和晶体。`slot` 使用 `SOURCE_PATTERNS` 桶内原序，从 0 到 19。

| 生成模式 | 可编译方法 | 含义 |
| --- | --- | --- |
| `materials` | `material_0` 至 `material_3` | 自底向上的四层材料，`0` 为空、`1` 为普通件、`2` 为针、`3` 为晶体。保留格的具体标签从目标原行读取。 |
| `masks` | `keep`、`crystals` | 保留格及晶体的四位掩码，最低位对应底层。`crystals` 包含目标材料字已确定的晶体格。 |

两种模式都生成 `valid`。无效槽的 `valid` 返回 `False`，该槽的所有整数输出返回 `-1`。有效候选可返回 `0`。用 `generate_pin_column_source(mode)` 可在内存生成同一份源码，再交给前端的单方法或批量入口。

### 分段导出顶针单列校验

分段版先解码目标的五格材料，按槽号取出保留格和晶体格模式，再用同一套检查恢复并校验候选。各槽复用这些模块。

```powershell
py -m shapez2_tmam.circuits.compiler_frontend.pin_column_stages --output pin_column_stages.py
```

用 `pin_column_stage_plan` 的频道表逐模块导出。将示例首频道换成现场连续空闲的 23 条频道的起点。每件蓝图导入时留出自己的平台位置。

```python
from pathlib import Path

from shapez2_tmam.circuits.compiler_backend.fields import export_fields
from shapez2_tmam.circuits.compiler_frontend import compile_field_methods
from shapez2_tmam.circuits.compiler_frontend.pin_column_stages import pin_column_stage_plan

source = Path("pin_column_stages.py")
for name, methods, inputs, outputs in pin_column_stage_plan(1701000):
    programs, _ = compile_field_methods(source, methods)
    export_fields(programs, Path("pin-column") / f"{name}.spz2bp",
                  input_channels=inputs, output_channels=outputs)
```

| 相对首频道 | 信号 |
| --- | --- |
| `+0`、`+1` | 五层材料字 `word`、槽号 `slot` |
| `+2` 至 `+17` | 模块间的五格材料、桶号、三份查表载荷、候选模式、两份落点检查结果与四格待发布材料 |
| `+18` | `valid` |
| `+19` 至 `+22` | 从底到顶的四格材料，沿用上表的 0～3 和 `-1` 编码 |

| 模块 | 门数 | 平台数 | 稳定输入后的保持期（信号刻） |
| --- | ---: | ---: | ---: |
| `read` | 75 | 1 | 960 |
| `bucket` | 74 | 2 | 1536 |
| `pack_0`、`pack_1`、`pack_2` | 56 / 96 / 2 | 1 / 2 / 1 | 1216 / 1856 / 448 |
| `pattern` | 88 | 2 | 1088 |
| `fit_low`、`fit_high` | 115 / 112 | 2 / 2 | 1728 / 1536 |
| `restore_lower`、`restore_upper` | 114 / 103 | 2 / 1 | 1600 / 1536 |
| `materials` | 88 | 2 | 1600 |

这套布局共 923 门、18 块平台、28,173 个建筑和 29 对模块内短距口。按接口表保持期及每次模块间无线传输另计 12 刻计算，同时更新 `word` 和 `slot` 后等 6960 信号刻。目标材料字和桶号已经稳定时，每次换槽等 6308 刻。期间保持整组输入，采样时同时读取有效位和四格材料。这是离线计算的保守等待值，游戏内联动尚待验收。

### 顺序搜索单列来源槽

用同一个单列校验器顺序查询槽 0～19。首个有效候选使推进器锁定当前槽，并随 `done=1` 发布 `valid=1` 和四格材料。全部失败时停在槽 20，`done=1`、`valid=0`，四格材料均为 `-1`。候选中的空格仍发整数 `0`。

```powershell
py -m shapez2_tmam.circuits.compiler_frontend.pin_column_cursor --column-base 1701000 --channel-base 1701023 --output pin-column/cursor.spz2bp
```

先按上一节导出并放置 11 个校验模块，再放置推进器。`--column-base` 须与 `pin_column_stage_plan` 的首频道一致。另为 `--channel-base` 起的 15 条连续频道留出空间。导出的同名 JSON 列出完整频道表。

| 信号 | 示例频道 | 用法 |
| --- | ---: | --- |
| `word` | 1701000 | 从启动到采样保持同一份五层材料字 |
| `enable` | 1701023 | 先置 `0` 至少 72 信号刻，再置 `1` 启动。中断或换目标时重复此操作 |
| `slot` | 1701001 | 推进器发出的查询槽和最终槽。采样时与 `done`、`valid` 一起读取 |
| `done`、`valid` | 1701024、1701025 | `done=1` 时读取 `valid` 和四格材料 |
| `material_0` 至 `material_3` | 1701026～1701029 | 自底向上的已发布材料 |

推进器占 6 块平台、8047 个建筑。它为每槽预留 6996 信号刻，其中包含整套校验的最长保持期和无线交接余量。在固定 12 刻无线传输的离线回放中，首槽完成用时 7044 刻，穷尽 20 槽用时 140196 刻，均从启动起算。接口表给出的整次搜索上界为 140712 刻。

#### 从指定槽继续枚举

用 `--start-slot-channel` 接入起始槽。枚举版占 7 块平台、9445 个建筑，为推进器保留 17 条连续频道，并为起始槽分配独占频道。

```powershell
py -m shapez2_tmam.circuits.compiler_frontend.pin_column_cursor --column-base 1701000 --channel-base 1701023 --start-slot-channel 1701040 --output pin-column/cursor.spz2bp
```

1. 保持目标材料字，置 `enable=0` 至少 72 信号刻。给 `start_slot` 发送整数 0～20，并在 `enable=1` 前保持该值至少 24 信号刻。两段等待可以重叠。
2. 等 `done=1` 后一起读 `slot`、`valid`、四格材料和 `next_slot`。`slot` 保持命中槽，`next_slot` 给出命中槽加一。两者保持到本轮复位。
3. 将读到的 `next_slot` 作为下次的 `start_slot`，重复复位和启动。若 `valid=0`，枚举已耗尽。命中槽 19 时 `next_slot=20`，从槽 20 启动会直接返回耗尽。

示例的 `start_slot` 为 1701040，`next_slot` 为 1701039。起始槽为空信号、越界或为其他类型时，按槽 20 处理。整数 `0` 可作起始槽，四格都为 `0` 的候选也可有效，按 `valid` 区分。

### 四列候选组合的推进接口

用 `compile_field_methods` 编译 `pin_column_combinations.py`。`next_column` 和 `next_start` 合编为一组，其余方法分别编译。组合控制重复调用一份单列枚举器，依次查询 q0 到 q3。每列保存命中槽 `slot`、续读槽 `next_slot` 和自底向上的四格材料。

| 方法 | 接线 |
| --- | --- |
| `select_word` | 按当前 `column` 选择送往单列枚举器的材料字。 |
| `retained_start` | 当前列耗尽时提供前一列保存的 `next_slot`。四列组合就绪时提供 q3 保存的 `next_slot`。 |
| `next_column`、`next_start` | 用同一份旧状态和当前事件计算下次调用的列号和起始槽。`restart` 接 `retained_start`。 |
| `update_value` | 对每列的每个字段各用一次。槽号字段的 `empty` 用 20，材料字段用 `-1`。 |

复位后以第 0 列、槽 0 开始。列号 0～3 表示要查询的列，4 表示四列结果就绪，`-1` 表示已穷尽。每次调用单列枚举器时沿用上一节的复位和起始槽稳定步骤。每轮新结果只提交一次 `result_ready`。同一次更新用旧状态计算新列、新起始槽和四列保存值，再统一写入。`result_valid` 取自单列枚举器的 `valid`。

当前列命中后，下一列从槽 0 起查。当前列耗尽后，回到前一列保存的 `next_slot`，由前一列的新命中重新开始后续列。收到 `column=4` 时读取四列保存值。读完发一次 `consume`，从 q3 的下一槽继续。q0 耗尽后保持 `column=-1`，复位开启下一轮。全空候选按 `result_valid` 决定是否保存。

#### 导出可暂停的四列循环

```powershell
py -m shapez2_tmam.circuits.compiler_frontend.pin_column_loop --column-base 1701800 --cursor-base 1701823 --channel-base 1701840 --output pin-column/loop.spz2bp
```

循环蓝图包含四列控制、结果保存和一份单列游标。按「分段导出顶针单列校验」一节导出 11 个校验模块，将 `pin_column_stage_plan` 的参数改为示例的 `1701800`。放置后按同名 JSON 连接槽号和材料结果。合装时为单列校验、游标和循环预留 `1701800`～`1701903`，这段频道与双半形验收蓝图错开。

| 信号 | 用法 |
| --- | --- |
| `q0` 至 `q3` | 四列五层材料字。启动前接入，整轮搜索和暂停期间保持。 |
| `enable` | 保持 `0` 至少 96 信号刻完成复位，再置 `1`。 |
| `ready` | `1` 表示四列槽号、续读槽和四格材料同时可读。 |
| `advance` | 保持 `0` 可暂停。一次继续先让当前候选在 `advance=0` 下就绪，再置 `1` 并保持到 `ready=0`，随后拉回 `0`。 |
| `exhausted` | `1` 表示全部候选组合已穷尽，复位后可搜索新目标。 |

示例占 31 块平台、38,777 个建筑。每列用一个控制频道选择写入、保持或清除，两块平台保存该列的六个字段。完整样件含 11 个原生单列校验模块，可按[四列顶针候选枚举样件](pin-column-sample.md)重导。
