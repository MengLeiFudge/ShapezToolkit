# 双普通格间隙

两次转交支撑并顶破，保留两个相隔一层的普通格及顶层晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuP-----:--Cu----:CuCu----:--P-----:crCu----`

共102步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
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
| 11 | rotate | 10 | 3 | `cr----Cu:Cu----Cu:Cu----Cu:cr----Cu` |
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
| 25 | rotate | 24 | 3 | `crCu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 26 | base | — | — | `CuCuCuP-` |
| 27 | crystal | 26 | r | `CuCuCucr` |
| 28 | rotate | 27 | 2 | `CucrCuCu` |
| 29 | cut | 28 | 0 | `Cucr----` |
| 30 | rotate | 29 | 3 | `cr----Cu` |
| 31 | cut | 30 | 0 | `cr------` |
| 32 | rotate | 31 | 3 | `------cr` |
| 33 | base | — | — | `------Cu` |
| 34 | stack | 32, 33 | — | `------cr:------Cu` |
| 35 | base | — | — | `------Cu` |
| 36 | stack | 34, 35 | — | `------cr:------Cu:------Cu` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------cr:------Cu:------Cu:------Cu` |
| 39 | base | — | — | `------Cu` |
| 40 | stack | 38, 39 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 41 | swap | 25, 40 | 0 | `crCu--cr:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 42 | cut | 41 | 0 | `--Cu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 43 | base | — | — | `------Cu` |
| 44 | base | — | — | `------Cu` |
| 45 | stack | 43, 44 | — | `------Cu:------Cu` |
| 46 | base | — | — | `------Cu` |
| 47 | stack | 45, 46 | — | `------Cu:------Cu:------Cu` |
| 48 | base | — | — | `------Cu` |
| 49 | stack | 47, 48 | — | `------Cu:------Cu:------Cu:------Cu` |
| 50 | base | — | — | `------Cu` |
| 51 | stack | 49, 50 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 52 | swap | 42, 51 | 0 | `--Cu--Cu:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 53 | rotate | 52 | 1 | `Cu--Cu--:CuCuCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 54 | cut | 53 | 0 | `Cu------:CuCu----:CuCu----:Cucr----:Cu------` |
| 55 | base | — | — | `CuCuCuCu` |
| 56 | base | — | — | `CuP-CuCu` |
| 57 | stack | 55, 56 | — | `CuCuCuCu:CuP-CuCu` |
| 58 | crystal | 57 | r | `CuCuCuCu:CucrCuCu` |
| 59 | cut | 58 | 0 | `CuCu----:Cucr----` |
| 60 | rotate | 59 | 3 | `Cu----Cu:cr----Cu` |
| 61 | cut | 60 | 0 | `Cu------:cr------` |
| 62 | rotate | 61 | 1 | `--Cu----:--cr----` |
| 63 | base | — | — | `--Cu----` |
| 64 | stack | 62, 63 | — | `--Cu----:--cr----:--Cu----` |
| 65 | rotate | 64 | 1 | `----Cu--:----cr--:----Cu--` |
| 66 | swap | 54, 65 | 0 | `Cu--Cu--:CuCucr--:CuCuCu--:Cucr----:Cu------` |
| 67 | rotate | 66 | 3 | `--Cu--Cu:Cucr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 68 | cut | 67 | 0 | `--Cu----:Cucr----:CuCu----:cr------` |
| 69 | base | — | — | `CuCuP-Cu` |
| 70 | crystal | 69 | r | `CuCucrCu` |
| 71 | base | — | — | `CuCuP-Cu` |
| 72 | stack | 70, 71 | — | `CuCucrCu:CuCuP-Cu` |
| 73 | crystal | 72 | r | `CuCucrCu:CuCucrCu` |
| 74 | base | — | — | `CuCuP-Cu` |
| 75 | stack | 73, 74 | — | `CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 76 | crystal | 75 | r | `CuCucrCu:CuCucrCu:CuCucrCu` |
| 77 | base | — | — | `CuCuP-Cu` |
| 78 | stack | 76, 77 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 79 | crystal | 78 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 80 | base | — | — | `CuCuP-Cu` |
| 81 | stack | 79, 80 | — | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCuP-Cu` |
| 82 | crystal | 81 | r | `CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu:CuCucrCu` |
| 83 | rotate | 82 | 3 | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 84 | cut | 83 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 85 | rotate | 84 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 86 | cut | 85 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 87 | rotate | 86 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 88 | base | — | — | `------Cu` |
| 89 | pin | 88 | — | `------P-:------Cu` |
| 90 | pin | 89 | — | `------P-:------P-:------Cu` |
| 91 | pin | 90 | — | `------P-:------P-:------P-:------Cu` |
| 92 | rotate | 91 | 3 | `----P---:----P---:----P---:----Cu--` |
| 93 | swap | 87, 92 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 94 | rotate | 93 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 95 | swap | 68, 94 | 0 | `--CucrP-:CucrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 96 | pin | 95 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 97 | base | — | — | `--P-----` |
| 98 | stack | 96, 97 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 99 | base | — | — | `--Cu----` |
| 100 | stack | 98, 99 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 101 | cut | 100 | 0 | `CuP-----:--Cu----:CuCu----:--P-----:crCu----` |
