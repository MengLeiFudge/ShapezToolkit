# 普通内块受列顶保护的悬空环

外组与q2第四层普通块互相支撑；内块两侧q1、q3列顶均在第五层，后续从上方加料无法粘到内块。它不属于K，但可安全逐层追加。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------`

共44步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
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
| 0 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 1 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu` |
| 3 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 4 | stack | 2, 3 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 5 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 6 | stack | 4, 5 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu:CuCuCuP-CuCuCuCu` |
| 7 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 8 | stack | 6, 7 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu:CuCuCuP-CuCuCuCu:CuCuCuP-CuCuCuCu` |
| 9 | crystal | 8 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 10 | cut | 9 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 11 | rotate | 10 | 5 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 12 | cut | 11 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 13 | rotate | 12 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 14 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 15 | crystal | 14 | r | `CuCuCucrCuCuCuCu` |
| 16 | cut | 15 | 0 | `CuCuCucr--------` |
| 17 | rotate | 16 | 1 | `--CuCuCucr------` |
| 18 | cut | 17 | 1 | `--------cr------` |
| 19 | swap | 13, 18 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 20 | rotate | 19 | 5 | `crcr------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 21 | base | — | — | `--------------Cu` |
| 22 | base | — | — | `--------------Cu` |
| 23 | pin | 22 | — | `--------------P-:--------------Cu` |
| 24 | stack | 21, 23 | — | `--------------Cu:--------------P-:--------------Cu` |
| 25 | base | — | — | `--------------Cu` |
| 26 | stack | 24, 25 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu` |
| 27 | base | — | — | `--------------Cu` |
| 28 | stack | 26, 27 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu:--------------Cu` |
| 29 | swap | 20, 28 | 0 | `crcr----------Cu:Cu------------P-:cr------------Cu:cr------------Cu:cr------------Cu` |
| 30 | rotate | 29 | 3 | `----Cucrcr------:----P-Cu--------:----Cucr--------:----Cucr--------:----Cucr--------` |
| 31 | cut | 30 | 0 | `----CuCu--------:----P-----------:----Cucr--------:----Cucr--------:----Cucr--------` |
| 32 | base | — | — | `--------------Cu` |
| 33 | base | — | — | `--------------Cu` |
| 34 | stack | 32, 33 | — | `--------------Cu:--------------Cu` |
| 35 | base | — | — | `--------CuCuCuCu` |
| 36 | stack | 34, 35 | — | `--------------Cu:--------------Cu:--------CuCuCuCu` |
| 37 | base | — | — | `----------Cu----` |
| 38 | stack | 36, 37 | — | `--------------Cu:--------------Cu:--------CuCuCuCu:----------Cu----` |
| 39 | base | — | — | `--------CuCuCu--` |
| 40 | stack | 38, 39 | — | `--------------Cu:--------------Cu:--------CuCuCuCu:----------Cu----:--------CuCuCu--` |
| 41 | swap | 31, 40 | 0 | `----CuCu------Cu:----P---------Cu:----CucrCuCuCuCu:----Cucr--Cu----:----CucrCuCuCu--` |
| 42 | rotate | 41 | 5 | `Cu------Cu----Cu:--------Cu----P-:crCuCuCuCu----Cu:cr--Cu--------Cu:crCuCuCu------Cu` |
| 43 | cut | 42 | 0 | `Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------` |
