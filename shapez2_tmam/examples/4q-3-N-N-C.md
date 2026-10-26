# 双普通格间隙

两次转交支撑并顶破，保留两个相隔一层的普通格及顶层晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuP-----:--Cu----:CuCu----:--P-----:crCu----`

共110步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCu` |
| 2 | base | — | — | `CuCuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCu:CuCuCuCu` |
| 4 | base | — | — | `CuCuCuCu` |
| 5 | stack | 3, 4 | — | `crCuCuCu:CuCuCuCu:CuCuCuCu` |
| 6 | base | — | — | `P-CuCuCu` |
| 7 | stack | 5, 6 | — | `crCuCuCu:CuCuCuCu:CuCuCuCu:P-CuCuCu` |
| 8 | crystal | 7 | r | `crCuCuCu:CuCuCuCu:CuCuCuCu:crCuCuCu` |
| 9 | rotate | 8 | 1 | `CucrCuCu:CuCuCuCu:CuCuCuCu:CucrCuCu` |
| 10 | cut | 9 | 0 | `Cucr----:CuCu----:CuCu----:Cucr----` |
| 11 | rotate | 10 | -1 | `cr----Cu:Cu----Cu:Cu----Cu:cr----Cu` |
| 12 | cut | 11 | 0 | `cr------:Cu------:Cu------:cr------` |
| 13 | rotate | 12 | 1 | `--cr----:--Cu----:--Cu----:--cr----` |
| 14 | base | — | — | `--Cu----` |
| 15 | base | — | — | `--Cu----` |
| 16 | stack | 14, 15 | — | `--Cu----:--Cu----` |
| 17 | base | — | — | `--Cu----` |
| 18 | stack | 16, 17 | — | `--Cu----:--Cu----:--Cu----` |
| 19 | base | — | — | `--Cu----` |
| 20 | stack | 18, 19 | — | `--Cu----:--Cu----:--Cu----:--Cu----` |
| 21 | base | — | — | `--Cu----` |
| 22 | stack | 20, 21 | — | `--Cu----:--Cu----:--Cu----:--Cu----:--Cu----` |
| 23 | rotate | 22 | 1 | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 24 | swap | 13, 23 | 0 | `--crCu--:--CuCu--:--CuCu--:--crCu--:----Cu--` |
| 25 | rotate | 24 | -1 | `crCu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 26 | base | — | — | `CuCuCuP-` |
| 27 | crystal | 26 | r | `CuCuCucr` |
| 28 | rotate | 27 | -2 | `CucrCuCu` |
| 29 | cut | 28 | 0 | `Cucr----` |
| 30 | rotate | 29 | 2 | `----Cucr` |
| 31 | rotate | 30 | -3 | `cr----Cu` |
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
| 42 | swap | 25, 41 | 0 | `crCu--cr:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 43 | cut | 42 | 0 | `--Cu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 44 | base | — | — | `------Cu` |
| 45 | base | — | — | `------Cu` |
| 46 | stack | 44, 45 | — | `------Cu:------Cu` |
| 47 | base | — | — | `------Cu` |
| 48 | stack | 46, 47 | — | `------Cu:------Cu:------Cu` |
| 49 | base | — | — | `------Cu` |
| 50 | stack | 48, 49 | — | `------Cu:------Cu:------Cu:------Cu` |
| 51 | base | — | — | `------Cu` |
| 52 | stack | 50, 51 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 53 | swap | 43, 52 | 0 | `--Cu--Cu:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 54 | rotate | 53 | -3 | `Cu--Cu--:CuCuCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 55 | cut | 54 | 0 | `Cu------:CuCu----:CuCu----:Cucr----:Cu------` |
| 56 | rotate | 55 | 3 | `------Cu:Cu----Cu:Cu----Cu:cr----Cu:------Cu` |
| 57 | rotate | 56 | -3 | `Cu------:CuCu----:CuCu----:Cucr----:Cu------` |
| 58 | base | — | — | `CuCuCuCu` |
| 59 | base | — | — | `CuP-CuCu` |
| 60 | stack | 58, 59 | — | `CuCuCuCu:CuP-CuCu` |
| 61 | crystal | 60 | r | `CuCuCuCu:CucrCuCu` |
| 62 | cut | 61 | 0 | `CuCu----:Cucr----` |
| 63 | rotate | 62 | -1 | `Cu----Cu:cr----Cu` |
| 64 | cut | 63 | 0 | `Cu------:cr------` |
| 65 | rotate | 64 | 1 | `--Cu----:--cr----` |
| 66 | base | — | — | `--Cu----` |
| 67 | stack | 65, 66 | — | `--Cu----:--cr----:--Cu----` |
| 68 | rotate | 67 | -3 | `----Cu--:----cr--:----Cu--` |
| 69 | swap | 57, 68 | 0 | `Cu--Cu--:CuCucr--:CuCuCu--:Cucr----:Cu------` |
| 70 | rotate | 69 | 3 | `--Cu--Cu:Cucr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 71 | cut | 70 | 0 | `--Cu----:Cucr----:CuCu----:cr------` |
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
| 86 | rotate | 85 | -1 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 87 | cut | 86 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 88 | rotate | 87 | 1 | `--Cucr--:--Cucr--:--Cucr--:--Cucr--:--Cucr--` |
| 89 | rotate | 88 | -2 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 90 | cut | 89 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 91 | rotate | 90 | 2 | `----cr--:----cr--:----cr--:----cr--:----cr--` |
| 92 | rotate | 91 | -1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 93 | base | — | — | `------P-` |
| 94 | base | — | — | `------P-` |
| 95 | stack | 93, 94 | — | `------P-:------P-` |
| 96 | base | — | — | `------P-` |
| 97 | stack | 95, 96 | — | `------P-:------P-:------P-` |
| 98 | base | — | — | `------Cu` |
| 99 | stack | 97, 98 | — | `------P-:------P-:------P-:------Cu` |
| 100 | rotate | 99 | -1 | `----P---:----P---:----P---:----Cu--` |
| 101 | swap | 92, 100 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 102 | rotate | 101 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 103 | swap | 71, 102 | 0 | `--CucrP-:CucrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 104 | pin | 103 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 105 | base | — | — | `--P-----` |
| 106 | stack | 104, 105 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 107 | base | — | — | `--Cu----` |
| 108 | stack | 106, 107 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 109 | cut | 108 | 0 | `CuP-----:--Cu----:CuCu----:--P-----:crCu----` |
