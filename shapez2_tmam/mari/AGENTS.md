# Mari 主控模型

从指定原包接线提取具名组合方程，复现固定候选重建和工厂下发信号。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 原包提取和接线追踪 | [blueprint.py](blueprint.py) 的 `Wiring`、`BOUNDARIES`、`export` | 包指纹、母线边界、短距口配对 |
| 原生端口与建筑类型 | [ports.py](ports.py) 的 `PORTS`、`OPERATIONS` | 建筑归一化、原生端口方向及顺序 |
| 信号合并和常量 | [signals.py](signals.py) 的 `merge`、`decode_constant`、`operate` | 空信号、冲突、整数、颜色与图形 |
| 固定四象限物理 | [shapes.py](shapes.py) 的 `Shape` | 保留颜色、晶体融合、截高和原层号 |
| 求值与候选观察 | [solver.py](solver.py) 的 `Mari.candidate`、`Mari.solve`、`Mari.inspect` | 拓扑顺序和最小匹配编号 |
| 虚拟拼合复核 | [assembly.py](assembly.py) 的 `assemble` | 四角、Hybrid、交换方向和 Claw 控制 |
| 重导及外部证据 | [模型说明](README.md)、[外部研究卷](../docs/proofs/09-sources.md) | 方程来源、原包开关与反例范围 |

## 约定

- `equations.json` 由接线提取生成。日常求值以该文件为输入，无需原包。节点记原始 `site`、操作、配置和输入输出引用。
- 坐标首项是原 `BP.Entries` 的零起始平台索引。建筑旋转、镜像和原生端口索引分别处理。布局改变后重新核对边界和竞争配对。
- 门先合并同线驱动。`Null` 为合并单位元，相异非空值产生 `Conflict`，整数 `0` 仍参与合并。
- 候选固定编号，求值从处理后目标母线开始。返回工厂指令时计算 `Update Factory` 开启时的载荷。
- `candidate` 将直接拼合和逐门重建对照。`matched` 同时要求比较门为真且重建图形等于目标。
- `inspect` 按原蓝图坐标读取一个建筑的全部输出端。观察点以方程的 `site` 记录为准。

## 禁止事项

- 未识别的原生建筑和不明配对应报告。不可把未知输入补成空信号或整数零。
- 模型边界在主控组合逻辑。反馈、采样延迟和实体生产需要各自的证据。
- 多层信号和 `parts` 只用于观察。制造证书须从可供给的实体原料展开。`no_candidate` 只说明原机候选未匹配。
