# 合成的 Python 接口

这个包接受偶数象限n≥2、层数上限H≥2的目标，输出具有逐步加工结果的制造证书。两象限默认采用[任意层数的完整直接判据](../proofs/03-general-construction.md#s03-05)；其他象限采用快速局部构造，无晶体目标仍完整判定，未覆盖的含晶体目标返回`unknown`。仅4q5l可用`--complete`启用[完整有界尾部逆推](../proofs/02-four-quadrants.md#s02-06)，最坏搜索时间仍很大。六象限及通用参数尚无实用完整求解器，具体边界见[参数化Python模型](../proofs/04-stacking.md#s04-20)。

## 输入目标，取得制造步骤

在仓库根目录运行：

```bash
python -m shapez2_tmam.synthesis 'CuCu----:Cu------' --quadrants 4
```

`--quadrants`指定偶数象限数，`--height`指定整个制造过程的层数上限；默认4q5l。完整逆推`--complete`只支持4q5l；六寄存器指令`--instructions`支持4q5l和6q5l，最终证书经过半圈规范化，四/六象限每个制造表项只需一包；直接传入未经优化的六象限树时，两格旋转仍拆成两条原位指令。输出是 JSON。`status` 有三种值：

| 状态 | 含义 | 退出码 |
|---|---|---|
| `solved` | `steps` 是从基础原料开始的合法制造树 | 0 |
| `unsolvable` | 违反已证必要条件、无晶体或两象限完整判据不通过，或完整四象限搜索已耗尽 | 2 |
| `unknown` | 默认局部构造未覆盖，或 `cu` 的实体供料未界定 | 3 |

编码语法错误由参数解析器报告。保留底部及中间空层，最高层必须非空。普通格使用游戏的 `C/R/S/W` 部件代码，晶体用小写 `c`，针用 `P-`；象限数由 `--quadrants` 指定。颜色语法与实体供料前提见[覆盖性研究](../proofs/01-foundations.md#s01-09)，虚拟信号本身不证明某种颜色流体可取得。`cu` 可作为分析信号，实体供料尚未界定，因此局部构造器对此返回 `unknown`；实体结晶配方只启用 `r/g/b/c/m/y/w`。

每一步有 `id`、`operation`、`inputs`、`parameter` 和 `result`。输入编号总在本步之前。物品输入会被消耗；相同子配方引用会展开成独立制造步骤，不隐式复制实体。

无晶体制造统一使用[逐层供料和堆叠](../proofs/04-stacking.md#s04-15)，h层需要2h−1步、最多两个活动物品槽；纯针段不再另设识别与Pin路径。独立列及矩形核心的无C后缀共用这套方式。完整4q控制器也删除纯针段专用逻辑，每行至多两条条件记录，使用同一加工核心与既有物品槽。

| 操作 | 参数与输入 |
|---|---|
| `base` | 取结果描述的一份无晶体单层原料 |
| `rotate` | 一个物品；参数为顺时针象限数，可为负数 |
| `cut` | 一个物品；出口 0 保留索引前半，出口 1 保留后半 |
| `pin` | 一个物品；执行一次顶针 |
| `crystal` | 一个物品；参数为颜色代码 |
| `stack` | 两个物品，按下料、上料排列 |
| `swap` | 两个物品；参数 0 取前半 A＋后半 B，参数 1 取前半 B＋后半 A |

`recipe.instructions()`按子树槽需求降序的后序逐项输出`opcode,a,b,destination,base,color,request,result`，保留原操作数顺序。基础料占最低空槽，其他操作消费输入并复用第一个源槽；预算不足时在输出首条指令前拒绝。当前四象限构造及完整尾部至多同时需要六个物品槽。请求从1开始交替为0/1，重新执行前完整复位。接口及443平台四象限电路回放器见[六寄存器证明](../proofs/08-circuits.md#s08-28)；它不包含游戏内候选搜索或角宏发令。

`Recipe.register_count`在建立节点时计算当前制造树的物品槽需求。先完整制造槽需求较大的子树，可最小化这类逐子树调度的峰值；具体递推及适用范围见[槽数调度证明](../proofs/04-stacking.md#s04-19)。它不代表完整机器的搜索状态数量。

CLI输出前用[`optimize_rotations`](orientation.py)安排整棵制造树的朝向：基础料直接按所需朝向供给，Pin/Crystal/Stack允许共同旋转，Cut/Swap只使用半圈换出口。它在固定非旋转加工树及这些变换内取得最少净旋转表项，物品槽需求保持；[证明与范围](../proofs/04-stacking.md#s04-18)。直接Python调用者可在取得证书后显式使用；构造和搜索内部不反复运行此优化。

## 从 Python 调用

```python
from shapez2_tmam.synthesis import Rules
from shapez2_tmam.synthesis.construct import Constructor
from shapez2_tmam.synthesis.orientation import optimize_rotations

rules = Rules(quadrants=4)
target = rules.parse("CuCu----:Cu------")
result = Constructor(rules).construct(target)
if result.recipe is not None:
    for step in optimize_rotations(result.recipe).steps():
        print(step)
```

`Rules(quadrants, height=5)`提供旋转、切割、顶针、堆叠、结晶及交换的局部物理，支持偶数n≥2、H≥2。它保留加工后不稳定的输出，不在交换后追加重力；结算中不合并新接触。Recipe记录制造上限，Builder拒绝不同上限或象限的配方输入混用；不能用成品层数代替整个制造过程的高度上限。

`Builder` 提供基础层、无晶体逐层构造、独立单列、独立晶体前缀、逐层 N/P 追加和列拼接。多层晶体原料通过基础原料、结晶和切割展开，不能作为免费的实体输入。

`Builder.rectangular_columns(target)`对具有矩形核心、占据连续角区间或全圈的列，使用[同色段并行结晶](../proofs/03-general-construction.md#s03-06)。共同纯针前缀及最高C之上的N/P后缀分开处理，后缀允许各列高度不同，但每列连续、占用集合逐层递减；中间N/C核心须同层晶体同色。核心多层先以针占位，换色前统一结晶，裁好角区间后再补地面针和无C后缀。纯N/C全圈L层只需`2L−1+k`步，k为忽略普通层后的连续晶体颜色段数。`independent_columns`先尝试整图及两个半面的这条直接路径，失败的半面仍合并相邻同NPC/晶体颜色模板的列段，其余保留逐列构造；失败仍不表示目标全局不可制作。

`Builder.replicate(source)`把相同H、较少偶数象限的真实配方提升到整数倍象限：每格扩张成相邻副本，旋转参数按倍数换算，其余操作保持。它根据[操作对应证明](../proofs/03-general-construction.md#s03-07)直接变换全部中间产物，不重新运行每个大图节点的物理。`Constructor`在旧构造失败后自动识别这种连续列结构，尝试较小商图并提升成功证书；小图不可制作不会被传为大图不可制作。

两象限的`Constructor.construct`检查稳定性、针前缀和全图最高C以下的连续列，随后先制造完整两列前缀，再追加上方N/P。它在已界定供料内直接返回solved或unsolvable，不查完整状态目录；`cu`仍返回unknown。配方长度O(H)、物品槽至多3，原生`--instructions`仅支持4q5l和6q5l，不包含这个两象限六层构造。

四象限五层的 `Constructor.half` 使用[逐列角构造](../proofs/02-four-quadrants.md#s02-03)，在合法颜色范围内精确判半形，成功时至多285个制造节点；所有半形统一制造外向两角、拼合并切去助手，无C直接制造和自带助手快捷分支均已删除。`CornerBuilder.accepts_half` 只检查列条件和新分组的稳定性；`CornerBuilder.build`准备单列及其N/P助手，四象限五层按直接释放或参数化顶破处理；顶破料由间隙上端r和落点m生成，不再匹配八种完整字串。`Solver4.solve`把所有起点统一到`Constructor.paired_halves(target, start)`，使用[同一完整整图流程](../proofs/03-general-construction.md#s03-08)及有界顶针/堆叠尾部；无C和独立柱不另设完整模式快捷制造；零Pin首轮由[`minimal_start`](prefix_closure.py)求两个切向的[强制最小前缀](../proofs/02-four-quadrants.md#s02-09)，每切向至多20次补格及一次最终检查。Pin后的S仍完整遍历，由[四次尾部Pin改写定理](../proofs/02-four-quadrants.md#s02-07)按最高C的零基层号H限定max(0,H−1)条递归边、最多三条，实际搜索分支仍需压缩。[两侧悬空N代表](../proofs/02-four-quadrants.md#s02-08)证明至少一次尾Pin确实必要，但尚未证明是否有目标必须两次或三次。理论上每个可制作四象限目标存在至多616节点的制造树。六象限另有通用两列角构造，但不能据此判断全部六象限含晶体目标。

偶数n≥6、任意H的`CornerBuilder.build(column, quadrant, direction)`统一使用[三列释放构造](../proofs/03-general-construction.md#s03-03)，列条件A是存在相邻N/P助手的充要条件。`CornerBuilder.pair(target)`制造指定q0/q1稳定两列目标，允许目标另一列含C及含针支撑环；六象限默认`Constructor`统一使用`CornerBuilder.supported_half`的[递归外侧脚手架](../proofs/03-general-construction.md#s03-04)，已覆盖原稳定两列角、H/V及多晶体列环，删除独立pair分支。更大象限保留相邻两列入口。递归过程逐列转交支撑，反向复用同一角程序；六象限后续支撑检查复用`stable_half(supported_column=0/1)`，单半形至多四槽、两半拼合至多五槽。失败不推断一般全图不可制作。四象限任意H另接受[直接释放](../proofs/02-four-quadrants.md#s02-15)，悬空落点仍未覆盖。列A必要筛选应用于所有参数；固定4q5l电路ROM已同步r/m参数及同层补料，六象限完整求解电路仍缺。

`pin_families`、`cut_families`是独立的惰性物理逆像接口。候选能产生目标，不等于候选本身可制作；使用者须给实际族成员补制造证明。

`stack_reduction.stack_successors(rules, lower, known)`面向普通格统一为Cu的结构目录：[K_add](../proofs/04-stacking.md#s04-02)下料只生成连续普通块及单针，并用列顶公式计算结果；未通过时再检查一次结算结果：若它进入K_add，只生成纯C上料触发这次结算，后续由安全基础块链覆盖；其余下料仍遍历known旧快照中的真实上料。该[结算后约化](../proofs/04-stacking.md#s04-04)也覆盖六象限不稳定V。六象限基础块分支至多37项，范围包含K及等列顶非K半形H，替换保持最终闭包。`support.in_addition_class`用两圈危险高度扫描和跨潜在组支撑边的反向传播实现判据，不计算强连通分量。该接口尚未接成完整六象限求解器，也不返回不可制造结论。

`HalfCatalog(builder).add(recipe)`按前半、后半用途分别保存已知最低成本原输入；`join(target)`直接投影目标并比较n个有向起点，4q查4对、6q查6对，选表内总步骤最少、同长时物品槽最少的制造树。目标本身不被切割，不对切后结果多算一次重力；缺失只返回None，见[交换化简](../proofs/04-stacking.md#s04-16)及[用途成本证明](../proofs/04-stacking.md#s04-17)。Builder.apply同时合并连续旋转、删去精确结果等于输入的一元加工；六象限V代表配方由此接口生成。

`ordinary_stack(builder, lower, target)`允许非K及不稳定下料。当目标相对下料一次结算结果只增加普通格时，直接检查列顶与新增块支撑，构造一份紧密N/C上料并执行一次Stack；不搜索任意上料，也不把一次加工拆成多次。失败仅表示固定下料的这一子问题不满足条件，见[证明](../proofs/04-stacking.md#s04-10)。

`single_stack(builder, lower, target)`把普通追加扩展到新增针：依次尝试[无C块数守恒与原位补C](../proofs/04-stacking.md#s04-11)、[列内压紧](../proofs/04-stacking.md#s04-12)、[保留针下间隙](../proofs/04-stacking.md#s04-13)。后两种载体共用差分下界求解器，分别调整列起点或物理块来源层。按块求解还会尝试把初始针固定为触地前缀，放宽允许补C的区间；全部补C候选须确认抬高后没有静止格，并取得独立列制造凭据。原针尾域及旧候选成功路径保持，实际始终只对原下料执行一次Stack。四种候选均失败时返回None，不能视为目标全局不可制作。

`stack_plan(rules, upper)`编译任意上料的有效N/P块序列；`StackPlan.apply(rules, settled)`读取下料的一次结算结果，保留超高块对后续列顶的阻挡。`StackCatalog(builder).add(recipe)`按两类摘要登记原配方，每键保留已知步数最少者，空/单块上料摘要使用已证极小替换；首次出现的多块摘要调用`StackPlan.noncrystal_carrier`，空地面落点块数保持时取得[同摘要的唯一无C载体](../proofs/04-stacking.md#s04-07)，仅在配方成本更低时替换。没有同摘要无C实体时，`StackPlan.carrier_orders`给出规范序及[同秩三着色序](../proofs/04-stacking.md#s04-09)，后者避免把独立块排成过高阶梯；`ordered_carriers`分别从两种保序块序列建立差分约束，尝试普通后缀和触地针前缀两种[含C紧凑载体](../proofs/04-stacking.md#s04-08)；两者均须全体释放、取得独立柱制造凭据，按成本择优。`construct(target)`先筛下料，再逐块检查新增格；可见格不匹配时立即停止该候选，成功返回已登记摘要对中总步数最少、同长时物品槽最少的真实加工树，缺失返回None。此接口可处理N/P交错及非K上料，见[通用证明](../proofs/04-stacking.md#s04-06)。

`Recipe.step_count`在建立节点时计算`1+sum(输入.step_count)`，等于消费式步骤展开的条数。共享子配方引用仍按每份实体分别计数。这个指标用于选配方，不代表建筑数量或游戏耗时，也不保证全局最短。

用户手工复现用的[完整目标代表及机制配方](../examples/README.md)由`python -m shapez2_tmam.synthesis.examples --output shapez2_tmam/examples`导出。每份给出明确目标及全部中间产物，不调用完整搜索；这些是观察机制的样本，不是必须保留的独立加工模板。

面向游戏材料寄存器可用 `Solver4(rules, certificate_first=True)`。`pin_families(..., check_output=False)`用[`pin_image_matches`](pin_constraints.py)按最大静止集合及块支撑精确匹配物理输出，无需先编码任意原生候选；[充要证明](../proofs/01-foundations.md#s01-16)补齐了原必要筛选。候选仍须递归取得制造证书，实际制造的Pin结果也须与目标相同；物理匹配不代替可制作性。两列判据使用[按层扫描](../proofs/01-foundations.md#s01-19)。CLI保留默认正向Pin检查模式，两种物理检查接受同一规范化逆像族；均没有实用搜索复杂度承诺。

`pin_column(target_column, keep_mask, crystal_mask)`接收五格目标和两个0～15掩码，返回一份前四层结构候选或None。它不计算整图Pin，也不判可制作性；晶体掩码只标记强制保留C以外的辅助红C。相应[八位数据通路与自动迭代器](../proofs/08-circuits.md#s08-23)已编译为原生蓝图，材料格与标签直接路由，另有`pin_column_at(target_column, slot)`以0～19直接选址，与[四列及完整顶盖电路](../proofs/08-circuits.md#s08-26)共用固定模式表；完整搜索、回退和成功路径发令已接入[四帧控制器](../proofs/08-circuits.md#s08-09)，规模和耗时仍须压缩。

[原生电路部件及频道接法](../blueprints/README.md) · [返回总目录](../README.md)
