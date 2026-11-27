# 二代原生电路

将解码、搜索、配方和工道转换成可导入的原生岛布局及公开信号接口。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 登记蓝图预设 | [__main__.py](__main__.py) 的 `BLUEPRINT_TARGETS`、`BOOK_BY_TARGET` | 目标名、分册及频道预留 |
| 手写门网表 | [circuit.py](circuit.py) 的 `Ref`、`Literal`、`Gate`、`Circuit` | 原生输出索引、保留输出、常量编码 |
| 编译 Python 方法 | [compile_method.py](compile_method.py)、[compiler_contract.py](compiler_contract.py) | 共用类型、控制流及虚拟操作签名 |
| 调整语言子集 | [前端规则](compiler_frontend/AGENTS.md) | AST、静态证明与诊断定位 |
| 调整网表降低、布局和定步控制 | [后端规则](compiler_backend/AGENTS.md) | 组合逻辑、时序及成组发布 |
| 复用时钟与寄存器 | [sequential_circuit.py](sequential_circuit.py)、[register_circuit.py](register_circuit.py)、[clocked_state.py](clocked_state.py) | 相位门控和状态交接 |
| 完整尾部搜索 | [full_solver_circuit.py](full_solver_circuit.py) 的 `build_solver`、[recipe_processor.py](recipe_processor.py) | 四帧状态、成功路径回放与放行 |
| 整线布置和外部供料 | [实体装配规则](factory_assembly/AGENTS.md) | 工段、各槽物流与站场接口 |

## 约定

- `Ref.port` 沿用游戏原始输出索引。`Circuit.channel_map` 分配频道，公开输出通过 `retain_outputs` 明确依赖边界。
- 布置后用 `Circuit.document` 内的 `Wiring` 核对端口实际驱动。装箱会重映射平台和建筑索引，追线以最终坐标为准。
- 新方法将算法留在 Python 的受支持子集中。建筑、端口与编码由编译器生成。布局及导出回查遵循 [电路走线与压缩](../blueprints/电路走线与压缩.md)。
- 模块内部优先用本地导线，同岛层相邻平台优先用短距飞线。公开无线频道对应参数、返回或调用。
- 完整求解器在搜索时保留游标和成功参数。确认成功后才重放制造路径。接实体的模式由 `factory_ack` 推进发包。
- 组件级命令、物理分层与公开接法见 [编译入口](README.md) 和 [电路证明卷](../docs/proofs/08-circuits.md)。

## 禁止事项

- 无线反馈改成短距布线时须重算延迟、复位与采样。保留本地组合路径的无环条件。
- 原生编码分别表达空信号和整数 `0`。虚拟加工的端口顺序保持原生语义。
- 搜索未结束、输入未界定、内部状态失配与穷尽失败分别发布。完整控制器的搜索中间态不得触发制造。
