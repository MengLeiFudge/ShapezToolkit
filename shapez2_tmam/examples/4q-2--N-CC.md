# 悬空普通格与连续双晶体

两次转交支撑，顶破远侧晶体脊；主列最终为-N-CC。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:crCu----:crCu----`

共79步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCu` |
| 1 | base | — | — | `CuCuCuCu` |
| 2 | stack | 0, 1 | — | `P-CuCuCu:CuCuCuCu` |
| 3 | base | — | — | `P-CuCuCu` |
| 4 | stack | 2, 3 | — | `P-CuCuCu:CuCuCuCu:P-CuCuCu` |
| 5 | base | — | — | `P-CuCuCu` |
| 6 | stack | 4, 5 | — | `P-CuCuCu:CuCuCuCu:P-CuCuCu:P-CuCuCu` |
| 7 | crystal | 6 | r | `crCuCuCu:CuCuCuCu:crCuCuCu:crCuCuCu` |
| 8 | cut | 7 | 0 | `crCu----:CuCu----:crCu----:crCu----` |
| 9 | base | — | — | `--Cu----` |
| 10 | stack | 8, 9 | — | `crCu----:CuCu----:crCu----:crCu----:--Cu----` |
| 11 | base | — | — | `CuP-CuCu` |
| 12 | crystal | 11 | r | `CucrCuCu` |
| 13 | cut | 12 | 0 | `Cucr----` |
| 14 | rotate | 13 | 3 | `cr----Cu` |
| 15 | cut | 14 | 0 | `cr------` |
| 16 | rotate | 15 | 3 | `------cr` |
| 17 | base | — | — | `------Cu` |
| 18 | stack | 16, 17 | — | `------cr:------Cu` |
| 19 | base | — | — | `------Cu` |
| 20 | stack | 18, 19 | — | `------cr:------Cu:------Cu` |
| 21 | base | — | — | `------Cu` |
| 22 | stack | 20, 21 | — | `------cr:------Cu:------Cu:------Cu` |
| 23 | base | — | — | `------Cu` |
| 24 | stack | 22, 23 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 25 | swap | 10, 24 | 0 | `crCu--cr:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 26 | cut | 25 | 0 | `--Cu----:CuCu----:crCu----:crCu----:--Cu----` |
| 27 | base | — | — | `------Cu` |
| 28 | base | — | — | `------Cu` |
| 29 | stack | 27, 28 | — | `------Cu:------Cu` |
| 30 | base | — | — | `------Cu` |
| 31 | stack | 29, 30 | — | `------Cu:------Cu:------Cu` |
| 32 | base | — | — | `------Cu` |
| 33 | stack | 31, 32 | — | `------Cu:------Cu:------Cu:------Cu` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 36 | swap | 26, 35 | 0 | `--Cu--Cu:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 37 | rotate | 36 | 1 | `Cu--Cu--:CuCuCu--:CucrCu--:CucrCu--:Cu--Cu--` |
| 38 | cut | 37 | 0 | `Cu------:CuCu----:Cucr----:Cucr----:Cu------` |
| 39 | base | — | — | `CuP-CuCu` |
| 40 | crystal | 39 | r | `CucrCuCu` |
| 41 | cut | 40 | 0 | `Cucr----` |
| 42 | rotate | 41 | 1 | `--Cucr--` |
| 43 | cut | 42 | 1 | `----cr--` |
| 44 | base | — | — | `----Cu--` |
| 45 | stack | 43, 44 | — | `----cr--:----Cu--` |
| 46 | swap | 38, 45 | 0 | `Cu--cr--:CuCuCu--:Cucr----:Cucr----:Cu------` |
| 47 | rotate | 46 | 3 | `--cr--Cu:CuCu--Cu:cr----Cu:cr----Cu:------Cu` |
| 48 | cut | 47 | 0 | `--cr----:CuCu----:cr------:cr------` |
| 49 | base | — | — | `CuP-CuCu` |
| 50 | base | — | — | `CuP-CuCu` |
| 51 | stack | 49, 50 | — | `CuP-CuCu:CuP-CuCu` |
| 52 | base | — | — | `CuP-CuCu` |
| 53 | stack | 51, 52 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 54 | base | — | — | `CuP-CuCu` |
| 55 | stack | 53, 54 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 56 | base | — | — | `CuP-CuCu` |
| 57 | stack | 55, 56 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 58 | crystal | 57 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 59 | cut | 58 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 60 | rotate | 59 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 61 | cut | 60 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 62 | rotate | 61 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 63 | base | — | — | `----P---` |
| 64 | base | — | — | `----P---` |
| 65 | stack | 63, 64 | — | `----P---:----P---` |
| 66 | base | — | — | `----Cu--` |
| 67 | stack | 65, 66 | — | `----P---:----P---:----Cu--` |
| 68 | swap | 62, 67 | 0 | `--crP---:--crP---:--crCu--:--cr----:--cr----` |
| 69 | rotate | 68 | 1 | `----crP-:----crP-:----crCu:----cr--:----cr--` |
| 70 | swap | 48, 69 | 0 | `--crcrP-:CuCucrP-:cr--crCu:cr--cr--:----cr--` |
| 71 | pin | 70 | — | `--P-P-P-:CuCu--P-:------P-:cr----Cu:cr------` |
| 72 | base | — | — | `--P-----` |
| 73 | stack | 71, 72 | — | `--P-P-P-:CuCu--P-:--P---P-:cr----Cu:cr------` |
| 74 | base | — | — | `--Cu----` |
| 75 | stack | 73, 74 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:cr------` |
| 76 | base | — | — | `--Cu----` |
| 77 | stack | 75, 76 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:crCu----` |
| 78 | cut | 77 | 0 | `--P-----:CuCu----:--P-----:crCu----:crCu----` |
