# 两层空底

通过侧面支撑保留悬空普通格，顶破后形成两层空底的主列。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:--Cu----:CuCu----:--P-----:crCu----`

共104步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 57 | base | — | — | `CuCuCuCu` |
| 58 | base | — | — | `CuP-CuCu` |
| 59 | stack | 57, 58 | — | `CuCuCuCu:CuP-CuCu` |
| 60 | crystal | 59 | r | `CuCuCuCu:CucrCuCu` |
| 61 | cut | 60 | 0 | `CuCu----:Cucr----` |
| 62 | rotate | 61 | 3 | `Cu----Cu:cr----Cu` |
| 63 | cut | 62 | 0 | `Cu------:cr------` |
| 64 | rotate | 63 | 1 | `--Cu----:--cr----` |
| 65 | base | — | — | `--Cu----` |
| 66 | stack | 64, 65 | — | `--Cu----:--cr----:--Cu----` |
| 67 | rotate | 66 | 1 | `----Cu--:----cr--:----Cu--` |
| 68 | swap | 56, 67 | 0 | `Cu--Cu--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 69 | rotate | 68 | 3 | `--Cu--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 70 | cut | 69 | 0 | `--Cu----:--cr----:CuCu----:cr------` |
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
| 85 | rotate | 84 | 3 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 86 | cut | 85 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 87 | rotate | 86 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 88 | cut | 87 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 89 | rotate | 88 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 90 | base | — | — | `------Cu` |
| 91 | pin | 90 | — | `------P-:------Cu` |
| 92 | pin | 91 | — | `------P-:------P-:------Cu` |
| 93 | pin | 92 | — | `------P-:------P-:------P-:------Cu` |
| 94 | rotate | 93 | 3 | `----P---:----P---:----P---:----Cu--` |
| 95 | swap | 89, 94 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 96 | rotate | 95 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 97 | swap | 70, 96 | 0 | `--CucrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 98 | pin | 97 | — | `--P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 99 | base | — | — | `--P-----` |
| 100 | stack | 98, 99 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 101 | base | — | — | `--Cu----` |
| 102 | stack | 100, 101 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 103 | cut | 102 | 0 | `--P-----:--Cu----:CuCu----:--P-----:crCu----` |
