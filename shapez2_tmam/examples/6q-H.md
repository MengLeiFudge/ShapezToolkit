# 可制造的非K稳定半形

晶体框架与内部普通格互相阻挡；支撑环不通地面，也不含针。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------`

共44步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 独立柱拼成准备形S | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 切掉q1辅助晶体得到A | `Cu--------Cu:----------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 无晶体阶梯B | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| A与B拼接 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 切出非K半形H | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuCuCuCuP-` |
| 1 | base | — | — | `CuCuCuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu` |
| 3 | base | — | — | `CuCuCuCuCuP-` |
| 4 | stack | 2, 3 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-` |
| 5 | base | — | — | `CuCuCuCuCuP-` |
| 6 | stack | 4, 5 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 7 | base | — | — | `CuCuCuCuCuP-` |
| 8 | stack | 6, 7 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-:CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 9 | crystal | 8 | r | `CuCuCuCuCucr:CuCuCuCuCuCu:CuCuCuCuCucr:CuCuCuCuCucr:CuCuCuCuCucr` |
| 10 | cut | 9 | 1 | `------CuCucr:------CuCuCu:------CuCucr:------CuCucr:------CuCucr` |
| 11 | rotate | 10 | 1 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 12 | cut | 11 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 13 | rotate | 12 | 5 | `----------cr:----------Cu:----------cr:----------cr:----------cr` |
| 14 | base | — | — | `CuCuCuCuCuP-` |
| 15 | crystal | 14 | r | `CuCuCuCuCucr` |
| 16 | cut | 15 | 1 | `------CuCucr` |
| 17 | rotate | 16 | 1 | `cr------CuCu` |
| 18 | cut | 17 | 0 | `cr----------` |
| 19 | swap | 13, 18 | 1 | `cr--------cr:----------Cu:----------cr:----------cr:----------cr` |
| 20 | rotate | 19 | 1 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 21 | base | — | — | `----------Cu` |
| 22 | base | — | — | `----------Cu` |
| 23 | pin | 22 | — | `----------P-:----------Cu` |
| 24 | stack | 21, 23 | — | `----------Cu:----------P-:----------Cu` |
| 25 | base | — | — | `----------Cu` |
| 26 | stack | 24, 25 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 27 | base | — | — | `----------Cu` |
| 28 | stack | 26, 27 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 29 | swap | 20, 28 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 30 | rotate | 29 | 5 | `cr------Cucr:--------P-Cu:--------Cucr:--------Cucr:--------Cucr` |
| 31 | cut | 30 | 1 | `--------CuCu:--------P---:--------Cucr:--------Cucr:--------Cucr` |
| 32 | base | — | — | `----Cu------` |
| 33 | base | — | — | `----Cu------` |
| 34 | stack | 32, 33 | — | `----Cu------:----Cu------` |
| 35 | base | — | — | `CuCuCu------` |
| 36 | stack | 34, 35 | — | `----Cu------:----Cu------:CuCuCu------` |
| 37 | base | — | — | `--Cu--------` |
| 38 | stack | 36, 37 | — | `----Cu------:----Cu------:CuCuCu------:--Cu--------` |
| 39 | base | — | — | `CuCu--------` |
| 40 | stack | 38, 39 | — | `----Cu------:----Cu------:CuCuCu------:--Cu--------:CuCu--------` |
| 41 | swap | 31, 40 | 1 | `----Cu--CuCu:----Cu--P---:CuCuCu--Cucr:--Cu----Cucr:CuCu----Cucr` |
| 42 | rotate | 41 | 1 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 43 | cut | 42 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
