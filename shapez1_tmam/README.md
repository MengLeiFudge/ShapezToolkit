# 一代 TMAM

每台已经分析过的机器拥有自己的目录，代码、说明和本地记录放在一起。根目录仅放共用的存档提取、信号运算、验证执行器和图形对照库。

| 目录 | 机器与内容 |
|---|---|
| [bugfix_20210622](bugfix_20210622/README.md) | TMAM-BugFix-20210622，旧名 CTMAM；漏解短代码、故障分析和历史验证记录 |
| [xianyu_20221129](xianyu_20221129/README.md) | TMAM-XianYu-20221129，旧名 XianYu2；Python 拆解器、控制器、通用思路和验证记录 |
| [xianyu_legacy](xianyu_legacy/README.md) | 更早的 TMAM-XianYu；历史电路和漏解记录 |
| `comparison/` | 本机跨机器的比较报告和共同反例，不上传 |
| `data/shapes/` | 本机共用图形 CSV 与 `shapes.json` 对照库，不上传 |

Nabi 存档尚未在本工具中建立验证配置，不与旧 XianYu 混用。

## 共用代码

- [tmam_circuit.py](tmam_circuit.py)：只读解码存档、提取电路，以及各机器输入输出坐标。
- [tmam_signals.py](tmam_signals.py)：游戏信号和图形操作语义。
- [tmam_verify.py](tmam_verify.py)：逐 tick 执行、完整状态周期检测与批量验证编排。

求解入口和通用说明见 [XianYu-20221129](xianyu_20221129/README.md)。它不需要原始存档或对照数据库。

## 存档验证

在工具箱根目录执行：

```text
python main.py tmam verify --machine BugFix-20210622 --saves "C:\Users\MLJ\AppData\Roaming\shapez.io\saves"
python main.py tmam verify --machine XianYu-20221129 --saves "C:\Users\MLJ\AppData\Roaming\shapez.io\saves"
```

需要自行准备原始存档和 `data/shapes/shapes.json`。目前端口与格式支持限定为无模组的一代 1010 存档，输入输出坐标绑定已分析的布局，不按任意显示名称自动匹配。

`--machine` 可以选择多个名称：`BugFix-20210622`、`XianYu-20221129`、`XianYu`；`CTMAM` 是 BugFix 的兼容别名，不能与新名重复选择。省略时仍选择旧 XianYu 和 BugFix。旧 XianYu 原文件目前只剩备份，使用默认组合前需准备相应 `.bin`，或显式选择其他机器。

每台机器的新报告默认保存在自身的 `verification/<时间>/`。使用 `--output 目录` 时，报告写入该目录下的各机器子目录；控制台返回汇总和实际路径。每台目录独立保存电路快照、分段 CSV、合并 CSV 和 `summary.json`。

命令遍历全部 65,536 个结构编号，默认 8 个进程；`--workers` 可设置 1..32，`--max-ticks` 设置每阶段上限，默认 4096。每个输入独立恢复保存状态，再关闭开关、换输入、开启开关，保持反馈和冲突语义。

只有持续还原目标并通过相等检查才算成功。固定点、周期、超时和非法编码分别记录，超时不证明不可制作。出现漏解、误报或超时时返回非零退出码，逐项结果仍保留。验证覆盖拆解和虚拟合成电路，不包含实体传送带、吞吐和出货。

## 本机资料

各机器的 `data/`、`verification/` 以及共用对照库和比较报告都被 Git 忽略。历史文件中的旧名称、存档路径和源码哈希保留当时含义；机器日期以已确认的名称为准，不把报告生成日期当作存档创建日期。
