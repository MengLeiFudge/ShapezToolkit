# 慢状态更新后冻结一轮

完整四象限电路把共享制造通路与来源搜索通路分开计时。当前制造周期从228模拟秒降至100模拟秒；目标、前缀、来源等慢状态变化后额外冻结一轮，相关更新连同等待为200模拟秒。该改动不减少分支总数，尚未取得实用搜索保证。

实现为 [`ClockedState.close`](../clocked_state.py) 的 `slow_reads`、`slow_event`、`pulses`，由[完整控制器](../full_solver_circuit.py)提供变化分类。没有执行反馈、目标或时序模拟。

## 状态分类

328项慢状态为五帧全部325项状态，以及depth、second_pass、support_prefix。其余为快状态，包括CPU、PC、Phase、结果、状态和包快照；新增一项冷却位cooling。总计358项状态，六个物品槽、486行ROM保持。

重K通路选择器改为独立慢状态support_prefix，初值0。下降到新帧时写0，ENTRY读完整帧目标；成功进入PREFIX时写1。回父或根开始重放时也写1，确保子帧在ENTRY直接失败后，父前缀扫描仍使用正确选择。Phase不再直接驱动K洪泛。

每次可能改慢状态的事件均触发slow_event：

| 慢写入 | 事件 |
|---|---|
| 新帧20格目标、下降depth | descend |
| 初始化前缀及遍次 | enter、begin_pin_search |
| 前缀推进 | move_prefix |
| 清来源游标 | start_source |
| 来源推进及整段跳过 | counter_event |
| 回父或跳成功叶端depth | search_pop、fail_pop、root_solved、replay_up |
| 制造遍次归零或第二遍 | start_leaf、root_solved、repeat |
| K选择器 | descend、enter、search_pop、fail_pop、root_solved、replay_up |

事件可包含不改变值的写入，只会多等一轮。不存在未列事件下的慢状态写入。复位另按全初始路径等待，不使用运行协议。

## 冻结协议与传播期限

令ready为NOT cooling。每个业务状态的next改为 `ready ? 原next : 旧值`。冷却位本身每周期更新为 `ready AND slow_event`，初值0。因此允许的慢更新发生时cooling置1；下一周期全部业务状态保持且cooling清0；再下一周期恢复业务更新。快状态和慢状态共享相同主副组。

以发生慢更新的副组写回时刻为0。下一主组关写在3P，此时正在冻结，业务next只需保留旧读值。随后冷却位在4P清0，下一次允许业务写入的主组关写在7P。故快变化必须满足 `3P > 12D_fast+36`；慢变化可以使用 `7P > 12D_slow+36`。同一个ready变化对掩码和保持路径的影响计入快路径，不能用“冻结”忽略掩码传播。

闭合反馈前，对包含所有写入掩码的组合DAG分别计算快根和慢根传播深度；没有裁掉路径。当前D_fast=64，D_slow=167，P=300tick：

- `3P=900 > 804=12×64+36`。
- `7P=2100 > 2040=12×167+36`。

初始最大路径184级，复位保持至少 `12×184+256=2464tick`。阶段300tick，周期1200tick，即100模拟秒。主副锁存及外部常速模式前提沿用[等深锁存证明](clocked-control.md)。

## 发令不重复

record_valid列入pulses，next为 `ready AND 原accepted`，冻结时写0；它不按业务状态保持。包数据仍随业务状态冻结。

允许周期收下最后一份包时，record_valid与cooling可同时变1。本周期阶段3仍以record_valid发布一次，不能再用新的ready屏蔽，否则会丢包。下一冻结周期record_valid清0，不重复发布旧包；随后恢复下一条指令。制造CPU、ack和PC在冻结周期都保持，所以冻结期内部组合通路算出的包不会消费实体，也不会改变虚拟物品。

外部协议保持：每个完整window上升后96tick读取一次；sample真先收指令，再处理done/status。搜索期间仍不发布制造流。

## 终止、规模与证据

删掉冻结轮后，业务状态序列与原控制器逐步一致。每个慢事件最多插入一轮，故不改变可靠性、完备性或有限终止；也不把预算耗尽误作不可制作。

当前38618逻辑门，未压缩版38618平台；[装箱版](packed-circuit.md)17240平台、132×131外框。新增掩码会增加占地，换取较短的制造周期。最坏来源数与递归分支界保持，必须继续压缩搜索。

两个Python文件LSP零诊断，两版生产蓝图通过组合DAG、逐端口和实际占地静态编译。未运行目标、搜索、指令、模拟、测试或游戏。

[完整控制器](full-tail-circuit.md) · [蓝图接口](../blueprints/README.md) · [返回目录](README.md)
