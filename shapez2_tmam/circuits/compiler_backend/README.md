# 原生蓝图编译器后端

`compile_program(program, channel_base)` 接收共享 [`Program`](../compiler_contract.py)，返回原生岛蓝图数据和接口表。`export_program(program, channel_base, output)` 写出 `.spz2bp` 和同名 `.json`。公开频道按参数声明顺序连续分配，最后一个频道发布返回值。调用方独占这些频道，并按接口表的 `settling.hold_signal_ticks` 保持整组有效输入后采样。布尔值用原生整数 0 和 1，图形和颜色允许空信号。输入类型、局部变量赋值和循环上界服从共享格式的约定。

在仓库根目录可以单独导出手写的补料方法。`append_five` 的输入依次是初始下料和五份从低到高排列的上料。

```bash
python -m shapez2_tmam.circuits.compiler_backend append_five --channel-base 1700010 --output append_five.spz2bp
```

后端先合并到达同一无环块的路径，按访问上界展开循环，并将非递归调用就地编译。相同谓词共用门，能够由布尔真值等价关系合并的路径共用信号。布尔、比较和虚拟加工使用原生门。`add` 支持编译时常量，也能为分支产生的有限整数取值生成选择电路。后端最多枚举 256 组操作数，用分支条件排除不可达组合，并检查有符号 32 位结果。任意取值的运行时整数只支持与恒零相加。图形操作采用四象限五层规则。

组合网表优先在一块 3×3 平台的三个建筑层上布置。布线前合并等价门和整组等价的选择总线。连续四次同向四分之一圈旋转等于原输入，同一输入转到同一方向也只生成一条路径。接口表的 `logic_gates_before_reuse` 是合并前的门数，`logic_gates` 是实际布置的门数。若合并后布线失败，后端尝试原门网。

单整数输入、整数返回的方法在常规布线失败时可尝试区间译码。后端只重建由输入与整数字面量比较、布尔组合和互斥常量选择构成的门网。比较端点将有符号 32 位输入划分为最多 128 个区间。相邻区间返回相同值时合并，较大的选择表分组接入索引和结果线，减小单根线的扇出和合流。越界路径沿用原方法的返回值。

