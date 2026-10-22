# TMAM-Nabi-20221128 · Version 7F

这份存档中的 v7f 不能直接认定为能解析全部一代图形。全量电路扫描已经发现：800 个可制作结构没有输出任何加工片段，另有 119 个可制作结构的 `true` 控制标志在进入右侧缓存时丢失。分析针对 `Version 7F` waypoint 附近的正式电路，不包含 `Version 7F Snapshots` 或其他版本。

## 文件

- [verify_v7f.py](verify_v7f.py)：只读提取存档、设置输入、逐 tick 记录片段与标志、核对缓存并生成全量报告。
- [diagnosis.md](diagnosis.md)：输入输出、启动方式、全量结果和已定位的时序问题。
- `verification/v7f-20261022/`：本机本次报告，包含全部 65536 个编号的 CSV、逐 tick 指令、反例短代码和原始游戏代码对照证据，不提交 Git。

本机短代码清单：

- [no_output_shapes.txt](verification/v7f-20261022/no_output_shapes.txt)：800 个可制作但没有输出片段的结构。
- [no_output_all_rotations.txt](verification/v7f-20261022/no_output_all_rotations.txt)：其中 384 个结构旋转四个方向后均无输出。
- [flag_loss_shapes.txt](verification/v7f-20261022/flag_loss_shapes.txt)：119 个发出 `true` 标志但未保存该标志的可制作结构。

这些是已确认问题的清单，不是完整的漏解总表。尚未完整解释加工控制标志，不能用“把所有片段逆序堆叠后不相等”代替完整的失败判据。

## 运行

在 ShapezToolkit 根目录执行：

```text
python main.py tmam verify-v7f --save "C:\Users\MLJ\AppData\Roaming\shapez.io\saves\savegame-0cde894a9373cd6414ee3432224b6658466e3626.bin"
```

需要本机共用的 `shapez1_tmam/data/shapes/shapes.json`。`--workers` 默认为 8，`--max-ticks` 默认为 4096；可用 `--output` 指定尚不存在的新报告目录。默认写入本目录的 `verification/v7f-<时间>/`。

当前输入输出位置绑定已分析存档的 SHA-256；文件发生变化时会拒绝直接套用布局。原始 `.bin` 只读。

命令正常退出表示审计完成，不表示机器通过验收。这里记录的是脉冲指令和缓存，不能套用另外两台机器的“最终稳定图形等于目标”判据，因此入口使用独立的 `verify-v7f` 子命令。
