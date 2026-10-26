# 地面针与晶体间隙

来源底部辅助晶体被顶破删除，地面补针，保留高处普通格与晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-----:--Cu----:CuCu----:--P-----:crCu----`

共91步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 25 | base | — | — | `------Cu` |
| 26 | base | — | — | `------Cu` |
| 27 | stack | 25, 26 | — | `------Cu:------Cu` |
| 28 | base | — | — | `------Cu` |
| 29 | stack | 27, 28 | — | `------Cu:------Cu:------Cu` |
| 30 | base | — | — | `------Cu` |
| 31 | stack | 29, 30 | — | `------Cu:------Cu:------Cu:------Cu` |
| 32 | base | — | — | `------Cu` |
| 33 | stack | 31, 32 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 34 | swap | 24, 33 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 35 | cut | 34 | 0 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 36 | base | — | — | `------Cu` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------Cu:------Cu` |
| 39 | base | — | — | `------Cu` |
| 40 | stack | 38, 39 | — | `------Cu:------Cu:------Cu` |
| 41 | base | — | — | `------Cu` |
| 42 | stack | 40, 41 | — | `------Cu:------Cu:------Cu:------Cu` |
| 43 | base | — | — | `------Cu` |
| 44 | stack | 42, 43 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 45 | swap | 35, 44 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 46 | rotate | 45 | 1 | `CucrCu--:CucrCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 47 | cut | 46 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----:Cu------` |
| 48 | base | — | — | `CuCuCuCu` |
| 49 | base | — | — | `CuP-CuCu` |
| 50 | stack | 48, 49 | — | `CuCuCuCu:CuP-CuCu` |
| 51 | crystal | 50 | r | `CuCuCuCu:CucrCuCu` |
| 52 | cut | 51 | 0 | `CuCu----:Cucr----` |
| 53 | rotate | 52 | 1 | `--CuCu--:--Cucr--` |
| 54 | cut | 53 | 1 | `----Cu--:----cr--` |
| 55 | base | — | — | `----Cu--` |
| 56 | stack | 54, 55 | — | `----Cu--:----cr--:----Cu--` |
| 57 | swap | 47, 56 | 0 | `CucrCu--:Cucrcr--:CuCuCu--:Cucr----:Cu------` |
| 58 | rotate | 57 | 3 | `crCu--Cu:crcr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 59 | cut | 58 | 0 | `crCu----:crcr----:CuCu----:cr------` |
| 60 | base | — | — | `CuP-CuCu` |
| 61 | crystal | 60 | r | `CucrCuCu` |
| 62 | base | — | — | `CuP-CuCu` |
| 63 | stack | 61, 62 | — | `CucrCuCu:CuP-CuCu` |
| 64 | crystal | 63 | r | `CucrCuCu:CucrCuCu` |
| 65 | base | — | — | `CuP-CuCu` |
| 66 | stack | 64, 65 | — | `CucrCuCu:CucrCuCu:CuP-CuCu` |
| 67 | crystal | 66 | r | `CucrCuCu:CucrCuCu:CucrCuCu` |
| 68 | base | — | — | `CuP-CuCu` |
| 69 | stack | 67, 68 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 70 | crystal | 69 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 71 | base | — | — | `CuP-CuCu` |
| 72 | stack | 70, 71 | — | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CuP-CuCu` |
| 73 | crystal | 72 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 74 | cut | 73 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 75 | rotate | 74 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 76 | cut | 75 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 77 | rotate | 76 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 78 | base | — | — | `----Cu--` |
| 79 | pin | 78 | — | `----P---:----Cu--` |
| 80 | pin | 79 | — | `----P---:----P---:----Cu--` |
| 81 | pin | 80 | — | `----P---:----P---:----P---:----Cu--` |
| 82 | swap | 77, 81 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 83 | rotate | 82 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 84 | swap | 59, 83 | 0 | `crCucrP-:crcrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 85 | pin | 84 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 86 | base | — | — | `--P-----` |
| 87 | stack | 85, 86 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 88 | base | — | — | `--Cu----` |
| 89 | stack | 87, 88 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 90 | cut | 89 | 0 | `P-P-----:--Cu----:CuCu----:--P-----:crCu----` |
