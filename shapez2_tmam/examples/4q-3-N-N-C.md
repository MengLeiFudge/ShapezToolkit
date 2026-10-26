# 双普通格间隙

两次转交支撑并顶破，保留两个相隔一层的普通格及顶层晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuP-----:--Cu----:CuCu----:--P-----:crCu----`

共90步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCu` |
| 1 | base | — | — | `CuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuP-CuCu:CuCuCuCu` |
| 3 | base | — | — | `CuCuCuCu` |
| 4 | stack | 2, 3 | — | `CuP-CuCu:CuCuCuCu:CuCuCuCu` |
| 5 | base | — | — | `CuP-CuCu` |
| 6 | stack | 4, 5 | — | `CuP-CuCu:CuCuCuCu:CuCuCuCu:CuP-CuCu` |
| 7 | crystal | 6 | r | `CucrCuCu:CuCuCuCu:CuCuCuCu:CucrCuCu` |
| 8 | cut | 7 | 0 | `Cucr----:CuCu----:CuCu----:Cucr----` |
| 9 | rotate | 8 | 3 | `cr----Cu:Cu----Cu:Cu----Cu:cr----Cu` |
| 10 | cut | 9 | 0 | `cr------:Cu------:Cu------:cr------` |
| 11 | rotate | 10 | 1 | `--cr----:--Cu----:--Cu----:--cr----` |
| 12 | base | — | — | `----Cu--` |
| 13 | base | — | — | `----Cu--` |
| 14 | stack | 12, 13 | — | `----Cu--:----Cu--` |
| 15 | base | — | — | `----Cu--` |
| 16 | stack | 14, 15 | — | `----Cu--:----Cu--:----Cu--` |
| 17 | base | — | — | `----Cu--` |
| 18 | stack | 16, 17 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 19 | base | — | — | `----Cu--` |
| 20 | stack | 18, 19 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 21 | swap | 11, 20 | 0 | `--crCu--:--CuCu--:--CuCu--:--crCu--:----Cu--` |
| 22 | rotate | 21 | 3 | `crCu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 23 | base | — | — | `CuP-CuCu` |
| 24 | crystal | 23 | r | `CucrCuCu` |
| 25 | cut | 24 | 0 | `Cucr----` |
| 26 | rotate | 25 | 3 | `cr----Cu` |
| 27 | cut | 26 | 0 | `cr------` |
| 28 | rotate | 27 | 3 | `------cr` |
| 29 | base | — | — | `------Cu` |
| 30 | stack | 28, 29 | — | `------cr:------Cu` |
| 31 | base | — | — | `------Cu` |
| 32 | stack | 30, 31 | — | `------cr:------Cu:------Cu` |
| 33 | base | — | — | `------Cu` |
| 34 | stack | 32, 33 | — | `------cr:------Cu:------Cu:------Cu` |
| 35 | base | — | — | `------Cu` |
| 36 | stack | 34, 35 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 37 | swap | 22, 36 | 0 | `crCu--cr:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 38 | cut | 37 | 0 | `--Cu----:CuCu----:CuCu----:crCu----:--Cu----` |
| 39 | base | — | — | `------Cu` |
| 40 | base | — | — | `------Cu` |
| 41 | stack | 39, 40 | — | `------Cu:------Cu` |
| 42 | base | — | — | `------Cu` |
| 43 | stack | 41, 42 | — | `------Cu:------Cu:------Cu` |
| 44 | base | — | — | `------Cu` |
| 45 | stack | 43, 44 | — | `------Cu:------Cu:------Cu:------Cu` |
| 46 | base | — | — | `------Cu` |
| 47 | stack | 45, 46 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 48 | swap | 38, 47 | 0 | `--Cu--Cu:CuCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 49 | rotate | 48 | 1 | `Cu--Cu--:CuCuCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 50 | cut | 49 | 0 | `Cu------:CuCu----:CuCu----:Cucr----:Cu------` |
| 51 | base | — | — | `CuCuCuCu` |
| 52 | base | — | — | `CuP-CuCu` |
| 53 | stack | 51, 52 | — | `CuCuCuCu:CuP-CuCu` |
| 54 | crystal | 53 | r | `CuCuCuCu:CucrCuCu` |
| 55 | cut | 54 | 0 | `CuCu----:Cucr----` |
| 56 | rotate | 55 | 1 | `--CuCu--:--Cucr--` |
| 57 | cut | 56 | 1 | `----Cu--:----cr--` |
| 58 | base | — | — | `----Cu--` |
| 59 | stack | 57, 58 | — | `----Cu--:----cr--:----Cu--` |
| 60 | swap | 50, 59 | 0 | `Cu--Cu--:CuCucr--:CuCuCu--:Cucr----:Cu------` |
| 61 | rotate | 60 | 3 | `--Cu--Cu:Cucr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 62 | cut | 61 | 0 | `--Cu----:Cucr----:CuCu----:cr------` |
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
| 83 | swap | 62, 82 | 0 | `--CucrP-:CucrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 84 | pin | 83 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 85 | base | — | — | `--P-----` |
| 86 | stack | 84, 85 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 87 | base | — | — | `--Cu----` |
| 88 | stack | 86, 87 | — | `CuP-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 89 | cut | 88 | 0 | `CuP-----:--Cu----:CuCu----:--P-----:crCu----` |
