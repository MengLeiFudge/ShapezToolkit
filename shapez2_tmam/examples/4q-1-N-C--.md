# 单次融合删除

先把普通格提高到间隙顶部，以针隔开辅助支撑，切掉辅助晶体后普通格回落。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuCu----:--P-----:crCu----:--Cu----:--Cu----`

共41步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCu` |
| 2 | base | — | — | `CuCuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCu:CuCuCuCu` |
| 4 | base | — | — | `P-CuCuCu` |
| 5 | stack | 3, 4 | — | `crCuCuCu:CuCuCuCu:P-CuCuCu` |
| 6 | crystal | 5 | r | `crCuCuCu:CuCuCuCu:crCuCuCu` |
| 7 | rotate | 6 | 1 | `CucrCuCu:CuCuCuCu:CucrCuCu` |
| 8 | cut | 7 | 0 | `Cucr----:CuCu----:Cucr----` |
| 9 | rotate | 8 | -1 | `cr----Cu:Cu----Cu:cr----Cu` |
| 10 | cut | 9 | 0 | `cr------:Cu------:cr------` |
| 11 | rotate | 10 | 1 | `--cr----:--Cu----:--cr----` |
| 12 | base | — | — | `--Cu----` |
| 13 | base | — | — | `--Cu----` |
| 14 | pin | 13 | — | `--P-----:--Cu----` |
| 15 | stack | 12, 14 | — | `--Cu----:--P-----:--Cu----` |
| 16 | base | — | — | `--Cu----` |
| 17 | stack | 15, 16 | — | `--Cu----:--P-----:--Cu----:--Cu----` |
| 18 | base | — | — | `--Cu----` |
| 19 | stack | 17, 18 | — | `--Cu----:--P-----:--Cu----:--Cu----:--Cu----` |
| 20 | rotate | 19 | 1 | `----Cu--:----P---:----Cu--:----Cu--:----Cu--` |
| 21 | swap | 11, 20 | 0 | `--crCu--:--CuP---:--crCu--:----Cu--:----Cu--` |
| 22 | rotate | 21 | -1 | `crCu----:CuP-----:crCu----:--Cu----:--Cu----` |
| 23 | base | — | — | `CuCuCuP-` |
| 24 | crystal | 23 | r | `CuCuCucr` |
| 25 | rotate | 24 | -2 | `CucrCuCu` |
| 26 | cut | 25 | 0 | `Cucr----` |
| 27 | rotate | 26 | 2 | `----Cucr` |
| 28 | rotate | 27 | -3 | `cr----Cu` |
| 29 | cut | 28 | 0 | `cr------` |
| 30 | rotate | 29 | 3 | `------cr` |
| 31 | base | — | — | `------Cu` |
| 32 | stack | 30, 31 | — | `------cr:------Cu` |
| 33 | base | — | — | `------Cu` |
| 34 | stack | 32, 33 | — | `------cr:------Cu:------Cu` |
| 35 | base | — | — | `------Cu` |
| 36 | stack | 34, 35 | — | `------cr:------Cu:------Cu:------Cu` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 39 | swap | 22, 38 | 0 | `crCu--cr:CuP---Cu:crCu--Cu:--Cu--Cu:--Cu--Cu` |
| 40 | cut | 39 | 0 | `CuCu----:--P-----:crCu----:--Cu----:--Cu----` |
