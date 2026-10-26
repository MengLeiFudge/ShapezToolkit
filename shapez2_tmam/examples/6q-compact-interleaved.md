# 非K下料上的紧凑交错上料

H旁准备q5两层普通柱；目标新增q3地面普通格及q5的NPN高尾。先让新增格独立下落，得到4步准备的三层无晶体上料，再一次堆到原下料。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu`

共60步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

| 阶段 | 结果 |
|---|---|
| 已有非K下料 | `Cu--------Cu:----------Cu:crCuCu------:cr--Cu------:crCuCu------` |
| 紧凑无晶体上料 | `------Cu--Cu:----------P-:----------Cu` |
| 一次堆叠成品 | `Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCuCuCu:CuCuCuCuCuCu` |
| 4 | base | — | — | `P-CuCuCuCuCu` |
| 5 | stack | 3, 4 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:P-CuCuCuCuCu` |
| 6 | crystal | 5 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu` |
| 7 | base | — | — | `P-CuCuCuCuCu` |
| 8 | stack | 6, 7 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 9 | crystal | 8 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 10 | base | — | — | `P-CuCuCuCuCu` |
| 11 | stack | 9, 10 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 12 | crystal | 11 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 13 | rotate | 12 | 2 | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 14 | cut | 13 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 15 | rotate | 14 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 16 | cut | 15 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 17 | rotate | 16 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 18 | base | — | — | `CuP-CuCuCuCu` |
| 19 | crystal | 18 | r | `CucrCuCuCuCu` |
| 20 | rotate | 19 | 1 | `CuCucrCuCuCu` |
| 21 | cut | 20 | 0 | `CuCucr------` |
| 22 | rotate | 21 | 4 | `cr------CuCu` |
| 23 | cut | 22 | 0 | `cr----------` |
| 24 | rotate | 23 | 3 | `------cr----` |
| 25 | swap | 17, 24 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 26 | rotate | 25 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 27 | base | — | — | `----------Cu` |
| 28 | base | — | — | `----------Cu` |
| 29 | pin | 28 | — | `----------P-:----------Cu` |
| 30 | stack | 27, 29 | — | `----------Cu:----------P-:----------Cu` |
| 31 | base | — | — | `----------Cu` |
| 32 | stack | 30, 31 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 33 | base | — | — | `----------Cu` |
| 34 | stack | 32, 33 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 35 | swap | 26, 34 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 36 | rotate | 35 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 37 | cut | 36 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 38 | base | — | — | `------Cu----` |
| 39 | base | — | — | `------Cu----` |
| 40 | stack | 38, 39 | — | `------Cu----:------Cu----` |
| 41 | base | — | — | `--CuCuCu----` |
| 42 | stack | 40, 41 | — | `------Cu----:------Cu----:--CuCuCu----` |
| 43 | base | — | — | `----Cu------` |
| 44 | stack | 42, 43 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------` |
| 45 | base | — | — | `--CuCu------` |
| 46 | stack | 44, 45 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| 47 | rotate | 46 | 2 | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 48 | swap | 37, 47 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 49 | rotate | 48 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 50 | cut | 49 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 51 | base | — | — | `----------Cu` |
| 52 | base | — | — | `----------Cu` |
| 53 | stack | 51, 52 | — | `----------Cu:----------Cu` |
| 54 | stack | 50, 53 | — | `Cu--------Cu:----------Cu:crCuCu------:cr--Cu------:crCuCu------` |
| 55 | base | — | — | `------Cu--Cu` |
| 56 | base | — | — | `----------Cu` |
| 57 | pin | 56 | — | `----------P-:----------Cu` |
| 58 | stack | 55, 57 | — | `------Cu--Cu:----------P-:----------Cu` |
| 59 | stack | 54, 58 | — | `Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu` |
