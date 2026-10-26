# 两层空底

通过侧面支撑保留悬空普通格，顶破后形成两层空底的主列。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:--Cu----:CuCu----:--P-----:crCu----`

共97步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCu` |
| 1 | crystal | 0 | r | `CucrCuCu` |
| 2 | base | — | — | `CuP-CuCu` |
| 3 | stack | 1, 2 | — | `CucrCuCu:CuP-CuCu` |
| 4 | crystal | 3 | r | `CucrCuCu:CucrCuCu` |
| 5 | base | — | — | `CuCuCuCu` |
| 6 | stack | 4, 5 | — | `CucrCuCu:CucrCuCu:CuCuCuCu` |
| 7 | base | — | — | `CuP-CuCu` |
| 8 | stack | 6, 7 | — | `CucrCuCu:CucrCuCu:CuCuCuCu:CuP-CuCu` |
| 9 | crystal | 8 | r | `CucrCuCu:CucrCuCu:CuCuCuCu:CucrCuCu` |
| 10 | cut | 9 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----` |
| 11 | rotate | 10 | 3 | `cr----Cu:cr----Cu:Cu----Cu:cr----Cu` |
| 12 | cut | 11 | 0 | `cr------:cr------:Cu------:cr------` |
| 13 | rotate | 12 | 1 | `--cr----:--cr----:--Cu----:--cr----` |
| 14 | base | — | — | `----Cu--` |
| 15 | base | — | — | `----Cu--` |
| 16 | stack | 14, 15 | — | `----Cu--:----Cu--` |
| 17 | base | — | — | `----Cu--` |
| 18 | stack | 16, 17 | — | `----Cu--:----Cu--:----Cu--` |
| 19 | base | — | — | `----Cu--` |
| 20 | stack | 18, 19 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 21 | base | — | — | `----Cu--` |
| 22 | stack | 20, 21 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 23 | swap | 13, 22 | 0 | `--crCu--:--crCu--:--CuCu--:--crCu--:----Cu--` |
| 24 | rotate | 23 | 3 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 25 | base | — | — | `CuP-CuCu` |
| 26 | crystal | 25 | r | `CucrCuCu` |
| 27 | base | — | — | `CuP-CuCu` |
| 28 | stack | 26, 27 | — | `CucrCuCu:CuP-CuCu` |
| 29 | crystal | 28 | r | `CucrCuCu:CucrCuCu` |
| 30 | cut | 29 | 0 | `Cucr----:Cucr----` |
| 31 | rotate | 30 | 3 | `cr----Cu:cr----Cu` |
| 32 | cut | 31 | 0 | `cr------:cr------` |
| 33 | rotate | 32 | 3 | `------cr:------cr` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------cr:------cr:------Cu` |
| 36 | base | — | — | `------Cu` |
| 37 | stack | 35, 36 | — | `------cr:------cr:------Cu:------Cu` |
| 38 | base | — | — | `------Cu` |
| 39 | stack | 37, 38 | — | `------cr:------cr:------Cu:------Cu:------Cu` |
| 40 | swap | 24, 39 | 0 | `crCu--cr:crCu--cr:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 41 | cut | 40 | 0 | `--Cu----:--Cu----:CuCu----:crCu----:--Cu----` |
| 42 | base | — | — | `------Cu` |
| 43 | base | — | — | `------Cu` |
| 44 | stack | 42, 43 | — | `------Cu:------Cu` |
| 45 | base | — | — | `------Cu` |
| 46 | stack | 44, 45 | — | `------Cu:------Cu:------Cu` |
| 47 | base | — | — | `------Cu` |
| 48 | stack | 46, 47 | — | `------Cu:------Cu:------Cu:------Cu` |
| 49 | base | — | — | `------Cu` |
| 50 | stack | 48, 49 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 51 | swap | 41, 50 | 0 | `--Cu--Cu:--Cu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 52 | rotate | 51 | 1 | `Cu--Cu--:Cu--Cu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 53 | cut | 52 | 0 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 54 | base | — | — | `CuCuCuCu` |
| 55 | base | — | — | `CuP-CuCu` |
| 56 | stack | 54, 55 | — | `CuCuCuCu:CuP-CuCu` |
| 57 | crystal | 56 | r | `CuCuCuCu:CucrCuCu` |
| 58 | cut | 57 | 0 | `CuCu----:Cucr----` |
| 59 | rotate | 58 | 1 | `--CuCu--:--Cucr--` |
| 60 | cut | 59 | 1 | `----Cu--:----cr--` |
| 61 | base | — | — | `----Cu--` |
| 62 | stack | 60, 61 | — | `----Cu--:----cr--:----Cu--` |
| 63 | swap | 53, 62 | 0 | `Cu--Cu--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 64 | rotate | 63 | 3 | `--Cu--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 65 | cut | 64 | 0 | `--Cu----:--cr----:CuCu----:cr------` |
| 66 | base | — | — | `CuP-CuCu` |
| 67 | crystal | 66 | r | `CucrCuCu` |
| 68 | base | — | — | `CuP-CuCu` |
| 69 | stack | 67, 68 | — | `CucrCuCu:CuP-CuCu` |
| 70 | crystal | 69 | r | `CucrCuCu:CucrCuCu` |
| 71 | base | — | — | `CuP-CuCu` |
| 72 | stack | 70, 71 | — | `CucrCuCu:CucrCuCu:CuP-CuCu` |
| 73 | crystal | 72 | r | `CucrCuCu:CucrCuCu:CucrCuCu` |
| 74 | base | — | — | `CuP-CuCu` |
| 75 | stack | 73, 74 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 76 | crystal | 75 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 77 | base | — | — | `CuP-CuCu` |
| 78 | stack | 76, 77 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 79 | crystal | 78 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 80 | cut | 79 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 81 | rotate | 80 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 82 | cut | 81 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 83 | rotate | 82 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 84 | base | — | — | `----Cu--` |
| 85 | pin | 84 | — | `----P---:----Cu--` |
| 86 | pin | 85 | — | `----P---:----P---:----Cu--` |
| 87 | pin | 86 | — | `----P---:----P---:----P---:----Cu--` |
| 88 | swap | 83, 87 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 89 | rotate | 88 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 90 | swap | 65, 89 | 0 | `--CucrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 91 | pin | 90 | — | `--P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 92 | base | — | — | `--P-----` |
| 93 | stack | 91, 92 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 94 | base | — | — | `--Cu----` |
| 95 | stack | 93, 94 | — | `--P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 96 | cut | 95 | 0 | `--P-----:--Cu----:CuCu----:--P-----:crCu----` |
