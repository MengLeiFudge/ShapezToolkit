# 一代 TMAM

从一代存档只读提取信号电路，按 tick 验证已分析机器的输出或指令。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 存档解码、引脚和机器布局 | [tmam_circuit.py](tmam_circuit.py) 的 `read_save`、`extract_circuit`、`PROFILES` | 保留全部输出反向依赖和保存时初值 |
| 信号和图形编码 | [tmam_signals.py](tmam_signals.py) 的 `from_structure`、`operate` | 低四位为底层，层内从右上顺时针 |
| tick 与批量报告 | [tmam_verify.py](tmam_verify.py) 的 `CircuitModel.run`、`verify_saves` | 完整引脚状态、相等检查与错误分类 |
| BugFix 历史结果 | [BugFix 说明](bugfix_20210622/README.md) | CTMAM 是兼容旧名，下载存档和本机存档格式有别 |
| Nabi v7f 脉冲指令 | [verify_v7f.py](nabi_20221128/verify_v7f.py) 的 `V7FAudit` | 指令、控制标志、缓存顺序和存档指纹 |
| XianYu 拆解转录 | [XianYu 规则](xianyu_20221129/AGENTS.md) | 无需原始存档的结构求解 |

## 约定

- 电路提取只接受端口表支持的无模组存档。输入、检查和输出按 `PROFILES` 中核对过的坐标定位。
- 每个输入从独立保存状态开始。先关闭开关，再换输入，最后启动。每 tick 先汇总网络，再计算门。
- `NULL`、`FALSE` 和网络冲突分别表示。相同非空值可以合并，不同非空值使接收门清空全部输出。
- BugFix 与 XianYu 的验证要求固定点或完整周期始终匹配目标且相等检查通过。瞬态匹配、周期和超时各自记录。
- Nabi v7f 审计按到达 tick 展开脉冲，对照片段与缓存。审计完成只表明记录已生成。
- Nabi 的端口位置绑定指定存档指纹。更换原件先核对布局和选择器，再使用审计入口。
- 机器报告按各自目录归档。共用结构对照库和验证命令见 [一代 TMAM 说明](README.md)。

## 禁止事项

- 不跨 tick 读取刚写入的门输出，不把 `FALSE` 当空信号，不压缩相邻 tick 上相同的 Nabi 指令。
- 提取遇到不受支持的端口或真实物流反馈时报告边界。不得用固定常量假造反馈。
- 机器漏解、超时、候选堆叠不相等均不能单独判定游戏不可制作。
