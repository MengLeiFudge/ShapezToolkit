# 一代 TMAM

这里放一代图形的结构拆解程序、存档电路验证程序、图形数据和验证记录。通用思路见 [logic.md](logic.md)。

## 文件位置

| 文件或目录 | 用途 |
|---|---|
| [xianyu_20221129.py](xianyu_20221129.py) | `XianYu20221129.solve` 求解入口，以及部件加工模板和拼装顺序 |
| [xianyu_20221129_controller.py](xianyu_20221129_controller.py) | `TMAM-XianYu-20221129` 存档的同步控制器状态方程 |
| [tmam_circuit.py](tmam_circuit.py) | 原始存档解码、电路提取和各存档输入输出坐标 |
| [tmam_signals.py](tmam_signals.py) | 游戏信号、切割、旋转、堆叠与拆层语义 |
| [tmam_verify.py](tmam_verify.py) | 电路逐 tick 执行、完整状态周期检测和穷举验证 |
| data/shapes（本机 `data/shapes`） | 历史图形 CSV 与 `shapes.json`；供验证对照，求解不查表 |
| verification（本机 `verification`） | 电路快照、逐项 CSV、汇总结果和具体案例 |

## 求解

在工具箱根目录执行 `python main.py tmam solve SHAPE`，把 `SHAPE` 换成 1..65535 的结构编号。低四位表示底层，层内各位依次对应右上、右下、左下、左上。空图形和空中间层会拒绝；当前接口使用无色圆形表示占用结构。

加 `--events` 可输出指令、模式和重试信号的变化 tick；`--max-ticks` 设置每阶段上限，默认 4096。

在其他 Python 程序中，将工具箱根目录放在模块搜索路径中后调用：

```python
from shapez1_tmam.xianyu_20221129 import XianYu20221129

solver = XianYu20221129()
result = solver.solve(shape, include_events=True)  # shape 是调用方提供的结构编号
```

结果包含 `success`、状态和 tick 数。成功时还包含五个部件位置、对应加工指令、命中的拼装支路和加工树。周期表示控制器重复了完整状态；超时单独报告，不能当作不可制作的结论。求解不读取原始存档或图形数据库。

## 存档验证

需先在本机准备 `data/shapes/shapes.json` 对照库与原始存档。图形数据库和生成的验证记录均不纳入 Git。

```text
python main.py tmam verify --machine XianYu-20221129 --saves "C:\Users\MLJ\AppData\Roaming\shapez.io\saves"
```

`--machine` 可选择 `XianYu-20221129`、`XianYu`、`CTMAM`，支持多个名称。省略时仍验证旧的 `XianYu` 和 `CTMAM`。这些配置绑定已分析的存档文件和布局；并非按任意存档显示名称自动识别。

命令遍历全部 65,536 个结构编号，默认使用 8 个进程；支持 `--workers`、`--max-ticks` 和 `--output`。报告默认写到本目录的 `verification/<时间>/`。每个输入独立恢复保存状态，再关闭开关、更换输入、开启开关，避免前一个输入的状态影响后一个。

只有持续还原目标并通过相等检查才算成功。结果分别记录固定点、周期、超时和无效编码。出现漏解、误报或超时时返回非零退出码，CSV 和汇总仍会保存。验证覆盖拆解与虚拟合成电路；实体工厂的传送带时序与实际出货不在此范围。

## 已有记录与名称

- XianYu-20221129 全量报告（本机 `verification/XianYu-20221129/REPORT.md`）：记录此前全部 48,432 个可制作结构通过，以及 Python 加工树与电路的一致性核对。
- 旧 XianYu 与 CTMAM 报告（本机 `verification/20261021/REPORT.md`）：保留两份旧存档的验证结果和反例。

游戏索引中的 `TMAM-XianYu-20221129` 对应存档 ID `916dcc85ebaf5438a5e23cb79d344e2fc28ef2c8`，也就是此前称作 `TMAM-XianYu2` 的存档。历史 JSON、CSV 和快照中的 `XianYu2` 标签及旧路径保留原始记录含义；说明和当前命令使用日期名称。源码哈希记录的是当时版本，不是此次目录整理后的版本。本次整理未重新运行全量验证。
