# 原生蓝图编译器后端

`compile_program(program, channel_base)` 接收共享 [`Program`](../compiler_contract.py)，返回原生岛蓝图数据和接口表。`export_program(program, channel_base, output)` 写出 `.spz2bp` 和同名 `.json`。公开频道按参数声明顺序连续分配，最后一个频道发布返回值。调用方独占这些频道，并按接口表的 `settling.hold_signal_ticks` 保持整组有效输入后采样。布尔值用原生整数 0 和 1，图形和颜色允许空信号。输入类型、局部变量赋值和循环上界服从共享格式的约定。

在仓库根目录可以单独导出手写的补料方法。`append_five` 的输入依次是初始下料和五份从低到高排列的上料。

```bash
python -m shapez2_tmam.circuits.compiler_backend append_five --channel-base 1700010 --output append_five.spz2bp
```

后端先合并到达同一无环块的路径，按访问上界展开循环，并将非递归调用就地编译。相同谓词共用门，能够由布尔真值等价关系合并的路径共用信号。布尔、比较和虚拟加工使用原生门。`add` 支持编译时常量，也能为分支产生的有限整数取值生成选择电路。后端最多枚举 256 组操作数，用分支条件排除不可达组合，并检查有符号 32 位结果。任意取值的运行时整数只支持与恒零相加。图形操作采用四象限五层规则。后端按固定顺序尝试摆放和走线。超过单平台容量或各布局均未找到布线时，编译会报告失败。

组合网表在一块 3×3 平台的三个建筑层上布置。布线前合并等价门和整组等价的选择总线。连续四次同向四分之一圈旋转等于原输入，同一输入转到同一方向也只生成一条路径。接口表的 `logic_gates_before_reuse` 是合并前的门数，`logic_gates` 是实际布置的门数。若合并后布线失败，后端尝试原门网。

单整数输入、整数返回的方法在常规布线失败时可尝试区间译码。后端只重建由输入与整数字面量比较、布尔组合和互斥常量选择构成的门网。比较端点将有符号 32 位输入划分为最多 128 个区间。相邻区间返回相同值时合并，较大的选择表分组接入索引和结果线，减小单根线的扇出和合流。越界路径沿用原方法的返回值。

