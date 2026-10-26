# 把四象限晶体间隙配方提升到八象限

目标每两列相同，复制块从q1开始。先压回四象限求角构造，再逐节点复制象限并把旋转参数乘二，最后恢复目标方向。中间图形由已证操作对应直接扩张。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------`

共38步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuP-P-CuCuCuCu` |
| 1 | crystal | 0 | r | `CuCucrcrCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `CuCucrcrCuCuCuCu:CuCuCuCuCuCuCuCu` |
| 4 | base | — | — | `CuCuP-P-CuCuCuCu` |
| 5 | stack | 3, 4 | — | `CuCucrcrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuP-P-CuCuCuCu` |
| 6 | crystal | 5 | r | `CuCucrcrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCucrcrCuCuCuCu` |
| 7 | cut | 6 | 0 | `CuCucrcr--------:CuCuCuCu--------:CuCucrcr--------` |
| 8 | rotate | 7 | 6 | `crcr--------CuCu:CuCu--------CuCu:crcr--------CuCu` |
| 9 | cut | 8 | 0 | `crcr------------:CuCu------------:crcr------------` |
| 10 | rotate | 9 | 2 | `----crcr--------:----CuCu--------:----crcr--------` |
| 11 | base | — | — | `--------CuCu----` |
| 12 | base | — | — | `--------CuCu----` |
| 13 | pin | 12 | — | `--------P-P-----:--------CuCu----` |
| 14 | stack | 11, 13 | — | `--------CuCu----:--------P-P-----:--------CuCu----` |
| 15 | base | — | — | `--------CuCu----` |
| 16 | stack | 14, 15 | — | `--------CuCu----:--------P-P-----:--------CuCu----:--------CuCu----` |
| 17 | base | — | — | `--------CuCu----` |
| 18 | stack | 16, 17 | — | `--------CuCu----:--------P-P-----:--------CuCu----:--------CuCu----:--------CuCu----` |
| 19 | swap | 10, 18 | 0 | `----crcrCuCu----:----CuCuP-P-----:----crcrCuCu----:--------CuCu----:--------CuCu----` |
| 20 | rotate | 19 | 6 | `crcrCuCu--------:CuCuP-P---------:crcrCuCu--------:----CuCu--------:----CuCu--------` |
| 21 | base | — | — | `CuCuP-P-CuCuCuCu` |
| 22 | crystal | 21 | r | `CuCucrcrCuCuCuCu` |
| 23 | cut | 22 | 0 | `CuCucrcr--------` |
| 24 | rotate | 23 | 6 | `crcr--------CuCu` |
| 25 | cut | 24 | 0 | `crcr------------` |
| 26 | rotate | 25 | 6 | `------------crcr` |
| 27 | base | — | — | `------------CuCu` |
| 28 | stack | 26, 27 | — | `------------crcr:------------CuCu` |
| 29 | base | — | — | `------------CuCu` |
| 30 | stack | 28, 29 | — | `------------crcr:------------CuCu:------------CuCu` |
| 31 | base | — | — | `------------CuCu` |
| 32 | stack | 30, 31 | — | `------------crcr:------------CuCu:------------CuCu:------------CuCu` |
| 33 | base | — | — | `------------CuCu` |
| 34 | stack | 32, 33 | — | `------------crcr:------------CuCu:------------CuCu:------------CuCu:------------CuCu` |
| 35 | swap | 20, 34 | 0 | `crcrCuCu----crcr:CuCuP-P-----CuCu:crcrCuCu----CuCu:----CuCu----CuCu:----CuCu----CuCu` |
| 36 | cut | 35 | 0 | `CuCuCuCu--------:----P-P---------:crcrCuCu--------:----CuCu--------:----CuCu--------` |
| 37 | rotate | 36 | 1 | `--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------` |
