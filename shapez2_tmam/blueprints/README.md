# 原生纯电路部件

这些 `.spz2bp` 文件采用游戏的 `SHAPEZ2-4` 岛蓝图格式。每份蓝图旁的 `.json` 文件给出输入、输出、频道保留范围和部件规模。无晶体部件有完整子类判据；标准四象限半形已有自动制造流，其他加工核心提供虚拟操作。四象限含晶体全图已有四帧完整控制首版，规模和耗时仍须压缩；六象限完整控制仍未实现。

## 导入与频道连接

按存档图形配置选择 `4q5l` 或 `6q5l` 文件。蓝图本身不会把四象限存档切换成六象限，也不修改游戏层数上限。六象限采用相同局部物理、连续三列半切的理论配置，具体 Mod 或存档的兼容性尚未验证。

将目标或其他输入信号接到受控无线发射器，控制端填对应 `.json` 的 `inputs` 频道。使用受控无线接收器读取 `outputs` 频道。`enable` 为整数真值时发布有效结果。每份实例须独占 `reserved_channels` 范围；同一份蓝图复制后会共用原频道，需以新基址重新编译以取得独立实例。

加工、解码及判据部件采用组合电路。输入改变时，不同路径可能暂时输出旧结果、空信号或冲突；应保持整组输入直到所有输出稳定。`enable`、`recognized`、`status` 都不是运算完成脉冲。自动扫描器另含四阶段时钟、寄存器与采样窗口，按下面的独立协议使用。

游戏的无线频道读取十二个信号 tick 以前的数据，每秒十二个信号 tick；本地输入缓冲和导线网络也有延迟。[保守保持期证明](../4q5l/signal-timing.md)覆盖这些因素：按频道依赖的最大深度 D，整组输入保持 `64×(D+2)` 个信号 tick 后可采样全部输出。各 JSON 的 `settling.hold_signal_ticks` 给出对应值。此结论要求本机 Hybrid 或 AlwaysHighUPS 模式的常速连续推进、频道独占、网络与配置保持不变。调试单步、强制低UPS、模拟模式切换和快进不在已证范围内。时间按游戏模拟计，不能改用墙钟或两次相同采样。

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

## 原层号解码与半形判定

`decoder-4q5l.spz2bp` 使用199块平台。输入为 `target`、`enable`；输出 `valid`、五个 `rows_bottom_to_top`，以及 `cells_bottom_to_top[z][q]` 的去色单格、原颜色和占用/针/晶体标志。空底层与中间整层空隙保留在原输出口；层号和象限均从零开始。内部使用15次密集拆层测高，把原始拆出的层安放回原层号，详见[解码证明](../4q5l/circuit-decoding.md)。

`half-4q5l.spz2bp` 使用458块平台并内含解码器。它完整判断 q2、q3 全空的标准 q0/q1 半形。`status=1/2/3` 表示可制作、不可制作、超出范围；输入无效或关闭时为空。非标准全图、未界定供料的 `cu` 返回3。输出还包括五个原始层位、标准半形标志、稳定性及列条件结果；诊断标志应在输入有效且保持稳定后读取。

半形判据为“两列满足 A AND 自身分组稳定”，由[逐列角构造](../4q5l/corner-synthesis.md)证明。稳定性通过原生半切与原目标比较取得。独立判定器不输出制造指令；自动制造部件见下一段，Python制造树由 `Constructor.half` 生成。

两份部件的频道和保留范围见对应 JSON。解码器的保守保持期为1152信号tick（96模拟秒）；半形判定器为2304信号tick（192模拟秒）。这些是充分等待期，并非实测耗时或最短时间。两份部件没有完成脉冲，`valid` 和状态值不表示新输入已经传播完成。

`material-half-4q5l.spz2bp` 用461平台直接读取十个材料整数：0空、1普通、2针、3晶体，按原层号每层q0/q1排列。输入有效、非空且启用时，status=1/2精确表示材料结构可制作/不可制作；其他输入为空状态。它用[按层稳定性判据](../4q5l/half-row-stability.md)与列A工作，无需先把逆推候选编码成原生图形信号。晶体3以rgbcmyw合法供料为前提，cu须由调用者另行排除；标签与配方流仍由制造端处理。

## 标准半形自动制造