导出前按实际建筑端口逐一核对来源。采样保持期按最终接线的依赖深度保守计算，适用条件遵循[信号传播说明](../../docs/proofs/08-circuits.md#s08-34)。接口表也列出公开频道、建筑层用量和全局收发器数量。

## 相邻平台的原生飞线

单方法和多字段组合编译在单板摆放失败时会尝试两个横向相邻的 3×3 平台。切分时同一选择总线的全部驱动留在同一块板上，每张跨板信号网只占一对短距口。布局器逐一核对飞线配对和实际输入来源，并将飞线计入最长依赖路径。调用方按接口表的 `settling.hold_signal_ticks` 等待再采样。双板接口表的 `short_range_links` 记载短距口对数，`island_footprint_chunks` 为 `[6, 3]`。找不到可走线的切口时，编译会报告失败。

同一模块拆到多个平台时，可把有数据依赖的 3×3 平台放在同一岛层，让相对的缺口对齐，再用 `WireTransmitterSenderInternalVariant` 和 `WireTransmitterReceiverInternalVariant` 跨缝。端口各占一格，发送器从背面接线，接收器从正面出线。以朝东、相距三个区块的两个未旋转平台为例，发送器放在岛内 `(37, -10, L)`，接收器放在 `(-18, -10, L)`，两者 `R=0` 且使用同一个建筑层 `L`。全局间距是 `60 - 18 - 37 = 5` 格，达到游戏 `PortSystem` 允许的上限。普通边缘的可建格间距为 7 格，连续导线无法跨缝。Mari 的 `TMAM Brain Exo` 原生蓝图中有 128 对跨 3×3 平台的同层短距口，覆盖建筑层 0、1、2。

短距口沿水平方向查找同高、同朝向的另一端，允许间距为 2～5 格。岛层相差一层时，全局高度相差 `20 + L₂ - L₁`，最小为 18 格。跨岛层的计算需要改为同岛层摆放，或经过有公开参数与返回值的模块接口。导出时应以最终平台坐标检查缺口占地、验证发送器与接收器唯一配对，并逐输入核对穿过飞线后的实际驱动来源。[短距端口配对](../../mari/blueprint.py)

飞线把两端纳入本地信号图。用飞线替换前馈中转时须按最终接线重算保持期。固定折叠的状态和计算模块依赖各方向 12 个信号刻的无线延迟，替换它们的往返链路需要重新设计状态推进与采样时序。[本地更新顺序与无线延迟](../../docs/proofs/08-circuits.md#s08-05)

## 共享输入的多字段组合导出

`fields.compile_fields(programs, input_channels=..., output_channels=...)` 将多个方法布置到共用输入的组合电路。`programs` 的键是输出字段，值是返回该字段的 `Program`。各方法的输入顺序、名称和类型须一致，生成的电路共用这些接收器。两张频道表须覆盖全部输入和输出，频道由调用方独占且互不重复。`fields.export_fields` 可写出原生 `.spz2bp` 和同名接口表。

`compile_fields` 和 `export_fields` 都接受可选的 `publish_when`。它的键是需要控制发布的输出字段，值是接收同一组参数且返回 `BOOL` 的 `Program`。条件为假时，字段发空信号。条件为真时，字段发方法返回的原值，包括整数槽号 `0`。接口表的 `publish_when` 列出配置的条件方法。读端按 `settling.hold_signal_ticks` 等待输入和条件稳定后采样。

例如，`synthesis/direct_recipe.py` 中的工序、下料槽、上料槽和目标槽方法都接收 `address`、`length`，可按 `opcode`、`a`、`b`、`destination` 组合导出。`address` 和四个输出用 `stage_memory.WRITE_BUS` 的频道，`length` 用 `stream_controller.PROGRAM_LENGTH`。接口表的 `reserved_channels` 列出实际占用的每个频道，按 `settling.hold_signal_ticks` 保持整组输入后采样。

## 固定次数的时序复用

`timed.compile_fold(program, steps, channel_base)` 编译一个 `(累积值, 本轮输入) → 累积值` 方法。从 `initial` 开始依次折叠 `item0` 至 `item{steps-1}`，支持 1～8 轮。状态模块占一块平台，四条频道在状态与计算模块之间传递当前索引、当前累计值、下一索引和下一累计值。

```bash
python -m shapez2_tmam.circuits.compiler_backend append_five_timed --channel-base 1700020 --output append_five_timed.spz2bp
```

在 `run=0` 时给出整组 `initial` 和 `item` 并按接口表等待复位，再一次置 `run=1`。保持整组输入，达到采样时间且 `done=1` 后读取 `result`。空图形也是有效结果。

状态和计算模块的本地门网均无环。记 `S(t)` 为状态模块发布的索引和累计值，`F` 为按索引运行一步的计算。复位时 `S(t)=(0, initial)`，一个往返后状态模块持续收到 `F(0, initial)`。启动后 `S(t)=F(S(t−24))`，第一轮在 `run` 抵达状态模块时已经可读。其余每轮相隔 24 tick，末轮索引和结果在后续往返中保持。运行前提见[固定频道边](../../docs/proofs/08-circuits.md#s08-05)。

采样时间包含启动和结果的各一次 12 tick 频道传播、后续各轮的 24 tick 往返及余量。生产编译核对常量、端口和收发频道。游戏内导入和时序观察单独验收。

### 同步更新多个状态字段

`timed.compile_state_fold(programs, steps, channel_base)` 按 `programs` 的映射顺序定义状态字段。映射的每个值是一个 `Program`，其入口按该顺序接收所有旧字段，再接收本轮 `item`。传入 `round_values` 时，各入口多接一个 `int` 参数，时序电路把相应轮的值传给它。它返回映射键所指字段的下一值。各入口的参数类型须一致，每个字段的初值、旧值、下一值和结果使用同一类型。

同一轮的各个入口共用同一份旧状态和当前 `item`。所有下一值都有相同的 12 tick 回程延迟，由状态平台同时发布到下一轮。复位、每轮 24 tick 的往返和 `done` 采样协议与单字段一致。向 `initial_<字段>` 提供初值，完成后从 `result_<字段>` 读取结果。频道表的 `module_links` 按两个方向列出索引以及各字段的类型和频道。

状态平台每侧占用 `2N+2` 个无线口，`N` 为字段数。计算平台最多接收 `N+1+steps` 个频道。逐轮输入模式按每侧最多 10 个无线口分配频道，最多支持四个字段，四字段最多折叠五轮。单板容量或走线不足时，后端按输出依赖分组，优先把共享计算较多的输出留在同一计算模块。每个模块只接收其输出依赖的输入。

每组最多三个输出可共用一对同岛层的相邻板。多输出分板优先均衡门数，布线失败时再拆小组。飞线端口共享一个 `SignalPortTransferSimulation`，按同一信号 tick 读取并写出。整件批量导入或完整重载后，这段前馈路径与两侧的本地导线属于同一无环更新图。状态与计算之间仍按每向 12 tick 传输，往返为 24 tick。

`worker_logic_gates_before_reuse` 和 `worker_logic_gates_after_reuse` 统计拆板前的计算门网。`worker_logic_gates` 是实际布置的计算门数总和。`worker_partitions` 和 `worker_ports` 分别列出各计算模块的输出分组及实际收发频道，`worker_layout_failures` 记录导致拆板或退回原门网的走线问题。使用飞线时，`worker_platforms` 给出每个计算模块的平台数，`short_range_links` 给出飞线端口对数。

```bash
python -m shapez2_tmam.circuits.compiler_backend scalar_ring_timed --channel-base 1700060 --output scalar_ring_timed.spz2bp
```

这个例子有两个整数状态 `a`、`b` 和三个布尔 `item`。每轮输入为 1 时，两字段各取对方的旧值。给定初值 `a=3`、`b=7`，依次输入 `1, 0, 0`，预期结果是 `a=7`、`b=3`。

堆叠前缀用 `synthesis/row_support.py` 的 `stack_scan_q0` 至 `stack_scan_q3` 作为四个更新入口，并传入 `round_values=(5, 4, 3, 2, 1)`。`initial_q0` 至 `initial_q3` 接四列初值，`item0` 至 `item4` 接从顶到底排列的单层支撑代码，`synthesis/prefix_closure.py` 的 `stack_scan_rows` 可生成这五份输入。若更新入口需要零起算的轮序号，传入 `round_values=tuple(range(steps))`。轮值列表必须与轮数相等。

### 固定轮数、常驻输入与轮值

`timed.compile_state_steps(programs, steps, channel_base)` 执行 1～32 轮，支持 1～4 个状态字段。各入口按映射顺序接收全部旧字段，下一轮同时使用各入口的返回值。公开频道为 `run`、各字段的初值、`done` 和各字段的结果。

用 `held_inputs=("material", "direction")` 增加具名公开输入。各入口在旧字段后按该顺序声明同名、同类型的参数。常驻输入频道排在原有保留范围之后，由需要它们的计算板直接接收。调用方从复位开始保持同一组常驻输入，直到采样结束。

用 `round_values=(5, 4, 3, 2, 1)` 为五轮提供整数轮值。各入口追加一个 `int` 参数，当前轮值由计算板从内部索引生成。

四状态的状态板每侧用满 10 个无线口。当一块计算板需要四个旧值和索引时，可再接 5 个常驻输入。输出拆到多块计算板时，每块只接所需的输入，容量按每块实际接收端口计算。

把 `synthesis/direct_stack.py` 的 `direct_scan_remaining`、`direct_scan_valid`、`direct_scan_replay` 按 `remaining`、`valid`、`replay` 的顺序编译并传入，设置 `steps=5`。`initial_remaining` 接原图，`initial_valid` 接稳定性判定，`initial_replay` 留空。按接口表复位和启动，待 `done=1` 后读取材料检查和回放。

## 连续调用定步模块

`module_caller` 从定步模块的 JSON 接口表读取参数和结果频道、复位等待和采样等待。每次调用在复位阶段先发布全部参数，再等被调用板的 `done` 清零和复位时间到期后启动。达到采样时间并读到新的 `done=1` 时，调用器锁存本次结果，再推进到下一次调用。批次 `done=1` 时，各次结果可从各自的频道读取，包括空图形和整数 `0`。

调用清单包含 1～4 组参数。每组按接口表给全除 `run` 之外的输入，每个参数使用 `{"literal": 值}` 或 `{"channel": 频道}`。频道参数须从复位前保持到批次完成。按生成接口表把 `enable` 保持为 `0` 到复位时间，再置为 `1`。需要重跑时先完整复位。

超过三次无线传递的等待用一套计数器。切换阶段时重新计数，复位和采样达到各自等待时间后发布对应阶段号，调用器仍检查阶段号和被调用板的 `done`。结果频道沿用原等待链的分配。

四列样件的复位和采样分别等 264、168 信号 tick，等待硬件从 22 块减到 2 块，合装后共 16 块平台、13,882 个建筑。

前缀列读取样件使用同一个定步模块，先读第一列全高，再读第二列的两层前缀。下面的命令在仓库根目录执行，`--callee` 将被调用的原生蓝图一起布置。

```bash
python -m shapez2_tmam.circuits.compiler_backend.module_caller \
  shapez2_tmam/blueprints/验收/电路/双半形/read-prefix-column.json \
  shapez2_tmam/circuits/compiler_backend/column-caller-calls.json \
  --channel-base 1700900 \
  --callee shapez2_tmam/blueprints/验收/电路/双半形/read-prefix-column.spz2bp \
  --output column-caller.spz2bp
```

用 `--result 字段名` 只锁存指定的结果，可重复添加该选项。省略该选项时锁存全部结果。四列调用从 `1700898`～`1700901` 分别读取四份已转到 q0 的图形，只锁存四份 `result_word`。

```bash
python -m shapez2_tmam.circuits.compiler_backend.module_caller \
  shapez2_tmam/blueprints/验收/电路/双半形/read-prefix-column.json \
  shapez2_tmam/blueprints/验收/电路/双半形/read-four-columns-calls.json \
  --channel-base 1700930 --result result_word \
  --callee shapez2_tmam/blueprints/验收/电路/双半形/read-prefix-column.spz2bp \
  --output read-four-columns.spz2bp
```

### 接续上一级调用

用 `--enable-channel` 接上一级的 `done`。上一级保持 `done=1` 时，下一级继续调用并保留各次结果。换单时，按下一级接口表将 `enable` 保持为 `0` 至少一整个复位期。

用 `--parameter-hold-signal-ticks` 为首轮增加参数稳定时间。调用器从首轮复位阶段起等满稳定时间与定步板复位时间之和，并等定步板的 `done=0` 才启动。后续各轮只等定步板复位时间及 `done=0`。两个等待值分别向上取整到 12 信号 tick。

含晶双半形样件与 `read-four-columns.spz2bp`、`seed-pair-0.spz2bp`、`seed-pair-1.spz2bp` 合用。四列的 `done` 频道为 `1700932`，两块参数板提供 `1701040`～`1701049` 的输入组。下一级首轮等待 `1920 + 264 = 2184` tick，第二轮等待 264 tick。下一级的 `done` 为 `1701062`，两个 `result_required` 分别为 `1701089` 和 `1701090`。

```bash
python -m shapez2_tmam.circuits.compiler_backend.module_caller \
  shapez2_tmam/blueprints/验收/电路/双半形/seed-crystal-half.json \
  shapez2_tmam/circuits/compiler_backend/seed-half-calls.json \
  --channel-base 1701060 --enable-channel 1700932 \
  --parameter-hold-signal-ticks 1920 --result result_required \
  --callee shapez2_tmam/blueprints/验收/电路/双半形/seed-crystal-half.spz2bp \
  --output seed-half-caller.spz2bp
```

### 连续调用组合模块

组合接口支持 1～5 组调用。每组按接口表提供全部输入，参数可来自字面量或频道。调用器从 `settling.hold_signal_ticks` 读取稳定时间，再为参数选通预留一次无线传递。组合模块本身没有 `run` 或 `done`，调用器等每组参数满时后锁存结果。批次 `done=1` 时读取各次结果。

`pack-prefix-row` 的稳定时间是 1984 信号 tick，每组从选通阶段起等待 2004 tick。五组样件共用同一对计算平台，计算平台之间沿用原生短距接线。按从高到低的顺序，结果在 `1701133`～`1701137`，批次 `done` 在 `1701122`。

```bash
python -m shapez2_tmam.circuits.compiler_backend.module_caller \
  shapez2_tmam/blueprints/验收/电路/双半形/pack-prefix-row.json \
  shapez2_tmam/circuits/compiler_backend/pack-prefix-row-calls.json \
  --channel-base 1701120 \
  --callee shapez2_tmam/blueprints/验收/电路/双半形/pack-prefix-row.spz2bp \
  --output pack-prefix-row-caller.spz2bp
```

### 五层行编码接入双半形闭包

`prefix_scan_wiring` 与验收册的切向转换、四列读取、两块 `seed-pair`、`seed-two-halves`、两块 `restore-seed` 和 `paired-prefix-scan` 合用。导入件已经包含原层读取和行编码。批次开关沿用四列的 `1700930`。从该开关复位开始保持目标与切向不变，直到闭包结果读完。

并行读取板从底到顶将原色单层发布到 `1701200`～`1701204`。行编码使用本层与紧邻下层，只有第 1 层的 `ground=1`，其下层为空。空顶层保留为空信号，第 5 至第 1 层依次进入 `1700770`～`1700774`。

批次开关拉高后，首组相位等待 4380 信号 tick，包含切向转换的 448 tick、原层读取的 1920 tick、行编码和参数选通时间。其余四组各等 2004 tick。原层读取持续发布，换单复位清空已锁存的行编码和闭包启动信号。

行编码 `1701252` 和两半预处理 `1701072` 均为 `1` 后，启动电路再等待 708 信号 tick，覆盖恢复列序和闭包复位，然后置 `1700760=1`。保持开关为 `1`，按闭包接口表等满采样时间并读到 `1700765=1` 后取四列高度。换单时将批次开关置 `0` 至少 384 tick，下一轮重读五层。

```bash
python -m shapez2_tmam.circuits.compiler_backend.prefix_scan_wiring \
  --circuits shapez2_tmam/blueprints/验收/电路 \
  --rows shapez2_tmam/blueprints/验收/电路/原层读取/read-five-rows.spz2bp \
  --output prefix-scan-wiring.spz2bp
```

### 稳定后按地址确认并提交状态

`confirmed_call.build` 复用组合状态板。每轮先保持旧状态和输入。`opcode` 为空则直接进入下一状态计算，非空则锁存待写地址。旧同址确认撤去后，控制器发布 `request_address`。发布期间保持该地址的六字段，写入端回报对应整数地址并保持到请求撤去。整数地址 `0` 可用。

控制器收到匹配确认后撤去请求，保持旧状态直到下一状态稳定，然后同拍提交所有字段。紧柱样件的输入等待为 3360 信号 tick，下一状态等待为 1488 tick。`enable=0` 保持至少 48 tick 以清空请求并恢复两项初值。

紧柱样件配合 `dense-column-input`、`dense-column-packet`、`dense-column-advance-phase` 和 `dense-column-advance-level` 使用。主控在 `1701480` 提供待写地址，在 `1701481` 回报写入的整数地址，请求地址在 `1701482`。实体写入器的布尔 ACK 需由主控与本笔请求地址配对。

```bash
python -m shapez2_tmam.circuits.compiler_backend.confirmed_call \
  --circuits shapez2_tmam/blueprints/验收/电路/双半形 \
  --address-channel 1701480 --ack-channel 1701481 --request-channel 1701482 \
  --channel-base 1701490 --output dense-confirmed-call.spz2bp
```

### 紧柱接入六字段实体工道

`dense_write_bridge` 将 `dense-confirmed-call` 接到 `mixed_sample` 的提交桥。公开地址与调用器请求相同时，适配板将六字段和地址送到私有频道 `1680001`–`1680007`。槽 `0` 传整数，未用字段传空信号。

适配板在本笔写入请求有效时先观察 ACK 为 `0`，再用同一公开地址确认 ACK 为 `1`。确认地址保持在 `1701481`，直到调用器撤去请求。即使工道先切到下一地址，调用器仍能收到末笔确认。

```bash
python -m shapez2_tmam.circuits.compiler_backend.dense_write_bridge \
  --circuits shapez2_tmam/blueprints/验收/电路/双半形 \
  --channel-base 1701500 --output dense-write-bridge.spz2bp
```

使用通用 `mixed-dynamic` 样件。移除其接口表 `fixture.platforms` 标出的固定订单头和候选字段板，保留提交桥、写入器和存储板。以工道原点计，将适配板、`dense-confirmed-call`、`dense-column-input`、`dense-column-packet`、`dense-column-advance-phase` 和 `dense-column-advance-level` 各自整体平移 `Y+60`，`X` 偏移依次取 `0/30/60/90/120/150`。

将原色单格送入 `1701466`，其余四层为空，设置目的槽 `1701404=0`、暂存槽 `1701405=1`。订单头按工道接口表接入目标、长度、通过位和回放结果。停料令 `1640059=0`，复位时将 `1640030` 和 `1640060` 置 `0`，等写入相位 `1640001=3` 连续 128 tick。切换订单头和行输入后再置 RUN 和清空确认，并在装方期间保持输入。

| 底层原色与目标 | 工道长度 | 指令顺序 |
| --- | ---: | --- |
| `cr------` | 6 | `14, 10, 4, 1, 4, 2` |
| `Cg------` | 5 | `14, 4, 1, 4, 2` |

离线回放核对了实际写入的六字段。六笔单在末笔确认后放行。第二笔进入相位 `2` 时中断，清空后五笔单从地址 `0` 重启。回放采用板内组合传播和 12 tick 无线延迟，游戏内存储接管见 #72。
