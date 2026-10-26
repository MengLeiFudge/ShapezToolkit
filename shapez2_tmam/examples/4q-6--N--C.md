# 两格高间隙

使用双针支撑尾部，保留普通格和顶层晶体之间的两格间隙。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:--P-----:crCu----`

共100步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCu` |
| 1 | crystal | 0 | r | `CucrCuCu` |
| 2 | base | — | — | `CuP-CuCu` |
| 3 | stack | 1, 2 | — | `CucrCuCu:CuP-CuCu` |
| 4 | crystal | 3 | r | `CucrCuCu:CucrCuCu` |
| 5 | base | — | — | `CuCuCuCu` |
| 6 | stack | 4, 5 | — | `CucrCuCu:CucrCuCu:CuCuCuCu` |
| 7 | base | — | — | `CuP-CuCu` |
| 8 | stack | 6, 7 | — | `CucrCuCu:CucrCuCu:CuCuCuCu:CuP-CuCu` |
| 9 | crystal | 8 | r | `CucrCuCu:CucrCuCu:CuCuCuCu:CucrCuCu` |
| 10 | cut | 9 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----` |
| 11 | rotate | 10 | 3 | `cr----Cu:cr----Cu:Cu----Cu:cr----Cu` |
| 12 | cut | 11 | 0 | `cr------:cr------:Cu------:cr------` |
| 13 | rotate | 12 | 1 | `--cr----:--cr----:--Cu----:--cr----` |
| 14 | base | — | — | `----Cu--` |
| 15 | base | — | — | `----Cu--` |
| 16 | stack | 14, 15 | — | `----Cu--:----Cu--` |
| 17 | base | — | — | `----Cu--` |
| 18 | stack | 16, 17 | — | `----Cu--:----Cu--:----Cu--` |
| 19 | base | — | — | `----Cu--` |
| 20 | stack | 18, 19 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 21 | base | — | — | `----Cu--` |
| 22 | stack | 20, 21 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 23 | swap | 13, 22 | 0 | `--crCu--:--crCu--:--CuCu--:--crCu--:----Cu--` |
| 24 | rotate | 23 | 3 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 25 | base | — | — | `CuP-CuCu` |
| 26 | crystal | 25 | r | `CucrCuCu` |
| 27 | base | — | — | `CuP-CuCu` |
| 28 | stack | 26, 27 | — | `CucrCuCu:CuP-CuCu` |
| 29 | crystal | 28 | r | `CucrCuCu:CucrCuCu` |
| 30 | cut | 29 | 0 | `Cucr----:Cucr----` |
| 31 | rotate | 30 | 3 | `cr----Cu:cr----Cu` |
| 32 | cut | 31 | 0 | `cr------:cr------` |
| 33 | rotate | 32 | 3 | `------cr:------cr` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------cr:------cr:------Cu` |
| 36 | base | — | — | `------Cu` |
| 37 | stack | 35, 36 | — | `------cr:------cr:------Cu:------Cu` |
| 38 | base | — | — | `------Cu` |
| 39 | stack | 37, 38 | — | `------cr:------cr:------Cu:------Cu:------Cu` |
| 40 | swap | 24, 39 | 0 | `crCu--cr:crCu--cr:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 41 | cut | 40 | 0 | `--Cu----:--Cu----:CuCu----:crCu----:--Cu----` |
| 42 | base | — | — | `------Cu` |
| 43 | base | — | — | `------Cu` |
| 44 | stack | 42, 43 | — | `------Cu:------Cu` |
| 45 | base | — | — | `------Cu` |
| 46 | stack | 44, 45 | — | `------Cu:------Cu:------Cu` |
| 47 | base | — | — | `------Cu` |
| 48 | stack | 46, 47 | — | `------Cu:------Cu:------Cu:------Cu` |
| 49 | base | — | — | `------Cu` |
| 50 | stack | 48, 49 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 51 | swap | 41, 50 | 0 | `--Cu--Cu:--Cu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 52 | rotate | 51 | 1 | `Cu--Cu--:Cu--Cu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 53 | cut | 52 | 0 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 54 | base | — | — | `CuP-CuCu` |
| 55 | crystal | 54 | r | `CucrCuCu` |
| 56 | base | — | — | `CuP-CuCu` |
| 57 | stack | 55, 56 | — | `CucrCuCu:CuP-CuCu` |
| 58 | crystal | 57 | r | `CucrCuCu:CucrCuCu` |
| 59 | cut | 58 | 0 | `Cucr----:Cucr----` |
| 60 | rotate | 59 | 1 | `--Cucr--:--Cucr--` |
| 61 | cut | 60 | 1 | `----cr--:----cr--` |
| 62 | base | — | — | `----Cu--` |
| 63 | stack | 61, 62 | — | `----cr--:----cr--:----Cu--` |
| 64 | swap | 53, 63 | 0 | `Cu--cr--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 65 | rotate | 64 | 3 | `--cr--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 66 | cut | 65 | 0 | `--cr----:--cr----:CuCu----:cr------` |
| 67 | base | — | — | `CuP-CuCu` |
| 68 | crystal | 67 | r | `CucrCuCu` |
| 69 | base | — | — | `CuP-CuCu` |
| 70 | stack | 68, 69 | — | `CucrCuCu:CuP-CuCu` |
| 71 | crystal | 70 | r | `CucrCuCu:CucrCuCu` |
| 72 | base | — | — | `CuP-CuCu` |
| 73 | stack | 71, 72 | — | `CucrCuCu:CucrCuCu:CuP-CuCu` |
| 74 | crystal | 73 | r | `CucrCuCu:CucrCuCu:CucrCuCu` |
| 75 | base | — | — | `CuP-CuCu` |
| 76 | stack | 74, 75 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 77 | crystal | 76 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 78 | base | — | — | `CuP-CuCu` |
| 79 | stack | 77, 78 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 80 | crystal | 79 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 81 | cut | 80 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 82 | rotate | 81 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 83 | cut | 82 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 84 | rotate | 83 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 85 | base | — | — | `----Cu--` |
| 86 | pin | 85 | — | `----P---:----Cu--` |
| 87 | pin | 86 | — | `----P---:----P---:----Cu--` |
| 88 | pin | 87 | — | `----P---:----P---:----P---:----Cu--` |
| 89 | swap | 84, 88 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 90 | rotate | 89 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 91 | swap | 66, 90 | 0 | `--crcrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 92 | pin | 91 | — | `--P-P-P-:CuCu--P-:------P-:------P-:cr----Cu` |
| 93 | base | — | — | `--P-----` |
| 94 | stack | 92, 93 | — | `--P-P-P-:CuCu--P-:--P---P-:------P-:cr----Cu` |
| 95 | base | — | — | `--P-----` |
| 96 | stack | 94, 95 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:cr----Cu` |
| 97 | base | — | — | `--Cu----` |
| 98 | stack | 96, 97 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:crCu--Cu` |
| 99 | cut | 98 | 0 | `--P-----:CuCu----:--P-----:--P-----:crCu----` |
