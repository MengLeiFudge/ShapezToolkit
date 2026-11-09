# 地面针与晶体间隙

来源底部辅助晶体被顶破删除，地面补针，保留高处普通格与晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-----:--Cu----:CuCu----:--P-----:crCu----`

共76步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../research/proofs/04-stacking.md#s04-19)。
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
| 11 | base | — | — | `------Cu` |
| 12 | base | — | — | `------Cu` |
| 13 | stack | 11, 12 | — | `------Cu:------Cu` |
| 14 | base | — | — | `------Cu` |
| 15 | stack | 13, 14 | — | `------Cu:------Cu:------Cu` |
| 16 | base | — | — | `------Cu` |
| 17 | stack | 15, 16 | — | `------Cu:------Cu:------Cu:------Cu` |
| 18 | base | — | — | `------Cu` |
| 19 | stack | 17, 18 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 20 | swap | 10, 19 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 21 | cut | 20 | 0 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 22 | base | — | — | `------Cu` |
| 23 | base | — | — | `------Cu` |
| 24 | stack | 22, 23 | — | `------Cu:------Cu` |
| 25 | base | — | — | `------Cu` |
| 26 | stack | 24, 25 | — | `------Cu:------Cu:------Cu` |
| 27 | base | — | — | `------Cu` |
| 28 | stack | 26, 27 | — | `------Cu:------Cu:------Cu:------Cu` |
| 29 | base | — | — | `------Cu` |
| 30 | stack | 28, 29 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 31 | swap | 21, 30 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 32 | rotate | 31 | 1 | `CucrCu--:CucrCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 33 | cut | 32 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----:Cu------` |
| 34 | base | — | — | `CuCuCuCu` |
| 35 | base | — | — | `CuP-CuCu` |
| 36 | stack | 34, 35 | — | `CuCuCuCu:CuP-CuCu` |
| 37 | crystal | 36 | r | `CuCuCuCu:CucrCuCu` |
| 38 | cut | 37 | 0 | `CuCu----:Cucr----` |
| 39 | rotate | 38 | 1 | `--CuCu--:--Cucr--` |
| 40 | cut | 39 | 1 | `----Cu--:----cr--` |
| 41 | base | — | — | `----Cu--` |
| 42 | stack | 40, 41 | — | `----Cu--:----cr--:----Cu--` |
| 43 | swap | 33, 42 | 0 | `CucrCu--:Cucrcr--:CuCuCu--:Cucr----:Cu------` |
| 44 | rotate | 43 | 3 | `crCu--Cu:crcr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 45 | cut | 44 | 0 | `crCu----:crcr----:CuCu----:cr------` |
| 46 | base | — | — | `CuP-CuCu` |
| 47 | base | — | — | `CuP-CuCu` |
| 48 | stack | 46, 47 | — | `CuP-CuCu:CuP-CuCu` |
| 49 | base | — | — | `CuP-CuCu` |
| 50 | stack | 48, 49 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 51 | base | — | — | `CuP-CuCu` |
| 52 | stack | 50, 51 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 53 | base | — | — | `CuP-CuCu` |
| 54 | stack | 52, 53 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 55 | crystal | 54 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 56 | cut | 55 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 57 | rotate | 56 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 58 | cut | 57 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 59 | rotate | 58 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 60 | base | — | — | `----P---` |
| 61 | base | — | — | `----P---` |
| 62 | stack | 60, 61 | — | `----P---:----P---` |
| 63 | base | — | — | `----P---` |
| 64 | stack | 62, 63 | — | `----P---:----P---:----P---` |
| 65 | base | — | — | `----Cu--` |
| 66 | stack | 64, 65 | — | `----P---:----P---:----P---:----Cu--` |
| 67 | swap | 59, 66 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 68 | rotate | 67 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 69 | swap | 45, 68 | 0 | `crCucrP-:crcrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 70 | pin | 69 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 71 | base | — | — | `--P-----` |
| 72 | stack | 70, 71 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 73 | base | — | — | `--Cu----` |
| 74 | stack | 72, 73 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 75 | cut | 74 | 0 | `P-P-----:--Cu----:CuCu----:--P-----:crCu----` |
