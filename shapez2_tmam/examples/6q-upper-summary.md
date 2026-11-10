# 复杂上料等价替换为单格基础料

H作上料时，悬空框架永远留在高度上限外；对任意下料仅留下q0普通格。用一份单格基础料替代整个H的上料准备，再堆到原下料。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:------crCuCu:------cr--Cu:------crCuCu`

共47步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 原本考虑的复杂上料H | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 已有旋转半形下料 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 等价基础上料 | `Cu----------` |
| 堆叠成品 | `Cu----Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuCuP-CuCuCu` |
| 1 | base | — | — | `CuCuCuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu` |
| 3 | base | — | — | `CuCuP-CuCuCu` |
| 4 | stack | 2, 3 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 5 | base | — | — | `CuCuP-CuCuCu` |
| 6 | stack | 4, 5 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 7 | base | — | — | `CuCuP-CuCuCu` |
| 8 | stack | 6, 7 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 9 | crystal | 8 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 10 | cut | 9 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 11 | rotate | 10 | 1 | `--CuCucr----:--CuCuCu----:--CuCucr----:--CuCucr----:--CuCucr----` |
| 12 | cut | 11 | 1 | `------cr----:------Cu----:------cr----:------cr----:------cr----` |
| 13 | rotate | 12 | 5 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 14 | base | — | — | `CuCuP-CuCuCu` |
| 15 | crystal | 14 | r | `CuCucrCuCuCu` |
| 16 | cut | 15 | 0 | `CuCucr------` |
| 17 | rotate | 16 | 1 | `--CuCucr----` |
| 18 | cut | 17 | 1 | `------cr----` |
| 19 | swap | 13, 18 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 20 | rotate | 19 | 1 | `------crcr--:------Cu----:------cr----:------cr----:------cr----` |
| 21 | base | — | — | `----Cu------` |
| 22 | base | — | — | `----P-------` |
| 23 | stack | 21, 22 | — | `----Cu------:----P-------` |
| 24 | base | — | — | `----Cu------` |
| 25 | stack | 23, 24 | — | `----Cu------:----P-------:----Cu------` |
| 26 | base | — | — | `----Cu------` |
| 27 | stack | 25, 26 | — | `----Cu------:----P-------:----Cu------:----Cu------` |
| 28 | base | — | — | `----Cu------` |
| 29 | stack | 27, 28 | — | `----Cu------:----P-------:----Cu------:----Cu------:----Cu------` |
| 30 | swap | 20, 29 | 1 | `----Cucrcr--:----P-Cu----:----Cucr----:----Cucr----:----Cucr----` |
| 31 | rotate | 30 | 5 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 32 | cut | 31 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 33 | base | — | — | `----------Cu` |
| 34 | base | — | — | `----------Cu` |
| 35 | stack | 33, 34 | — | `----------Cu:----------Cu` |
| 36 | base | — | — | `------CuCuCu` |
| 37 | stack | 35, 36 | — | `----------Cu:----------Cu:------CuCuCu` |
| 38 | base | — | — | `--------Cu--` |
| 39 | stack | 37, 38 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--` |
| 40 | base | — | — | `------CuCu--` |
| 41 | stack | 39, 40 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 42 | swap | 32, 41 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 43 | rotate | 42 | 1 | `Cu--CuCu----:Cu--P-------:Cu--CucrCuCu:----Cucr--Cu:----CucrCuCu` |
| 44 | cut | 43 | 1 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 45 | base | — | — | `Cu----------` |
| 46 | stack | 44, 45 | — | `Cu----Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
