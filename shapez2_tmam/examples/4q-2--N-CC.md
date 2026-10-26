# 悬空普通格与连续双晶体

两次转交支撑，顶破远侧晶体脊；主列最终为-N-CC。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:crCu----:crCu----`

共89步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCu` |
| 1 | base | — | — | `CuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuP-CuCu:CuCuCuCu` |
| 3 | base | — | — | `CuP-CuCu` |
| 4 | stack | 2, 3 | — | `CuP-CuCu:CuCuCuCu:CuP-CuCu` |
| 5 | base | — | — | `CuP-CuCu` |
| 6 | stack | 4, 5 | — | `CuP-CuCu:CuCuCuCu:CuP-CuCu:CuP-CuCu` |
| 7 | crystal | 6 | r | `CucrCuCu:CuCuCuCu:CucrCuCu:CucrCuCu` |
| 8 | cut | 7 | 0 | `Cucr----:CuCu----:Cucr----:Cucr----` |
| 9 | rotate | 8 | 3 | `cr----Cu:Cu----Cu:cr----Cu:cr----Cu` |
| 10 | cut | 9 | 0 | `cr------:Cu------:cr------:cr------` |
| 11 | rotate | 10 | 1 | `--cr----:--Cu----:--cr----:--cr----` |
| 12 | base | — | — | `----Cu--` |
| 13 | base | — | — | `----Cu--` |
| 14 | stack | 12, 13 | — | `----Cu--:----Cu--` |
| 15 | base | — | — | `----Cu--` |
| 16 | stack | 14, 15 | — | `----Cu--:----Cu--:----Cu--` |
| 17 | base | — | — | `----Cu--` |
| 18 | stack | 16, 17 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 19 | base | — | — | `----Cu--` |
| 20 | stack | 18, 19 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 21 | swap | 11, 20 | 0 | `--crCu--:--CuCu--:--crCu--:--crCu--:----Cu--` |
| 22 | rotate | 21 | 3 | `crCu----:CuCu----:crCu----:crCu----:--Cu----` |
| 23 | base | — | — | `CuP-CuCu` |
| 24 | crystal | 23 | r | `CucrCuCu` |
| 25 | cut | 24 | 0 | `Cucr----` |
| 26 | rotate | 25 | 3 | `cr----Cu` |
| 27 | cut | 26 | 0 | `cr------` |
| 28 | rotate | 27 | 3 | `------cr` |
| 29 | base | — | — | `------Cu` |
| 30 | stack | 28, 29 | — | `------cr:------Cu` |
| 31 | base | — | — | `------Cu` |
| 32 | stack | 30, 31 | — | `------cr:------Cu:------Cu` |
| 33 | base | — | — | `------Cu` |
| 34 | stack | 32, 33 | — | `------cr:------Cu:------Cu:------Cu` |
| 35 | base | — | — | `------Cu` |
| 36 | stack | 34, 35 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 37 | swap | 22, 36 | 0 | `crCu--cr:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 38 | cut | 37 | 0 | `--Cu----:CuCu----:crCu----:crCu----:--Cu----` |
| 39 | base | — | — | `------Cu` |
| 40 | base | — | — | `------Cu` |
| 41 | stack | 39, 40 | — | `------Cu:------Cu` |
| 42 | base | — | — | `------Cu` |
| 43 | stack | 41, 42 | — | `------Cu:------Cu:------Cu` |
| 44 | base | — | — | `------Cu` |
| 45 | stack | 43, 44 | — | `------Cu:------Cu:------Cu:------Cu` |
| 46 | base | — | — | `------Cu` |
| 47 | stack | 45, 46 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 48 | swap | 38, 47 | 0 | `--Cu--Cu:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 49 | rotate | 48 | 1 | `Cu--Cu--:CuCuCu--:CucrCu--:CucrCu--:Cu--Cu--` |
| 50 | cut | 49 | 0 | `Cu------:CuCu----:Cucr----:Cucr----:Cu------` |
| 51 | base | — | — | `CuP-CuCu` |
| 52 | crystal | 51 | r | `CucrCuCu` |
| 53 | cut | 52 | 0 | `Cucr----` |
| 54 | rotate | 53 | 1 | `--Cucr--` |
| 55 | cut | 54 | 1 | `----cr--` |
| 56 | base | — | — | `----Cu--` |
| 57 | stack | 55, 56 | — | `----cr--:----Cu--` |
| 58 | swap | 50, 57 | 0 | `Cu--cr--:CuCuCu--:Cucr----:Cucr----:Cu------` |
| 59 | rotate | 58 | 3 | `--cr--Cu:CuCu--Cu:cr----Cu:cr----Cu:------Cu` |
| 60 | cut | 59 | 0 | `--cr----:CuCu----:cr------:cr------` |
| 61 | base | — | — | `CuP-CuCu` |
| 62 | base | — | — | `CuP-CuCu` |
| 63 | stack | 61, 62 | — | `CuP-CuCu:CuP-CuCu` |
| 64 | base | — | — | `CuP-CuCu` |
| 65 | stack | 63, 64 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 66 | base | — | — | `CuP-CuCu` |
| 67 | stack | 65, 66 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 68 | base | — | — | `CuP-CuCu` |
| 69 | stack | 67, 68 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 70 | crystal | 69 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 71 | cut | 70 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 72 | rotate | 71 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 73 | cut | 72 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 74 | rotate | 73 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 75 | base | — | — | `----Cu--` |
| 76 | pin | 75 | — | `----P---:----Cu--` |
| 77 | pin | 76 | — | `----P---:----P---:----Cu--` |
| 78 | swap | 74, 77 | 0 | `--crP---:--crP---:--crCu--:--cr----:--cr----` |
| 79 | rotate | 78 | 1 | `----crP-:----crP-:----crCu:----cr--:----cr--` |
| 80 | swap | 60, 79 | 0 | `--crcrP-:CuCucrP-:cr--crCu:cr--cr--:----cr--` |
| 81 | pin | 80 | — | `--P-P-P-:CuCu--P-:------P-:cr----Cu:cr------` |
| 82 | base | — | — | `--P-----` |
| 83 | stack | 81, 82 | — | `--P-P-P-:CuCu--P-:--P---P-:cr----Cu:cr------` |
| 84 | base | — | — | `--Cu----` |
| 85 | stack | 83, 84 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:cr------` |
| 86 | base | — | — | `--Cu----` |
| 87 | stack | 85, 86 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:crCu----` |
| 88 | cut | 87 | 0 | `--P-----:CuCu----:--P-----:crCu----:crCu----` |
