# 两格高间隙

使用双针支撑尾部，保留普通格和顶层晶体之间的两格间隙。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-----:CuCu----:--P-----:--P-----:crCu----`

共92步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCu` |
| 1 | base | — | — | `CuP-CuCu` |
| 2 | stack | 0, 1 | — | `CuP-CuCu:CuP-CuCu` |
| 3 | base | — | — | `CuCuCuCu` |
| 4 | stack | 2, 3 | — | `CuP-CuCu:CuP-CuCu:CuCuCuCu` |
| 5 | base | — | — | `CuP-CuCu` |
| 6 | stack | 4, 5 | — | `CuP-CuCu:CuP-CuCu:CuCuCuCu:CuP-CuCu` |
| 7 | crystal | 6 | r | `CucrCuCu:CucrCuCu:CuCuCuCu:CucrCuCu` |
| 8 | cut | 7 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----` |
| 9 | rotate | 8 | 3 | `cr----Cu:cr----Cu:Cu----Cu:cr----Cu` |
| 10 | cut | 9 | 0 | `cr------:cr------:Cu------:cr------` |
| 11 | rotate | 10 | 1 | `--cr----:--cr----:--Cu----:--cr----` |
| 12 | base | — | — | `----Cu--` |
| 13 | base | — | — | `----Cu--` |
| 14 | stack | 12, 13 | — | `----Cu--:----Cu--` |
| 15 | base | — | — | `----Cu--` |
| 16 | stack | 14, 15 | — | `----Cu--:----Cu--:----Cu--` |
| 17 | base | — | — | `----Cu--` |
| 18 | stack | 16, 17 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 19 | base | — | — | `----Cu--` |
| 20 | stack | 18, 19 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 21 | swap | 11, 20 | 0 | `--crCu--:--crCu--:--CuCu--:--crCu--:----Cu--` |
| 22 | rotate | 21 | 3 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 23 | base | — | — | `CuP-CuCu` |
| 24 | base | — | — | `CuP-CuCu` |
| 25 | stack | 23, 24 | — | `CuP-CuCu:CuP-CuCu` |
| 26 | base | — | — | `CuCuCuCu` |
| 27 | stack | 25, 26 | — | `CuP-CuCu:CuP-CuCu:CuCuCuCu` |
| 28 | base | — | — | `CuCuCuCu` |
| 29 | stack | 27, 28 | — | `CuP-CuCu:CuP-CuCu:CuCuCuCu:CuCuCuCu` |
| 30 | base | — | — | `CuCuCuCu` |
| 31 | stack | 29, 30 | — | `CuP-CuCu:CuP-CuCu:CuCuCuCu:CuCuCuCu:CuCuCuCu` |
| 32 | crystal | 31 | r | `CucrCuCu:CucrCuCu:CuCuCuCu:CuCuCuCu:CuCuCuCu` |
| 33 | cut | 32 | 0 | `Cucr----:Cucr----:CuCu----:CuCu----:CuCu----` |
| 34 | rotate | 33 | 3 | `cr----Cu:cr----Cu:Cu----Cu:Cu----Cu:Cu----Cu` |
| 35 | cut | 34 | 0 | `cr------:cr------:Cu------:Cu------:Cu------` |
| 36 | rotate | 35 | 3 | `------cr:------cr:------Cu:------Cu:------Cu` |
| 37 | swap | 22, 36 | 0 | `crCu--cr:crCu--cr:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 38 | cut | 37 | 0 | `--Cu----:--Cu----:CuCu----:crCu----:--Cu----` |
| 39 | base | — | — | `------Cu` |
| 40 | base | — | — | `------Cu` |
| 41 | stack | 39, 40 | — | `------Cu:------Cu` |
| 42 | base | — | — | `------Cu` |
| 43 | stack | 41, 42 | — | `------Cu:------Cu:------Cu` |
| 44 | base | — | — | `------Cu` |
| 45 | stack | 43, 44 | — | `------Cu:------Cu:------Cu:------Cu` |
| 46 | base | — | — | `------Cu` |
| 47 | stack | 45, 46 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 48 | swap | 38, 47 | 0 | `--Cu--Cu:--Cu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 49 | rotate | 48 | 1 | `Cu--Cu--:Cu--Cu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 50 | cut | 49 | 0 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 51 | base | — | — | `CuP-CuCu` |
| 52 | base | — | — | `CuP-CuCu` |
| 53 | stack | 51, 52 | — | `CuP-CuCu:CuP-CuCu` |
| 54 | crystal | 53 | r | `CucrCuCu:CucrCuCu` |
| 55 | cut | 54 | 0 | `Cucr----:Cucr----` |
| 56 | rotate | 55 | 1 | `--Cucr--:--Cucr--` |
| 57 | cut | 56 | 1 | `----cr--:----cr--` |
| 58 | base | — | — | `----Cu--` |
| 59 | stack | 57, 58 | — | `----cr--:----cr--:----Cu--` |
| 60 | swap | 50, 59 | 0 | `Cu--cr--:Cu--cr--:CuCuCu--:Cucr----:Cu------` |
| 61 | rotate | 60 | 3 | `--cr--Cu:--cr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 62 | cut | 61 | 0 | `--cr----:--cr----:CuCu----:cr------` |
| 63 | base | — | — | `CuP-CuCu` |
| 64 | base | — | — | `CuP-CuCu` |
| 65 | stack | 63, 64 | — | `CuP-CuCu:CuP-CuCu` |
| 66 | base | — | — | `CuP-CuCu` |
| 67 | stack | 65, 66 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 68 | base | — | — | `CuP-CuCu` |
| 69 | stack | 67, 68 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 70 | base | — | — | `CuP-CuCu` |
| 71 | stack | 69, 70 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 72 | crystal | 71 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 73 | cut | 72 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 74 | rotate | 73 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 75 | cut | 74 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 76 | rotate | 75 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 77 | base | — | — | `----Cu--` |
| 78 | pin | 77 | — | `----P---:----Cu--` |
| 79 | pin | 78 | — | `----P---:----P---:----Cu--` |
| 80 | pin | 79 | — | `----P---:----P---:----P---:----Cu--` |
| 81 | swap | 76, 80 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 82 | rotate | 81 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 83 | swap | 62, 82 | 0 | `--crcrP-:--crcrP-:CuCucrP-:cr--crCu:----cr--` |
| 84 | pin | 83 | — | `--P-P-P-:CuCu--P-:------P-:------P-:cr----Cu` |
| 85 | base | — | — | `--P-----` |
| 86 | stack | 84, 85 | — | `--P-P-P-:CuCu--P-:--P---P-:------P-:cr----Cu` |
| 87 | base | — | — | `--P-----` |
| 88 | stack | 86, 87 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:cr----Cu` |
| 89 | base | — | — | `--Cu----` |
| 90 | stack | 88, 89 | — | `--P-P-P-:CuCu--P-:--P---P-:--P---P-:crCu--Cu` |
| 91 | cut | 90 | 0 | `--P-----:CuCu----:--P-----:--P-----:crCu----` |