`automatic-half-4q5l.spz2bp`接受任意原生输入，范围内的q0/q1标准半形自动输出消费式指令并回放到目标。它共用半形判据、459行条件程序及六个物品槽，使用7108平台；状态0运行、1已制造且与目标相同、2判据否定、3非标准半形或cu、4内部失配。4不能作为不可制作结论。

target全程保持，enable=0至少988tick后启用。每个window上升后等48tick，窗口内读一次；sample为真先保存instruction包，再处理同窗done/status。每阶段204tick，每周期68模拟秒；初始化加全部程序行的保守上界为8小时41模拟分20秒，仍需压缩，尚未通过实用性能验收。它不带背压，也未接全四象限逆推控制。范围、宏证明、复位及完整接口见[自动半形说明](../4q5l/automatic-half.md)。

## 双半形起点

`startpoint-4q5l.spz2bp`用8644平台判断两个切向的互补原格半面，稳定且满足A就分两遍制造并拼接。两遍共用一份465行角程序和六个物品槽，覆盖有界尾部的全部起点A；尚未含S/顶针搜索。状态3表示需要尾部或cu范围外，不能判不可制作。

target保持，enable=0至少1420tick后启用；window上升后48tick采样，sample为真先收指令，再处理done/status。阶段228tick、周期76模拟秒，最多931周期的保守上界约19小时39分，仍需继续压缩。切向选择、空半形、两遍及六槽证明见[双半形起点](../4q5l/two-half-startpoint.md)。

## 起点与纯N/P追加尾部

`s-tail-4q5l.spz2bp`用10651平台完整遍历允许S前缀，再制造双半形起点并补齐目标。每列跳过空层重复、保留全部C，最多1296个不同组合，含C时最多1080。475行制造程序仍共用两遍，使用六物品槽及六个搜索寄存器。含C搜索失败只返回3，仍须顶针尾部；无C范围可完整判不可制作。

target保持，enable=0至少1612tick后启用；window上升后48tick采一次，sample为真先收指令，再处理done/status。每周期76模拟秒，通用最坏上界约47小时26分，含C约42小时52分；它尚未通过实用规模/性能验收。搜索与冻结预计算分别按37/87级路径计时，制造按52级，证明见[完整S段](../4q5l/s-tail-circuit.md)。

## 完整四象限尾部控制

`full-tail-4q5l.spz2bp`接收任意原目标与enable，在既定供料模型内先搜完整有界尾部，成功后才发布消费式制造流。四帧保存目标及游标，目标先过K必要筛选；零Pin闭包失败后先要求完整目标属于G，Pin轮前缀也要求G；K/G共用通路，搜索只按材料格和[精确Pin关系](../4q5l/pin-image-exact.md)取得存在性证书，不执行制造ROM；根成功后制造叶端，再逐层Pin/追加，最终原生结果等于原目标才返回1。状态2只在全部分支真正穷尽后发布，cu返回3，内部失配返回4。

两份完整蓝图使用145项状态、262行ROM和六物品槽，每格只查本列9项标签。target保持，enable=0在未压缩版至少2032tick、固定局部压缩版至少1792tick；每完整window上升后96tick读一次，sample为真先收包再处理done。采用[慢更新冻结协议](../4q5l/multicycle-control.md)，未压缩版制造周期80模拟秒，压缩版按[固定局部边计时](../4q5l/packed-timing.md)为68模拟秒；慢状态更新后额外等待一轮。

[两角共用](../4q5l/shared-angle.md)压缩含C半形制造ROM，现存蓝图仍含无C半形直接制造和纯针行段快捷路径，最多9条加工指令；源码已按[通用两角流程](../4q5l/shared-angle.md)合并这些路径。叶端和父帧[共用同一S追加段](../4q5l/shared-append.md)，仅父帧先执行Pin。[直接有效行后继](../4q5l/inactive-rom-runs.md)跳过不发包的普通行，[同色段结晶](../4q5l/color-run-program.md)进一步减少制造发令。[强制闭包](../4q5l/prefix-closure.md)把首轮改成每切向至多21次检查；[可选顶格](../4q5l/optional-top.md)让每族共用A→S检查，失败后用[全族G筛选](../4q5l/family-grounding.md)排除没有地面可达成员的族，其余才逐成员搜Pin尾部。[来源槽约束](../4q5l/pin-source-conflicts.md)提前排除强制C冲突及邻接N的非法下落；[最大顶盖](../4q5l/maximal-cap.md)物理失败时排除同一前四层的全部顶盖，通过仍逐族找证书。Pin分支仍过大，尚未通过实用性能验收。完整覆盖、帧回退、重放及互斥选择证明见[四帧控制](../4q5l/full-tail-circuit.md)。

