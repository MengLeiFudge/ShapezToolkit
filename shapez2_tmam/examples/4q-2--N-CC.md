# 悬空普通格与连续双晶体

两次转交支撑，顶破远侧晶体脊；主列最终为-N-CC。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:crCu----:crCu----`

共109步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 12 | rotate | 11 | -1 | `cr----Cu:Cu----Cu:cr----Cu:cr----Cu` |
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
| 26 | rotate | 25 | -1 | `crCu----:CuCu----:crCu----:crCu----:--Cu----` |
| 27 | base | — | — | `CuCuCuP-` |
| 28 | crystal | 27 | r | `CuCuCucr` |
| 29 | rotate | 28 | -2 | `CucrCuCu` |
| 30 | cut | 29 | 0 | `Cucr----` |
| 31 | rotate | 30 | 2 | `----Cucr` |
| 32 | rotate | 31 | -3 | `cr----Cu` |
| 33 | cut | 32 | 0 | `cr------` |
| 34 | rotate | 33 | 3 | `------cr` |
| 35 | base | — | — | `------Cu` |
| 36 | stack | 34, 35 | — | `------cr:------Cu` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------cr:------Cu:------Cu` |
| 39 | base | — | — | `------Cu` |
| 40 | stack | 38, 39 | — | `------cr:------Cu:------Cu:------Cu` |
| 41 | base | — | — | `------Cu` |
| 42 | stack | 40, 41 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 43 | swap | 26, 42 | 0 | `crCu--cr:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 44 | cut | 43 | 0 | `--Cu----:CuCu----:crCu----:crCu----:--Cu----` |
| 45 | base | — | — | `------Cu` |
| 46 | base | — | — | `------Cu` |
| 47 | stack | 45, 46 | — | `------Cu:------Cu` |
| 48 | base | — | — | `------Cu` |
| 49 | stack | 47, 48 | — | `------Cu:------Cu:------Cu` |
| 50 | base | — | — | `------Cu` |
| 51 | stack | 49, 50 | — | `------Cu:------Cu:------Cu:------Cu` |
| 52 | base | — | — | `------Cu` |
| 53 | stack | 51, 52 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 54 | swap | 44, 53 | 0 | `--Cu--Cu:CuCu--Cu:crCu--Cu:crCu--Cu:--Cu--Cu` |
| 55 | rotate | 54 | -3 | `Cu--Cu--:CuCuCu--:CucrCu--:CucrCu--:Cu--Cu--` |
| 56 | cut | 55 | 0 | `Cu------:CuCu----:Cucr----:Cucr----:Cu------` |
| 57 | rotate | 56 | 3 | `------Cu:Cu----Cu:cr----Cu:cr----Cu:------Cu` |
| 58 | rotate | 57 | -3 | `Cu------:CuCu----:Cucr----:Cucr----:Cu------` |
| 59 | base | — | — | `CuP-CuCu` |
| 60 | crystal | 59 | r | `CucrCuCu` |
| 61 | cut | 60 | 0 | `Cucr----` |
| 62 | rotate | 61 | -1 | `cr----Cu` |
| 63 | cut | 62 | 0 | `cr------` |
| 64 | rotate | 63 | 1 | `--cr----` |
| 65 | base | — | — | `--Cu----` |
| 66 | stack | 64, 65 | — | `--cr----:--Cu----` |
| 67 | rotate | 66 | -3 | `----cr--:----Cu--` |
| 68 | swap | 58, 67 | 0 | `Cu--cr--:CuCuCu--:Cucr----:Cucr----:Cu------` |
| 69 | rotate | 68 | 3 | `--cr--Cu:CuCu--Cu:cr----Cu:cr----Cu:------Cu` |
| 70 | cut | 69 | 0 | `--cr----:CuCu----:cr------:cr------` |
| 71 | base | — | — | `CuCuP-Cu` |
| 72 | crystal | 71 | r | `CuCucrCu` |
| 73 | base | — | — | `CuCuP-Cu` |
| 74 | stack | 72, 73 | — | `CuCucrCu:CuCuP-Cu` |
| 75 | crystal | 74 | r | `CuCucrCu:CuCucrCu` |
| 76 | base | — | — | `CuCuP-Cu` |
| 77 | stack | 75, 76 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 78 | crystal | 77 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 79 | base | — | — | `CuCuP-Cu` |
| 80 | stack | 78, 79 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 81 | crystal | 80 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 82 | base | — | — | `CuCuP-Cu` |
| 83 | stack | 81, 82 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 84 | crystal | 83 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 85 | rotate | 84 | -1 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 86 | cut | 85 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 87 | rotate | 86 | 1 | `--Cucr--:--Cucr--:--Cucr--:--Cucr--:--Cucr--` |
| 88 | rotate | 87 | -2 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 89 | cut | 88 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 90 | rotate | 89 | 2 | `----cr--:----cr--:----cr--:----cr--:----cr--` |
| 91 | rotate | 90 | -1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 92 | base | — | — | `------P-` |
| 93 | base | — | — | `------P-` |
| 94 | stack | 92, 93 | — | `------P-:------P-` |
| 95 | base | — | — | `------Cu` |
| 96 | stack | 94, 95 | — | `------P-:------P-:------Cu` |
| 97 | rotate | 96 | -1 | `----P---:----P---:----Cu--` |
| 98 | swap | 91, 97 | 0 | `--crP---:--crP---:--crCu--:--cr----:--cr----` |
| 99 | rotate | 98 | 1 | `----crP-:----crP-:----crCu:----cr--:----cr--` |
| 100 | swap | 70, 99 | 0 | `--crcrP-:CuCucrP-:cr--crCu:cr--cr--:----cr--` |
| 101 | pin | 100 | — | `--P-P-P-:CuCu--P-:------P-:cr----Cu:cr------` |
| 102 | base | — | — | `--P-----` |
| 103 | stack | 101, 102 | — | `--P-P-P-:CuCu--P-:--P---P-:cr----Cu:cr------` |
| 104 | base | — | — | `--Cu----` |
| 105 | stack | 103, 104 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:cr------` |
| 106 | base | — | — | `--Cu----` |
| 107 | stack | 105, 106 | — | `--P-P-P-:CuCu--P-:--P---P-:crCu--Cu:crCu----` |
| 108 | cut | 107 | 0 | `--P-----:CuCu----:--P-----:crCu----:crCu----` |
