# 悬空普通格与连续双晶体

两次转交支撑，顶破远侧晶体脊；主列最终为-N-CC。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:crCu----:crCu----`

共95步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCu` |
| 1 | crystal | 0 | r | `CucrCuCu` |
| 2 | base | — | — | `CuCuCuCu` |
| 3 | stack | 1, 2 | — | `CucrCuCu:CuCuCuCu` |
| 4 | base | — | — | `CuP-CuCu` |
| 5 | stack | 3, 4 | — | `CucrCuCu:CuCuCuCu:CuP-CuCu` |
| 6 | crystal | 5 | r | `CucrCuCu:CuCuCuCu:CucrCuCu` |
| 7 | base | — | — | `CuP-CuCu` |
| 8 | stack | 6, 7 | — | `CucrCuCu:CuCuCuCu:CucrCuCu:CuP-CuCu` |
| 9 | crystal | 8 | r | `CucrCuCu:CuCuCuCu:CucrCuCu:CucrCuCu` |
| 10 | cut | 9 | 0 | `Cucr----:CuCu----:Cucr----:Cucr----` |
| 11 | rotate | 10 | 3 | `cr----Cu:Cu----Cu:cr----Cu:cr----Cu` |
| 12 | cut | 11 | 0 | `cr------:Cu------:cr------:cr------` |
| 13 | rotate | 12 | 1 | `--cr----:--Cu----:--cr----:--cr----` |
| 14 | base | — | — | `----Cu--` |
| 15 | base | — | — | `----Cu--` |
| 16 | stack | 14, 15 | — | `----Cu--:----Cu--` |
| 17 | base | — | — | `----Cu--` |
| 18 | stack | 16, 17 | — | `----Cu--:----Cu--:----Cu--` |
| 19 | base | — | — | `----Cu--` |
| 20 | stack | 18, 19 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 21 | base | — | — | `----Cu--` |
| 22 | stack | 20, 21 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 23 | swap | 13, 22 | 0 | `--crCu--:--CuCu--:--crCu--:--crCu--:----Cu--` |
| 24 | rotate | 23 | 3 | `crCu----:CuCu----:crCu----:crCu----:--Cu----` |
| 25 | base | — | — | `CuP-CuCu` |
| 26 | crystal | 25 | r | `CucrCuCu` |
| 27 | cut | 26 | 0 | `Cucr----` |
| 28 | rotate | 27 | 3 | `cr----Cu` |
| 29 | cut | 28 | 0 | `cr------` |
| 30 | rotate | 29 | 3 | `------cr` |
| 31 | base | — | — | `------Cu` |
| 32 | stack | 30, 31 | — | `------cr:------Cu` |
| 33 | base | — | — | `------Cu` |
| 34 | stack | 32, 33 | — | `------cr:------Cu:------Cu` |
| 35 | base | — | — | `------Cu` |
| 36 | stack | 34, 35 | — | `------cr:------Cu:------Cu:------Cu` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 39 | swap | 24, 38 | 0 | `crCu--cr:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 40 | cut | 39 | 0 | `--Cu----:CuCu----:crCu----:crCu----:--Cu----` |
| 41 | base | — | — | `------Cu` |
| 42 | base | — | — | `------Cu` |
| 43 | stack | 41, 42 | — | `------Cu:------Cu` |
| 44 | base | — | — | `------Cu` |
| 45 | stack | 43, 44 | — | `------Cu:------Cu:------Cu` |
| 46 | base | — | — | `------Cu` |
| 47 | stack | 45, 46 | — | `------Cu:------Cu:------Cu:------Cu` |
| 48 | base | — | — | `------Cu` |
| 49 | stack | 47, 48 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 50 | swap | 40, 49 | 0 | `--Cu--Cu:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 51 | rotate | 50 | 1 | `Cu--Cu--:CuCuCu--:CucrCu--:CucrCu--:Cu--Cu--` |
| 52 | cut | 51 | 0 | `Cu------:CuCu----:Cucr----:Cucr----:Cu------` |
| 53 | base | — | — | `CuP-CuCu` |
| 54 | crystal | 53 | r | `CucrCuCu` |
| 55 | cut | 54 | 0 | `Cucr----` |
| 56 | rotate | 55 | 1 | `--Cucr--` |
| 57 | cut | 56 | 1 | `----cr--` |
| 58 | base | — | — | `----Cu--` |
| 59 | stack | 57, 58 | — | `----cr--:----Cu--` |
| 60 | swap | 52, 59 | 0 | `Cu--cr--:CuCuCu--:Cucr----:Cucr----:Cu------` |
| 61 | rotate | 60 | 3 | `--cr--Cu:CuCu--Cu:cr----Cu:cr----Cu:------Cu` |
| 62 | cut | 61 | 0 | `--cr----:CuCu----:cr------:cr------` |
| 63 | base | — | — | `CuP-CuCu` |
| 64 | crystal | 63 | r | `CucrCuCu` |
| 65 | base | — | — | `CuP-CuCu` |
| 66 | stack | 64, 65 | — | `CucrCuCu:CuP-CuCu` |
| 67 | crystal | 66 | r | `CucrCuCu:CucrCuCu` |
| 68 | base | — | — | `CuP-CuCu` |
| 69 | stack | 67, 68 | — | `CucrCuCu:CucrCuCu:CuP-CuCu` |
| 70 | crystal | 69 | r | `CucrCuCu:CucrCuCu:CucrCuCu` |
| 71 | base | — | — | `CuP-CuCu` |
| 72 | stack | 70, 71 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 73 | crystal | 72 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 74 | base | — | — | `CuP-CuCu` |
| 75 | stack | 73, 74 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 76 | crystal | 75 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 77 | cut | 76 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 78 | rotate | 77 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 79 | cut | 78 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 80 | rotate | 79 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 81 | base | — | — | `----Cu--` |
| 82 | pin | 81 | — | `----P---:----Cu--` |
| 83 | pin | 82 | — | `----P---:----P---:----Cu--` |
| 84 | swap | 80, 83 | 0 | `--crP---:--crP---:--crCu--:--cr----:--cr----` |
| 85 | rotate | 84 | 1 | `----crP-:----crP-:----crCu:----cr--:----cr--` |
| 86 | swap | 62, 85 | 0 | `--crcrP-:CuCucrP-:cr--crCu:cr--cr--:----cr--` |
| 87 | pin | 86 | — | `--P-P-P-:CuCu--P-:------P-:cr----Cu:cr------` |
| 88 | base | — | — | `--P-----` |
| 89 | stack | 87, 88 | — | `--P-P-P-:CuCu--P-:--P---P-:cr----Cu:cr------` |
| 90 | base | — | — | `--Cu----` |
| 91 | stack | 89, 90 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:cr------` |
| 92 | base | — | — | `--Cu----` |
| 93 | stack | 91, 92 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:crCu----` |
| 94 | cut | 93 | 0 | `--P-----:CuCu----:--P-----:crCu----:crCu----` |
