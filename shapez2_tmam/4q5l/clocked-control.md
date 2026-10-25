# 四阶段控制与等深锁存

本页为 [`sequential_circuit.py`](../sequential_circuit.py) 的反馈网络给出源码证明。它补充自动时钟和可重复使用的状态单元；完整四象限求解器仍须实现候选生成、搜索和制造配方流。

## 1. 精确延迟的适用条件

这里使用比[组合保持期](signal-timing.md)更强的前提：整份生成蓝图一次批量导入，或完整重载后，在固定接线、固定配置和独占频道下运行。本机采用 Hybrid 或 AlwaysHighUPS 的常速连续推进，每个集群批次最多四个信号 tick。不覆盖调试单步、模式切换、强制低UPS、快进、改线期间或任意外接反馈电路。

`ActionModifyIsland.ExecutePlace` 把岛及建筑的放置包在 `Map.StartBunchEdit` 中。`MapLayout` 的开始/结束事件由 `Simulator` 注册；结束时 `Simulator.FinalizeBunchEditMode` 又用 `SimulationGraph.StartBunchEdit` 批量加入模拟节点。`SimulationGraph.FinalizeBunchEditMode` 通过 `AddNodeFast` 加入节点，令更新顺序无效，第一次更新前由 `PrepareClusterForUpdate → ValidateCluster → RecomputeUpdateOrder` 重建。完整加载的 `Simulator.InitializeSystemsWithLayoutContent` 同样分批注册建筑，连接到旧节点的脏集群也被合并后重建。

信号建筑的提供端优先级为 `MeFirst=1`，接收端为 `MeLast=-1`，导线网络端为 `DontCare=0`。`RecomputeUpdateOrder` 先访问连接到自身更高优先级端口的节点，再加入当前节点。因此对无环本地接线，提供者在消费者之前更新。生成器每个平台内的路径只有常量、无线接收器、至多一段连续导线、运算门、至多一段连续导线、无线发射器；无线频道不构成这个本地连接图的边。本地图无环，即使逻辑网表含无线反馈也如此。

同一连接组件属于同一集群，同批次起点和信号 tick 范围相同。提供者先把至多四个 tick 全部写进 `SignalBuffer`，消费者随后读取时，`LastStartTicks_T` 等于当前起点。自适应分支的起点差为零，读取槽号为 `t mod 4`。本批次范围内最多四个连续 tick，槽互不覆盖，因此读到的恰为提供者在同一 t 写的值。由本地路径归纳，门到无线发射器以及无线接收器到门都不额外移动信号 tick。

无线环表读取恰为 `t−12` 的记录。强制更新阈值为 `1/3−1/30` 秒，每次正常模拟推进最多再加 `1/30` 秒；上一次推进结束已完成所有强制更新，所以每个集群的已完成时间不落后当前推进终点超过 `1/3` 秒。并发更新中的集群也不可能先于当前终点。对接收器本批次的任意 t，发送方最新已完成位置和 t 的差只有当前或相邻短批次的范围，远小于十二 tick；故 t−12 已写入。发送方也没有领先到 t+12，长24的环槽尚未覆盖这条历史记录。多驱动在同 tick 合并完成之后才会被十二 tick 后的读者消费。

因此在复位和常量启动结束后，每条 `Ref` 数据边精确提供源频道的 `t−12` 值。直接相邻 `Literal` 是本批次固定常量。用固定整数选频的显式无线接收门会另增加一次十二 tick；本页时钟只把它用于外部 enable，递推以该门的输出为 enable。

这个结论不能推广到任意搭建顺序。增量 `IntegrateNode` 与批量拓扑重建属于不同路径；本页只依赖已核实的批量路径。先前对自适应缓冲毛刺的顾虑仍适用于没有此更新顺序前提的线路。

## 2. 只有一个反相的延迟环

设每阶段 S 个无线延迟级，S≥2，默认 S=48。q 经 `2S−2` 个恒真 IF、一个 NOT，再经与 enable 相与的 AND 回到 q；每级十二 tick。记 P=12S，L=2P，则：

```text
q(t) = truthy(enable(t−12)) AND NOT truthy(q(t−L))。
```

