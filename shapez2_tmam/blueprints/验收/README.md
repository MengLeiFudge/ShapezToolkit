# 四象限五层验收蓝图

这套蓝图用于同一条 48 工段生产线的两份订单。`stack` 是五层纯堆叠，`pin-crystal` 包含结晶和尾部顶针。实体册带固定发送器，通过频道 `1640047` 的整数 `1` 或 `2` 选单。

| 分册 | 图纸 | 接口 |
|---|---|---|
| 实体 | 48 工段、发送器与单带出口 | [完整站场及用料](实体/physical.json) |
| 实体精简版 | 同一条工道，保留两份固定订单所需的 21 个基础料站和 2 个结晶站 | [精简站场及用料](实体/six-slot-acceptance-compact.json) |
| 实体 | 固定两步订单，核对整组提交及复位 | [样件接口](实体/two-step-sender.json) |
| 配料 | 基础料与结晶染料的换装站、两种混合车库 | [货种、车厢、层位及接口](配料/proportioning.json) |
| 通用火车 | 图形和流体单料车的车库、装货站、卸货站 | [装载类型及方向](通用火车/trains.json) |
| 电路 | 按原层号读取目标的两层 | [复位、选择与采样](电路/原层读取/read-target-rows.json) |
| 电路 | 四列逐层堆叠前缀扫描 | [复位、行输入和采样时序](电路/堆叠前缀/stack-prefix-scan.json) |
| 电路 | 筛选覆盖必要晶体分量的顶盖 | [顶盖、接触集及通过信号](电路/顶盖筛选/cap-covers-required.json) |
| 电路 | 无晶体路线的原图稳定性和回放 | [稳定性判定](电路/纯堆叠/direct-stability.json) · [五轮扫描](电路/纯堆叠/direct-stack-scan.json) |
| 纯堆叠 | 动态制单、九工段实体、火车配料与一带出口 | [纯堆叠各分册与接线](电路/纯堆叠/README.md) |
| 电路 | 从原图提取一列并检查列 A | [材料读取](电路/双半形/read-column.json) · [列 A 判定](电路/双半形/read-column-admissible.json) |
| 电路 | 生成角的晶下落点参数和助手柱 | [落点参数](电路/双半形/corner-gap.json) · [助手柱](电路/双半形/corner-helper.json) |
| 电路 | 从原图检查两列半形的支撑 | [虚拟半切稳定性判定](电路/双半形/half-stability.json) |
| 电路 | 从已取出的原单层读取 q0 格及原色 | [原单格读取](电路/双半形/read-labeled-corner.json) |
| 电路 | 直接释放角的前态与外侧锚料 | [最高晶体层](电路/双半形/corner-highest-crystal.json) · [逐层原料](电路/双半形/simple-corner-source.json) |
| 电路 | 顶破角的前态与辅助锚柱 | [逐层原料](电路/双半形/pin-corner-source.json) · [近锚和远侧顶针柱](电路/双半形/pin-corner-anchors.json) |

单料车把同一种货物送往配料站。配料站按装载表把每种货物放入混合车的指定层，再由混合车向制作工段供货。同一车厢每层的带或管使用同一种物料。游戏内按坐标接轨、装方、开料和换单，验收时记录满带出货和卸货量。实机持续产量待测。

生成命令、运行顺序和测量格式见[六槽实体装配](../../circuits/factory_assembly/README.md)。整厂接口见[蓝图约定](../整厂约定.md)。

原层读取电路的 `initial_remaining` 接目标图形，`initial_top`、`initial_below` 为空。`item0` 至 `item4` 对应原第五层到第一层。填写 `1` 的层位写入 `result_top`，填写 `2` 的层位写入 `result_below`，其余填写 `0`。到采样时刻且 `done=1` 后读结果，所选层原本为空时输出空信号。

前缀扫描电路接受四列初始前缀高度和五份已编码的行。每轮从同一份旧高度计算四列，依次处理第五层到第一层。电路与实体订单分别验收，实体册当前由固定发送器供给配方。

纯堆叠电路的目标输入为 `1600000`。稳定性判定板同时转发目标和初始通过位。`initial_replay` 留空。按接口表启动五轮扫描，待 `done=1` 后再采样。装方信息板将实际回放与目标比较，通过后才发布配方长度和回放结果。

列读取每次处理 `q0`。将待查列旋转到 `q0`，原图接 `initial_remaining`，`initial_word` 留空，`initial_height` 置 5。五轮后输出保留全部原层位的材料图形，其中 `Cu`、`Ru`、`Su`、`Wu` 依次表示空、普通格、针和晶体。判定与落点两块板共用材料频道。等读取器到采样时刻且 `done=1` 后，再按各接口表等满保持时间。`column_a=1` 时，`crystal` 和 `landing` 给出晶下间隙的原层号，从 0 起算。无间隙时两者为 `-1`。`needs_pin=1` 表示该落点须走顶破路线。换列前重新复位。

半形支撑检查的图形只占 `q0/q1`。把它接入 `target`，等满接口表的保持时间后读 `result`。虚拟半切后图形与输入相等时输出 `1`。含晶体半形还要对每列分别检查列 A。

直接释放的原料板接收正在处理的原格、落点层的原格及其层号。列 A 通过且 `needs_pin=0` 时，`main` 给出该层的主列前态，`far` 给出外侧锚柱该层材料。原色由单格读取模块保留。

顶破路线的原料板读取原目标的上一层格、落点原格、地面原格与当前层号，输出截去顶层前的主列格及初次底部补晶使用的远柱格。近锚和远侧顶针柱由同一组落点参数生成，输出统一在 q0。后续支撑交接和最终顶破尚需接到工序控制。

```bash
python -m shapez2_tmam.circuits.compile_stack_scan --read-rows --channel-base 1700300 --output read-target-rows.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --channel-base 1700200 --output stack-prefix-scan.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --check-direct --channel-base 1700450 --output direct-stack-scan.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/half_support.py \
  half_is_stable --channel-base 1700600 --output half-stability.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --read-column --channel-base 1700560 --output read-column.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/column_scan.py \
  --field crystal=column_gap_crystal --field landing=column_gap_landing \
  --field needs_pin=column_gap_needs_pin --input-channel word=1700566 \
  --output-channel crystal=1700577 --output-channel landing=1700578 \
  --output-channel needs_pin=1700579 --output corner-gap.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/column_scan.py \
  --field helper=corner_helper_column --input-channel crystal=1700577 \
  --input-channel landing=1700578 --input-channel suspended=1700579 \
  --output-channel helper=1700587 --output corner-helper.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/shape_methods.py \
  read_labeled_corner --channel-base 1700620 --output read-labeled-corner.spz2bp
```
