# TMAM-XianYu-20221129

原名 XianYu2，存档 ID 为 `916dcc85ebaf5438a5e23cb79d344e2fc28ef2c8`。这里放该机器的 Python 转录、通用拆解说明和本机验证记录。

| 文件 | 内容 |
|---|---|
| [solver.py](solver.py) | `XianYu20221129.solve`、七种制件模板、四种拼装顺序和加工树 |
| [controller.py](controller.py) | 存档的同步状态方程，保留初始状态、延迟、反馈与冲突 |
| [logic.md](logic.md) | 用自然语言说明通用拆解思路和代码对应关系 |
| `verification/20261022/` | 本机全量记录，包含 `REPORT.md`、电路快照、CSV 和独立对照结果；不上传 |

在工具箱根目录执行：

```text
python main.py tmam solve SHAPE
python main.py tmam solve SHAPE --events
python main.py tmam verify --machine XianYu-20221129 --saves "C:\Users\MLJ\AppData\Roaming\shapez.io\saves"
```

把 `SHAPE` 换为结构编号。编号为 1..65535，低四位表示底层，层内位依次为右上、右下、左下、左上；拒绝空图形和空中间层。当前接口以无色圆形表示角块占用结构。

程序调用：

```python
from shapez1_tmam.xianyu_20221129.solver import XianYu20221129

solver = XianYu20221129()
result = solver.solve(shape, include_events=True)
```

求解不读取原始存档或图形数据库。返回成功状态、固定点/周期/超时分类和 tick 数，成功时还返回部件、指令、拼装支路与加工树。超时不能当作不可制作结论。`--events` 输出指令、模式和重试信号的变化 tick；`--max-ticks` 默认 4096。

已有全量记录覆盖 65,536 个编号，其中全部 48,432 个可制作结构通过。历史文件中的 XianYu2 标签与源码哈希保留当时含义。此次按机器归类没有改变算法，也没有重新执行全量验证。

共用执行器、信号规则及报告参数见 [上级 README](../README.md)。
