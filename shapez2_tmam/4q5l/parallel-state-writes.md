# 互斥状态写入的并行选择

完整控制器对同一寄存器的部分写入采用`ClockedState.put_exclusive`：每个条件单独门控对应数据，输出共用一个别名频道；全部条件为假时，保留此前计算的next。以下各组条件两两互斥，所以这与依次覆盖的串联选择具有相同的稳定状态转移。只改变组合选择结构，不改变事件、数据或优先级语义。

| 状态 | 互斥依据 |
|---|---|
| 当前帧pin_search | enter_leaf与enter_pin同在ENTRY，但known_no_leaf分别为假和真；begin_pin_search在PREFIX |
| 当前帧family_checked | descend在SOURCE；清零只来自PREFIX的start_source或SOURCE_NEXT/FAMILY_NEXT的族推进 |
| 当前帧前缀 | ENTRY的enter_leaf/enter_pin互斥；PREFIX的grow要求非impossible且changed，结束分支要求impossible或非changed；结束后next_cut和begin_pin_search又由leaf_direction的0/1区分；move_prefix在PREFIX_NEXT |
| 当前帧C掩码、来源槽、NPC顶盖 | 来源推进在SOURCE_NEXT/FAMILY_NEXT；来源初始化在PREFIX |
| leaf_direction | enter_leaf在ENTRY，next_cut在PREFIX |
| leaf_mode | descend在SOURCE；commit_top在PREFIX，fail_pop在FAIL |
| PC的根初始化/父段起点 | reset_cpu在根RETURN，replay_up在重放CHECK；两者不成立时保留已经计算的正常PC更新 |
| support_prefix | 写0来自SOURCE、ENTRY的enter_pin或PREFIX的begin_pin_search；写1来自ENTRY的enter_leaf、PIN_PREFLIGHT、RETURN、FAIL或重放CHECK；ENTRY的两支由known_no_leaf区分 |
| status | root_failed在FAIL；outside在ENTRY且uncolored；internal的ENTRY支要求in_scope，排除uncolored；重放成功与比较失败互补，CPU错误只在真正REPLAY而非CHECK |

所有帧内条件还带当前depth的独热选择。父帧下降时清新子帧状态，与该子帧作为当前帧的写入不能同时成立；并行选择的保留支路继续保留先前登记的子帧清零，未删除这条写入。

状态更新依赖的信号在周期中途可以尚未稳定。并行别名也可能暂时取得空值或多路冲突；它与原控制器的组合通路一样，必须在主副状态协议的稳定窗口内采纳。传播上界对完整别名依赖图重新计算，包含全部分支及保留支路，不以“互斥”忽略控制延迟。

时钟环、等深正反控制、锁存器反馈及外部窗口都保持原连接。PC内部take_jump、重复角和重复半形的已有选择优先级保持，不在未证明互斥时改成并行选择。

[完整控制](full-tail-circuit.md) · [慢更新协议](multicycle-control.md)
