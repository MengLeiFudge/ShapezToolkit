# 两层空底

通过侧面支撑保留悬空普通格，顶破后形成两层空底的主列。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:--Cu----:CuCu----:--P-----:crCu----`

共78步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCu` |
| 1 | base | — | — | `P-CuCuCu` |
| 2 | stack | 0, 1 | — | `P-CuCuCu:P-CuCuCu` |
| 3 | base | — | — | `CuCuCuCu` |
| 4 | stack | 2, 3 | — | `P-CuCuCu:P-CuCuCu:CuCuCuCu` |
| 5 | base | — | — | `P-CuCuCu` |
| 6 | stack | 4, 5 | — | `P-CuCuCu:P-CuCuCu:CuCuCuCu:P-CuCuCu` |
| 7 | crystal | 6 | r | `crCuCuCu:crCuCuCu:CuCuCuCu:crCuCuCu` |
| 8 | cut | 7 | 0 | `crCu----:crCu----:CuCu----:crCu----` |
| 9 | base | — | — | `--Cu----` |
| 10 | stack | 8, 9 | — | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 11 | base | — | — | `CuP-CuCu` |
| 12 | base | — | — | `CuP-CuCu` |
| 13 | stack | 11, 12 | — | `CuP-CuCu:CuP-CuCu` |
| 14 | crystal | 13 | r | `CucrCuCu:CucrCuCu` |
| 15 | cut | 14 | 0 | `Cucr----:Cucr----` |
| 16 | rotate | 15 | 3 | `cr----Cu:cr----Cu` |
| 17 | cut | 16 | 0 | `cr------:cr------` |
| 18 | rotate | 17 | 3 | `------cr:------cr` |
| 19 | base | — | — | `------Cu` |
| 20 | stack | 18, 19 | — | `------cr:------cr:------Cu` |
| 21 | base | — | — | `------Cu` |
| 22 | stack | 20, 21 | — | `------cr:------cr:------Cu:------Cu` |
| 23 | base | — | — | `------Cu` |
| 24 | stack | 22, 23 | — | `------cr:------cr:------Cu:------Cu:------Cu` |
| 25 | swap | 10, 24 | 0 | `crCu--cr:crCu--cr:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 26 | cut | 25 | 0 | `--Cu----:--Cu----:CuCu----:crCu----:--Cu----` |
| 27 | base | — | — | `------Cu` |
| 28 | base | — | — | `------Cu` |
| 29 | stack | 27, 28 | — | `------Cu:------Cu` |
| 30 | base | — | — | `------Cu` |
| 31 | stack | 29, 30 | — | `------Cu:------Cu:------Cu` |
| 32 | base | — | — | `------Cu` |
| 33 | stack | 31, 32 | — | `------Cu:------Cu:------Cu:------Cu` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 36 | swap | 26, 35 | 0 | `--Cu--Cu:--Cu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 37 | rotate | 36 | 1 | `Cu--Cu--:Cu--Cu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 38 | cut | 37 | 0 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 39 | base | — | — | `CuCuCuCu` |
| 40 | base | — | — | `CuP-CuCu` |
| 41 | stack | 39, 40 | — | `CuCuCuCu:CuP-CuCu` |
| 42 | crystal | 41 | r | `CuCuCuCu:CucrCuCu` |
| 43 | cut | 42 | 0 | `CuCu----:Cucr----` |
| 44 | rotate | 43 | 1 | `--CuCu--:--Cucr--` |
| 45 | cut | 44 | 1 | `----Cu--:----cr--` |
| 46 | base | — | — | `----Cu--` |
| 47 | stack | 45, 46 | — | `----Cu--:----cr--:----Cu--` |
| 48 | swap | 38, 47 | 0 | `Cu--Cu--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 49 | rotate | 48 | 3 | `--Cu--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 50 | cut | 49 | 0 | `--Cu----:--cr----:CuCu----:cr------` |
| 51 | base | — | — | `CuP-CuCu` |
| 52 | base | — | — | `CuP-CuCu` |
| 53 | stack | 51, 52 | — | `CuP-CuCu:CuP-CuCu` |
| 54 | base | — | — | `CuP-CuCu` |
| 55 | stack | 53, 54 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 56 | base | — | — | `CuP-CuCu` |
| 57 | stack | 55, 56 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 58 | base | — | — | `CuP-CuCu` |
| 59 | stack | 57, 58 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 60 | crystal | 59 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 61 | cut | 60 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 62 | rotate | 61 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 63 | cut | 62 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 64 | rotate | 63 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 65 | base | — | — | `----Cu--` |
| 66 | pin | 65 | — | `----P---:----Cu--` |
| 67 | pin | 66 | — | `----P---:----P---:----Cu--` |
| 68 | pin | 67 | — | `----P---:----P---:----P---:----Cu--` |
| 69 | swap | 64, 68 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 70 | rotate | 69 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 71 | swap | 50, 70 | 0 | `--CucrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 72 | pin | 71 | — | `--P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 73 | base | — | — | `--P-----` |
| 74 | stack | 72, 73 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 75 | base | — | — | `--Cu----` |
| 76 | stack | 74, 75 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 77 | cut | 76 | 0 | `--P-----:--Cu----:CuCu----:--P-----:crCu----` |
