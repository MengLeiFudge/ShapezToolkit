# 六槽实体装配

`layout.assemble(count, packet_tag=...)` 生成原生岛蓝图和可序列化的站场接口表。一个地址对应一个实体工段。每段保留六槽直通带、两个操作数入口、加工回带、四角基础料和独立结晶供料。`recipe.replay(target, packets)` 用同一组六字段回放物品，保留两个操作数的顺序、目的槽和被舍弃的半形。回放结束时，唯一活槽须等于目标形状。

## 写入与换单

接口用 `changeover`、`stage_memory`、`stage_writer` 和 `stream_controller` 中的频道常量。上游在虚拟回放成功后发布目标、回放结果、成功信号和长度。实体按 `WRITE_BUS['address']` 收取每个地址的六字段和 `packet_tag`，直到两组回读完成。`LOADED` 表示整份配方写入完成。实体交货以东侧成品带实际经过的图形和数量为准。

| 阶段 | `RUN` | `CLEAN_CONFIRMED` | `ENABLE_FEED` | 操作 |
|---|---:|---:|---:|---|
| 初始化或复位 | 0 | 0 | 0 | 停料并复位工段。等写入总线进入清空相位且两组回读都为空 |
| 装方 | 1 | 1 | 0 | 在空线发布稳定的新目标、回放和配方。等待 `LOADED=1` |
| 生产 | 1 | 1 | 1 | 保持目标和配方。基础料开始进线，匹配目标的实物进入成品带 |
| 排空 | 1 | 1 | 0 | 保持旧目标和配方。停止领料，末端切入废料口，让在途品按旧路径排出 |
| 清空确认后复位 | 0 | 0 | 0 | 从入口选择器下游到成品口检查槽带、支路、缓存和机内。清除仍卡在双输入机器中的单边物料，再允许复位并换目标 |

`CLEAN_CONFIRMED` 由操作方在检查后提供。停料后先排空在途物品。双输入机仍有残料时，选中对应建筑并清空选区内容。游戏的建筑清空操作会调用 `StackerSimulation.ClearContent`，清掉两侧输入、加工位和输出位。使用整岛清空前先隔离需保留的原料与固定色管线。若仍有残料且无法清理，在断开进料后重建该段。收货方也须排空成品过滤器之后的出货带。

## 供货接口

工段 `i` 的装配原点为 `(18i, 0, 0)`，列车车头方向朝北。`assemble` 返回每段车头位置和末端出带坐标。`layout.cargo_ports()` 为配料和制作提供同一份货种、车厢、层和接收行表，车厢从车头后第 1 节起算，层从 0 起算。

| 车种 | 装载 | 配料端接口 |
|---|---|---|
| 单料车 | 所有货厢及占用层保持同一种整片或原色 | 使用 `factory_book` 的同类型车库、装货站和卸货站 |
| 基础料混合车 | 从车头起按 `q2、q3、q1、q0` 重复三节一组。三节分别装 `C/R/S`、`W/空/空`、`r/g/b` | 用 `freight_loader.loading(cargo)` 装指定货，并以 `freight_stage.depot()` 生成编组 |
| 结晶混合车 | 一节流体车，从底层起装 `r/g/b` | 用 `layout.crystal_loading(cargo)` 将指定原色的底层四路装进混合车对应层。各换装板接连贯通的单向铁路线 |

每个图形货层目前在对应角料台使用一条带。每个原色货层有四路独立管，供直通及不同混色支路。不同管路的剩余运力须按实际接管位置分配。车站和装卸方向应核对至每一个使用的端口。

## 一满带核算

先将通过的 `Production` 交给 `capacity.demands`，取得每个加工路径和每节车每层每行的单位成品需求。`check_capacity` 用成品带速乘需求量得到每秒所需件数或升数。输入每种机器、物品带路径和染料管路径的持续实测速率。各路径使用同一个速率参数时，取该类路径的实测下限。将每条站场缓冲每趟实际收到的货量填入 `TrainDelivery`，除以平均到站间隔得到该路供货率。供给量按实际卸货计，库存只用于缓冲。

