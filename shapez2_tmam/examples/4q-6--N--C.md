# 两格高间隙

使用双针支撑尾部，保留普通格和顶层晶体之间的两格间隙。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:--P-----:crCu----`

共107步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCu` |
| 2 | base | — | — | `P-CuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCu:P-CuCuCu` |
| 4 | crystal | 3 | r | `crCuCuCu:crCuCuCu` |
| 5 | base | — | — | `CuCuCuCu` |
| 6 | stack | 4, 5 | — | `crCuCuCu:crCuCuCu:CuCuCuCu` |
| 7 | base | — | — | `P-CuCuCu` |
| 8 | stack | 6, 7 | — | `crCuCuCu:crCuCuCu:CuCuCuCu:P-CuCuCu` |
| 9 | crystal | 8 | r | `crCuCuCu:crCuCuCu:CuCuCuCu:crCuCuCu` |
| 10 | rotate | 9 | 1 | `CucrCuCu:CucrCuCu:CuCuCuCu:CucrCuCu` |
| 11 | cut | 10 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----` |
| 12 | rotate | 11 | 3 | `cr----Cu:cr----Cu:Cu----Cu:cr----Cu` |
| 13 | cut | 12 | 0 | `cr------:cr------:Cu------:cr------` |
| 14 | rotate | 13 | 1 | `--cr----:--cr----:--Cu----:--cr----` |
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
| 25 | swap | 14, 24 | 0 | `--crCu--:--crCu--:--CuCu--:--crCu--:----Cu--` |
| 26 | rotate | 25 | 3 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 27 | base | — | — | `CuCuCuP-` |
| 28 | crystal | 27 | r | `CuCuCucr` |
| 29 | base | — | — | `CuCuCuP-` |
| 30 | stack | 28, 29 | — | `CuCuCucr:CuCuCuP-` |
| 31 | crystal | 30 | r | `CuCuCucr:CuCuCucr` |
| 32 | rotate | 31 | 2 | `CucrCuCu:CucrCuCu` |
| 33 | cut | 32 | 0 | `Cucr----:Cucr----` |
| 34 | rotate | 33 | 3 | `cr----Cu:cr----Cu` |
| 35 | cut | 34 | 0 | `cr------:cr------` |
| 36 | rotate | 35 | 3 | `------cr:------cr` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------cr:------cr:------Cu` |
| 39 | base | — | — | `------Cu` |
| 40 | stack | 38, 39 | — | `------cr:------cr:------Cu:------Cu` |
| 41 | base | — | — | `------Cu` |
| 42 | stack | 40, 41 | — | `------cr:------cr:------Cu:------Cu:------Cu` |
| 43 | swap | 26, 42 | 0 | `crCu--cr:crCu--cr:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 44 | cut | 43 | 0 | `--Cu----:--Cu----:CuCu----:crCu----:--Cu----` |
| 45 | base | — | — | `------Cu` |
| 46 | base | — | — | `------Cu` |
| 47 | stack | 45, 46 | — | `------Cu:------Cu` |
| 48 | base | — | — | `------Cu` |
| 49 | stack | 47, 48 | — | `------Cu:------Cu:------Cu` |
| 50 | base | — | — | `------Cu` |
| 51 | stack | 49, 50 | — | `------Cu:------Cu:------Cu:------Cu` |
| 52 | base | — | — | `------Cu` |
| 53 | stack | 51, 52 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 54 | swap | 44, 53 | 0 | `--Cu--Cu:--Cu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 55 | rotate | 54 | 1 | `Cu--Cu--:Cu--Cu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 56 | cut | 55 | 0 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 57 | base | — | — | `CuP-CuCu` |
| 58 | crystal | 57 | r | `CucrCuCu` |
| 59 | base | — | — | `CuP-CuCu` |
| 60 | stack | 58, 59 | — | `CucrCuCu:CuP-CuCu` |
| 61 | crystal | 60 | r | `CucrCuCu:CucrCuCu` |
| 62 | cut | 61 | 0 | `Cucr----:Cucr----` |
| 63 | rotate | 62 | 3 | `cr----Cu:cr----Cu` |
| 64 | cut | 63 | 0 | `cr------:cr------` |
| 65 | rotate | 64 | 1 | `--cr----:--cr----` |
| 66 | base | — | — | `--Cu----` |
| 67 | stack | 65, 66 | — | `--cr----:--cr----:--Cu----` |
| 68 | rotate | 67 | 1 | `----cr--:----cr--:----Cu--` |
| 69 | swap | 56, 68 | 0 | `Cu--cr--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 70 | rotate | 69 | 3 | `--cr--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 71 | cut | 70 | 0 | `--cr----:--cr----:CuCu----:cr------` |
| 72 | base | — | — | `CuCuP-Cu` |
| 73 | crystal | 72 | r | `CuCucrCu` |
| 74 | base | — | — | `CuCuP-Cu` |
| 75 | stack | 73, 74 | — | `CuCucrCu:CuCuP-Cu` |
| 76 | crystal | 75 | r | `CuCucrCu:CuCucrCu` |
| 77 | base | — | — | `CuCuP-Cu` |
| 78 | stack | 76, 77 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 79 | crystal | 78 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 80 | base | — | — | `CuCuP-Cu` |
| 81 | stack | 79, 80 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 82 | crystal | 81 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 83 | base | — | — | `CuCuP-Cu` |
| 84 | stack | 82, 83 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 85 | crystal | 84 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 86 | rotate | 85 | 3 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 87 | cut | 86 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 88 | rotate | 87 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 89 | cut | 88 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 90 | rotate | 89 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 91 | base | — | — | `------Cu` |
| 92 | pin | 91 | — | `------P-:------Cu` |
| 93 | pin | 92 | — | `------P-:------P-:------Cu` |
| 94 | pin | 93 | — | `------P-:------P-:------P-:------Cu` |
| 95 | rotate | 94 | 3 | `----P---:----P---:----P---:----Cu--` |
| 96 | swap | 90, 95 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 97 | rotate | 96 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 98 | swap | 71, 97 | 0 | `--crcrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 99 | pin | 98 | — | `--P-P-P-:CuCu--P-:------P-:------P-:cr----Cu` |
| 100 | base | — | — | `--P-----` |
| 101 | stack | 99, 100 | — | `--P-P-P-:CuCu--P-:--P---P-:------P-:cr----Cu` |
| 102 | base | — | — | `--P-----` |
| 103 | stack | 101, 102 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:cr----Cu` |
| 104 | base | — | — | `--Cu----` |
| 105 | stack | 103, 104 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:crCu--Cu` |
| 106 | cut | 105 | 0 | `--P-----:CuCu----:--P-----:--P-----:crCu----` |
