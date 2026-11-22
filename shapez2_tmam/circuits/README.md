# 二代原生电路编译器

本包将 TMAM 的解码、判据、候选枚举、六槽配方回放和四帧完整搜索编译为游戏 `SHAPEZ2-4` 原生岛蓝图（`.spz2bp`）及配套频道与时序说明（`.json`）。导出的蓝图与外部连接协议见 [`../blueprints/README.md`](../blueprints/README.md)，各部件的数学与时序证明见[`../docs/proofs/08-circuits.md`](../docs/proofs/08-circuits.md)。

## 游戏内的信号连接

一个部件的边界由它完成的运算及调用者需要的输入和返回值确定。部件内部用本地导线，多个消费者共用分支。相邻平台优先从对齐的接口用短距飞线连接。调用者能直接接线时也可省去全局频道。编译时将全局收发器逐一对应到参数、返回值或对其他部件的调用。依赖无线延迟的既有时钟和反馈，要先核对替代实现的相位与采样窗口。

布局采用3×3大平台，使用平台内三层建筑空间。多平台布局可上下叠放。比较蓝图时分别统计收发器数量、含线缆建筑数、各建筑层用量、平台数及俯视长宽。单步扫描部件通过 [wired_module.py](wired_module.py) 生成，按最终几何逐个核对输入来源。完整控制器仍有逐门无线连接，其平台叠放与内部布线是两项独立进度。

## 模块分层

| 分层 | 模块 | 职责 |
|---|---|---|
| 网表与装箱基建 | [circuit.py](circuit.py)、[circuit_packing.py](circuit_packing.py)、[tag_palette.py](tag_palette.py) | 信号门网表、频道分配、保持期界、3×3 大平台占地装箱及递归标签路由表 |
| 时钟与控制器基元 | [sequential_circuit.py](sequential_circuit.py)、[register_circuit.py](register_circuit.py)、[clocked_state.py](clocked_state.py)、[program_controller.py](program_controller.py)、[corner_program.py](corner_program.py)、[shared_angle.py](shared_angle.py) | 四阶段时钟、三阶段寄存器、主副状态闭合、条件指令 ROM 及两角时序复用 |
| 解码与基础判据 | [operation_core.py](operation_core.py)、[decoder_circuit.py](decoder_circuit.py)、[scan_circuit.py](scan_circuit.py)、[iterative_scanner.py](iterative_scanner.py)、[noncrystal_circuit.py](noncrystal_circuit.py)、[half_circuit.py](half_circuit.py)、[material_half_circuit.py](material_half_circuit.py) | 共用虚拟加工核心、原层号解码、拆层循环、无晶体完整配方及标准半形判定 |
| 支撑闭包与顶针逆像 | [ring_circuit.py](ring_circuit.py)、[support_circuit.py](support_circuit.py)、[stationary_circuit.py](stationary_circuit.py)、[prefix_search.py](prefix_search.py)、[prefix_closure_circuit.py](prefix_closure_circuit.py)、[pin_column_circuit.py](pin_column_circuit.py)、[pin_column_iterator.py](pin_column_iterator.py)、[pin_pattern_circuit.py](pin_pattern_circuit.py)、[pin_slot_circuit.py](pin_slot_circuit.py)、[pin_image_circuit.py](pin_image_circuit.py)、[pin_source_circuit.py](pin_source_circuit.py)、[tagged_goal_circuit.py](tagged_goal_circuit.py) | K/G 支撑可达、静止集合、S 前缀强制闭包、单列与四列二十槽顶针前态及标签网格核对 |
| 自动制造与完整控制 | [recipe_processor.py](recipe_processor.py)、[half_synthesizer.py](half_synthesizer.py)、[startpoint_circuit.py](startpoint_circuit.py)、[full_solver_circuit.py](full_solver_circuit.py) | 六槽消费式回放、标准半形自动制造、双半形起点/S 尾部及四帧完整四象限搜索回放 |

## 编译命令

### 从 Python 方法导出

指定源码文件、顶层方法名和起始频道。命令生成可导入的 `.spz2bp` 与相邻的 `.json` 接口表。支持的写法见[编译器前端](compiler_frontend/README.md)，布局和采样条件见[编译器后端](compiler_backend/README.md)。

```bash
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/layer_methods.py append_five --channel-base 1700020 --output append_five.spz2bp
```

同一文件中的多个方法共用一组输入时，用 `--field 字段=方法` 对应每个输出，并为方法参数和输出字段指定频道。所有方法的参数顺序、名称和类型须相同。

```bash
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/direct_recipe.py \
  --field opcode=direct_recipe_opcode --field a=direct_recipe_lower \
  --field b=direct_recipe_upper --field destination=direct_recipe_destination \
  --input-channel address=1640000 --input-channel length=1640043 \
  --output-channel opcode=1640002 --output-channel a=1640003 \
  --output-channel b=1640004 --output-channel destination=1640005 \
  --output direct_recipe.spz2bp
```

用 `--publish-when 字段=方法` 为某个字段指定同文件、同参数的布尔发布方法。条件为假时，该字段输出空信号。现有配方值方法仍可和发布方法一起编译，见[发布方法示例](compiler_frontend/README.md#编译共享输入的多个字段)。

### 编译现有预设

在仓库根目录运行以下命令。

```bash
# 查看全部预设蓝图目标
python main.py tmam2 blueprint --list

# 按预设频道编译单个或多个蓝图到 shapez2_tmam/blueprints/
python main.py tmam2 blueprint decoder-4q5l recipe-processor-4q5l

# 仅更新 shapez2_tmam/reports/ 下的静态网表与关键路径报告
python main.py tmam2 blueprint --reports

# 自定义参数单独调用某个部件模块
python -m shapez2_tmam.circuits.operation_core --quadrants 4 --channel-base 1000000 --output shapez2_tmam/blueprints/电路/加工与指令/operation-core-4q5l.spz2bp
```

[导出蓝图说明](../blueprints/README.md) · [静态元件报告](../reports/README.md) · [返回二代总目录](../README.md)
