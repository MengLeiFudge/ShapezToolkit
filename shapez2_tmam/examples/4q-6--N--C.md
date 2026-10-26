# 两格高间隙

使用双针支撑尾部，保留普通格和顶层晶体之间的两格间隙。

配置：4象限、五层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:--P-----:crCu----`

共115步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 12 | rotate | 11 | -1 | `cr----Cu:cr----Cu:Cu----Cu:cr----Cu` |
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
| 26 | rotate | 25 | -1 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 27 | base | — | — | `CuCuCuP-` |
| 28 | crystal | 27 | r | `CuCuCucr` |
| 29 | base | — | — | `CuCuCuP-` |
| 30 | stack | 28, 29 | — | `CuCuCucr:CuCuCuP-` |
| 31 | crystal | 30 | r | `CuCuCucr:CuCuCucr` |
| 32 | rotate | 31 | -2 | `CucrCuCu:CucrCuCu` |
| 33 | cut | 32 | 0 | `Cucr----:Cucr----` |
| 34 | rotate | 33 | 2 | `----Cucr:----Cucr` |
| 35 | rotate | 34 | -3 | `cr----Cu:cr----Cu` |
| 36 | cut | 35 | 0 | `cr------:cr------` |
| 37 | rotate | 36 | 3 | `------cr:------cr` |
| 38 | base | — | — | `------Cu` |
| 39 | stack | 37, 38 | — | `------cr:------cr:------Cu` |
| 40 | base | — | — | `------Cu` |
| 41 | stack | 39, 40 | — | `------cr:------cr:------Cu:------Cu` |
| 42 | base | — | — | `------Cu` |
| 43 | stack | 41, 42 | — | `------cr:------cr:------Cu:------Cu:------Cu` |
| 44 | swap | 26, 43 | 0 | `crCu--cr:crCu--cr:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 45 | cut | 44 | 0 | `--Cu----:--Cu----:CuCu----:crCu----:--Cu----` |
| 46 | base | — | — | `------Cu` |
| 47 | base | — | — | `------Cu` |
| 48 | stack | 46, 47 | — | `------Cu:------Cu` |
| 49 | base | — | — | `------Cu` |
| 50 | stack | 48, 49 | — | `------Cu:------Cu:------Cu` |
| 51 | base | — | — | `------Cu` |
| 52 | stack | 50, 51 | — | `------Cu:------Cu:------Cu:------Cu` |
| 53 | base | — | — | `------Cu` |
| 54 | stack | 52, 53 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 55 | swap | 45, 54 | 0 | `--Cu--Cu:--Cu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 56 | rotate | 55 | -3 | `Cu--Cu--:Cu--Cu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 57 | cut | 56 | 0 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 58 | rotate | 57 | 3 | `------Cu:------Cu:Cu----Cu:cr----Cu:------Cu` |
| 59 | rotate | 58 | -3 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 60 | base | — | — | `CuP-CuCu` |
| 61 | crystal | 60 | r | `CucrCuCu` |
| 62 | base | — | — | `CuP-CuCu` |
| 63 | stack | 61, 62 | — | `CucrCuCu:CuP-CuCu` |
| 64 | crystal | 63 | r | `CucrCuCu:CucrCuCu` |
| 65 | cut | 64 | 0 | `Cucr----:Cucr----` |
| 66 | rotate | 65 | -1 | `cr----Cu:cr----Cu` |
| 67 | cut | 66 | 0 | `cr------:cr------` |
| 68 | rotate | 67 | 1 | `--cr----:--cr----` |
| 69 | base | — | — | `--Cu----` |
| 70 | stack | 68, 69 | — | `--cr----:--cr----:--Cu----` |
| 71 | rotate | 70 | -3 | `----cr--:----cr--:----Cu--` |
| 72 | swap | 59, 71 | 0 | `Cu--cr--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 73 | rotate | 72 | 3 | `--cr--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 74 | cut | 73 | 0 | `--cr----:--cr----:CuCu----:cr------` |
| 75 | base | — | — | `CuCuP-Cu` |
| 76 | crystal | 75 | r | `CuCucrCu` |
| 77 | base | — | — | `CuCuP-Cu` |
| 78 | stack | 76, 77 | — | `CuCucrCu:CuCuP-Cu` |
| 79 | crystal | 78 | r | `CuCucrCu:CuCucrCu` |
| 80 | base | — | — | `CuCuP-Cu` |
| 81 | stack | 79, 80 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 82 | crystal | 81 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 83 | base | — | — | `CuCuP-Cu` |
| 84 | stack | 82, 83 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 85 | crystal | 84 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 86 | base | — | — | `CuCuP-Cu` |
| 87 | stack | 85, 86 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 88 | crystal | 87 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 89 | rotate | 88 | -1 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 90 | cut | 89 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 91 | rotate | 90 | 1 | `--Cucr--:--Cucr--:--Cucr--:--Cucr--:--Cucr--` |
| 92 | rotate | 91 | -2 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 93 | cut | 92 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 94 | rotate | 93 | 2 | `----cr--:----cr--:----cr--:----cr--:----cr--` |
| 95 | rotate | 94 | -1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 96 | base | — | — | `------P-` |
| 97 | base | — | — | `------P-` |
| 98 | stack | 96, 97 | — | `------P-:------P-` |
| 99 | base | — | — | `------P-` |
| 100 | stack | 98, 99 | — | `------P-:------P-:------P-` |
| 101 | base | — | — | `------Cu` |
| 102 | stack | 100, 101 | — | `------P-:------P-:------P-:------Cu` |
| 103 | rotate | 102 | -1 | `----P---:----P---:----P---:----Cu--` |
| 104 | swap | 95, 103 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 105 | rotate | 104 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 106 | swap | 74, 105 | 0 | `--crcrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 107 | pin | 106 | — | `--P-P-P-:CuCu--P-:------P-:------P-:cr----Cu` |
| 108 | base | — | — | `--P-----` |
| 109 | stack | 107, 108 | — | `--P-P-P-:CuCu--P-:--P---P-:------P-:cr----Cu` |
| 110 | base | — | — | `--P-----` |
| 111 | stack | 109, 110 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:cr----Cu` |
| 112 | base | — | — | `--Cu----` |
| 113 | stack | 111, 112 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:crCu--Cu` |
| 114 | cut | 113 | 0 | `--P-----:CuCu----:--P-----:--P-----:crCu----` |
