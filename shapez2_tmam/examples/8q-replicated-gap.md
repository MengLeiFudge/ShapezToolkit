# 把四象限晶体间隙配方提升到八象限

目标每两列相同，复制块从q1开始。先压回四象限求角构造，再逐节点复制象限并把旋转参数乘二，最后恢复目标方向。中间图形由已证操作对应直接扩张。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------`

共37步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuP-P-CuCuCuCu` |
| 1 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuP-P-CuCuCuCu:CuCuCuCuCuCuCuCu` |
| 3 | base | — | — | `CuCuP-P-CuCuCuCu` |
| 4 | stack | 2, 3 | — | `CuCuP-P-CuCuCuCu:CuCuCuCuCuCuCuCu:CuCuP-P-CuCuCuCu` |
| 5 | crystal | 4 | r | `CuCucrcrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCucrcrCuCuCuCu` |
| 6 | cut | 5 | 0 | `CuCucrcr--------:CuCuCuCu--------:CuCucrcr--------` |
| 7 | rotate | 6 | 6 | `crcr--------CuCu:CuCu--------CuCu:crcr--------CuCu` |
| 8 | cut | 7 | 0 | `crcr------------:CuCu------------:crcr------------` |
| 9 | rotate | 8 | 2 | `----crcr--------:----CuCu--------:----crcr--------` |
| 10 | base | — | — | `--------CuCu----` |
| 11 | base | — | — | `--------CuCu----` |
| 12 | pin | 11 | — | `--------P-P-----:--------CuCu----` |
| 13 | stack | 10, 12 | — | `--------CuCu----:--------P-P-----:--------CuCu----` |
| 14 | base | — | — | `--------CuCu----` |
| 15 | stack | 13, 14 | — | `--------CuCu----:--------P-P-----:--------CuCu----:--------CuCu----` |
| 16 | base | — | — | `--------CuCu----` |
| 17 | stack | 15, 16 | — | `--------CuCu----:--------P-P-----:--------CuCu----:--------CuCu----:--------CuCu----` |
| 18 | swap | 9, 17 | 0 | `----crcrCuCu----:----CuCuP-P-----:----crcrCuCu----:--------CuCu----:--------CuCu----` |
| 19 | rotate | 18 | 6 | `crcrCuCu--------:CuCuP-P---------:crcrCuCu--------:----CuCu--------:----CuCu--------` |
| 20 | base | — | — | `CuCuP-P-CuCuCuCu` |
| 21 | crystal | 20 | r | `CuCucrcrCuCuCuCu` |
| 22 | cut | 21 | 0 | `CuCucrcr--------` |
| 23 | rotate | 22 | 6 | `crcr--------CuCu` |
| 24 | cut | 23 | 0 | `crcr------------` |
| 25 | rotate | 24 | 6 | `------------crcr` |
| 26 | base | — | — | `------------CuCu` |
| 27 | stack | 25, 26 | — | `------------crcr:------------CuCu` |
| 28 | base | — | — | `------------CuCu` |
| 29 | stack | 27, 28 | — | `------------crcr:------------CuCu:------------CuCu` |
| 30 | base | — | — | `------------CuCu` |
| 31 | stack | 29, 30 | — | `------------crcr:------------CuCu:------------CuCu:------------CuCu` |
| 32 | base | — | — | `------------CuCu` |
| 33 | stack | 31, 32 | — | `------------crcr:------------CuCu:------------CuCu:------------CuCu:------------CuCu` |
| 34 | swap | 19, 33 | 0 | `crcrCuCu----crcr:CuCuP-P-----CuCu:crcrCuCu----CuCu:----CuCu----CuCu:----CuCu----CuCu` |
| 35 | cut | 34 | 0 | `CuCuCuCu--------:----P-P---------:crcrCuCu--------:----CuCu--------:----CuCu--------` |
| 36 | rotate | 35 | 1 | `--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------` |
