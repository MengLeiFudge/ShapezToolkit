# 非K下料上的紧凑交错上料

H旁准备q5两层普通柱；目标新增q3地面普通格及q5的NPN高尾。先让新增格独立下落，得到5步准备的三层无晶体上料，再一次堆到原下料。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu`

共55步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../research/proofs/04-stacking.md#s04-19)。
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
| 0 | base | — | — | `CuCuCuCuCuP-` |
| 1 | base | — | — | `CuCuCuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu` |
| 3 | base | — | — | `CuCuCuCuCuP-` |
| 4 | stack | 2, 3 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-` |
| 5 | base | — | — | `CuCuCuCuCuP-` |
| 6 | stack | 4, 5 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 7 | base | — | — | `CuCuCuCuCuP-` |
| 8 | stack | 6, 7 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-:CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 9 | crystal | 8 | r | `CuCuCuCuCucr:CuCuCuCuCuCu:CuCuCuCuCucr:CuCuCuCuCucr:CuCuCuCuCucr` |
| 10 | cut | 9 | 1 | `------CuCucr:------CuCuCu:------CuCucr:------CuCucr:------CuCucr` |
| 11 | rotate | 10 | 1 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 12 | cut | 11 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 13 | rotate | 12 | 5 | `----------cr:----------Cu:----------cr:----------cr:----------cr` |
| 14 | base | — | — | `CuCuCuCuCuP-` |
| 15 | crystal | 14 | r | `CuCuCuCuCucr` |
| 16 | cut | 15 | 1 | `------CuCucr` |
| 17 | rotate | 16 | 1 | `cr------CuCu` |
| 18 | cut | 17 | 0 | `cr----------` |
| 19 | swap | 13, 18 | 1 | `cr--------cr:----------Cu:----------cr:----------cr:----------cr` |
| 20 | rotate | 19 | 1 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 21 | base | — | — | `----------Cu` |
| 22 | base | — | — | `----------P-` |
| 23 | stack | 21, 22 | — | `----------Cu:----------P-` |
| 24 | base | — | — | `----------Cu` |
| 25 | stack | 23, 24 | — | `----------Cu:----------P-:----------Cu` |
| 26 | base | — | — | `----------Cu` |
| 27 | stack | 25, 26 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 28 | base | — | — | `----------Cu` |
| 29 | stack | 27, 28 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 30 | swap | 20, 29 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 31 | rotate | 30 | 5 | `cr------Cucr:--------P-Cu:--------Cucr:--------Cucr:--------Cucr` |
| 32 | cut | 31 | 1 | `--------CuCu:--------P---:--------Cucr:--------Cucr:--------Cucr` |
| 33 | base | — | — | `----Cu------` |
| 34 | base | — | — | `----Cu------` |
| 35 | stack | 33, 34 | — | `----Cu------:----Cu------` |
| 36 | base | — | — | `CuCuCu------` |
| 37 | stack | 35, 36 | — | `----Cu------:----Cu------:CuCuCu------` |
| 38 | base | — | — | `--Cu--------` |
| 39 | stack | 37, 38 | — | `----Cu------:----Cu------:CuCuCu------:--Cu--------` |
| 40 | base | — | — | `CuCu--------` |
| 41 | stack | 39, 40 | — | `----Cu------:----Cu------:CuCuCu------:--Cu--------:CuCu--------` |
| 42 | swap | 32, 41 | 1 | `----Cu--CuCu:----Cu--P---:CuCuCu--Cucr:--Cu----Cucr:CuCu----Cucr` |
| 43 | rotate | 42 | 1 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 44 | cut | 43 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 45 | base | — | — | `----------Cu` |
| 46 | base | — | — | `----------Cu` |
| 47 | stack | 45, 46 | — | `----------Cu:----------Cu` |
| 48 | stack | 44, 47 | — | `Cu--------Cu:----------Cu:crCuCu------:cr--Cu------:crCuCu------` |
| 49 | base | — | — | `------Cu--Cu` |
| 50 | base | — | — | `----------P-` |
| 51 | stack | 49, 50 | — | `------Cu--Cu:----------P-` |
| 52 | base | — | — | `----------Cu` |
| 53 | stack | 51, 52 | — | `------Cu--Cu:----------P-:----------Cu` |
| 54 | stack | 48, 53 | — | `Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu` |