每台机器和每条进料路径的供给率均须满足每秒需求。对已有供给记录，`parallel_lines` 取各需求除以单线供给率并向上取整的最大值，得到所需的独立生产线数量估算。计算依赖每条线具有独立供料和处理能力，合流后的出带也须达到目标带速。缺测的速率或零供给会使并联数量无法确认。多线的频道与站场分配、实机供料、换单和持续一满带一起验收。

## 两份配方共用一条工道

在仓库根目录分别生成三册。各册的 JSON 与该册蓝图放在同一目录。省略 `--output-dir` 时在内存中验证生成结果。

```bash
python -m shapez2_tmam.circuits.factory_assembly.books physical --belt-rate 3 --output-dir 验收/实体
python -m shapez2_tmam.circuits.factory_assembly.books proportioning --output-dir 验收/配料
python -m shapez2_tmam.circuits.factory_assembly.books trains --output-dir 验收/通用火车
```

| 分册 | 生成内容 |
|---|---|
| 实体 `physical` | 48 工段线与固定双订单发送器，含地址、原料接收口、用料和运力表 |
| 配料 `proportioning` | 七种基础料换装位、三种结晶原色换装位、两种混合车及装载表 |
| 通用火车 `trains` | 图形和流体单料车各自的车库、装货站和卸货站 |

| 订单 | 配方来源 | 工段 | 每件成品用料 |
|---|---|---:|---|
| `stack` | 五层逐层堆叠，沿用 `Builder.noncrystal` | 9 | C 2 件，R、S、W 各 1 件 |
| `pin-crystal` | [尾部顶针配方](../../examples/json/4q-required-tail-pin.instructions.json)，含两次结晶和末次顶针 | 48 | C 77 件，红染料 160 升 |

两份订单共用同一张 48 工段蓝图，最终产物都在槽 0。纯堆叠订单只写入地址 0–8，其余 39 段从清空状态直通。离线生成检查区块占地、跨台连接、站场方向、使用的装卸层位和最终出带。生成的 JSON 在 `interfaces.stations` 标出每段两个车头位置，`interfaces.load` 列出统一装载表，`orders` 保存目标、指令和每条路径的每件用量。`paths[].stage` 从 0 起算。列车货量按 `station`、`wagon`、`layer`、`row` 定位。

固定发送器按当前地址发布六字段，再读取同一写入总线。所有字段和地址与订单匹配后，才在 `sender.write.packet_tag` 回送地址。工道保持当前地址到 `sender.write.ack` 应答。最后一笔确认后，`sender.control.loaded` 表示整份配方已经写入。两份固定配方在导出前由 Python 完整回放，实机测试可直接使用该发送器。

## 接入 Solver4 的成功配方

在仓库根目录生成指令 JSON，再用同一个验收入口编译实体工道和固定发送器。

```bash
python -m shapez2_tmam.synthesis --complete --instructions 'CucrCuCu' > solver4-order.json
python -m shapez2_tmam.circuits.factory_assembly.acceptance --recipe solver4-order.json --compact --output solver4-acceptance.spz2bp
```

`--recipe` 读取带 `status: solved` 的四象限五层指令 JSON。导出先按六槽消费语义回放，再按指令数生成实体工段。每条指令的六个字段原样进入发送器。邻接 JSON 中的 `stage_capacity` 给出容量，`interfaces.stations` 给出停靠点，`interfaces.load` 给出车厢层位，`orders.solver4.paths` 给出每件所需的供料路径。`--compact` 仅安装该订单用到的供料站。

也可把同一份 JSON 分别交给三个分册命令。实体册使用精简站场，并保留单带运力表。

```bash
python -m shapez2_tmam.circuits.factory_assembly.books physical --recipe solver4-order.json --output-dir 验收-订单/实体
python -m shapez2_tmam.circuits.factory_assembly.books proportioning --recipe solver4-order.json --output-dir 验收-订单/配料
python -m shapez2_tmam.circuits.factory_assembly.books trains --recipe solver4-order.json --output-dir 验收-订单/通用火车
```

