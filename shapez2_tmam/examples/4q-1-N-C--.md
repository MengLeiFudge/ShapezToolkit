# 单次融合删除

先把普通格提高到间隙顶部，以针隔开辅助支撑，切掉辅助晶体后普通格回落。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuCu----:--P-----:crCu----:--Cu----:--Cu----`

共42步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 13 | base | — | — | `--P-----` |
| 14 | stack | 12, 13 | — | `--Cu----:--P-----` |
| 15 | base | — | — | `--Cu----` |
| 16 | stack | 14, 15 | — | `--Cu----:--P-----:--Cu----` |
| 17 | base | — | — | `--Cu----` |
| 18 | stack | 16, 17 | — | `--Cu----:--P-----:--Cu----:--Cu----` |
| 19 | base | — | — | `--Cu----` |
| 20 | stack | 18, 19 | — | `--Cu----:--P-----:--Cu----:--Cu----:--Cu----` |
| 21 | rotate | 20 | 1 | `----Cu--:----P---:----Cu--:----Cu--:----Cu--` |
| 22 | swap | 11, 21 | 0 | `--crCu--:--CuP---:--crCu--:----Cu--:----Cu--` |
| 23 | rotate | 22 | -1 | `crCu----:CuP-----:crCu----:--Cu----:--Cu----` |
| 24 | base | — | — | `CuCuCuP-` |
| 25 | crystal | 24 | r | `CuCuCucr` |
| 26 | rotate | 25 | -2 | `CucrCuCu` |
| 27 | cut | 26 | 0 | `Cucr----` |
| 28 | rotate | 27 | 2 | `----Cucr` |
| 29 | rotate | 28 | -3 | `cr----Cu` |
| 30 | cut | 29 | 0 | `cr------` |
| 31 | rotate | 30 | 3 | `------cr` |
| 32 | base | — | — | `------Cu` |
| 33 | stack | 31, 32 | — | `------cr:------Cu` |
| 34 | base | — | — | `------Cu` |
| 35 | stack | 33, 34 | — | `------cr:------Cu:------Cu` |
| 36 | base | — | — | `------Cu` |
| 37 | stack | 35, 36 | — | `------cr:------Cu:------Cu:------Cu` |
| 38 | base | — | — | `------Cu` |
| 39 | stack | 37, 38 | — | `------cr:------Cu:------Cu:------Cu:------Cu` |
| 40 | swap | 23, 39 | 0 | `crCu--cr:CuP---Cu:crCu--Cu:--Cu--Cu:--Cu--Cu` |
| 41 | cut | 40 | 0 | `CuCu----:--P-----:crCu----:--Cu----:--Cu----` |
