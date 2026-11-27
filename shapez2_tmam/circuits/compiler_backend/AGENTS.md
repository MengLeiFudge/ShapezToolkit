# 原生蓝图编译后端

将四象限五层 `Program` 降低为组合门网，再生成布局、采样协议和时序调用器。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 单方法编译和导出 | [__init__.py](__init__.py) 的 `compile_program`、`export_program` | 参数频道连续分配，末频道是返回值 |
| 路径展开和调用 | [_lower.py](_lower.py) 的 `Lowering` | 块访问上界、谓词和可达整数值 |
| 组合门复用 | [_optimize.py](_optimize.py) 的 `compact` | 等价门、选择总线和旋转路径 |
| 布局容量和备选布线 | [_layout.py](_layout.py)、[_split.py](_split.py)、[_table.py](_table.py) | 单板、区间译码和同层双板切分 |
| 多字段发布 | [fields.py](fields.py) 的 `compile_fields`、`export_fields` | 共用接收器、逐字段发布条件 |
| 定步循环 | [timed.py](timed.py) 的 `compile_fold`、`compile_state_fold`、`compile_state_steps` | 索引、轮值、常驻输入和状态写回 |
| 连续发令与确认 | [module_caller.py](module_caller.py)、[confirmed_call.py](confirmed_call.py)、[dense_write_bridge.py](dense_write_bridge.py) | 先复位，再等新的完成或同址确认 |

## 约定

- 无环块合并到达路径，循环按访问上界展开，非递归子调用就地降低。整数加法的动态选择只枚举可达有限操作数组合。
- 常规组合布局先尝试复用后的网表，再按容量回退。适用的单整数入出网表可改用区间译码。
- 双板切分将同一选择总线的全部驱动留在一侧。跨板网用成对端口，飞线计入最终依赖路径。
- 多字段编译保持参数顺序、名称与类型一致。条件为假时只屏蔽所属输出。读取时整组保持 `settling.hold_signal_ticks`。
- 定步调用在 `run=0` 送齐初值后等待复位。运行期间保持常驻输入，各字段从同一份旧状态计算并同时写回。
- 稳定期、复位、采样和调用器导出参数见 [后端说明](README.md)。

## 禁止事项

- 公开频道由本次模块独占。禁止多字段重用同一公开输入或输出频道给不同信号。
- 旧 `done` 和旧同址确认须先撤销。等新结果稳定后再推进，空图形可作为已完成结果。
- 定步折叠的状态板与计算板依赖固定的双向无线延迟。后续轮按往返推进，首轮可读时间与最终采样时间分别计算。
