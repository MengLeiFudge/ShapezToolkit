# 把四象限晶体间隙配方提升到八象限

目标每两列相同，复制块从q1开始。先压回四象限求角构造，再逐节点复制象限并把旋转参数乘二，最后恢复目标方向。中间图形由已证操作对应直接扩张。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------`

共41步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-P-CuCuCuCuCuCu` |
| 1 | crystal | 0 | r | `crcrCuCuCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `crcrCuCuCuCuCuCu:CuCuCuCuCuCuCuCu` |
| 4 | base | — | — | `P-P-CuCuCuCuCuCu` |
| 5 | stack | 3, 4 | — | `crcrCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:P-P-CuCuCuCuCuCu` |
| 6 | crystal | 5 | r | `crcrCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crcrCuCuCuCuCuCu` |
| 7 | rotate | 6 | 2 | `CuCucrcrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCucrcrCuCuCuCu` |
| 8 | cut | 7 | 0 | `CuCucrcr--------:CuCuCuCu--------:CuCucrcr--------` |
| 9 | rotate | 8 | 6 | `crcr--------CuCu:CuCu--------CuCu:crcr--------CuCu` |
| 10 | cut | 9 | 0 | `crcr------------:CuCu------------:crcr------------` |
| 11 | rotate | 10 | 2 | `----crcr--------:----CuCu--------:----crcr--------` |
| 12 | base | — | — | `----CuCu--------` |
| 13 | base | — | — | `----CuCu--------` |
| 14 | pin | 13 | — | `----P-P---------:----CuCu--------` |
| 15 | stack | 12, 14 | — | `----CuCu--------:----P-P---------:----CuCu--------` |
| 16 | base | — | — | `----CuCu--------` |
| 17 | stack | 15, 16 | — | `----CuCu--------:----P-P---------:----CuCu--------:----CuCu--------` |
| 18 | base | — | — | `----CuCu--------` |
| 19 | stack | 17, 18 | — | `----CuCu--------:----P-P---------:----CuCu--------:----CuCu--------:----CuCu--------` |
| 20 | rotate | 19 | 2 | `--------CuCu----:--------P-P-----:--------CuCu----:--------CuCu----:--------CuCu----` |
| 21 | swap | 11, 20 | 0 | `----crcrCuCu----:----CuCuP-P-----:----crcrCuCu----:--------CuCu----:--------CuCu----` |
| 22 | rotate | 21 | 6 | `crcrCuCu--------:CuCuP-P---------:crcrCuCu--------:----CuCu--------:----CuCu--------` |
| 23 | base | — | — | `CuCuCuCuCuCuP-P-` |
| 24 | crystal | 23 | r | `CuCuCuCuCuCucrcr` |
| 25 | rotate | 24 | 4 | `CuCucrcrCuCuCuCu` |
| 26 | cut | 25 | 0 | `CuCucrcr--------` |
| 27 | rotate | 26 | 6 | `crcr--------CuCu` |
| 28 | cut | 27 | 0 | `crcr------------` |
| 29 | rotate | 28 | 6 | `------------crcr` |
| 30 | base | — | — | `------------CuCu` |
| 31 | stack | 29, 30 | — | `------------crcr:------------CuCu` |
| 32 | base | — | — | `------------CuCu` |
| 33 | stack | 31, 32 | — | `------------crcr:------------CuCu:------------CuCu` |
| 34 | base | — | — | `------------CuCu` |
| 35 | stack | 33, 34 | — | `------------crcr:------------CuCu:------------CuCu:------------CuCu` |
| 36 | base | — | — | `------------CuCu` |
| 37 | stack | 35, 36 | — | `------------crcr:------------CuCu:------------CuCu:------------CuCu:------------CuCu` |
| 38 | swap | 22, 37 | 0 | `crcrCuCu----crcr:CuCuP-P-----CuCu:crcrCuCu----CuCu:----CuCu----CuCu:----CuCu----CuCu` |
| 39 | cut | 38 | 0 | `CuCuCuCu--------:----P-P---------:crcrCuCu--------:----CuCu--------:----CuCu--------` |
| 40 | rotate | 39 | 1 | `--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------` |
