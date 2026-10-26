# 用针下晶体间隙解除上料对齐冲突

q1四层柱与q5三层柱作下料。q3的NPN与q4的NN共享底顶普通块，不能同时全列压紧；改造NPN、NCN、CCN三列并对齐顶端，辅助C在一次堆叠中碎裂。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------`

共46步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 原下料 | `--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------` |
| 保留针下晶体间隙的三层上料 | `Cucr--CuCucr:--Cu--P-crcr:------CuCuCu` |
| 一次堆叠成品 | `CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `----Cu------` |
| 1 | base | — | — | `----Cu------` |
| 2 | pin | 1 | — | `----P-------:----Cu------` |
| 3 | stack | 0, 2 | — | `----Cu------:----P-------:----Cu------` |
| 4 | base | — | — | `CuCuCuCuCuCu` |
| 5 | base | — | — | `CuCuP-CuCuCu` |
| 6 | stack | 4, 5 | — | `CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 7 | crystal | 6 | r | `CuCuCuCuCuCu:CuCucrCuCuCu` |
| 8 | cut | 7 | 0 | `CuCuCu------:CuCucr------` |
| 9 | rotate | 8 | 1 | `--CuCuCu----:--CuCucr----` |
| 10 | cut | 9 | 1 | `------Cu----:------cr----` |
| 11 | base | — | — | `------Cu----` |
| 12 | stack | 10, 11 | — | `------Cu----:------cr----:------Cu----` |
| 13 | swap | 3, 12 | 0 | `----CuCu----:----P-cr----:----CuCu----` |
| 14 | rotate | 13 | 5 | `--CuCu------:--P-cr------:--CuCu------` |
| 15 | base | — | — | `CuCuP-CuCuCu` |
| 16 | crystal | 15 | r | `CuCucrCuCuCu` |
| 17 | base | — | — | `CuCuP-CuCuCu` |
| 18 | stack | 16, 17 | — | `CuCucrCuCuCu:CuCuP-CuCuCu` |
| 19 | crystal | 18 | r | `CuCucrCuCuCu:CuCucrCuCuCu` |
| 20 | cut | 19 | 0 | `CuCucr------:CuCucr------` |
| 21 | rotate | 20 | 1 | `--CuCucr----:--CuCucr----` |
| 22 | cut | 21 | 1 | `------cr----:------cr----` |
| 23 | base | — | — | `------Cu----` |
| 24 | stack | 22, 23 | — | `------cr----:------cr----:------Cu----` |
| 25 | swap | 14, 24 | 0 | `--CuCucr----:--P-crcr----:--CuCuCu----` |
| 26 | rotate | 25 | 2 | `------CuCucr:------P-crcr:------CuCuCu` |
| 27 | base | — | — | `CuCuP-CuCuCu` |
| 28 | crystal | 27 | r | `CuCucrCuCuCu` |
| 29 | cut | 28 | 0 | `CuCucr------` |
| 30 | rotate | 29 | 1 | `--CuCucr----` |
| 31 | cut | 30 | 1 | `------cr----` |
| 32 | base | — | — | `------Cu----` |
| 33 | stack | 31, 32 | — | `------cr----:------Cu----` |
| 34 | base | — | — | `----Cu------` |
| 35 | swap | 34, 33 | 0 | `----Cucr----:------Cu----` |
| 36 | rotate | 35 | 4 | `Cucr--------:--Cu--------` |
| 37 | swap | 36, 26 | 0 | `Cucr--CuCucr:--Cu--P-crcr:------CuCuCu` |
| 38 | base | — | — | `--Cu------Cu` |
| 39 | base | — | — | `--Cu------Cu` |
| 40 | stack | 38, 39 | — | `--Cu------Cu:--Cu------Cu` |
| 41 | base | — | — | `--Cu------Cu` |
| 42 | stack | 40, 41 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu` |
| 43 | base | — | — | `--Cu--------` |
| 44 | stack | 42, 43 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------` |
| 45 | stack | 44, 37 | — | `CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------` |
