# 两层空底

通过侧面支撑保留悬空普通格，顶破后形成两层空底的主列。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:--Cu----:CuCu----:--P-----:crCu----`

共109步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 60 | base | — | — | `CuCuCuCu` |
| 61 | base | — | — | `CuP-CuCu` |
| 62 | stack | 60, 61 | — | `CuCuCuCu:CuP-CuCu` |
| 63 | crystal | 62 | r | `CuCuCuCu:CucrCuCu` |
| 64 | cut | 63 | 0 | `CuCu----:Cucr----` |
| 65 | rotate | 64 | -1 | `Cu----Cu:cr----Cu` |
| 66 | cut | 65 | 0 | `Cu------:cr------` |
| 67 | rotate | 66 | 1 | `--Cu----:--cr----` |
| 68 | base | — | — | `--Cu----` |
| 69 | stack | 67, 68 | — | `--Cu----:--cr----:--Cu----` |
| 70 | rotate | 69 | -3 | `----Cu--:----cr--:----Cu--` |
| 71 | swap | 59, 70 | 0 | `Cu--Cu--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 72 | rotate | 71 | 3 | `--Cu--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 73 | cut | 72 | 0 | `--Cu----:--cr----:CuCu----:cr------` |
| 74 | base | — | — | `CuCuP-Cu` |
| 75 | crystal | 74 | r | `CuCucrCu` |
| 76 | base | — | — | `CuCuP-Cu` |
| 77 | stack | 75, 76 | — | `CuCucrCu:CuCuP-Cu` |
| 78 | crystal | 77 | r | `CuCucrCu:CuCucrCu` |
| 79 | base | — | — | `CuCuP-Cu` |
| 80 | stack | 78, 79 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 81 | crystal | 80 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 82 | base | — | — | `CuCuP-Cu` |
| 83 | stack | 81, 82 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 84 | crystal | 83 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 85 | base | — | — | `CuCuP-Cu` |
| 86 | stack | 84, 85 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 87 | crystal | 86 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 88 | rotate | 87 | -1 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 89 | cut | 88 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 90 | rotate | 89 | 1 | `--Cucr--:--Cucr--:--Cucr--:--Cucr--:--Cucr--` |
| 91 | rotate | 90 | -2 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 92 | cut | 91 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 93 | rotate | 92 | 2 | `----cr--:----cr--:----cr--:----cr--:----cr--` |
| 94 | rotate | 93 | -1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 95 | base | — | — | `------Cu` |
| 96 | pin | 95 | — | `------P-:------Cu` |
| 97 | pin | 96 | — | `------P-:------P-:------Cu` |
| 98 | pin | 97 | — | `------P-:------P-:------P-:------Cu` |
| 99 | rotate | 98 | -1 | `----P---:----P---:----P---:----Cu--` |
| 100 | swap | 94, 99 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 101 | rotate | 100 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 102 | swap | 73, 101 | 0 | `--CucrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 103 | pin | 102 | — | `--P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 104 | base | — | — | `--P-----` |
| 105 | stack | 103, 104 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 106 | base | — | — | `--Cu----` |
| 107 | stack | 105, 106 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 108 | cut | 107 | 0 | `--P-----:--Cu----:CuCu----:--P-----:crCu----` |
