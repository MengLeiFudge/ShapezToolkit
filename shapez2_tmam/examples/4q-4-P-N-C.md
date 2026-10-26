# 地面针与晶体间隙

来源底部辅助晶体被顶破删除，地面补针，保留高处普通格与晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-----:--Cu----:CuCu----:--P-----:crCu----`

共97步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 27 | base | — | — | `------Cu` |
| 28 | base | — | — | `------Cu` |
| 29 | stack | 27, 28 | — | `------Cu:------Cu` |
| 30 | base | — | — | `------Cu` |
| 31 | stack | 29, 30 | — | `------Cu:------Cu:------Cu` |
| 32 | base | — | — | `------Cu` |
| 33 | stack | 31, 32 | — | `------Cu:------Cu:------Cu:------Cu` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 36 | swap | 26, 35 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 37 | cut | 36 | 0 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 38 | base | — | — | `------Cu` |
| 39 | base | — | — | `------Cu` |
| 40 | stack | 38, 39 | — | `------Cu:------Cu` |
| 41 | base | — | — | `------Cu` |
| 42 | stack | 40, 41 | — | `------Cu:------Cu:------Cu` |
| 43 | base | — | — | `------Cu` |
| 44 | stack | 42, 43 | — | `------Cu:------Cu:------Cu:------Cu` |
| 45 | base | — | — | `------Cu` |
| 46 | stack | 44, 45 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 47 | swap | 37, 46 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 48 | rotate | 47 | 1 | `CucrCu--:CucrCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 49 | cut | 48 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----:Cu------` |
| 50 | base | — | — | `CuCuCuCu` |
| 51 | base | — | — | `CuP-CuCu` |
| 52 | stack | 50, 51 | — | `CuCuCuCu:CuP-CuCu` |
| 53 | crystal | 52 | r | `CuCuCuCu:CucrCuCu` |
| 54 | cut | 53 | 0 | `CuCu----:Cucr----` |
| 55 | rotate | 54 | 3 | `Cu----Cu:cr----Cu` |
| 56 | cut | 55 | 0 | `Cu------:cr------` |
| 57 | rotate | 56 | 1 | `--Cu----:--cr----` |
| 58 | base | — | — | `--Cu----` |
| 59 | stack | 57, 58 | — | `--Cu----:--cr----:--Cu----` |
| 60 | rotate | 59 | 1 | `----Cu--:----cr--:----Cu--` |
| 61 | swap | 49, 60 | 0 | `CucrCu--:Cucrcr--:CuCuCu--:Cucr----:Cu------` |
| 62 | rotate | 61 | 3 | `crCu--Cu:crcr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 63 | cut | 62 | 0 | `crCu----:crcr----:CuCu----:cr------` |
| 64 | base | — | — | `CuCuP-Cu` |
| 65 | crystal | 64 | r | `CuCucrCu` |
| 66 | base | — | — | `CuCuP-Cu` |
| 67 | stack | 65, 66 | — | `CuCucrCu:CuCuP-Cu` |
| 68 | crystal | 67 | r | `CuCucrCu:CuCucrCu` |
| 69 | base | — | — | `CuCuP-Cu` |
| 70 | stack | 68, 69 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 71 | crystal | 70 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 72 | base | — | — | `CuCuP-Cu` |
| 73 | stack | 71, 72 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 74 | crystal | 73 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 75 | base | — | — | `CuCuP-Cu` |
| 76 | stack | 74, 75 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 77 | crystal | 76 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 78 | rotate | 77 | 3 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 79 | cut | 78 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 80 | rotate | 79 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 81 | cut | 80 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 82 | rotate | 81 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 83 | base | — | — | `------Cu` |
| 84 | pin | 83 | — | `------P-:------Cu` |
| 85 | pin | 84 | — | `------P-:------P-:------Cu` |
| 86 | pin | 85 | — | `------P-:------P-:------P-:------Cu` |
| 87 | rotate | 86 | 3 | `----P---:----P---:----P---:----Cu--` |
| 88 | swap | 82, 87 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 89 | rotate | 88 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 90 | swap | 63, 89 | 0 | `crCucrP-:crcrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 91 | pin | 90 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 92 | base | — | — | `--P-----` |
| 93 | stack | 91, 92 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 94 | base | — | — | `--Cu----` |
| 95 | stack | 93, 94 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 96 | cut | 95 | 0 | `P-P-----:--Cu----:CuCu----:--P-----:crCu----` |
