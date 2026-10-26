# 普通内块受列顶保护的悬空环

外组与q2第四层普通块互相支撑；内块两侧q1、q3列顶均在第五层，后续从上方加料无法粘到内块。它不属于K，但可安全逐层追加。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------`

共47步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 1 | crystal | 0 | r | `CuCuCucrCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu` |
| 4 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 5 | stack | 3, 4 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 6 | crystal | 5 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu` |
| 7 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 8 | stack | 6, 7 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 9 | crystal | 8 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 10 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 11 | stack | 9, 10 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 12 | crystal | 11 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 13 | cut | 12 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 14 | rotate | 13 | 5 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 15 | cut | 14 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 16 | rotate | 15 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 17 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 18 | crystal | 17 | r | `CuCuCucrCuCuCuCu` |
| 19 | cut | 18 | 0 | `CuCuCucr--------` |
| 20 | rotate | 19 | 1 | `--CuCuCucr------` |
| 21 | cut | 20 | 1 | `--------cr------` |
| 22 | swap | 16, 21 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 23 | rotate | 22 | 5 | `crcr------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 24 | base | — | — | `--------------Cu` |
| 25 | base | — | — | `--------------Cu` |
| 26 | pin | 25 | — | `--------------P-:--------------Cu` |
| 27 | stack | 24, 26 | — | `--------------Cu:--------------P-:--------------Cu` |
| 28 | base | — | — | `--------------Cu` |
| 29 | stack | 27, 28 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu` |
| 30 | base | — | — | `--------------Cu` |
| 31 | stack | 29, 30 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu:--------------Cu` |
| 32 | swap | 23, 31 | 0 | `crcr----------Cu:Cu------------P-:cr------------Cu:cr------------Cu:cr------------Cu` |
| 33 | rotate | 32 | 3 | `----Cucrcr------:----P-Cu--------:----Cucr--------:----Cucr--------:----Cucr--------` |
| 34 | cut | 33 | 0 | `----CuCu--------:----P-----------:----Cucr--------:----Cucr--------:----Cucr--------` |
| 35 | base | — | — | `--------------Cu` |
| 36 | base | — | — | `--------------Cu` |
| 37 | stack | 35, 36 | — | `--------------Cu:--------------Cu` |
| 38 | base | — | — | `--------CuCuCuCu` |
| 39 | stack | 37, 38 | — | `--------------Cu:--------------Cu:--------CuCuCuCu` |
| 40 | base | — | — | `----------Cu----` |
| 41 | stack | 39, 40 | — | `--------------Cu:--------------Cu:--------CuCuCuCu:----------Cu----` |
| 42 | base | — | — | `--------CuCuCu--` |
| 43 | stack | 41, 42 | — | `--------------Cu:--------------Cu:--------CuCuCuCu:----------Cu----:--------CuCuCu--` |
| 44 | swap | 34, 43 | 0 | `----CuCu------Cu:----P---------Cu:----CucrCuCuCuCu:----Cucr--Cu----:----CucrCuCuCu--` |
| 45 | rotate | 44 | 5 | `Cu------Cu----Cu:--------Cu----P-:crCuCuCuCu----Cu:cr--Cu--------Cu:crCuCuCu------Cu` |
| 46 | cut | 45 | 0 | `Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------` |
