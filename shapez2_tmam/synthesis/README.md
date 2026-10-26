# 合成的 Python 接口

这个包接受偶数象限n≥2、层数上限H≥2的目标，输出具有逐步加工结果的制造证书。默认使用快速局部构造；无晶体目标采用完整判据，未覆盖的含晶体目标返回`unknown`。仅4q5l可用`--complete`启用[完整有界尾部逆推](../4q5l/tail-solver.md)，最坏搜索时间仍很大。六象限及通用参数尚无实用完整求解器，具体边界见[参数化Python模型](../general/python-model.md)。

## 输入目标，取得制造步骤

在仓库根目录运行：

```bash
python -m shapez2_tmam.synthesis 'CuCu----:Cu------' --quadrants 4
```

`--quadrants`指定偶数象限数，`--height`指定整个制造过程的层数上限；默认4q5l。完整逆推`--complete`和六寄存器指令`--instructions`均只支持4q5l。输出是 JSON。`status` 有三种值：

| 状态 | 含义 | 退出码 |
|---|---|---|
| `solved` | `steps` 是从基础原料开始的合法制造树 | 0 |
| `unsolvable` | 违反已证必要条件、无晶体完整判据不通过，或完整四象限搜索已耗尽 | 2 |
| `unknown` | 默认局部构造未覆盖，或 `cu` 的实体供料未界定 | 3 |

编码语法错误由参数解析器报告。保留底部及中间空层，最高层必须非空。普通格使用游戏的 `C/R/S/W` 部件代码，晶体用小写 `c`，针用 `P-`；象限数由 `--quadrants` 指定。颜色语法与实体供料前提见[覆盖性研究](../4q5l/coverage-research.md)，虚拟信号本身不证明某种颜色流体可取得。`cu` 可作为分析信号，实体供料尚未界定，因此局部构造器对此返回 `unknown`；实体结晶配方只启用 `r/g/b/c/m/y/w`。

每一步有 `id`、`operation`、`inputs`、`parameter` 和 `result`。输入编号总在本步之前。物品输入会被消耗；相同子配方引用会展开成独立制造步骤，不隐式复制实体。

| 操作 | 参数与输入 |
|---|---|
| `base` | 取结果描述的一份无晶体单层原料 |
| `rotate` | 一个物品；参数为顺时针象限数，可为负数 |
| `cut` | 一个物品；出口 0 保留索引前半，出口 1 保留后半 |
| `pin` | 一个物品；执行一次顶针 |
| `crystal` | 一个物品；参数为颜色代码 |
| `stack` | 两个物品，按下料、上料排列 |
| `swap` | 两个物品；参数 0 取前半 A＋后半 B，参数 1 取前半 B＋后半 A |

`recipe.instructions()`沿原后序逐项输出`opcode,a,b,destination,base,color,request,result`。基础料占最低空槽，其他操作消费输入并复用第一个源槽；当前四象限构造及完整尾部至多同时需要六个物品槽。请求从1开始交替为0/1，重新执行前完整复位。接口及445平台电路回放器见[六寄存器证明](../4q5l/recipe-registers.md)；它不包含游戏内候选搜索或角宏发令。

## 从 Python 调用

```python
from shapez2_tmam.synthesis import Rules
from shapez2_tmam.synthesis.construct import Constructor

rules = Rules(quadrants=4)
target = rules.parse("CuCu----:Cu------")
result = Constructor(rules).construct(target)
if result.recipe is not None:
    for step in result.recipe.steps():
        print(step)
```

`Rules(quadrants, height=5)`提供旋转、切割、顶针、堆叠、结晶及交换的局部物理，支持偶数n≥2、H≥2。它保留加工后不稳定的输出，不在交换后追加重力；结算中不合并新接触。Recipe记录制造上限，Builder拒绝不同上限或象限的配方输入混用；不能用成品层数代替整个制造过程的高度上限。

`Builder` 提供基础层、无晶体逐层构造、独立单列、独立晶体前缀、逐层 N/P 追加和列拼接。多层晶体原料通过基础原料、结晶和切割展开，不能作为免费的实体输入。

四象限的 `Constructor.half` 使用[逐列角构造](../4q5l/corner-synthesis.md)，在合法颜色范围内精确判半形，成功时至多285个制造节点。`CornerBuilder.accepts_half` 只检查列条件和新分组的稳定性；`CornerBuilder.build` 准备单列及其 N/P 助手，处理八种顶针难列。`Solver4.solve` 使用这些局部起点及完整顶针/堆叠尾部；零Pin首轮由[`minimal_start`](prefix_closure.py)求两个切向的[强制最小前缀](../4q5l/prefix-closure.md)，每切向至多20次补格及一次最终检查。Pin后的S仍完整遍历，由[四次尾部Pin改写定理](../4q5l/three-pin-tail.md)按最高C的零基层号H限定max(0,H−1)条递归边、最多三条，实际搜索分支仍需压缩。理论上每个可制作四象限目标存在至多616节点的制造树。六象限目前只启用无晶体及独立柱构造，不能据此判断全部六象限含晶体目标。