enable 保持零时，q 不依赖反馈而持续为整数零。复位保持 `4P+128` tick，足以清掉整条反馈环、相位抽头、常量启动和外部收发历史。随后 enable 在本部件输入只发生一次0→1并持续为1。q 先在一段长度L的连续区间为1，此后每经过L反相一次，得到高L/低L的方波；批次长度变化不改变这个逐 tick 递推。

从复制链取 S 级抽头 d(t)=q(t−P)。q/d 各经同一级数的正相复制和反相，再由 AND 解出：

| 阶段 | q | d |
|---|---|---|
| 0 | 1 | 0 |
| 1 | 1 | 1 |
| 2 | 0 | 1 |
| 3 | 0 | 0 |

四个解码结果均比 q/d 多24 tick，每 tick 恰有一个为1。它们依次持续 P tick，周期4P。默认每阶段576 tick、48模拟秒，完整周期2304 tick、192模拟秒。复位时阶段3为真；启动时先有一段不完整的阶段3，再出现完整的0、1、2、3。阶段3本身不表示一次运算已完成。

## 3. 四门锁存器

设 `load`、`data` 为门输出频道。先对 load 分别用恒真 IF 复制、用 NOT 反相；再用两份 IF 产生：

```text
D = IF(data, copy(load))
H = IF(R, NOT(load))
R = 同频道合并(D,H)
```

复制与反相各恰延迟12，D/H 的控制再延迟12，所以每个 t 两路 IF 的选中状态严格互补。不存在一边已关闭而另一边尚未打开的 tick，也不存在两个不同值同时驱动。R 本身只通过无线返回 H，反馈也遵循同一精确边延迟。

当 data 是 Ref 时，有逐 tick 递推：

```text
R(t) = load(t−24) 为真 ? data(t−12) : R(t−12)。
```

关闭写入后，十二个余数类各自保留旧值。因此写入必须把所有十二个历史位置统一为 V：data 从a起恒为V，load 在覆盖 `[a,a+12)` 的区间保持真并再留传播余量，就能使一个连续十二 tick 的 R 历史全为V。若 load 从b起为假，data 仍须保持V至b+12以后，覆盖尚在途中的选中分支。随后 R 永久为V，直到下次写入。V 可以是整数0、空信号、颜色或图形；空值被选中时两路均为空，正是正确结果。

与[分离双控制寄存器](register-circuit.md)相比，这个四门版本依赖更强的本地拓扑和精确延迟前提。前者的三阶段协议继续保留，不能在任意未知接线中直接替换。

## 4. 两组状态交替更新

使用上述时钟时，可以令主寄存器组在阶段0透明写入，副寄存器组在阶段2透明复制主组；阶段1和3让两组关闭并留出传播余量。下一状态只由副组计算。副组在阶段2改变之后，距下次主组写入尚有阶段3；主组在阶段0改变之后，距副组写入尚有阶段1。

下一状态必须在主组关闭前连续十二tick保持正确，关写后数据还须保持至少十二tick。若相位经一级OR和等深选择，主副组的实际开关均比阶段边界晚36tick：副组在阶段2后36tick改变，到下一周期阶段1后36tick的主组关闭，相隔3P。数据路径上界加十二tick历史小于3P，就允许阶段0前半段暂时写入旧计算；无需要求所有数据在单个阶段内完成。初始化和输出窗口还须单独证明。

独立时钟默认P=576；自动拆层器用复位预计算把P缩到96，顶针单列迭代器用P=156，分别见各部件证明。更深的完整搜索电路仍须计算自身路径界，不能因为有时钟就自动判定满足。

源码依据：`ConnectableBuildingSimulation`、`SignalProviderConnector`、`SignalReceiverConnector`、`SignalNetworkConnector`、`SimulationGraph`、`SimulationCluster`、`Simulator`、`MapLayout`、`ActionModifyIsland`、`SignalBuffer`、`SignalNetworkSimulation`、`SignalChannelRingBuffer`、`ProcessingUpdateStrategy` 以及前页核实的正常推进调用链。结论来自静态源码与递推证明，未运行时钟、门级模拟或游戏。

[蓝图与频道](../blueprints/README.md) · [拆层数据通路](circuit-decoding.md) · [返回四象限目录](README.md)
