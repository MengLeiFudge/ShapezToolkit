# 地面针与晶体间隙

来源底部辅助晶体被顶破删除，地面补针，保留高处普通格与晶体。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-----:--Cu----:CuCu----:--P-----:crCu----`

共85步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 23 | base | — | — | `------Cu` |
| 24 | base | — | — | `------Cu` |
| 25 | stack | 23, 24 | — | `------Cu:------Cu` |
| 26 | base | — | — | `------Cu` |
| 27 | stack | 25, 26 | — | `------Cu:------Cu:------Cu` |
| 28 | base | — | — | `------Cu` |
| 29 | stack | 27, 28 | — | `------Cu:------Cu:------Cu:------Cu` |
| 30 | base | — | — | `------Cu` |
| 31 | stack | 29, 30 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 32 | swap | 22, 31 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 33 | cut | 32 | 0 | `crCu----:crCu----:CuCu----:crCu----:--Cu----` |
| 34 | base | — | — | `------Cu` |
| 35 | base | — | — | `------Cu` |
| 36 | stack | 34, 35 | — | `------Cu:------Cu` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------Cu:------Cu:------Cu` |
| 39 | base | — | — | `------Cu` |
| 40 | stack | 38, 39 | — | `------Cu:------Cu:------Cu:------Cu` |
| 41 | base | — | — | `------Cu` |
| 42 | stack | 40, 41 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 43 | swap | 33, 42 | 0 | `crCu--Cu:crCu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 44 | rotate | 43 | 1 | `CucrCu--:CucrCu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 45 | cut | 44 | 0 | `Cucr----:Cucr----:CuCu----:Cucr----:Cu------` |
| 46 | base | — | — | `CuCuCuCu` |
| 47 | base | — | — | `CuP-CuCu` |
| 48 | stack | 46, 47 | — | `CuCuCuCu:CuP-CuCu` |
| 49 | crystal | 48 | r | `CuCuCuCu:CucrCuCu` |
| 50 | cut | 49 | 0 | `CuCu----:Cucr----` |
| 51 | rotate | 50 | 1 | `--CuCu--:--Cucr--` |
| 52 | cut | 51 | 1 | `----Cu--:----cr--` |
| 53 | base | — | — | `----Cu--` |
| 54 | stack | 52, 53 | — | `----Cu--:----cr--:----Cu--` |
| 55 | swap | 45, 54 | 0 | `CucrCu--:Cucrcr--:CuCuCu--:Cucr----:Cu------` |
| 56 | rotate | 55 | 3 | `crCu--Cu:crcr--Cu:CuCu--Cu:cr----Cu:------Cu` |
| 57 | cut | 56 | 0 | `crCu----:crcr----:CuCu----:cr------` |
| 58 | base | — | — | `CuP-CuCu` |
| 59 | base | — | — | `CuP-CuCu` |
| 60 | stack | 58, 59 | — | `CuP-CuCu:CuP-CuCu` |
| 61 | base | — | — | `CuP-CuCu` |
| 62 | stack | 60, 61 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 63 | base | — | — | `CuP-CuCu` |
| 64 | stack | 62, 63 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 65 | base | — | — | `CuP-CuCu` |
| 66 | stack | 64, 65 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 67 | crystal | 66 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 68 | cut | 67 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 69 | rotate | 68 | 3 | `cr----Cu:cr----Cu:cr----Cu:cr----Cu:cr----Cu` |
| 70 | cut | 69 | 0 | `cr------:cr------:cr------:cr------:cr------` |
| 71 | rotate | 70 | 1 | `--cr----:--cr----:--cr----:--cr----:--cr----` |
| 72 | base | — | — | `----Cu--` |
| 73 | pin | 72 | — | `----P---:----Cu--` |
| 74 | pin | 73 | — | `----P---:----P---:----Cu--` |
| 75 | pin | 74 | — | `----P---:----P---:----P---:----Cu--` |
| 76 | swap | 71, 75 | 0 | `--crP---:--crP---:--crP---:--crCu--:--cr----` |
| 77 | rotate | 76 | 1 | `----crP-:----crP-:----crP-:----crCu:----cr--` |
| 78 | swap | 57, 77 | 0 | `crCucrP-:crcrcrP-:CuCucrP-:cr--crCu:----cr--` |
| 79 | pin | 78 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:------P-:cr----Cu` |
| 80 | base | — | — | `--P-----` |
| 81 | stack | 79, 80 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:cr----Cu` |
| 82 | base | — | — | `--Cu----` |
| 83 | stack | 81, 82 | — | `P-P-P-P-:--Cu--P-:CuCu--P-:--P---P-:crCu--Cu` |
| 84 | cut | 83 | 0 | `P-P-----:--Cu----:CuCu----:--P-----:crCu----` |
