# 普通内块受列顶保护的悬空环

外组与q2第四层普通块互相支撑；内块两侧q1、q3列顶均在第五层，后续从上方加料无法粘到内块。它不属于K，但可安全逐层追加。

配置：8象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------`

共51步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

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
| 0 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCuCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu` |
| 4 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 5 | stack | 3, 4 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:P-CuCuCuCuCuCuCu` |
| 6 | crystal | 5 | r | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu` |
| 7 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 8 | stack | 6, 7 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:P-CuCuCuCuCuCuCu` |
| 9 | crystal | 8 | r | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu` |
| 10 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 11 | stack | 9, 10 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:P-CuCuCuCuCuCuCu` |
| 12 | crystal | 11 | r | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu` |
| 13 | rotate | 12 | 3 | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 14 | cut | 13 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 15 | rotate | 14 | 5 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 16 | cut | 15 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 17 | rotate | 16 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 18 | base | — | — | `CuP-CuCuCuCuCuCu` |
| 19 | crystal | 18 | r | `CucrCuCuCuCuCuCu` |
| 20 | rotate | 19 | 2 | `CuCuCucrCuCuCuCu` |
| 21 | cut | 20 | 0 | `CuCuCucr--------` |
| 22 | rotate | 21 | 5 | `cr--------CuCuCu` |
| 23 | cut | 22 | 0 | `cr--------------` |
| 24 | rotate | 23 | 4 | `--------cr------` |
| 25 | swap | 17, 24 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 26 | rotate | 25 | 5 | `crcr------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 27 | base | — | — | `--------------Cu` |
| 28 | base | — | — | `--------------Cu` |
| 29 | pin | 28 | — | `--------------P-:--------------Cu` |
| 30 | stack | 27, 29 | — | `--------------Cu:--------------P-:--------------Cu` |
| 31 | base | — | — | `--------------Cu` |
| 32 | stack | 30, 31 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu` |
| 33 | base | — | — | `--------------Cu` |
| 34 | stack | 32, 33 | — | `--------------Cu:--------------P-:--------------Cu:--------------Cu:--------------Cu` |
| 35 | swap | 26, 34 | 0 | `crcr----------Cu:Cu------------P-:cr------------Cu:cr------------Cu:cr------------Cu` |
| 36 | rotate | 35 | 3 | `----Cucrcr------:----P-Cu--------:----Cucr--------:----Cucr--------:----Cucr--------` |
| 37 | cut | 36 | 0 | `----CuCu--------:----P-----------:----Cucr--------:----Cucr--------:----Cucr--------` |
| 38 | base | — | — | `--------Cu------` |
| 39 | base | — | — | `--------Cu------` |
| 40 | stack | 38, 39 | — | `--------Cu------:--------Cu------` |
| 41 | base | — | — | `--CuCuCuCu------` |
| 42 | stack | 40, 41 | — | `--------Cu------:--------Cu------:--CuCuCuCu------` |
| 43 | base | — | — | `----Cu----------` |
| 44 | stack | 42, 43 | — | `--------Cu------:--------Cu------:--CuCuCuCu------:----Cu----------` |
| 45 | base | — | — | `--CuCuCu--------` |
| 46 | stack | 44, 45 | — | `--------Cu------:--------Cu------:--CuCuCuCu------:----Cu----------:--CuCuCu--------` |
| 47 | rotate | 46 | 3 | `--------------Cu:--------------Cu:--------CuCuCuCu:----------Cu----:--------CuCuCu--` |
| 48 | swap | 37, 47 | 0 | `----CuCu------Cu:----P---------Cu:----CucrCuCuCuCu:----Cucr--Cu----:----CucrCuCuCu--` |
| 49 | rotate | 48 | 5 | `Cu------Cu----Cu:--------Cu----P-:crCuCuCuCu----Cu:cr--Cu--------Cu:crCuCuCu------Cu` |
| 50 | cut | 49 | 0 | `Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------` |
