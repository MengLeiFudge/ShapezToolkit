# 四象限五层验收蓝图

这套蓝图用于同一条 48 工段生产线的两份订单。`stack` 是五层纯堆叠，`pin-crystal` 包含结晶和尾部顶针。实体册带固定发送器，通过频道 `1640047` 的整数 `1` 或 `2` 选单。

| 分册 | 图纸 | 接口 |
|---|---|---|
| 实体 | 48 工段、发送器与单带出口 | [完整站场及用料](实体/physical.json) |
| 实体精简版 | 同一条工道，保留两份固定订单所需的 21 个基础料站和 2 个结晶站 | [精简站场及用料](实体/six-slot-acceptance-compact.json) |
| 配料 | 基础料与结晶染料的换装站、两种混合车库 | [货种、车厢、层位及接口](配料/proportioning.json) |
| 通用火车 | 图形和流体单料车的车库、装货站、卸货站 | [装载类型及方向](通用火车/trains.json) |
| 电路 | 按原层号读取目标的两层 | [复位、选择与采样](电路/原层读取/read-target-rows.json) |
| 电路 | 四列逐层堆叠前缀扫描 | [复位、行输入和采样时序](电路/堆叠前缀/stack-prefix-scan.json) |
| 电路 | 筛选覆盖必要晶体分量的顶盖 | [顶盖、接触集及通过信号](电路/顶盖筛选/cap-covers-required.json) |

单料车把同一种货物送往配料站。配料站按装载表把每种货物放入混合车的指定层，再由混合车向制作工段供货。同一车厢每层的带或管使用同一种物料。游戏内按坐标接轨、装方、开料和换单，验收时记录满带出货和卸货量。实机持续产量待测。

生成命令、运行顺序和测量格式见[六槽实体装配](../../circuits/factory_assembly/README.md)。整厂接口见[蓝图约定](../整厂约定.md)。

原层读取电路的 `initial_remaining` 接目标图形，`initial_top`、`initial_below` 为空。`item0` 至 `item4` 对应原第五层到第一层。填写 `1` 的层位写入 `result_top`，填写 `2` 的层位写入 `result_below`，其余填写 `0`。到采样时刻且 `done=1` 后读结果，所选层原本为空时输出空信号。

前缀扫描电路接受四列初始前缀高度和五份已编码的行。每轮从同一份旧高度计算四列，依次处理第五层到第一层。电路与实体订单分别验收，实体册当前由固定发送器供给配方。

```bash
python -m shapez2_tmam.circuits.compile_stack_scan --read-rows --channel-base 1700300 --output read-target-rows.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --channel-base 1700200 --output stack-prefix-scan.spz2bp
```