`full-tail-packed-4q5l.spz2bp`把固定常量放到输入旁，合并5579对单消费者内部组合门，再按真实占地装箱。共563块3×3大平台，占5067个区块，外框72×72个区块（每区块20×20建筑格），独占频道1277000～1342535；含147216个非线缆建筑。未压缩版为25408块平台、170498个非线缆建筑。两版都省去公开输出[依赖闭包](../4q5l/output-cone.md)以外的570个门，被吸收或省去的内部频道不能用于外接监测。逐端口核对及[装箱证明](../4q5l/packed-circuit.md)说明占地与时序边界。

本目录两份完整蓝图及旁置JSON保留合并前快照；[最新网表报告](../reports/README.md)为249行ROM、压缩版142255个非线缆建筑，本轮未生成新布局。使用现存蓝图必须读取本目录相邻JSON，不能混用新报告的输出频道。其他独立部件保留各自原产物。生产编译不代表已在游戏中验证。

## 递归候选的固定标签网格

`tagged-goal-4q5l.spz2bp`用5768平台将20份格ID还原为原层号的NPC片段、占用、针、晶体和颜色。0～3为空/Cu/P/红C，4～23固定引用最外层原目标格；原空格ID无效。C只在npc信号中用P占位，不生成免费晶体原料。

另输入一份实际原生加工结果，逐格比较位置、材料、部件和颜色，matches为真才完全相同。输入全组保持2368信号tick后读取；无完成脉冲。它供Pin递归控制使用，不判可制作性。固定标签闭包、空格及比较证明见[标签目标网格](../4q5l/tagged-goal-grid.md)。

`tagged-leaf-4q5l.spz2bp`进一步把这些ID直接接入A→S叶端，使用16021平台、同一475行程序及六物品槽，输出制造指令与真实结果。无需先提供候选目标的原生信号。换ID须完整复位至少1696tick；每周期76模拟秒，末端另等一周期逐格比较。它仍缺Pin递归，当前通用2248周期上界尚未通过实用性能验收。完整接口与等待证明见[编号目标叶端](../4q5l/tagged-leaf.md)。

## 时序复用的数据通路与寄存器

`scan-4q5l.spz2bp` 用38平台读取当前最高非空层。输出原始 `top` 单层、保留原层位的 `lower` 下半，以及从1开始的 `original_layer`。控制器可锁存这些结果，再把新下半作为下一次输入，最多调用五次。它是供循环调用的共用数据通路，未包含写回和阶段控制。

`signal-register.spz2bp` 用5平台保存任意信号，包括整数0和空值。输入为 `data`、`load`、`retain`。依次使用 `(load,retain)=(1,0)→(1,1)→(0,1)`，每阶段保持512信号tick，data在三阶段均保持不变。第三阶段结束后才可复用数据总线；保持 `(0,1)` 就持续保存该值。首次使用必须完整写入一次。

重叠阶段两路同时发布同一个值；同值信号合并不会冲突。三阶段协议及反馈保持的[源码证明](../4q5l/register-circuit.md)独立于组合保持期。该寄存器没有时钟、地址选择器或完成脉冲，不能省略重叠阶段或用单个控制及其反相直接代替。

`four-phase-clock.spz2bp` 提供105平台的自动时钟。每阶段576信号tick，依次循环0、1、2、3。整份批量导入或完整重载后，保持 `enable=0` 至少2432tick，再改为1并保持。复位时阶段3为真，启动先有一段不完整阶段3，随后出现第一个完整阶段0。适用的本地拓扑与常速更新条件、四门等深锁存器见[控制证明](../4q5l/clocked-control.md)。

`iterative-scanner-4q5l.spz2bp` 把同一拆层通路与时钟、主副寄存器接成127平台的自动循环，每阶段96信号tick、每轮32模拟秒。保持target，先让enable=0至少512tick再启用；每个阶段3输出一份 `top`、原层号 `original_layer` 和 `sample` 窗口。输出端sample上升后再等24tick，并在本窗口内只采一份。最后一份记录的sample与done同时为真，先接收该层再处理done。最多五份非空层，保留原空层坐标；之后sample为假。详见[循环证明](../4q5l/iterative-scanner.md)。它尚不输出完整制造配方或判断可制作性。

