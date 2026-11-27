# 二代制造证书

以偶数象限、固定过程层数的局部规则构造真实制造树，并在证明覆盖的范围内判定可制作性。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 图形表示及物理 | [physics.py](physics.py) 的 `Shape`、`Rules` | 原层号、分组、结算和截高 |
| 构造及半形 | [construct.py](construct.py) 的 `Constructor`、[corners.py](corners.py) 的 `CornerBuilder` | 标准半形、切向、列条件和脚手架 |
| 完整四象限五层 | [solver4.py](solver4.py) 的 `Solver4`、[prefix_closure.py](prefix_closure.py) 的 `minimal_start` | 双半形起点、S 前缀和尾部 Pin 界 |
| 逆像和支撑 | [inverse.py](inverse.py) 的 `pin_families`、[pin_constraints.py](pin_constraints.py)、[support.py](support.py) | 物理匹配、前态证书及原晶体层位 |
| 消费式配方及朝向 | [recipe.py](recipe.py) 的 `Recipe`、`Builder`、[orientation.py](orientation.py) 的 `optimize_rotations` | 活槽峰值、操作数顺序、选定出口 |
| 参数、用料和示例导出 | [__main__.py](__main__.py)、[production_bill.py](production_bill.py)、[Python 接口](README.md) | 三态输出、导出范围和基础单层订单 |

## 约定

- `Shape.layers` 从底到顶。编码保留空底层与中间空层，顶层非空。`None` 表示无产物。
- `Rules.height` 限制整个制造过程。局部操作按证明保留分组、融合与结算顺序。`stack` 参数依次为下料、上料。
- 旋转参数按象限计。半切出口 `0`、`1` 分别取索引前半和后半，交换沿用同一侧序。
- 默认构造按覆盖范围返回证书。完整四象限模式从两个切向的最小前缀找双半形起点，再使用有界尾部逆推。
- `Recipe.steps()` 先做槽需求较大的子树，仍按原操作数语义引用。重复的子树各展开一份物品。
- `Recipe.instructions()` 在发出首包前核对槽预算，基础料取最低空槽，加工复用第一操作数槽。
- CLI 只在已有证书上做整树朝向优化。制造步骤、寄存器峰值、整厂耗材分别读取对应字段。

## 禁止事项

- 不在 `Swap` 结果后补重力，不把下落后新接触的格重新分组。保留参数化过程上限，禁止混用不同 `Rules` 配置。
- 基础料限无晶体单层。虚拟拆层、逆像候选和多层字面量不能作为实体输入。
- `unsolvable` 要有已证的必要条件或完备判定失败。局部构造缺口与未界定的 `cu` 供料归 `unknown`。