`pin_families`、`cut_families`是独立的惰性物理逆像接口。候选能产生目标，不等于候选本身可制作；使用者须给实际族成员补制造证明。

`stack_reduction.stack_successors(rules, lower, known)`面向普通格统一为Cu的结构目录：K下料只生成连续普通块及单针，并用列顶公式计算结果；非K下料遍历known旧快照中的真实上料。六象限K分支至多37项，替换保持最终闭包，详见[证明](../general/conditional-stacking.md)。该接口尚未接成完整六象限求解器，也不返回不可制造结论。

`HalfCatalog(builder).add(recipe)`登记已知配方各切向的半形结果及原输入凭据；`join(target)`直接投影目标并查表，四象限最多2对、六象限最多3对，找到时返回消费原输入的真实制造树。目标本身不被切割，不对切后结果多算一次重力；缺失只返回None，见[交换化简证明](../general/swap-witnesses.md)。六象限V的代表配方已由此接口生成。

`ordinary_stack(builder, lower, target)`允许非K及不稳定下料。当目标相对下料一次结算结果只增加普通格时，直接检查列顶与新增块支撑，构造一份紧密N/C上料并执行一次Stack；不搜索任意上料，也不把一次加工拆成多次。失败仅表示固定下料的这一子问题不满足条件，见[证明](../general/ordinary-stack.md)。

`single_stack(builder, lower, target)`把普通追加扩展到新增针：先尝试平移后的无晶体上料；失败时，对每列普通格在下、连续针尾在上的目标构造N/C列前缀及针尾。空列不填C，列顶以上不补C。依据[无环支撑森林证明](../general/pin-tail-stack.md)，实际仍执行一次Stack。普通格和针交错且直接上料失败时返回None，不能视为不可制作。

`stack_plan(rules, upper)`编译任意上料的有效N/P块序列；`StackPlan.apply(rules, settled)`读取下料的一次结算结果，保留超高块对后续列顶的阻挡。`StackCatalog(builder).add(recipe)`按两类摘要登记原配方，每键保留已知步数最少者，空/单块上料摘要使用已证极小替换。`construct(target)`先筛下料，再逐块检查新增格；可见格不匹配时立即停止该候选，成功返回已登记摘要对中总步数最少的真实加工树，缺失返回None。此接口可处理N/P交错及非K上料，见[通用证明](../general/stack-summaries.md)。

`Recipe.step_count`在建立节点时计算`1+sum(输入.step_count)`，等于消费式步骤展开的条数。共享子配方引用仍按每份实体分别计数。这个指标用于选配方，不代表建筑数量或游戏耗时，也不保证全局最短。

用户手工复现用的[十二个代表配方](../examples/README.md)由`python -m shapez2_tmam.synthesis.examples --output shapez2_tmam/examples`导出。每类给一个明确目标及全部中间产物，不调用完整搜索。

面向游戏材料寄存器可用 `Solver4(rules, certificate_first=True)`。`pin_families(..., check_output=False)`用[`pin_image_matches`](pin_constraints.py)按最大静止集合及块支撑精确匹配物理输出，无需先编码任意原生候选；[充要证明](../4q5l/pin-image-exact.md)补齐了原必要筛选。候选仍须递归取得制造证书，实际制造的Pin结果也须与目标相同；物理匹配不代替可制作性。两列判据使用[按层扫描](../4q5l/half-row-stability.md)。CLI保留默认正向Pin检查模式，两种物理检查接受同一规范化逆像族；均没有实用搜索复杂度承诺。

`pin_column(target_column, keep_mask, crystal_mask)`接收五格目标和两个0～15掩码，返回一份前四层结构候选或None。它不计算整图Pin，也不判可制作性；晶体掩码只标记强制保留C以外的辅助红C。相应[八位数据通路与自动迭代器](../4q5l/pin-column-circuit.md)已编译为原生蓝图，材料格与标签直接路由，另有`pin_column_at(target_column, slot)`以0～19直接选址，与[四列及完整顶盖电路](../4q5l/pin-patterns.md)共用固定模式表；完整搜索、回退和成功路径发令已接入[四帧控制器](../4q5l/full-tail-circuit.md)，规模和耗时仍须压缩。

[原生电路部件及频道接法](../blueprints/README.md) · [返回总目录](../README.md)
