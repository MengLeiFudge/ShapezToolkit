# Python 方法编译前端

静态解析方法源码，证明可达路径上的类型、局部状态与循环边界，再生成 `Program`。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 单方法、同参多字段编译 | [__init__.py](__init__.py) 的 `compile_method`、`compile_field_methods` | 入口名称、同组参数签名与布尔发布条件 |
| 相对导入和源码诊断 | [_sources.py](_sources.py) 的 `_Sources`、`FrontendError` | 文件名、顶层绑定、调用路径和行列 |
| 整数与索引范围分析 | [_ranges.py](_ranges.py) 的 `_analyze_ranges` | 按块传播区间、调用返回界、汇合和循环 |
| 共享内建操作 | [compiler_contract.py](../compiler_contract.py) 的 `BUILTINS` | 保留名称及固定参数顺序 |
| 单列候选源码 | [pin_column_source.py](pin_column_source.py)、[模式表](../../synthesis/pin_patterns.py) | 由底到顶的材料字与固定槽序 |
| 单列枚举和四列组合 | [pin_column_cursor.py](pin_column_cursor.py)、[pin_column_loop.py](pin_column_loop.py)、[pin_column_combinations.py](pin_column_combinations.py) | 暂停、续读槽和候选耗尽 |

## 约定

- 入口是有类型签名的顶层方法。值使用 `bool`、`int`、`Shape` 或 `Color`。空值有明确的图形或颜色类型。
- 相对导入用 `from .模块 import 方法`，传入实际 `filename` 供源码解析。调用参数采用固定位置。
- 局部变量读取前在所有到达路径已赋值，类型始终一致。短路 `and`、`or` 生成分支，布尔 `&`、`|` 求值两侧。
- 只读表是非空同类型字面量元组。索引和算术的有符号 32 位界须从可达路径证明。
- `for` 使用固定元组或字面量范围。`while` 使用定步长游标，更新朝结束边界推进，`continue` 置于更新之后。
- 多字段发布方法接收同一组参数并返回 `bool`。发布条件只绑定到声明过的输出字段。
- `max_block_visits` 包含本方法的退出块，子调用单独计数。语法子集与导出命令见 [前端说明](README.md)。

## 禁止事项

- 调用图须无环。保留名称按 `BUILTINS` 或 `shape_literal` 解析，自定义加工选用其他名称。
- 禁用运行时属性调用、关键字参数和展开参数。链式比较拆成短路连接的单次比较。
- 无效候选通过发布条件或 `valid` 表示。保留合法的全空候选与整数槽 `0`。
