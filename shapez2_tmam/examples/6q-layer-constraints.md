# 用针下晶体间隙解除上料对齐冲突

q1四层柱与q5三层柱作下料。q3的NPN与q4的NN共享底顶普通块，不能同时全列压紧；改造NPN、NCN、CCN三列并对齐顶端，辅助C在一次堆叠中碎裂。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------`

共45步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
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
| 1 | base | — | — | `----------Cu` |
| 2 | pin | 1 | — | `----------P-:----------Cu` |
| 3 | stack | 0, 2 | — | `----------Cu:----------P-:----------Cu` |
| 4 | base | — | — | `CuCuCuCuCuCu` |
| 5 | base | — | — | `CuCuCuCuCuP-` |
| 6 | stack | 4, 5 | — | `CuCuCuCuCuCu:CuCuCuCuCuP-` |
| 7 | crystal | 6 | r | `CuCuCuCuCuCu:CuCuCuCuCucr` |
| 8 | cut | 7 | 1 | `------CuCuCu:------CuCucr` |
| 9 | rotate | 8 | 1 | `Cu------CuCu:cr------CuCu` |
| 10 | cut | 9 | 0 | `Cu----------:cr----------` |
| 11 | base | — | — | `Cu----------` |
| 12 | stack | 10, 11 | — | `Cu----------:cr----------:Cu----------` |
| 13 | swap | 3, 12 | 1 | `Cu--------Cu:cr--------P-:Cu--------Cu` |
| 14 | rotate | 13 | 5 | `--------CuCu:--------P-cr:--------CuCu` |
| 15 | base | — | — | `CuCuCuCuCuP-` |
| 16 | base | — | — | `CuCuCuCuCuP-` |
| 17 | stack | 15, 16 | — | `CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 18 | crystal | 17 | r | `CuCuCuCuCucr:CuCuCuCuCucr` |
| 19 | cut | 18 | 1 | `------CuCucr:------CuCucr` |
| 20 | rotate | 19 | 1 | `cr------CuCu:cr------CuCu` |
| 21 | cut | 20 | 0 | `cr----------:cr----------` |
| 22 | base | — | — | `Cu----------` |
| 23 | stack | 21, 22 | — | `cr----------:cr----------:Cu----------` |
| 24 | swap | 14, 23 | 1 | `cr------CuCu:cr------P-cr:Cu------CuCu` |
| 25 | rotate | 24 | 5 | `------CuCucr:------P-crcr:------CuCuCu` |
| 26 | base | — | — | `CuCuCuCuCuP-` |
| 27 | crystal | 26 | r | `CuCuCuCuCucr` |
| 28 | cut | 27 | 1 | `------CuCucr` |
| 29 | rotate | 28 | 1 | `cr------CuCu` |
| 30 | cut | 29 | 0 | `cr----------` |
| 31 | base | — | — | `Cu----------` |
| 32 | stack | 30, 31 | — | `cr----------:Cu----------` |
| 33 | base | — | — | `----------Cu` |
| 34 | swap | 33, 32 | 1 | `cr--------Cu:Cu----------` |
| 35 | rotate | 34 | 1 | `Cucr--------:--Cu--------` |
| 36 | swap | 35, 25 | 0 | `Cucr--CuCucr:--Cu--P-crcr:------CuCuCu` |
| 37 | base | — | — | `--Cu------Cu` |
| 38 | base | — | — | `--Cu------Cu` |
| 39 | stack | 37, 38 | — | `--Cu------Cu:--Cu------Cu` |
| 40 | base | — | — | `--Cu------Cu` |
| 41 | stack | 39, 40 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu` |
| 42 | base | — | — | `--Cu--------` |
| 43 | stack | 41, 42 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------` |
| 44 | stack | 43, 36 | — | `CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------` |
