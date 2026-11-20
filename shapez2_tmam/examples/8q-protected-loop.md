# 普通内块受列顶保护的悬空环

外组与q2第四层普通块互相支撑；内块两侧q1、q3列顶均在第五层，后续从上方加料无法粘到内块。它不属于K，但可安全逐层追加。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------`

共45步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../docs/proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 独立柱准备形 | `crcr----------Cu:Cu------------P-:cr------------Cu:cr------------Cu:cr------------Cu` |
| 切掉牺牲晶体的A | `Cu------------Cu:--------------P-:cr------------Cu:cr------------Cu:cr------------Cu` |
| 带q2内块的脚手架 | `--------Cu------:--------Cu------:--CuCuCuCu------:----Cu----------:--CuCuCu--------` |
| 切掉外侧支撑前 | `Cu------Cu----Cu:--------Cu----P-:crCuCuCuCu----Cu:cr--Cu--------Cu:crCuCuCu------Cu` |
| 受保护悬空环W_4 | `Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 1 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu` |
| 3 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 4 | stack | 2, 3 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCuP-` |
| 5 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 6 | stack | 4, 5 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 7 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 8 | stack | 6, 7 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 9 | crystal | 8 | r | `CuCuCuCuCuCuCucr:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr` |
| 10 | cut | 9 | 1 | `--------CuCuCucr:--------CuCuCuCu:--------CuCuCucr:--------CuCuCucr:--------CuCuCucr` |
| 11 | rotate | 10 | 1 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 12 | cut | 11 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 13 | rotate | 12 | 7 | `--------------cr:--------------Cu:--------------cr:--------------cr:--------------cr` |
| 14 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 15 | crystal | 14 | r | `CuCuCuCuCuCuCucr` |
| 16 | cut | 15 | 1 | `--------CuCuCucr` |
| 17 | rotate | 16 | 1 | `cr--------CuCuCu` |
| 18 | cut | 17 | 0 | `cr--------------` |
| 19 | swap | 13, 18 | 1 | `cr------------cr:--------------Cu:--------------cr:--------------cr:--------------cr` |
| 20 | rotate | 19 | 1 | `crcr------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 21 | base | — | — | `--------------Cu` |
| 22 | base | — | — | `--------------P-` |
| 23 | stack | 21, 22 | — | `--------------Cu:--------------P-` |
| 24 | base | — | — | `--------------Cu` |
| 25 | stack | 23, 24 | — | `--------------Cu:--------------P-:--------------Cu` |
| 26 | base | — | — | `--------------Cu` |
| 27 | stack | 25, 26 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu` |
| 28 | base | — | — | `--------------Cu` |
| 29 | stack | 27, 28 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu:--------------Cu` |
| 30 | swap | 20, 29 | 0 | `crcr----------Cu:Cu------------P-:cr------------Cu:cr------------Cu:cr------------Cu` |
| 31 | rotate | 30 | 7 | `cr----------Cucr:------------P-Cu:------------Cucr:------------Cucr:------------Cucr` |
| 32 | cut | 31 | 1 | `------------CuCu:------------P---:------------Cucr:------------Cucr:------------Cucr` |
| 33 | base | — | — | `------Cu--------` |
| 34 | base | — | — | `------Cu--------` |
| 35 | stack | 33, 34 | — | `------Cu--------:------Cu--------` |
| 36 | base | — | — | `CuCuCuCu--------` |
| 37 | stack | 35, 36 | — | `------Cu--------:------Cu--------:CuCuCuCu--------` |
| 38 | base | — | — | `--Cu------------` |
| 39 | stack | 37, 38 | — | `------Cu--------:------Cu--------:CuCuCuCu--------:--Cu------------` |
| 40 | base | — | — | `CuCuCu----------` |
| 41 | stack | 39, 40 | — | `------Cu--------:------Cu--------:CuCuCuCu--------:--Cu------------:CuCuCu----------` |
| 42 | swap | 32, 41 | 1 | `------Cu----CuCu:------Cu----P---:CuCuCuCu----Cucr:--Cu--------Cucr:CuCuCu------Cucr` |
| 43 | rotate | 42 | 1 | `Cu------Cu----Cu:--------Cu----P-:crCuCuCuCu----Cu:cr--Cu--------Cu:crCuCuCu------Cu` |
| 44 | cut | 43 | 0 | `Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------` |
