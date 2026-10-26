# 非K下料上的紧凑交错上料

H旁准备q5两层普通柱；目标新增q3地面普通格及q5的NPN高尾。先让新增格独立下落，得到4步准备的三层无晶体上料，再一次堆到原下料。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu`

共56步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 已有非K下料 | `Cu--------Cu:----------Cu:crCuCu------:cr--Cu------:crCuCu------` |
| 紧凑无晶体上料 | `------Cu--Cu:----------P-:----------Cu` |
| 一次堆叠成品 | `Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuP-CuCuCu` |
| 1 | crystal | 0 | r | `CuCucrCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `CuCucrCuCuCu:CuCuCuCuCuCu` |
| 4 | base | — | — | `CuCuP-CuCuCu` |
| 5 | stack | 3, 4 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 6 | crystal | 5 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu` |
| 7 | base | — | — | `CuCuP-CuCuCu` |
| 8 | stack | 6, 7 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCuP-CuCuCu` |
| 9 | crystal | 8 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 10 | base | — | — | `CuCuP-CuCuCu` |
| 11 | stack | 9, 10 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCuP-CuCuCu` |
| 12 | crystal | 11 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 13 | cut | 12 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 14 | rotate | 13 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 15 | cut | 14 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 16 | rotate | 15 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 17 | base | — | — | `CuCuP-CuCuCu` |
| 18 | crystal | 17 | r | `CuCucrCuCuCu` |
| 19 | cut | 18 | 0 | `CuCucr------` |
| 20 | rotate | 19 | 1 | `--CuCucr----` |
| 21 | cut | 20 | 1 | `------cr----` |
| 22 | swap | 16, 21 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 23 | rotate | 22 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 24 | base | — | — | `----------Cu` |
| 25 | base | — | — | `----------Cu` |
| 26 | pin | 25 | — | `----------P-:----------Cu` |
| 27 | stack | 24, 26 | — | `----------Cu:----------P-:----------Cu` |
| 28 | base | — | — | `----------Cu` |
| 29 | stack | 27, 28 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 30 | base | — | — | `----------Cu` |
| 31 | stack | 29, 30 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 32 | swap | 23, 31 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 33 | rotate | 32 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 34 | cut | 33 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 35 | base | — | — | `----------Cu` |
| 36 | base | — | — | `----------Cu` |
| 37 | stack | 35, 36 | — | `----------Cu:----------Cu` |
| 38 | base | — | — | `------CuCuCu` |
| 39 | stack | 37, 38 | — | `----------Cu:----------Cu:------CuCuCu` |
| 40 | base | — | — | `--------Cu--` |
| 41 | stack | 39, 40 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--` |
| 42 | base | — | — | `------CuCu--` |
| 43 | stack | 41, 42 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 44 | swap | 34, 43 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 45 | rotate | 44 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 46 | cut | 45 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 47 | base | — | — | `----------Cu` |
| 48 | base | — | — | `----------Cu` |
| 49 | stack | 47, 48 | — | `----------Cu:----------Cu` |
| 50 | stack | 46, 49 | — | `Cu--------Cu:----------Cu:crCuCu------:cr--Cu------:crCuCu------` |
| 51 | base | — | — | `------Cu--Cu` |
| 52 | base | — | — | `----------Cu` |
| 53 | pin | 52 | — | `----------P-:----------Cu` |
| 54 | stack | 51, 53 | — | `------Cu--Cu:----------P-:----------Cu` |
| 55 | stack | 50, 54 | — | `Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu` |
