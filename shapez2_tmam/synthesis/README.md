# 合成的 Python 接口

这个包接受四象限或六象限五层目标，输出具有逐步加工结果的制造证书。默认使用快速局部构造；无晶体目标采用完整判据，未覆盖的含晶体目标返回 `unknown`。四象限另有 `--complete` 启用[完整有界尾部逆推](../4q5l/tail-solver.md)，不建立半形目录，但最坏搜索时间仍很大。六象限完整求解及完整游戏控制器尚未完成。

## 输入目标，取得制造步骤

在仓库根目录运行：

```bash
python -m shapez2_tmam.synthesis 'CuCu----:Cu------' --quadrants 4
```

四象限完整逆推在命令末尾加 `--complete`；此选项不支持六象限。输出是 JSON。`status` 有三种值：

| 状态 | 含义 | 退出码 |
|---|---|---|
| `solved` | `steps` 是从基础原料开始的合法制造树 | 0 |
| `unsolvable` | 违反已证必要条件、无晶体完整判据不通过，或完整四象限搜索已耗尽 | 2 |
| `unknown` | 默认局部构造未覆盖，或 `cu` 的实体供料未界定 | 3 |

编码语法错误由参数解析器报告。保留底部及中间空层，最高层必须非空。普通格使用游戏的 `C/R/S/W` 部件代码，晶体用小写 `c`，针用 `P-`；象限数由 `--quadrants` 指定。颜色语法与实体供料前提见[覆盖性研究](../4q5l/coverage-research.md)，虚拟信号本身不证明某种颜色流体可取得。`cu` 可作为分析信号，实体供料尚未界定，因此局部构造器对此返回 `unknown`；实体结晶配方只启用 `r/g/b/c/m/y/w`。

每一步有 `id`、`operation`、`inputs`、`parameter` 和 `result`。输入编号总在本步之前。物品输入会被消耗；相同子配方引用会展开成独立制造步骤，不隐式复制实体。

| 操作 | 参数与输入 |
|---|---|
| `base` | 取结果描述的一份无晶体单层原料 |
| `rotate` | 一个物品；参数为顺时针象限数，可为负数 |
| `cut` | 一个物品；出口 0 保留索引前半，出口 1 保留后半 |
| `pin` | 一个物品；执行一次顶针 |
| `crystal` | 一个物品；参数为颜色代码 |
| `stack` | 两个物品，按下料、上料排列 |
| `swap` | 两个物品；参数 0 取前半 A＋后半 B，参数 1 取前半 B＋后半 A |

## 从 Python 调用

```python
from shapez2_tmam.synthesis import Rules
from shapez2_tmam.synthesis.construct import Constructor

rules = Rules(quadrants=4)
target = rules.parse("CuCu----:Cu------")
result = Constructor(rules).construct(target)
if result.recipe is not None:
    for step in result.recipe.steps():
        print(step)
```

`Rules` 提供旋转、切割、顶针、堆叠、结晶及交换的局部物理。它保留制造后不稳定的输出，不在交换后追加重力；结算过程中不合并新接触。四象限、六象限均使用五层上限，不能把规则实例的物品跨配置混用。

`Builder` 提供基础层、无晶体逐层构造、独立单列、独立晶体前缀、逐层 N/P 追加和列拼接。多层晶体原料通过基础原料、结晶和切割展开，不能作为免费的实体输入。

四象限的 `Constructor.half` 使用[逐列角构造](../4q5l/corner-synthesis.md)，在合法颜色范围内精确判半形，成功时至多285个制造节点。`CornerBuilder.accepts_half` 只检查列条件和新分组的稳定性；`CornerBuilder.build` 准备单列及其 N/P 助手，处理八种顶针难列。`Solver4.solve` 使用这些局部起点及完整顶针/堆叠尾部；最多四条递归边，实际搜索分支仍需压缩。理论上每个可制作四象限目标存在至多627节点的制造树。六象限目前只启用无晶体及独立柱构造，不能据此判断全部六象限含晶体目标。

`pin_families`、`cut_families` 是独立的惰性物理逆像接口。候选能产生目标，不等于候选本身可制作；使用者须给实际族成员补制造证明。

[原生电路部件及频道接法](../blueprints/README.md) · [返回总目录](../README.md)
