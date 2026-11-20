# 用针下晶体间隙解除上料对齐冲突

q1四层柱与q5三层柱作下料。q3的NPN与q4的NN共享底顶普通块，不能同时全列压紧；改造NPN、NCN、CCN三列并对齐顶端，辅助C在一次堆叠中碎裂。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------`

共43步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../docs/proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 原下料 | `--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------` |
| 保留针下晶体间隙的三层上料 | `Cucr--CuCucr:--Cu--P-crcr:------CuCuCu` |
| 一次堆叠成品 | `CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `----------Cu` |
| 1 | base | — | — | `----------P-` |
| 2 | stack | 0, 1 | — | `----------Cu:----------P-` |
| 3 | base | — | — | `----------Cu` |
| 4 | stack | 2, 3 | — | `----------Cu:----------P-:----------Cu` |
| 5 | base | — | — | `CuCuCuCuCuCu` |
| 6 | base | — | — | `CuCuCuCuCuP-` |
| 7 | stack | 5, 6 | — | `CuCuCuCuCuCu:CuCuCuCuCuP-` |
| 8 | crystal | 7 | r | `CuCuCuCuCuCu:CuCuCuCuCucr` |
| 9 | cut | 8 | 1 | `------CuCuCu:------CuCucr` |
| 10 | rotate | 9 | 1 | `Cu------CuCu:cr------CuCu` |
| 11 | cut | 10 | 0 | `Cu----------:cr----------` |
| 12 | base | — | — | `Cu----------` |
| 13 | stack | 11, 12 | — | `Cu----------:cr----------:Cu----------` |
| 14 | swap | 4, 13 | 1 | `Cu--------Cu:cr--------P-:Cu--------Cu` |
| 15 | rotate | 14 | 5 | `--------CuCu:--------P-cr:--------CuCu` |
| 16 | base | — | — | `CuCuCuCuCuP-` |
| 17 | base | — | — | `CuCuCuCuCuP-` |
| 18 | stack | 16, 17 | — | `CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 19 | crystal | 18 | r | `CuCuCuCuCucr:CuCuCuCuCucr` |
| 20 | cut | 19 | 1 | `------CuCucr:------CuCucr` |
| 21 | rotate | 20 | 1 | `cr------CuCu:cr------CuCu` |
| 22 | cut | 21 | 0 | `cr----------:cr----------` |
| 23 | base | — | — | `Cu----------` |
| 24 | stack | 22, 23 | — | `cr----------:cr----------:Cu----------` |
| 25 | swap | 15, 24 | 1 | `cr------CuCu:cr------P-cr:Cu------CuCu` |
| 26 | rotate | 25 | 5 | `------CuCucr:------P-crcr:------CuCuCu` |
| 27 | base | — | — | `CuCuP-CuCuCu` |
| 28 | crystal | 27 | r | `CuCucrCuCuCu` |
| 29 | cut | 28 | 0 | `CuCucr------` |
| 30 | rotate | 29 | 5 | `Cucr------Cu` |
| 31 | cut | 30 | 0 | `Cucr--------` |
| 32 | base | — | — | `--Cu--------` |
| 33 | stack | 31, 32 | — | `Cucr--------:--Cu--------` |
| 34 | swap | 33, 26 | 0 | `Cucr--CuCucr:--Cu--P-crcr:------CuCuCu` |
| 35 | base | — | — | `--Cu------Cu` |
| 36 | base | — | — | `--Cu------Cu` |
| 37 | stack | 35, 36 | — | `--Cu------Cu:--Cu------Cu` |
| 38 | base | — | — | `--Cu------Cu` |
| 39 | stack | 37, 38 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu` |
| 40 | base | — | — | `--Cu--------` |
| 41 | stack | 39, 40 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------` |
| 42 | stack | 41, 34 | — | `CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------` |