实体册的 `interfaces.load` 与配料册的 `load` 使用同一张装载表，车厢和层位保持原有编号。配料册为实际用到的货种生成对应换装站，区分四角备料和工道结晶。通用火车册按需生成图形或流体车站，`cargo` 将各货种映射到 `shape` 或 `fluid` 的车库、装货站及卸货站模板。在单料环线上为每种货各用一套模板。省略 `--recipe` 时，三个命令生成前一节的双订单验收分册。

实机按下节先清空工道，在 `sender.select.channel` 发布整数 `1` 选择这份配方。地址回读、写入应答、装方结束和领料放行沿用同一组信号。

## 实机接入与验收

1. 导入验收工道。按 `interfaces.stations` 对接基础料车和结晶车。单料车先卸入配料端，再按 `interfaces.load` 装混合车。逐个核对使用的车厢、层位和行的货种、流向与制作端接收到的实物。
2. 保持 `RUN`、`CLEAN_CONFIRMED` 和 `ENABLE_FEED` 为 0，确认工段已复位。在 `sender.select.channel`（默认 `1640047`）发布整数 `1` 选择 `stack`。订单发送器会设置目标、配方长度和回放成功信号。
3. 按[写入与换单](#写入与换单)放行装方，等待 `LOADED=1` 再启用领料。从 `interfaces.output` 指定的东侧带口验收，记录收到的目标图形、稳定出货时刻和成品数。
4. 停料并保持旧订单，观察废料口并检查全线在途品。清除双输入机两边的残留，排空槽带、加工支路和成品过滤器之后的出货带。复位并确认写入状态清空，再在 `sender.select.channel` 发布整数 `2` 选择 `pin-crystal`。按同一出货口记录新成品，确认换单后出货带只出现新目标。
5. 记录游戏版本、带速档位、每种加工机和管带的持续速率、每个有效卸货行的实际到货量和到站间隔。各订单从启动缓冲稳定后开始连续观察，覆盖各有效停靠点的多个到站周期。用成品数除以游戏内观察时间计算出货率，并检查供料库存是否持续下降。

设目标带速为 `B` 件/秒。两份订单的每个在用工序及单带路径都须保持 `B` 件/秒的成品当量。顶针结晶订单的两处工道结晶机与各个在用制针结晶机分别需要 `20B` 升红染料/秒。该订单全线合计需要 `77B` 件 C 整片/秒与 `160B` 升红染料/秒。默认 `--belt-rate` 为 1，便于按比例换算。示例命令里的 3 仅用于演示完整带速的填法，验收按实际档位填写。堆叠机的持续速率取决于游戏的加工延时和带速配置，还受上下料和输出阻塞影响。

给实体册传入 `--measurements` 可填写持续加工率、实测卸货量和到货间隔。记录格式如下。`base` 是基础料混合车，`crystal` 是结晶混合车。速率和货量支持整数、小数或分数字符串。各订单只检查实际使用的工段与端口。

```json
{
  "rates": {"belt": "3", "pipe": "100", "StackerStraight": "2"},
  "deliveries": [{
    "stage": 0, "station": "base", "interval_seconds": "10",
    "payload": [{"wagon": 10, "layer": 0, "row": -12, "amount": "20"}]
  }]
}
```

`capacity.<订单>.loads` 按车厢和层汇合需求。`paths` 仍逐条带或管列出需求。若某路每秒需求为 `R`，实测每趟收到 `Q`，到站间隔 `T` 秒，则每趟至少需 `R×T`，最大到站间隔为 `Q/R`，每分钟至少到站 `60×R/Q` 次。同站各路取最严格的到站要求。`lowest_measured_capacity` 给出已记录的最低供给／需求比。`unknown_capacity_checks` 为 0 时才能据此判定最慢工段。持续一满带以实机验收第 5 步的记录为准。

## 集成所需源码

三个物流快照包含本目录的实现与说明。干净检出须同时包含下列工段依赖以及 `mari/ports.py` 中的 `BeltFilter` 端口定义。

| 用途 | `circuits/` 下的文件 |
|---|---|
| 六槽工段 | `production_stage.py`、`production_line.py`、`slot_streams.py`、`slot_stream_ports.py`、`work_lane.py`、`work_lane_ports.py` |
| 写入和工段联通 | `stage_memory.py`、`stage_writer.py`、`stream_controller.py`、`layer_factory.py`、`layer_controller.py`、`layer_packet.py`、`scaffold_controller.py` |
| 四角备料 | `assembled_stage.py`、`angle_prep.py`、`layer_supply.py`、`quarter_gather.py`、`quarter_join.py`、`stock_selector.py` |
| 货运装卸 | `freight_stage.py`、`freight_loader.py`、`wagon_intake.py`、`intake_ports.py` |

验收例沿用已入库的[尾部顶针指令包](../../examples/json/4q-required-tail-pin.instructions.json)。总物料清单若与验收线并用，`synthesis/production_bill.py` 的占位整片和制针染料也应采用装载表里的固定 C 片和红色支管。

## 工段容量与共用供料

当前装配让每个配方地址占一个工段。两份订单中较长的一份有 48 条指令，因此固定双订单示例需要 48 段。两份订单的地址 `0、1、5、7` 都领取基础单层，地址 `2、6、8` 都走堆叠。这七段可随换单重用同一路径，基础料选择器按当前订单领货。

```bash
python -m shapez2_tmam.circuits.factory_assembly.acceptance --compact --output six-slot-compact.spz2bp
```

精简蓝图安装两份订单地址并集所需的 21 个基础料停靠点与 2 个结晶停靠点。地址 3 随订单在接收基础单层与结晶之间切换，因此保留两个停靠点。两处结晶地址为 3 和 32。实际站位以 JSON 的 `interfaces.stations` 为准。只接表中给出的 `base_head` 和 `crystal_head`。示例仍按每个地址保留加工工段和槽带，内置发送器供这两份固定订单使用。

| 动态工段预算 | 依据 | 通用布置的岛项目数估算 |
|---|---|---:|
| 616 | [理论制造树上界](../../docs/proofs/02-four-quadrants.md#s02-06-h7)。要用这个容量，输出器须保证每次都选到不超过 616 条的制造流 | 48,666 |
| 971 | [既有四帧程序的保守发包上界](../../docs/proofs/08-circuits.md#s08-09)。也对应当前工段地址及写入门控上限 | 76,711 |

估算按通用布局每段含 75 个岛项目、相邻段间 4 个六槽桥、全线共 6 个出口及控制项目计算。动态整厂的实际工段容量取编译后发送器可能发出的最大物理指令数，统计基础料与加工指令，扣去控制行及不发指令的分支。发送器上界确认后，再用 `layout.assemble` 的通用配置生成并核对该规模的蓝图。

合并同货供给时，先列出同一订单下同时取料的所有支路。目标带速为 `B` 件/秒时，支路每件成品需求乘 `B` 后在同一分流干线上求和。换单后两份订单互斥，共用干线按两份订单中的最大合计需求定容。每条带或管用持续实测速率，列车还要满足每一层每一行的实际卸货量除以到站间隔。缓冲要能支撑两个到站批次之间的领料。相同货种可在上游共用装载站或车队，下游须有足够的并行带路及分流。

例如，顶针结晶订单两处工道结晶合计需要 `40B` 升红染料/秒，四角备料中的制针另用 `120B` 升/秒。若结晶与制针支路共用上游红染料干线，持续供货需达到 `160B` 升/秒，并分别送达每个活跃卸货行。若把 77 路 C 整片需求上收至同一个上游干线，持续供给需 `77B` 件/秒。同档带的单路持续速率等于 `B` 时，至少占用 77 路带。若每个同货车厢层的四路都能并行有效卸货，还至少需要 20 个这样的满载层位等效供给。工道精简示例继续使用各地址的车站、固定车厢位置和独立缓冲。实机验收按各路到货数据确定合并能力。

参见[四象限五层整厂约定](../../blueprints/整厂约定.md)。
