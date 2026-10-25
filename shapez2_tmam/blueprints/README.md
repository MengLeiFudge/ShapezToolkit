# 原生纯电路部件

这些 `.spz2bp` 文件采用游戏的 `SHAPEZ2-4` 岛蓝图格式。每份蓝图旁的 `.json` 文件给出输入、输出、频道保留范围和部件规模。无晶体部件有完整子类判据；加工核心提供虚拟操作。含晶体完整 TMAM 的搜索控制、配方存储及完成握手仍待实现。

## 导入与频道连接

按存档图形配置选择 `4q5l` 或 `6q5l` 文件。蓝图本身不会把四象限存档切换成六象限，也不修改游戏层数上限。六象限采用相同局部物理、连续三列半切的理论配置，具体 Mod 或存档的兼容性尚未验证。

将目标或其他输入信号接到受控无线发射器，控制端填对应 `.json` 的 `inputs` 频道。使用受控无线接收器读取 `outputs` 频道。`enable` 为整数真值时发布有效结果。每份实例须独占 `reserved_channels` 范围；同一份蓝图复制后会共用原频道，需以新基址重新编译以取得独立实例。

这些部件是组合电路。输入改变时，不同路径可能暂时输出旧结果、空信号或冲突；应保持整组输入直到所有输出稳定。`enable`、`recognized`、`status` 都不是运算完成脉冲。时序控制器须另设稳定输入、等待传播、采样和写回阶段。

游戏的无线频道读取十二个信号 tick 以前的数据，每秒十二个信号 tick；门输入缓冲还使用批次自适应延迟。因此不能把一门当作一个 tick，也不能用两个相邻采样相同就证明整个组合网络已经稳定。本文没有给出经过证明的固定等待周期。

## 无晶体目标的判定与配方

使用 `noncrystal-4q5l.spz2bp` 或 `noncrystal-6q5l.spz2bp`。输入是目标图形与 `enable`。状态输出为：

| `status` | 含义 |
|---|---|
| 1 | 目标不含晶体，且可制作 |
| 2 | 目标不含晶体，且不可制作 |
| 3 | 目标含晶体，超出该部件的判定范围 |
| 空信号 | 输入不是非空图形，或 `enable` 为假 |

另外分别输出 `solvable`、`unsolvable`、`unknown` 布尔信号。只有状态 1 时，发布 `reconstructed` 和五份 `layers_top_to_bottom`。跳过空信号，按这五份层输出的逆序取基础单层原料并堆叠，就是合成配方。实体供料按任意无晶体单层原料的[模型前提](../4q5l/coverage-research.md)处理。

### 判据与配方为何完整

连续五次虚拟拆层，取得所有非空单层；拆层会删除下半部分新暴露的空顶层，但不改各格标签。每一层的每个象限都旋转到 q0，经分析器获得去色部件，并与单格 `cu` 比较，从而识别晶体。两个规则实例分别检查最多二十格、三十格。

无晶体目标没有跨层粘连。每个水平普通块、每个针必须在原位置直接得到下一层的支撑，否则下落。故目标可制作当且仅当可从其单层原料由底向上堆叠重建，证明见[逐层供料定理](../4q5l/compact-synthesis.md)。这个无晶体结论同样适用于六象限，不依赖四象限 K 闭包。

电路从最后拆出的底层开始，按逆序做最多四次虚拟堆叠。输入为空时旁路另一份物品；两份都有值才取得堆叠结果。重建结果与原目标完全相同才发布状态 1。若目标有底部或整层空隙，拆层、重建无法恢复原层号，比较拒绝；不会把压缩空层后的目标当成原目标。

这里的拆层与分析只用于信号求解。实体配方只有基础单层和堆叠，不把虚拟拆层当作免费的实体材料。

## 共用虚拟加工核心

使用 `operation-core-4q5l.spz2bp` 或 `operation-core-6q5l.spz2bp`。输入为 `opcode`、图形 `a`、图形 `b`、流体颜色信号 `color` 和 `enable`。

| opcode | 操作 | primary | secondary |
|---|---|---|---|
| 0 | 复制信号 | a | 空 |
| 1 | 顺时针旋转一个象限 | 旋转结果 | 空 |
| 2 | 逆时针旋转一个象限 | 旋转结果 | 空 |
| 3 | 半周旋转 | 旋转结果 | 空 |
| 4 | 半切 | 索引前半 | 空 |
| 5 | 半切 | 索引后半，保持世界朝向 | 空 |
| 6 | 顶针 | 顶针结果 | 空 |
| 7 | 堆叠 | a 为下料、b 为上料 | 空 |
| 8 | 半形交换 | 前半 a＋后半 b | 空 |
| 9 | 半形交换 | 前半 b＋后半 a | 空 |
| 10 | 结晶 | 用 color 填充 a | 空 |
| 11 | 拆层 | 下半物品 | 最高层，移至地面 |
| 12 | 分析 q0 地面格 | 去色单格部件 | 原颜色 |
| 13 | 顶层染色 | a 的可染色顶层改为 color | 空 |

`recognized` 只表示 opcode 属于 0～13 且 enable 为真。操作输入类型不合法时，游戏虚拟操作可以返回空信号；这个标志不判断输入类型、可制作性或传播是否完成。

## 重新编译

在仓库根目录运行生产编译：

```bash
python -m shapez2_tmam.operation_core --quadrants 4 --channel-base 1000000 --output shapez2_tmam/blueprints/operation-core-4q5l.spz2bp
python -m shapez2_tmam.operation_core --quadrants 6 --channel-base 1001000 --output shapez2_tmam/blueprints/operation-core-6q5l.spz2bp
python -m shapez2_tmam.noncrystal_circuit --quadrants 4 --channel-base 1002000 --output shapez2_tmam/blueprints/noncrystal-4q5l.spz2bp
python -m shapez2_tmam.noncrystal_circuit --quadrants 6 --channel-base 1004000 --output shapez2_tmam/blueprints/noncrystal-6q5l.spz2bp
```

[`Circuit.document`](../circuit.py) 在编译时检查每个门的输入数量、输出引用、频道范围、别名组，以及旋转后的建筑实际占地与每个本地输入端口的真实几何来源。每门单独使用一块 1×1 基础平台；无线收发器占用 3×3×3 格，交换门占两格，其余本次所用门占一格。

原生占地、端口来自 `resources.assets`，指纹及端口约定见 [`mari/ports.py`](../mari/ports.py)。格式对应 `BlueprintSerializer`、两种 `BlueprintEntryJsonConverter` 和 `SignalSerializer`；省略图标时 `BlueprintJsonConverter` 使用默认图标。无线时序依据 `SignalChannelRingBuffer.ReadSignal`、`SignalSimulation` 和 `SignalBuffer.TryPopSignal`。

生产编译与静态接线检查不包含门级模拟、游戏导入或运行验证。平台数、频道和状态合同以对应生成 JSON 为准。

[Python 局部制造证书](../synthesis/README.md) · [半形构造证明](../4q5l/compact-inverse.md) · [返回总目录](../README.md)
