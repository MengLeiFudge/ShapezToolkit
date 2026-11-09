# 四象限完整目标：一次尾部顶针不可省

先拼接两个稳定半形，再顶破q2辅助晶体塔。两侧悬空N都必须在零尾起点中，但任何两列分割都会使其中一侧失去晶体支撑，所以目标不能只由双半形加普通料追加得到。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`P---P---:Cu------:crCu--Cu`

共48步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../research/proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 双半形起点 | `Cu--cr--:crCucrCu:----cr--:----cr--:----cr--` |
| 一次尾部Pin成品 | `P---P---:Cu------:crCu--Cu` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuCuCu` |
| 1 | base | — | — | `CuP-CuCu` |
| 2 | stack | 0, 1 | — | `CuCuCuCu:CuP-CuCu` |
| 3 | crystal | 2 | r | `CuCuCuCu:CucrCuCu` |
| 4 | cut | 3 | 0 | `CuCu----:Cucr----` |
| 5 | base | — | — | `Cu------` |
| 6 | stack | 4, 5 | — | `CuCu----:Cucr----:Cu------` |
| 7 | base | — | — | `Cu------` |
| 8 | stack | 6, 7 | — | `CuCu----:Cucr----:Cu------:Cu------` |
| 9 | base | — | — | `Cu------` |
| 10 | stack | 8, 9 | — | `CuCu----:Cucr----:Cu------:Cu------:Cu------` |
| 11 | base | — | — | `------Cu` |
| 12 | base | — | — | `----CuCu` |
| 13 | stack | 11, 12 | — | `------Cu:----CuCu` |
| 14 | base | — | — | `------Cu` |
| 15 | stack | 13, 14 | — | `------Cu:----CuCu:------Cu` |
| 16 | base | — | — | `------Cu` |
| 17 | stack | 15, 16 | — | `------Cu:----CuCu:------Cu:------Cu` |
| 18 | base | — | — | `------Cu` |
| 19 | stack | 17, 18 | — | `------Cu:----CuCu:------Cu:------Cu:------Cu` |
| 20 | swap | 10, 19 | 0 | `CuCu--Cu:CucrCuCu:Cu----Cu:Cu----Cu:Cu----Cu` |
| 21 | rotate | 20 | 3 | `Cu--CuCu:crCuCuCu:----CuCu:----CuCu:----CuCu` |
| 22 | cut | 21 | 0 | `Cu------:crCu----` |
| 23 | base | — | — | `CuP-CuCu` |
| 24 | base | — | — | `CuP-CuCu` |
| 25 | stack | 23, 24 | — | `CuP-CuCu:CuP-CuCu` |
| 26 | base | — | — | `CuP-CuCu` |
| 27 | stack | 25, 26 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 28 | base | — | — | `CuP-CuCu` |
| 29 | stack | 27, 28 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 30 | base | — | — | `CuP-CuCu` |
| 31 | stack | 29, 30 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 32 | crystal | 31 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 33 | cut | 32 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 34 | base | — | — | `------Cu` |
| 35 | base | — | — | `----CuCu` |
| 36 | stack | 34, 35 | — | `------Cu:----CuCu` |
| 37 | base | — | — | `------Cu` |
| 38 | stack | 36, 37 | — | `------Cu:----CuCu:------Cu` |
| 39 | base | — | — | `------Cu` |
| 40 | stack | 38, 39 | — | `------Cu:----CuCu:------Cu:------Cu` |
| 41 | base | — | — | `------Cu` |
| 42 | stack | 40, 41 | — | `------Cu:----CuCu:------Cu:------Cu:------Cu` |
| 43 | swap | 33, 42 | 0 | `Cucr--Cu:CucrCuCu:Cucr--Cu:Cucr--Cu:Cucr--Cu` |
| 44 | rotate | 43 | 1 | `CuCucr--:CuCucrCu:CuCucr--:CuCucr--:CuCucr--` |
| 45 | cut | 44 | 1 | `----cr--:----crCu:----cr--:----cr--:----cr--` |
| 46 | swap | 22, 45 | 0 | `Cu--cr--:crCucrCu:----cr--:----cr--:----cr--` |
| 47 | pin | 46 | — | `P---P---:Cu------:crCu--Cu` |
