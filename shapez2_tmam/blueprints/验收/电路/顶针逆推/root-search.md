# 从目标自动生成直接路线配方

`direct-root.spz2bp` 接入原图读取、供料判定、原图闭包、叶端锁存和两遍成功路径。闭包选出切向和前缀后，控制器先冻结全部叶端参数，再撤销闭包并启动配方回放。虚拟回放核对成品，实体两组存储回读确认后才发布供料许可。

| 频道 | 用途 |
| --- | --- |
| `1600000` | 四象限五层内的目标形状。开单前接入，保持到实体写入结束。 |
| `1704673` | 启动。开单及换单时先在低电平保持至少 456 信号 tick。 |
| `1704674` | 订单阶段。`0` 待机，`1` 等原色稳定，`2` 查双切向，`3` 锁存，`8` 回放。 |
| `1704678` | 阶段 `6`。两切向已耗尽，等待外层堆叠和顶针逆推。 |
| `1704679` | 阶段 `4`。目标含供料未定的未着色晶体。 |
| `1704680` | 阶段 `5`。目标为空。 |
| `1704681` | 阶段 `7`。闭包同时报选定和耗尽。 |
| `1702851` | 供料许可请求，沿用两遍控制接口。 |

虚拟回放与实体装单沿用[成功路径回放](../配方回放/success-path.md)和[两遍接口](../配方回放/two-pass-recipe.md)。外层逆推入口预留为 `1704678`。`root-search.spz2bp` 提供独立的六板调度器，输入与输出见同名 JSON。`order-entry.spz2bp` 接五层原色，输出非空、未着色晶体和剩余尾针上界。

```bash
parts=shapez2_tmam/blueprints/验收/电路
python -m shapez2_tmam.circuits.compile_root_search \
  --reader "$parts/原层读取/read-five-rows.spz2bp" \
  --closure "$parts/顶针逆推/dual-source-closure.spz2bp" \
  --path "$parts/配方回放/success-path.spz2bp" \
  --output direct-root.spz2bp
python -m shapez2_tmam.circuits.compile_root_search --output root-search.spz2bp
python -m shapez2_tmam.circuits.compile_order_entry --output order-entry.spz2bp
```

直接路线合装为 422 块 3×3 平台和 432,740 个建筑，772 个发射频道均为单发。含晶目标 `Cu--cr--:crCucrCu:----cr--:----cr--:----cr--` 从原图自动选出前缀 `(2,2,5,2)`，两遍各写入 74 笔，地址 `0`–`73`。原生离线回放逐笔核对六字段和实体存储，最终唯一槽 `0` 为原目标。独立调度器另核对空输入、供料未定、闭包耗尽、矛盾回报及复位。游戏内时序待验。
