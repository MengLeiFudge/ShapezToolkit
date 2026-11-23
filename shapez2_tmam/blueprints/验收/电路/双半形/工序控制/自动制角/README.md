# 自动制角与双半形写入

将 `corner-jobs`、`pair-writer` 和 `pair-corner-stream-bridge` 与[共用前缀闭包](../../../顶针逆推/dual-source-closure.md)合装。闭包保留所选切向、四列高度和原色行。配方从槽 0 开始，依次造四角、拼半形、恢复整形和追加原色尾料。三块板组分别使用 21、86 和 47 块平台。闭包另占 101 块平台。

| 接点 | 频道 | 作用 |
| --- | --- | --- |
| 闭包启动和模式 | 1703000～1703002 | 原图取模式 0，封存候选取模式 1。可选顶盖模式只把已选中的顶格留在前缀内。 |
| 闭包选择结果 | 1703004、1703005 | 等待选中切向或两向耗尽。 |
| 双半形运行和完成 | 1701695、1701699 | 选中切向后启动。四列、原色行和模式保持到完工。 |
| 六字段和候选地址 | 1680001～1680007 | 同址确认后推进，槽号 0 是有效信号。 |
| 写入侧 | 1640000、1640011～1640013、1640030 | 地址、请求、复位、确认和运行。 |

制角排程用 `1702052/1702053` 接主确认器。子步骤用 `1701636～1701638` 接共用写入确认器。四角复用紧柱、释放和逐层追加。槽 3～5 在制角期间作临时槽，造完一角后归还。先对整份配方做[虚拟回放](../../../配方回放/virtual-recipe-replay.md)，成功后可用同一套制角和拼合电路给实体写入。

离线原生回放按 12 信号刻的无线模型运行，由模型确认写入地址。接共用前缀闭包时，直接落角和悬空落角样例分别生成 87、175 道，槽 0 等于目标。制角板从闭包输出的四份完整材料字裁剪当前列。直接落角样例的闭包高度为 `3、3、0、3`，独立输入高度 `3、3、3、3` 时生成 94 道。悬空样例走通用的锚柱和支撑交接。145 道专用实体页签使用经独立优化的固定配方，按各自的工序表装方。游戏内时序和持续产量待验。

```bash
validation=shapez2_tmam/blueprints/验收/电路
python -m shapez2_tmam.circuits.compile_pair_writer \
  --circuits "$validation/双半形" --corner-inputs \
  --closure "$validation/顶针逆推/dual-source-closure.json" --output-dir corner-writer
python -m shapez2_tmam.circuits.compiler_backend.pair_corner_bridge \
  --writer corner-writer/pair-writer.spz2bp --dense-clock corner-writer/dense-stream-clock.json \
  --output corner-writer/pair-corner-stream-bridge.spz2bp
```
