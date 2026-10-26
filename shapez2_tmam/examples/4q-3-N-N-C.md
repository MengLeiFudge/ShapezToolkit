# 双普通格间隙

两次转交支撑并顶破，保留两个相隔一层的普通格及顶层晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuP-----:--Cu----:CuCu----:--P-----:crCu----`

共95步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCu` |
| 1 | crystal | 0 | r | `CucrCuCu` |
| 2 | base | — | — | `CuCuCuCu` |
| 3 | stack | 1, 2 | — | `CucrCuCu:CuCuCuCu` |
| 4 | base | — | — | `CuCuCuCu` |
| 5 | stack | 3, 4 | — | `CucrCuCu:CuCuCuCu:CuCuCuCu` |
| 6 | base | — | — | `CuP-CuCu` |
| 7 | stack | 5, 6 | — | `CucrCuCu:CuCuCuCu:CuCuCuCu:CuP-CuCu` |
| 8 | crystal | 7 | r | `CucrCuCu:CuCuCuCu:CuCuCuCu:CucrCuCu` |
| 9 | cut | 8 | 0 | `Cucr----:CuCu----:CuCu----:Cucr----` |
| 10 | rotate | 9 | 3 | `cr----Cu:Cu----Cu:Cu----Cu:cr----Cu` |
| 11 | cut | 10 | 0 | `cr------:Cu------:Cu------:cr------` |
| 12 | rotate | 11 | 1 | `--cr----:--Cu----:--Cu----:--cr----` |
| 13 | base | — | — | `----Cu--` |
| 14 | base | — | — | `----Cu--` |
| 15 | stack | 13, 14 | — | `----Cu--:----Cu--` |
| 16 | base | — | — | `----Cu--` |
| 17 | stack | 15, 16 | — | `----Cu--:----Cu--:----Cu--` |
| 18 | base | — | — | `----Cu--` |
| 19 | stack | 17, 18 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 20 | base | — | — | `----Cu--` |
| 21 | stack | 19, 20 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 22 | swap | 12, 21 | 0 | `--crCu--:--CuCu--:--CuCu--:--crCu--:----Cu--` |
| 23 | rotate | 22 | 3 | `crCu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 24 | base | — | — | `CuP-CuCu` |
| 25 | crystal | 24 | r | `CucrCuCu` |
| 26 | cut | 25 | 0 | `Cucr----` |
| 27 | rotate | 26 | 3 | `cr----Cu` |
| 28 | cut | 27 | 0 | `cr------` |
| 29 | rotate | 28 | 3 | `------cr` |
| 30 | base | — | — | `------Cu` |
| 31 | stack | 29, 30 | — | `------cr:------Cu` |
| 32 | base | — | — | `------Cu` |
| 33 | stack | 31, 32 | — | `------cr:------Cu:------Cu` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------cr:------Cu:------Cu:------Cu` |
| 36 | base | — | — | `------Cu` |
| 37 | stack | 35, 36 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 38 | swap | 23, 37 | 0 | `crCu--cr:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 39 | cut | 38 | 0 | `--Cu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 40 | base | — | — | `------Cu` |
| 41 | base | — | — | `------Cu` |
| 42 | stack | 40, 41 | — | `------Cu:------Cu` |
| 43 | base | — | — | `------Cu` |
| 44 | stack | 42, 43 | — | `------Cu:------Cu:------Cu` |
| 45 | base | — | — | `------Cu` |
| 46 | stack | 44, 45 | — | `------Cu:------Cu:------Cu:------Cu` |
| 47 | base | — | — | `------Cu` |
| 48 | stack | 46, 47 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 49 | swap | 39, 48 | 0 | `--Cu--Cu:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 50 | rotate | 49 | 1 | `Cu--Cu--:CuCuCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 51 | cut | 50 | 0 | `Cu------:CuCu----:CuCu----:Cucr----:Cu------` |
| 52 | base | — | — | `CuCuCuCu` |
| 53 | base | — | — | `CuP-CuCu` |
| 54 | stack | 52, 53 | — | `CuCuCuCu:CuP-CuCu` |
| 55 | crystal | 54 | r | `CuCuCuCu:CucrCuCu` |
| 56 | cut | 55 | 0 | `CuCu----:Cucr----` |
| 57 | rotate | 56 | 1 | `--CuCu--:--Cucr--` |
| 58 | cut | 57 | 1 | `----Cu--:----cr--` |
| 59 | base | — | — | `----Cu--` |
| 60 | stack | 58, 59 | — | `----Cu--:----cr--:----Cu--` |
| 61 | swap | 51, 60 | 0 | `Cu--Cu--:CuCucr--:CuCuCu--:Cucr----:Cu------` |
| 62 | rotate | 61 | 3 | `--Cu--Cu:Cucr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 63 | cut | 62 | 0 | `--Cu----:Cucr----:CuCu----:cr------` |
| 64 | base | — | — | `CuP-CuCu` |
| 65 | crystal | 64 | r | `CucrCuCu` |
| 66 | base | — | — | `CuP-CuCu` |
| 67 | stack | 65, 66 | — | `CucrCuCu:CuP-CuCu` |
| 68 | crystal | 67 | r | `CucrCuCu:CucrCuCu` |
| 69 | base | — | — | `CuP-CuCu` |
| 70 | stack | 68, 69 | — | `CucrCuCu:CucrCuCu:CuP-CuCu` |
| 71 | crystal | 70 | r | `CucrCuCu:CucrCuCu:CucrCuCu` |
| 72 | base | — | — | `CuP-CuCu` |
| 73 | stack | 71, 72 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 74 | crystal | 73 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 75 | base | — | — | `CuP-CuCu` |
| 76 | stack | 74, 75 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 77 | crystal | 76 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 78 | cut | 77 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 79 | rotate | 78 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 80 | cut | 79 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 81 | rotate | 80 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 82 | base | — | — | `----Cu--` |
| 83 | pin | 82 | — | `----P---:----Cu--` |
| 84 | pin | 83 | — | `----P---:----P---:----Cu--` |
| 85 | pin | 84 | — | `----P---:----P---:----P---:----Cu--` |
| 86 | swap | 81, 85 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 87 | rotate | 86 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 88 | swap | 63, 87 | 0 | `--CucrP-:CucrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 89 | pin | 88 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 90 | base | — | — | `--P-----` |
| 91 | stack | 89, 90 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 92 | base | — | — | `--Cu----` |
| 93 | stack | 91, 92 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 94 | cut | 93 | 0 | `CuP-----:--Cu----:CuCu----:--P-----:crCu----` |