导出前按实际建筑端口逐一核对来源。任一局部路径只经过一段连续导线网络，采样保持期按实际依赖深度保守计算，适用条件遵循[信号传播说明](../../docs/proofs/08-circuits.md#s08-34)。接口表也列出公开频道、建筑层用量和全局收发器数量。

## 共享输入的多字段组合导出

`fields.compile_fields(programs, input_channels=..., output_channels=...)` 把多个字段编译到同一块平台。`programs` 的键是输出字段，值是返回该字段的 `Program`。各方法的输入顺序、名称和类型须一致，生成的电路共用这些接收器。两张频道表须覆盖全部输入和输出，频道由调用方独占且互不重复。`fields.export_fields` 可写出原生 `.spz2bp` 和同名接口表。

例如，`synthesis/direct_recipe.py` 中的工序、下料槽、上料槽和目标槽方法都接收 `address`、`length`，可按 `opcode`、`a`、`b`、`destination` 组合导出。`address` 和四个输出用 `stage_memory.WRITE_BUS` 的频道，`length` 用 `stream_controller.PROGRAM_LENGTH`。接口表的 `reserved_channels` 列出实际占用的每个频道，按 `settling.hold_signal_ticks` 保持整组输入后采样。

## 固定次数的时序复用

`timed.compile_fold(program, steps, channel_base)` 编译一个 `(累积值, 本轮输入) → 累积值` 方法。从 `initial` 开始依次折叠 `item0` 至 `item{steps-1}`，支持 1～8 轮。状态和单步计算各占一块平台，四条公开频道传递当前索引、当前累计值、下一索引和下一累计值。

```bash
python -m shapez2_tmam.circuits.compiler_backend append_five_timed --channel-base 1700020 --output append_five_timed.spz2bp
```

在 `run=0` 时给出整组 `initial` 和 `item` 并按接口表等待复位，再一次置 `run=1`。保持整组输入，达到采样时间且 `done=1` 后读取 `result`。空图形也是有效结果。

两块内部的门网均无环。记 `S(t)` 为状态模块发布的索引和累计值，`F` 为按索引运行一步的计算。复位时 `S(t)=(0, initial)`，一个往返后状态模块持续收到 `F(0, initial)`。启动后 `S(t)=F(S(t−24))`，第一轮在 `run` 抵达状态模块时已经可读。其余每轮相隔 24 tick，末轮索引和结果在后续往返中保持。运行前提见[固定频道边](../../docs/proofs/08-circuits.md#s08-05)。

采样时间包含启动和结果的各一次 12 tick 频道传播、后续各轮的 24 tick 往返及余量。生产编译核对常量、端口和收发频道。游戏内导入和时序观察单独验收。

### 同步更新多个状态字段

`timed.compile_state_fold(programs, steps, channel_base)` 按 `programs` 的映射顺序定义状态字段。映射的每个值是一个 `Program`，其入口按该顺序接收所有旧字段，再接收本轮 `item`。传入 `round_values` 时，各入口多接一个 `int` 参数，时序电路把相应轮的值传给它。它返回映射键所指字段的下一值。各入口的参数类型须一致，每个字段的初值、旧值、下一值和结果使用同一类型。

同一轮的各个入口共用同一份旧状态和当前 `item`。所有下一值都有相同的 12 tick 回程延迟，由状态平台同时发布到下一轮。复位、每轮 24 tick 的往返和 `done` 采样协议与单字段一致。向 `initial_<字段>` 提供初值，完成后从 `result_<字段>` 读取结果。频道表的 `module_links` 按两个方向列出索引以及各字段的类型和频道。

状态平台每侧占用 `2N+2` 个无线口，计算平台占用 `N+1+steps` 个接收口，其中 `N` 是字段数。每个平台每侧可放 10 个无线口，因此最多支持四个字段，四字段最多折叠五轮。后端在计算平台内共用行解码、旋转及等价谓词，再尝试布线。计算门网超出单板容量或走线失败时，后端按下一状态输出分到并行计算平台。每个平台从相同频道接收旧状态和各轮 `item`，对自己的输出就地计算。每个下一状态频道由一个平台发布，往返仍为 24 tick。

`worker_logic_gates_before_reuse` 和 `worker_logic_gates_after_reuse` 统计拆板前的计算门网。`worker_logic_gates` 是各计算平台实际布置的门数总和，各板重复计算也计入。`worker_partitions` 列出各计算平台的输出频道，`worker_layout_failures` 记录导致拆板或退回原门网的走线问题。

```bash
python -m shapez2_tmam.circuits.compiler_backend scalar_ring_timed --channel-base 1700060 --output scalar_ring_timed.spz2bp
```

这个例子有两个整数状态 `a`、`b` 和三个布尔 `item`。每轮输入为 1 时，两字段各取对方的旧值。给定初值 `a=3`、`b=7`，依次输入 `1, 0, 0`，预期结果是 `a=7`、`b=3`。

堆叠前缀用 `synthesis/row_support.py` 的 `stack_scan_q0` 至 `stack_scan_q3` 作为四个更新入口，并传入 `round_values=(5, 4, 3, 2, 1)`。`initial_q0` 至 `initial_q3` 接四列初值，`item0` 至 `item4` 接从顶到底排列的单层支撑代码，`synthesis/prefix_closure.py` 的 `stack_scan_rows` 可生成这五份输入。若更新入口需要零起算的轮序号，传入 `round_values=tuple(range(steps))`。轮值列表必须与轮数相等。

### 只更新旧状态

`timed.compile_state_steps(programs, steps, channel_base)` 用于每轮只读取旧状态的更新方法。各入口按映射顺序接收全部旧字段，下一轮同时使用各入口的返回值。支持 1～4 个字段，轮数可设为 1～32，庞大的计算仍受平台布线容量限制。对于 `N` 个字段，计算平台接收索引和 `N` 个旧字段，公开频道只有 `run`、各字段的初值、`done` 和各字段的结果。

把 `synthesis/direct_stack.py` 的 `direct_scan_remaining`、`direct_scan_upper`、`direct_scan_valid` 分别编译为 `remaining`、`upper`、`valid`，按这个顺序传入并设 `steps=5`。`initial_remaining` 接待拆层的图形，`initial_upper` 接空图形，`initial_valid` 接上游的有效性标志。复位时保持三个初值，按接口表启动并在 `done=1` 后读取三个结果。
