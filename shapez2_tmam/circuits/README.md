# 二代原生电路编译器

本包将 TMAM 的解码、判据、候选枚举、六槽配方回放和四帧完整搜索编译为游戏 `SHAPEZ2-4` 原生岛蓝图（`.spz2bp`）及配套频道与时序说明（`.json`）。导出的蓝图与外部连接协议见 [`../blueprints/README.md`](../blueprints/README.md)，各部件的数学与时序证明见[`../docs/proofs/08-circuits.md`](../docs/proofs/08-circuits.md)。

## 模块分层

| 分层 | 模块 | 职责 |
|---|---|---|
| 网表与装箱基建 | [circuit.py](circuit.py)、[circuit_packing.py](circuit_packing.py)、[tag_palette.py](tag_palette.py) | 信号门网表、频道分配、保持期界、3×3 大平台占地装箱及递归标签路由表 |
| 时钟与控制器基元 | [sequential_circuit.py](sequential_circuit.py)、[register_circuit.py](register_circuit.py)、[clocked_state.py](clocked_state.py)、[program_controller.py](program_controller.py)、[corner_program.py](corner_program.py)、[shared_angle.py](shared_angle.py) | 四阶段时钟、三阶段寄存器、主副状态闭合、条件指令 ROM 及两角时序复用 |
| 解码与基础判据 | [operation_core.py](operation_core.py)、[decoder_circuit.py](decoder_circuit.py)、[scan_circuit.py](scan_circuit.py)、[iterative_scanner.py](iterative_scanner.py)、[noncrystal_circuit.py](noncrystal_circuit.py)、[half_circuit.py](half_circuit.py)、[material_half_circuit.py](material_half_circuit.py) | 共用虚拟加工核心、原层号解码、拆层循环、无晶体完整配方及标准半形判定 |
| 支撑闭包与顶针逆像 | [ring_circuit.py](ring_circuit.py)、[support_circuit.py](support_circuit.py)、[stationary_circuit.py](stationary_circuit.py)、[prefix_search.py](prefix_search.py)、[prefix_closure_circuit.py](prefix_closure_circuit.py)、[pin_column_circuit.py](pin_column_circuit.py)、[pin_column_iterator.py](pin_column_iterator.py)、[pin_pattern_circuit.py](pin_pattern_circuit.py)、[pin_slot_circuit.py](pin_slot_circuit.py)、[pin_image_circuit.py](pin_image_circuit.py)、[pin_source_circuit.py](pin_source_circuit.py)、[tagged_goal_circuit.py](tagged_goal_circuit.py) | K/G 支撑可达、静止集合、S 前缀强制闭包、单列与四列二十槽顶针前态及标签网格核对 |
| 自动制造与完整控制 | [recipe_processor.py](recipe_processor.py)、[half_synthesizer.py](half_synthesizer.py)、[startpoint_circuit.py](startpoint_circuit.py)、[full_solver_circuit.py](full_solver_circuit.py) | 六槽消费式回放、标准半形自动制造、双半形起点/S 尾部及四帧完整四象限搜索回放 |

## 编译命令

在仓库根目录可通过统一入口或包入口调用：

```bash
# 查看全部预设蓝图目标
python main.py tmam2 blueprint --list

# 按预设频道编译单个或多个蓝图到 shapez2_tmam/blueprints/
python main.py tmam2 blueprint decoder-4q5l recipe-processor-4q5l

# 仅更新 shapez2_tmam/reports/ 下的静态网表与关键路径报告
python main.py tmam2 blueprint --reports

# 自定义参数单独调用某个部件模块
python -m shapez2_tmam.circuits.operation_core --quadrants 4 --channel-base 1000000 --output shapez2_tmam/blueprints/operation-core-4q5l.spz2bp
```

[导出蓝图说明](../blueprints/README.md) · [静态元件报告](../reports/README.md) · [返回二代总目录](../README.md)
