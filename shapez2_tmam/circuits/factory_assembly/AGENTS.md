# 六槽实体装配

将消费式配方装配为实体工道、供料站和列车图册，逐工段记录物品流与接点。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 回放配方 | [recipe.py](recipe.py) 的 `replay` | 操作数方向、目的槽、废弃出口及唯一成品 |
| 通用及纯堆叠实体 | [layout.py](layout.py) 的 `assemble`、`assemble_direct_stack`、[production.py](production.py) | 工段地址、六槽路径、实体出口和站位 |
| 订单写入 | [interface.py](interface.py)、[submit_bridge.py](submit_bridge.py)、[writer_handoff.py](writer_handoff.py) | 私有字段、双回读、接管等待和地址确认 |
| 槽位接合及顶破 | [half_assembly.py](half_assembly.py)、[corner_release.py](corner_release.py)、[dense_column.py](dense_column.py) | 保留槽、暂存槽及释放前后朝向 |
| 站场分册与容量 | [books.py](books.py)、[capacity.py](capacity.py)、[layout.py](layout.py) 的 `cargo_ports` | 车厢编号、层位、实测卸货与需求 |
| 工道与供料分页 | [stage_pages.py](stage_pages.py)、[full_line_pages.py](full_line_pages.py)、[shared_supply_page.py](shared_supply_page.py) | 页间接点、共用供料、层高及流向 |
| 换单控制与接线 | [装配说明](README.md#写入与换单)、[changeover.py](changeover.py) | 停料、排空、清除、装方、供料 |

## 约定

- 六字段是 `opcode/a/b/destination/base/color`。槽 `0` 与地址 `0` 为整数，未使用字段留空。
- 回放消费实际输入。目标槽须为空或是本步消费的槽，双输入来自不同活槽。整单结束仅保留一件等于目标的成品。
- 两组回读都要完成 `2 → 3 → 1` 才确认当前地址。保持当前包至 `ack=1`，接管等待按接口表。
- 换单先维持旧配方排空实物，再进行电路复位。满足 `loaded=1` 后才打开领料。
- 制作端与配料端共用 `cargo_ports()` 装载定义。车厢从车头后第 1 节起算，层从 0 起算。
- 共用干线按同一订单的同时需求求和，互斥订单取合计需求最大者。站场按卸货量、到达间隔及持续通路能力核对。

## 禁止事项

- 固定发送器和动态主控不可同时驱动公开配方总线。安装动态主控前移除固定发送器。
- 空回读不足以确认反馈存储已清除。相位等待和实物排空都完成才发布清空确认。
- 一满带的持续能力由实际到货、加工和成品带计量验证。预填的缓冲库存仅用于消化到货间隔。
