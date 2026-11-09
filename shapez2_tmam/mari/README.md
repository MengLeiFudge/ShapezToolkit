# Mari 四象限五层 TMAM 的 Python 模型

本目录把 Mari 主控的实际接线写成可追溯的 Python 组合模型：固定目标和候选编号，计算虚拟重建、四个角、五个 Hybrid 载荷及 51 路工厂指令。原机有六种候选；程序按编号从小到大选择匹配项。

**原包默认目标直通配置下，六候选算法已被证明不全覆盖。** [整层空隙反例](../research/proofs/09-sources.md#s09-03)给出一个合法可制作目标，并从接线与操作规则统一排除六条候选路径。模型保留原机规则。`matched` 仅表示虚拟匹配；`no_candidate` 不表示目标不可制作。完整范围见 [Mari 调查记录](../research/proofs/09-sources.md#s09-01)。

## 使用

使用 Python 3.10 或更新版本，无第三方依赖。在仓库根目录调用：

```text
python main.py tmam2 solve CuCuCuCu
python main.py tmam2 solve --iteration 3 CuCuCuCu
python main.py tmam2 solve -- --Cu----
```

图形代码以 `--` 开头时，用独立的 `--` 结束选项解析。以上是调用方式，未作为运行通过的案例报告。

输入保留普通形状、颜色、顶针、晶体和空中间层；目前支持四象限、1～5 层，部件为 `C/R/S/W/c/P`，颜色为 `u/r/g/b/c/m/y/w`。语法合法不代表可制作；全空结果在内部用 `None` 表示。

输出字段：

| 字段 | 含义 |
|---|---|
| `status` | `matched`：虚拟匹配；`mismatch`：指定的单个候选不匹配；`no_candidate`：六候选均不匹配 |
| `iteration` | 被计算或选中的候选编号，1～6 |
| `target`、`result` | 输入目标和虚拟重建结果 |
| `parts` | 四个角、五个 Hybrid 载荷、交换方向及 claw 顶针控制 |
| `commands` | 51 个发射器的位置、频道和载荷；空信号与 Conflict 分开表示 |

无匹配项时退出码为 1，匹配时为 0。指定单个候选时，即使它不匹配，也保留该候选的部件与指令供分析。

Python 调用方式：

```python
from shapez2_tmam.mari import Mari, Shape

machine = Mari()
target = Shape.from_key("CuCuCuCu")
answer = machine.solve(target)
one_candidate = machine.candidate(target, 3)
# inspect 的坐标为 (平台零起始索引, X, Y, L)，返回该建筑的全部输出端。
intermediate = machine.inspect(target, 3, ((79, 8, 2, 0),))
```

`candidate`、`solve` 和 `inspect` 的 `save_flood_color` 默认值为 `True`，对应原包的 Claw Flood Color Saving 开关。求值是本地计算，不连接或修改游戏。

## 实现层次

| 文件 | 职责 |
|---|---|
| [shapes.py](shapes.py) | 对照游戏 `ShapeLogic` 和 `ShapeOperation*` 翻译物理操作，保留晶体融合、组下落、顶破和截高顺序 |
| [signals.py](signals.py) | Null、Conflict、整数、颜色和图形信号；同线合并、条件门、比较门及虚拟加工器 |
| [ports.py](ports.py) | 从本机游戏资源读取并核对的 38 类主控建筑端口定义 |
| [blueprint.py](blueprint.py) | 校验原包指纹，恢复几何接线和四处短距端口竞争，提取组合方程 |
| [equations.json](equations.json) | 原蓝图导出的 28,097 个具名节点、30,703 个输出槽及观察端，不是目标答案数据库 |
| [assembly.py](assembly.py) | 将 P80 最终拼合写成四角交换、可选顶针和五级堆叠的直接表达式 |
| [solver.py](solver.py) | 按拓扑顺序计算候选并选取最小成功编号，返回部件和指令 |

方程每个节点保留 `site`、`op`、`config`、`inputs`、`outputs`。一个输入端可有多个驱动源，先按游戏规则合并；无驱动输入是 Null，不会自动补成 0。坐标中的平台编号是原蓝图 `BP.Entries` 的零起始索引，不是用户放置后的世界坐标。

拆层和分析器是信号操作。即使它们产生某个多层图形，也不能把该信号当作合法实体原料。`parts` 目前是拆解记录，不是从基础输入开始的完整制造证书。

## 组合边界

模型保留主控的六候选函数，使用以下边界：

- 目标取自 P60 的处理后目标母线。原包 `Pin For Gap Replacement` 关闭时，稳定状态下它等于输入目标。开启该开关后的反馈预处理未纳入模型。
- 候选编号固定为 1～6。成功记录的最小编号优先级保留；游戏时钟、反馈寄存器、目标切换及采样延迟未纳入模型。
- 为了返回指令，计算时把 `Update Factory` 设为 1，得到开启更新时会发送的数据。原包该开关是关闭的。
- 下游收到 Null 可以保留旧指令；收到 Conflict 才清空。因此关闭更新不能解释成停机或清空工厂。

P80 的直接拼合表达式与逐门结果在求解时作一致性检查。两者使用相同的图形物理实现；这一检查不替代与游戏的等价性证明。

## 提取与证据

程序附带方程源，日常求值不需要原始压缩包。若要从原件重新提取：

```python
from pathlib import Path
from shapez2_tmam.mari.blueprint import export

export(Path("shapez2_tmam/data/group_files/Mari的TMAM.zip"),
       Path("shapez2_tmam/mari/equations.json"))
```

提取只解码蓝图和分析连线，不执行图形加工。仅接受 SHA-256 为 `573cfd23dcd0149fd77279ce86287f19c04e1c3485d87b1a9b27ee4aaeeb89cd` 的原包；更换蓝图时需重新核对边界坐标和竞争配对。

已完成的静态检查包括：端口定义对应、核心拓扑无环、输出引用完整，以及 51 路下发频道与工厂接收接口对应。没有运行目标图形、功能测试、全量枚举或游戏。[41 项角模板表](../research/proofs/09-sources.md#s09-02)记录局部分类；[整层空隙反例](../research/proofs/09-sources.md#s09-03)记录合法制造树、输入拆层接线及六候选排除证明。
