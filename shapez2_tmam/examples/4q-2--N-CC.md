# 悬空普通格与连续双晶体

两次转交支撑，顶破远侧晶体脊；主列最终为-N-CC。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:crCu----:crCu----`

共102步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCu` |
| 2 | base | — | — | `CuCuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCu:CuCuCuCu` |
| 4 | base | — | — | `P-CuCuCu` |
| 5 | stack | 3, 4 | — | `crCuCuCu:CuCuCuCu:P-CuCuCu` |
| 6 | crystal | 5 | r | `crCuCuCu:CuCuCuCu:crCuCuCu` |
| 7 | base | — | — | `P-CuCuCu` |
| 8 | stack | 6, 7 | — | `crCuCuCu:CuCuCuCu:crCuCuCu:P-CuCuCu` |
| 9 | crystal | 8 | r | `crCuCuCu:CuCuCuCu:crCuCuCu:crCuCuCu` |
| 10 | rotate | 9 | 1 | `CucrCuCu:CuCuCuCu:CucrCuCu:CucrCuCu` |
| 11 | cut | 10 | 0 | `Cucr----:CuCu----:Cucr----:Cucr----` |
| 12 | rotate | 11 | 3 | `cr----Cu:Cu----Cu:cr----Cu:cr----Cu` |
| 13 | cut | 12 | 0 | `cr------:Cu------:cr------:cr------` |
| 14 | rotate | 13 | 1 | `--cr----:--Cu----:--cr----:--cr----` |
| 15 | base | — | — | `--Cu----` |
| 16 | base | — | — | `--Cu----` |
| 17 | stack | 15, 16 | — | `--Cu----:--Cu----` |
| 18 | base | — | — | `--Cu----` |
| 19 | stack | 17, 18 | — | `--Cu----:--Cu----:--Cu----` |
| 20 | base | — | — | `--Cu----` |
| 21 | stack | 19, 20 | — | `--Cu----:--Cu----:--Cu----:--Cu----` |
| 22 | base | — | — | `--Cu----` |
| 23 | stack | 21, 22 | — | `--Cu----:--Cu----:--Cu----:--Cu----:--Cu----` |
| 24 | rotate | 23 | 1 | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 25 | swap | 14, 24 | 0 | `--crCu--:--CuCu--:--crCu--:--crCu--:----Cu--` |
| 26 | rotate | 25 | 3 | `crCu----:CuCu----:crCu----:crCu----:--Cu----` |
| 27 | base | — | — | `CuCuCuP-` |
| 28 | crystal | 27 | r | `CuCuCucr` |
| 29 | rotate | 28 | 2 | `CucrCuCu` |
| 30 | cut | 29 | 0 | `Cucr----` |
| 31 | rotate | 30 | 3 | `cr----Cu` |
| 32 | cut | 31 | 0 | `cr------` |
| 33 | rotate | 32 | 3 | `------cr` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------cr:------Cu` |
| 36 | base | — | — | `------Cu` |
| 37 | stack | 35, 36 | — | `------cr:------Cu:------Cu` |
| 38 | base | — | — | `------Cu` |
| 39 | stack | 37, 38 | — | `------cr:------Cu:------Cu:------Cu` |
| 40 | base | — | — | `------Cu` |
| 41 | stack | 39, 40 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 42 | swap | 26, 41 | 0 | `crCu--cr:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 43 | cut | 42 | 0 | `--Cu----:CuCu----:crCu----:crCu----:--Cu----` |
| 44 | base | — | — | `------Cu` |
| 45 | base | — | — | `------Cu` |
| 46 | stack | 44, 45 | — | `------Cu:------Cu` |
| 47 | base | — | — | `------Cu` |
| 48 | stack | 46, 47 | — | `------Cu:------Cu:------Cu` |
| 49 | base | — | — | `------Cu` |
| 50 | stack | 48, 49 | — | `------Cu:------Cu:------Cu:------Cu` |
| 51 | base | — | — | `------Cu` |
| 52 | stack | 50, 51 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 53 | swap | 43, 52 | 0 | `--Cu--Cu:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 54 | rotate | 53 | 1 | `Cu--Cu--:CuCuCu--:CucrCu--:CucrCu--:Cu--Cu--` |
| 55 | cut | 54 | 0 | `Cu------:CuCu----:Cucr----:Cucr----:Cu------` |
| 56 | base | — | — | `CuP-CuCu` |
| 57 | crystal | 56 | r | `CucrCuCu` |
| 58 | cut | 57 | 0 | `Cucr----` |
| 59 | rotate | 58 | 3 | `cr----Cu` |
| 60 | cut | 59 | 0 | `cr------` |
| 61 | rotate | 60 | 1 | `--cr----` |
| 62 | base | — | — | `--Cu----` |
| 63 | stack | 61, 62 | — | `--cr----:--Cu----` |
| 64 | rotate | 63 | 1 | `----cr--:----Cu--` |
| 65 | swap | 55, 64 | 0 | `Cu--cr--:CuCuCu--:Cucr----:Cucr----:Cu------` |
| 66 | rotate | 65 | 3 | `--cr--Cu:CuCu--Cu:cr----Cu:cr----Cu:------Cu` |
| 67 | cut | 66 | 0 | `--cr----:CuCu----:cr------:cr------` |
| 68 | base | — | — | `CuCuP-Cu` |
| 69 | crystal | 68 | r | `CuCucrCu` |
| 70 | base | — | — | `CuCuP-Cu` |
| 71 | stack | 69, 70 | — | `CuCucrCu:CuCuP-Cu` |
| 72 | crystal | 71 | r | `CuCucrCu:CuCucrCu` |
| 73 | base | — | — | `CuCuP-Cu` |
| 74 | stack | 72, 73 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 75 | crystal | 74 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 76 | base | — | — | `CuCuP-Cu` |
| 77 | stack | 75, 76 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 78 | crystal | 77 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 79 | base | — | — | `CuCuP-Cu` |
| 80 | stack | 78, 79 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 81 | crystal | 80 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 82 | rotate | 81 | 3 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 83 | cut | 82 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 84 | rotate | 83 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 85 | cut | 84 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 86 | rotate | 85 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 87 | base | — | — | `------Cu` |
| 88 | pin | 87 | — | `------P-:------Cu` |
| 89 | pin | 88 | — | `------P-:------P-:------Cu` |
| 90 | rotate | 89 | 3 | `----P---:----P---:----Cu--` |
| 91 | swap | 86, 90 | 0 | `--crP---:--crP---:--crCu--:--cr----:--cr----` |
| 92 | rotate | 91 | 1 | `----crP-:----crP-:----crCu:----cr--:----cr--` |
| 93 | swap | 67, 92 | 0 | `--crcrP-:CuCucrP-:cr--crCu:cr--cr--:----cr--` |
| 94 | pin | 93 | — | `--P-P-P-:CuCu--P-:------P-:cr----Cu:cr------` |
| 95 | base | — | — | `--P-----` |
| 96 | stack | 94, 95 | — | `--P-P-P-:CuCu--P-:--P---P-:cr----Cu:cr------` |
| 97 | base | — | — | `--Cu----` |
| 98 | stack | 96, 97 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:cr------` |
| 99 | base | — | — | `--Cu----` |
| 100 | stack | 98, 99 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:crCu----` |
| 101 | cut | 100 | 0 | `--P-----:CuCu----:--P-----:crCu----:crCu----` |
