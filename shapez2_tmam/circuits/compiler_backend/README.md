# 原生蓝图编译器后端

`compile_program(program, channel_base)` 接收共享 [`Program`](../compiler_contract.py)，返回原生岛蓝图数据和接口表。`export_program(program, channel_base, output)` 写出 `.spz2bp` 和同名 `.json`。公开频道按参数声明顺序连续分配，最后一个频道发布返回值。调用方独占这些频道，并按接口表的 `settling.hold_signal_ticks` 保持整组有效输入后采样。布尔值用原生整数 0 和 1，图形和颜色允许空信号。输入类型、局部变量赋值和循环上界服从共享格式的约定。

在仓库根目录可以单独导出手写的补料方法。`append_five` 的输入依次是初始下料和五份从低到高排列的上料。

```bash
python -m shapez2_tmam.circuits.compiler_backend append_five --channel-base 1700010 --output append_five.spz2bp
```

后端先合并到达同一无环块的路径，按访问上界展开循环，并将非递归调用就地编译。相同谓词共用门，能够由布尔真值等价关系合并的路径共用信号。布尔、比较和虚拟加工使用原生门。`add` 支持编译时常量，也能为分支产生的有限整数取值生成选择电路。后端最多枚举 256 组操作数，用分支条件排除不可达组合，并检查有符号 32 位结果。任意取值的运行时整数只支持与恒零相加。图形操作采用四象限五层规则。后端按固定顺序尝试摆放和走线。超过单平台容量或各布局均未找到布线时，编译会报告失败。

组合网表在一块 3×3 平台的三个建筑层上布置。导出前按实际建筑端口逐一核对来源。任一局部路径只经过一段连续导线网络，采样保持期按实际依赖深度保守计算，适用条件遵循[信号传播说明](../../docs/proofs/08-circuits.md#s08-34)。接口表列出公开频道、建筑层用量和全局收发器数量。

## 固定次数的时序复用

`timed.compile_fold(program, steps, channel_base)` 编译一个 `(累积值, 本轮输入) → 累积值` 方法。从 `initial` 开始依次折叠 `item0` 至 `item{steps-1}`，支持 1～8 轮。状态和单步计算各占一块平台，四条公开频道传递当前索引、当前累计值、下一索引和下一累计值。

```bash
python -m shapez2_tmam.circuits.compiler_backend append_five_timed --channel-base 1700020 --output append_five_timed.spz2bp
```

在 `run=0` 时给出整组 `initial` 和 `item` 并按接口表等待复位，再一次置 `run=1`。保持整组输入，达到采样时间且 `done=1` 后读取 `result`。空图形也是有效结果。

两块内部的门网均无环。记 `S(t)` 为状态模块发布的索引和累计值，`F` 为按索引运行一步的计算。复位时 `S(t)=(0, initial)`，一个往返后状态模块持续收到 `F(0, initial)`。启动后 `S(t)=F(S(t−24))`，第一轮在 `run` 抵达状态模块时已经可读。其余每轮相隔 24 tick，末轮索引和结果在后续往返中保持。运行前提见[固定频道边](../../docs/proofs/08-circuits.md#s08-05)。

采样时间包含启动和结果的各一次 12 tick 频道传播、后续各轮的 24 tick 往返及余量。生产编译核对常量、端口和收发频道。游戏内导入和时序观察单独验收。

### 同步更新多个状态字段

`timed.compile_state_fold(programs, steps, channel_base)` 按 `programs` 的映射顺序定义状态字段。映射的每个值是一个 `Program`，其入口按该顺序接收所有旧字段，并以本轮 `item` 为最后一个参数。它返回映射键所指字段的下一值。各入口的参数类型须一致，每个字段的初值、旧值、下一值和结果使用同一类型。

同一轮的各个入口共用同一份旧状态和当前 `item`。所有下一值都有相同的 12 tick 回程延迟，由状态平台同时发布到下一轮。复位、每轮 24 tick 的往返和 `done` 采样协议与单字段一致。向 `initial_<字段>` 提供初值，完成后从 `result_<字段>` 读取结果。频道表的 `module_links` 按两个方向列出索引以及各字段的类型和频道。

状态平台每侧占用 `2N+2` 个无线口，计算平台占用 `N+1+steps` 个接收口，其中 `N` 是字段数。每个平台每侧可放 10 个无线口，因此最多支持四个字段，四字段最多折叠五轮。每个模块的门网还须能在对应平台上完成布线。

```bash
python -m shapez2_tmam.circuits.compiler_backend scalar_ring_timed --channel-base 1700060 --output scalar_ring_timed.spz2bp
```

这个例子有两个整数状态 `a`、`b` 和三个布尔 `item`。每轮输入为 1 时，两字段各取对方的旧值。给定初值 `a=3`、`b=7`，依次输入 `1, 0, 0`，预期结果是 `a=7`、`b=3`。
