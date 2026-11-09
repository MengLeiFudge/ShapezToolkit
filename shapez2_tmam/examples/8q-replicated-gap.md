# 把四象限晶体间隙配方提升到八象限

目标每两列相同，复制块从q1开始。先压回四象限求角构造，再逐节点复制象限并把旋转参数乘二，最后恢复目标方向。中间图形由已证操作对应直接扩张。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------`

共48步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../research/proofs/04-stacking.md#s04-19)。
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
| 9 | base | — | — | `------------CuCu` |
| 10 | base | — | — | `------------P-P-` |
| 11 | stack | 9, 10 | — | `------------CuCu:------------P-P-` |
| 12 | base | — | — | `------------CuCu` |
| 13 | stack | 11, 12 | — | `------------CuCu:------------P-P-:------------CuCu` |
| 14 | base | — | — | `------------CuCu` |
| 15 | stack | 13, 14 | — | `------------CuCu:------------P-P-:------------CuCu:------------CuCu` |
| 16 | base | — | — | `------------CuCu` |
| 17 | stack | 15, 16 | — | `------------CuCu:------------P-P-:------------CuCu:------------CuCu:------------CuCu` |
| 18 | swap | 8, 17 | 0 | `crcr--------CuCu:CuCu--------P-P-:crcr--------CuCu:------------CuCu:------------CuCu` |
| 19 | rotate | 18 | 2 | `CuCucrcr--------:P-P-CuCu--------:CuCucrcr--------:CuCu------------:CuCu------------` |
| 20 | base | — | — | `CuCuP-P-CuCuCuCu` |
| 21 | crystal | 20 | r | `CuCucrcrCuCuCuCu` |
| 22 | cut | 21 | 0 | `CuCucrcr--------` |
| 23 | rotate | 22 | 2 | `----CuCucrcr----` |
| 24 | cut | 23 | 1 | `--------crcr----` |
| 25 | base | — | — | `--------CuCu----` |
| 26 | stack | 24, 25 | — | `--------crcr----:--------CuCu----` |
| 27 | base | — | — | `--------CuCu----` |
| 28 | stack | 26, 27 | — | `--------crcr----:--------CuCu----:--------CuCu----` |
| 29 | base | — | — | `--------CuCu----` |
| 30 | stack | 28, 29 | — | `--------crcr----:--------CuCu----:--------CuCu----:--------CuCu----` |
| 31 | base | — | — | `--------CuCu----` |
| 32 | stack | 30, 31 | — | `--------crcr----:--------CuCu----:--------CuCu----:--------CuCu----:--------CuCu----` |
| 33 | swap | 19, 32 | 0 | `CuCucrcrcrcr----:P-P-CuCuCuCu----:CuCucrcrCuCu----:CuCu----CuCu----:CuCu----CuCu----` |
| 34 | cut | 33 | 0 | `CuCuCuCu--------:P-P-------------:CuCucrcr--------:CuCu------------:CuCu------------` |
| 35 | base | — | — | `--------CuCuCuCu` |
| 36 | base | — | — | `--------P-P-CuCu` |
| 37 | stack | 35, 36 | — | `--------CuCuCuCu:--------P-P-CuCu` |
| 38 | base | — | — | `--------CuCuCuCu` |
| 39 | stack | 37, 38 | — | `--------CuCuCuCu:--------P-P-CuCu:--------CuCuCuCu` |
| 40 | base | — | — | `--------CuCuCuCu` |
| 41 | stack | 39, 40 | — | `--------CuCuCuCu:--------P-P-CuCu:--------CuCuCuCu:--------CuCuCuCu` |
| 42 | base | — | — | `--------CuCuCuCu` |
| 43 | stack | 41, 42 | — | `--------CuCuCuCu:--------P-P-CuCu:--------CuCuCuCu:--------CuCuCuCu:--------CuCuCuCu` |
| 44 | swap | 34, 43 | 0 | `CuCuCuCuCuCuCuCu:P-P-----P-P-CuCu:CuCucrcrCuCuCuCu:CuCu----CuCuCuCu:CuCu----CuCuCuCu` |
| 45 | rotate | 44 | 6 | `CuCuCuCuCuCuCuCu:----P-P-CuCuP-P-:crcrCuCuCuCuCuCu:----CuCuCuCuCuCu:----CuCuCuCuCuCu` |
| 46 | cut | 45 | 0 | `CuCuCuCu--------:----P-P---------:crcrCuCu--------:----CuCu--------:----CuCu--------` |
| 47 | rotate | 46 | 1 | `--CuCuCuCu------:------P-P-------:--crcrCuCu------:------CuCu------:------CuCu------` |
