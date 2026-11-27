# XianYu-20221129

以可追溯的存档方程复现部件选择，由 Python 加工树核对制件和拼装。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 核对原机寄存器 | [controller.py](controller.py) 的 `INITIAL`、`CONSTANTS` | 保存时状态、常量覆盖、坐标和输出索引 |
| 核对器件连接 | [controller.py](controller.py) 的 `EQUATIONS` | 元组列出一个输入网络的全部信号提供者 |
| 运行拆解 | [solver.py](solver.py) 的 `build_controller`、`XianYu20221129.solve` | 复位状态、目标切换、部件寄存器与事件 |
| 解释加工指令 | [solver.py](solver.py) 的 `decode_recipe`、`Plan` | 载荷、模板标记、朝向标记 |
| 核对原机拼装 | [solver.py](solver.py) 的 `assembly_candidates`、`assemble_plans` | 堆叠支路、旁路位置与加工树 |
| 查指令语义与坐标 | [拆解逻辑](logic.md)、[运行说明](README.md) | 载荷定向、加工模板与历史机器名称 |

## 约定

- `g_x_y` 来自存档坐标，`second` 标记第二输出。`INITIAL` 的顺序用于逐引脚比对，`SAVE_SHA256` 定位原始转录。
- 指令尾两层分别为模板与朝向标记。载荷先按原机定向解释，制件后恢复目标朝向。
- 堆叠树参数按下料、上料排序。支路中的空值旁路仅保留原机存在的那几处。
- `solve` 从实际指令事件找最终部件，再对照每条电路候选，最后输出与目标相等的加工树。
- `build_controller` 按提供者元组登记网络。同一元组共用一个网络索引。
- `SuSuSuSu` 模板直接领一层原料。交错角模板借支架制造悬空块，再用定向半切移除支架。
- 拼装先比较电路各支路的实际图形，再按匹配编号选加工树。`ASSEMBLY_TREES` 与 `assembly_candidates` 顺序对应。
- 求解和 `--events` 的调用参数见 [运行说明](README.md)。

## 禁止事项

- 保留看似多余的延迟门和反馈。更改转录须能对到原存档的引脚和网络。
- `raw` 只接受非空单层。虚拟拆层只解释指令，模板与朝向层不能混入制件，多层部件由加工树生产。
