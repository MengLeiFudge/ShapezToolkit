# 地面针与晶体间隙

来源底部辅助晶体被顶破删除，地面补针，保留高处普通格与晶体。

配置：4象限、五层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-----:--Cu----:CuCu----:--P-----:crCu----`

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
| 48 | rotate | 47 | -3 | `CucrCu--:CucrCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 49 | cut | 48 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----:Cu------` |
| 50 | rotate | 49 | 3 | `cr----Cu:cr----Cu:Cu----Cu:cr----Cu:------Cu` |
| 51 | rotate | 50 | -3 | `Cucr----:Cucr----:CuCu----:Cucr----:Cu------` |
| 52 | base | — | — | `CuCuCuCu` |
| 53 | base | — | — | `CuP-CuCu` |
| 54 | stack | 52, 53 | — | `CuCuCuCu:CuP-CuCu` |
| 55 | crystal | 54 | r | `CuCuCuCu:CucrCuCu` |
| 56 | cut | 55 | 0 | `CuCu----:Cucr----` |
| 57 | rotate | 56 | -1 | `Cu----Cu:cr----Cu` |
| 58 | cut | 57 | 0 | `Cu------:cr------` |
| 59 | rotate | 58 | 1 | `--Cu----:--cr----` |
| 60 | base | — | — | `--Cu----` |
| 61 | stack | 59, 60 | — | `--Cu----:--cr----:--Cu----` |
| 62 | rotate | 61 | -3 | `----Cu--:----cr--:----Cu--` |
| 63 | swap | 51, 62 | 0 | `CucrCu--:Cucrcr--:CuCuCu--:Cucr----:Cu------` |
| 64 | rotate | 63 | 3 | `crCu--Cu:crcr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 65 | cut | 64 | 0 | `crCu----:crcr----:CuCu----:cr------` |
| 66 | base | — | — | `CuCuP-Cu` |
| 67 | crystal | 66 | r | `CuCucrCu` |
| 68 | base | — | — | `CuCuP-Cu` |
| 69 | stack | 67, 68 | — | `CuCucrCu:CuCuP-Cu` |
| 70 | crystal | 69 | r | `CuCucrCu:CuCucrCu` |
| 71 | base | — | — | `CuCuP-Cu` |
| 72 | stack | 70, 71 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 73 | crystal | 72 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 74 | base | — | — | `CuCuP-Cu` |
| 75 | stack | 73, 74 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 76 | crystal | 75 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 77 | base | — | — | `CuCuP-Cu` |
| 78 | stack | 76, 77 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 79 | crystal | 78 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 80 | rotate | 79 | -1 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 81 | cut | 80 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 82 | rotate | 81 | 1 | `--Cucr--:--Cucr--:--Cucr--:--Cucr--:--Cucr--` |
| 83 | rotate | 82 | -2 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 84 | cut | 83 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 85 | rotate | 84 | 2 | `----cr--:----cr--:----cr--:----cr--:----cr--` |
| 86 | rotate | 85 | -1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 87 | base | — | — | `------P-` |
| 88 | base | — | — | `------P-` |
| 89 | stack | 87, 88 | — | `------P-:------P-` |
| 90 | base | — | — | `------P-` |
| 91 | stack | 89, 90 | — | `------P-:------P-:------P-` |
| 92 | base | — | — | `------Cu` |
| 93 | stack | 91, 92 | — | `------P-:------P-:------P-:------Cu` |
| 94 | rotate | 93 | -1 | `----P---:----P---:----P---:----Cu--` |
| 95 | swap | 86, 94 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 96 | rotate | 95 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 97 | swap | 65, 96 | 0 | `crCucrP-:crcrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 98 | pin | 97 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 99 | base | — | — | `--P-----` |
| 100 | stack | 98, 99 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 101 | base | — | — | `--Cu----` |
| 102 | stack | 100, 101 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 103 | cut | 102 | 0 | `P-P-----:--Cu----:CuCu----:--P-----:crCu----` |
