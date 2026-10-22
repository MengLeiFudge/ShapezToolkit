# TMAM-BugFix-20210622

这就是此前报告和命令中称为 CTMAM 的机器。名称和日期按用户确认使用，存档 ID 为 `3c4c1c08fc4161406e4353e25f06c4b92e824b48`。

## 文件位置

| 文件或目录 | 内容 |
|---|---|
| [diagnosis.md](diagnosis.md) | 已知漏解、修复方向，以及下载存档和本机存档的区别 |
| `data/unreachable_shapes.txt` | 本机 176 个漏解结构的短代码，每行一个，无标题、无编号 |
| `verification/20261021/CTMAM-differences.csv` | 176 个漏解的编号、终态、输出和冲突统计 |
| `verification/20261021/CTMAM.csv` | 全部 65,536 个编号的历史结果 |
| `verification/20261021/CTMAM-circuit.json` | 当时验证的完整相关电路快照 |

`data/` 和 `verification/` 只保存在本机，不上传。文件中的“漏解”是游戏本身可制作、但这台机器在已验证的输入方式下未还原的结构；不是游戏不允许制作的结构。短代码统一使用无色圆形 `Cu`，表示占用结构，按原结构编号升序排列。

## 当前结论

历史全量结果中，48,432 个可制作结构成功 48,256 个，漏解 176 个。这 176 个都达到错误固定点，相等检查不通过；终态没有导线冲突，也没有瞬时成功或超时。对已有 CSV 做四方向统计，96 个可以通过旋转输入避开失败，80 个在四个方向都失败，后者归为 20 个旋转等价类。

本轮只读比较确认：当前本机存档的 1,176 个门、1,274 个网络、常量、输入输出及 1,537 个初始引脚值与历史电路快照完全一致。176 个短代码由原始 CSV 导出，没有重新运行模拟。

## 命令

```text
python main.py tmam verify --machine BugFix-20210622 --saves "C:\Users\MLJ\AppData\Roaming\shapez.io\saves"
```

`--machine CTMAM` 保留为同一机器的旧名。新报告默认写入本目录的 `verification/<时间>/`。验证需要原始本机存档和上级 `data/shapes/shapes.json` 对照库。

下载的 `Bugfix.bin` 为 1009 格式，本机验证器目前仅接受无模组的 1010 格式；不能直接拿下载文件替换已验证的本机存档。具体静态差异见 [diagnosis.md](diagnosis.md)。原文件均未修改。
