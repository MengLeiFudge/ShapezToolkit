# 半面混色时合并相邻兼容列

q0/q1普通部件不同，但晶体层均为红色，两列一起制造；q2单独蓝色结晶。另一半面直接堆叠普通料，最后交换拼合。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuSrCuCuCuCu:crcrcbCuCuCu`

共21步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../docs/proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuSrCuCuCu` |
| 1 | base | — | — | `CuP-P-CuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuSrCuCuCu:CuP-P-CuCuCu` |
| 3 | crystal | 2 | r | `CuCuSrCuCuCu:CucrcrCuCuCu` |
| 4 | cut | 3 | 0 | `CuCuSr------:Cucrcr------` |
| 5 | rotate | 4 | 5 | `CuSr------Cu:crcr------Cu` |
| 6 | cut | 5 | 0 | `CuSr--------:crcr--------` |
| 7 | rotate | 6 | 1 | `--CuSr------:--crcr------` |
| 8 | base | — | — | `CuCuCuCuCuCu` |
| 9 | base | — | — | `CuCuP-CuCuCu` |
| 10 | stack | 8, 9 | — | `CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 11 | crystal | 10 | b | `CuCuCuCuCuCu:CuCucbCuCuCu` |
| 12 | cut | 11 | 0 | `CuCuCu------:CuCucb------` |
| 13 | rotate | 12 | 1 | `--CuCuCu----:--CuCucb----` |
| 14 | cut | 13 | 1 | `------Cu----:------cb----` |
| 15 | swap | 7, 14 | 0 | `--CuSrCu----:--crcrcb----` |
| 16 | rotate | 15 | 5 | `CuSrCu------:crcrcb------` |
| 17 | base | — | — | `------CuCuCu` |
| 18 | base | — | — | `------CuCuCu` |
| 19 | stack | 17, 18 | — | `------CuCuCu:------CuCuCu` |
| 20 | swap | 16, 19 | 0 | `CuSrCuCuCuCu:crcrcbCuCuCu` |