## 顶针结构候选

`pin-column-4q5l.spz2bp` 用555平台从目标的一列恢复顶针前态的前四格。输入五份材料/标签与八个控制位；`candidate_valid`只表示单列结构约束通过，输出仍须补第五格、组合其他三列、取得制造证书并核对整图Pin。标签只在保留格之间复制，辅助红C用标签3；编号含义由调用者管理。

`pin-column-iterator-4q5l.spz2bp` 用911平台自动遍历同一单列通路的256个控制字。每阶段156信号tick，复位保持752tick；阶段3的sample窗口发布通过本地约束的四格材料/标签与本轮八位控制字。sample上升后再等24tick，在窗口内只采一次；sample为假时继续等。256轮后exhausted为真，不再重复发布候选。整列当前保守耗时约3小时42模拟分，完整搜索仍需进一步提速。

这两份部件保留原层位，不生成任意候选的原生图形信号，也不把耗尽一列当作目标不可制作。八位覆盖证明、晶体屏障前缀等式、一热标签路由、主副状态与三阶段传播余量见[单列候选证明](../4q5l/pin-column-circuit.md)。

## 顶针像的制造前必要筛选

`pin-image-4q5l.spz2bp`用3871平台同时读取四列keep/extraC控制及顶层C掩码，精确算触顶融合删除，并以来源NPC目标层恢复静止/移动标记。它拒绝同粘连组标记不同、移动格被静止格挡住、移动块成员目标层不同或缺少目标下方支撑。

necessary_pass只表示必要条件通过，仍须制造前态并原生Pin完整比较。全输入保持3904信号tick后读取；没有完成脉冲。第五层NPC不影响本次Pin物理，同一晶体掩码族可先共用筛选。Python取证优先模式已接入同样规则；证明及未检查的F最大性边界见[顶针像筛选](../4q5l/pin-image-constraints.md)。

## 四列及完整顶盖的压缩前态

`pin-source-4q5l.spz2bp`用8788平台，四列分别输入0～19槽号，第五层四格分别输入0空、1Cu、2P、3红C。它输出完整五层材料与标签，覆盖全部规范化顶针输入结构，并检查完整列A及融合/组位移必要条件。Python与电路共用固定模式表；二十槽上界来自组合计数，不是目标枚举。

全输入保持5376信号tick后读取candidate_valid及网格，没有完成脉冲。has_slots表示四列均有单列合法槽；first_slots给出各列最小合法地址，next_slots给出各列下一个合法地址，last_slots表示该次后继将回绕。它们处理列内条件及由邻列目标强制C确定的晶体禁位，使用方式见[合法槽后继](../4q5l/valid-slot-cursor.md)。通过仍须递归制造前态、原生Pin及完整目标比较。独立部件由完整四帧控制器接入游标、F检查和帧回退；范围、唯一性及覆盖证明见[二十槽前态](../4q5l/pin-patterns.md)。

## 六寄存器配方回放

`recipe-processor-4q5l.spz2bp`用443平台接受加工指令包，在六个物品槽中顺序回放。Python配方的`instructions()`或CLI的`--instructions`输出对应包；操作1～10沿用下表，14取无晶体单层基础料。操作消费源槽，结果写入空槽或被消费槽，拒绝覆盖其他物品；无效新请求确认后status=2且物品槽不变。

四象限版复位enable=0、request=0至少800tick，再启用。每个window上升后24tick可读取ack/status并提交下一份翻转请求；整包须在该阶段3开始后96tick以前到达内部接收器输出，保持到下一窗口确认。每阶段168tick、每周期56模拟秒。六槽覆盖当前四象限构造的证明、完整协议和字段见[配方寄存器说明](../4q5l/recipe-registers.md)。它不自动搜索或生成角宏指令，不能单独判定目标可解性。

`recipe-processor-6q5l.spz2bp`为对应的[六象限时序回放器](../6q5l/recipe-processor.md)，453平台，默认独占频道1343000～1345047；阶段168tick、周期56模拟秒、复位至少800tick。其余提交协议相同。它逐树检查六槽预算，没有全部六象限制造树的统一六槽保证；Python将净两格旋转展开为两次原位发令，仍复用同一加工通路。

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
python -m shapez2_tmam.decoder_circuit --channel-base 1006000 --output shapez2_tmam/blueprints/decoder-4q5l.spz2bp
python -m shapez2_tmam.half_circuit --channel-base 1008000 --output shapez2_tmam/blueprints/half-4q5l.spz2bp
python -m shapez2_tmam.scan_circuit --channel-base 1011000 --output shapez2_tmam/blueprints/scan-4q5l.spz2bp
python -m shapez2_tmam.register_circuit --channel-base 1012000 --output shapez2_tmam/blueprints/signal-register.spz2bp
python -m shapez2_tmam.sequential_circuit --channel-base 1013000 --output shapez2_tmam/blueprints/four-phase-clock.spz2bp
python -m shapez2_tmam.iterative_scanner --channel-base 1014000 --output shapez2_tmam/blueprints/iterative-scanner-4q5l.spz2bp
python -m shapez2_tmam.material_half_circuit --channel-base 1016000 --output shapez2_tmam/blueprints/material-half-4q5l.spz2bp
python -m shapez2_tmam.pin_column_circuit --channel-base 1019000 --output shapez2_tmam/blueprints/pin-column-4q5l.spz2bp
python -m shapez2_tmam.pin_column_iterator --channel-base 1022000 --output shapez2_tmam/blueprints/pin-column-iterator-4q5l.spz2bp
python -m shapez2_tmam.recipe_processor --channel-base 1025000 --output shapez2_tmam/blueprints/recipe-processor-4q5l.spz2bp
python -m shapez2_tmam.recipe_processor --quadrants 6 --output shapez2_tmam/blueprints/recipe-processor-6q5l.spz2bp
python -m shapez2_tmam.half_synthesizer --channel-base 1028000 --output shapez2_tmam/blueprints/automatic-half-4q5l.spz2bp
python -m shapez2_tmam.startpoint_circuit --channel-base 1061000 --output shapez2_tmam/blueprints/startpoint-4q5l.spz2bp
python -m shapez2_tmam.startpoint_circuit --s-tail --channel-base 1094000 --output shapez2_tmam/blueprints/s-tail-4q5l.spz2bp
python -m shapez2_tmam.tagged_goal_circuit --channel-base 1127000 --output shapez2_tmam/blueprints/tagged-goal-4q5l.spz2bp
python -m shapez2_tmam.pin_image_circuit --channel-base 1144000 --output shapez2_tmam/blueprints/pin-image-4q5l.spz2bp
python -m shapez2_tmam.pin_source_circuit --channel-base 1194000 --output shapez2_tmam/blueprints/pin-source-4q5l.spz2bp
python -m shapez2_tmam.full_solver_circuit --channel-base 1211000 --output shapez2_tmam/blueprints/full-tail-4q5l.spz2bp
python -m shapez2_tmam.full_solver_circuit --pack --output shapez2_tmam/blueprints/full-tail-packed-4q5l.spz2bp
python -m shapez2_tmam.startpoint_circuit --tagged-goal --channel-base 1161000 --output shapez2_tmam/blueprints/tagged-leaf-4q5l.spz2bp
```

[`Circuit.document`](../circuit.py)在编译时检查每个门的输入数量、输出引用、频道范围、别名组，以及旋转后的建筑实际占地与每个本地输入端口的真实几何来源。默认每门单独使用一块1×1基础平台；`packed=True`按组件实际占地装入3×3大平台，允许刚性旋转和平移，组件间留一格。无线收发器占用3×3×3格，交换门占两格，其余本次所用门占一格。

原生占地、端口来自 `resources.assets`，指纹及端口约定见 [`mari/ports.py`](../mari/ports.py)。格式对应 `BlueprintSerializer`、两种 `BlueprintEntryJsonConverter` 和 `SignalSerializer`；省略图标时 `BlueprintJsonConverter` 使用默认图标。无线时序依据 `SignalChannelRingBuffer.ReadSignal`、`SignalSimulation` 和 `SignalBuffer.TryPopSignal`。

生产编译与静态接线检查不包含门级模拟、游戏导入或运行验证。平台数、频道和状态合同以对应生成 JSON 为准。

[Python 局部制造证书](../synthesis/README.md) · [半形构造证明](../4q5l/compact-inverse.md) · [返回总目录](../README.md)
