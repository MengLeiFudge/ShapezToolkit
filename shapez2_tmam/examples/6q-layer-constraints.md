# 用针下晶体间隙解除上料对齐冲突

q1四层柱与q5三层柱作下料。q3的NPN与q4的NN共享底顶普通块，不能同时全列压紧；改造NPN、NCN、CCN三列并对齐顶端，辅助C在一次堆叠中碎裂。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------`

共57步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

| 阶段 | 结果 |
|---|---|
| 原下料 | `--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------` |
| 保留针下晶体间隙的三层上料 | `Cucr--CuCucr:--Cu--P-crcr:------CuCuCu` |
| 一次堆叠成品 | `CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `------Cu----` |
| 1 | base | — | — | `------Cu----` |
| 2 | pin | 1 | — | `------P-----:------Cu----` |
| 3 | stack | 0, 2 | — | `------Cu----:------P-----:------Cu----` |
| 4 | rotate | 3 | 5 | `----Cu------:----P-------:----Cu------` |
| 5 | base | — | — | `CuCuCuCuCuCu` |
| 6 | base | — | — | `CuCuCuCuP-Cu` |
| 7 | stack | 5, 6 | — | `CuCuCuCuCuCu:CuCuCuCuP-Cu` |
| 8 | crystal | 7 | r | `CuCuCuCuCuCu:CuCuCuCucrCu` |
| 9 | rotate | 8 | 4 | `CuCuCuCuCuCu:CuCucrCuCuCu` |
| 10 | cut | 9 | 0 | `CuCuCu------:CuCucr------` |
| 11 | rotate | 10 | 4 | `Cu------CuCu:cr------CuCu` |
| 12 | cut | 11 | 0 | `Cu----------:cr----------` |
| 13 | rotate | 12 | 4 | `--------Cu--:--------cr--` |
| 14 | base | — | — | `--------Cu--` |
| 15 | stack | 13, 14 | — | `--------Cu--:--------cr--:--------Cu--` |
| 16 | rotate | 15 | 5 | `------Cu----:------cr----:------Cu----` |
| 17 | swap | 4, 16 | 0 | `----CuCu----:----P-cr----:----CuCu----` |
| 18 | rotate | 17 | 5 | `--CuCu------:--P-cr------:--CuCu------` |
| 19 | base | — | — | `CuCuCuCuCuP-` |
| 20 | crystal | 19 | r | `CuCuCuCuCucr` |
| 21 | base | — | — | `CuCuCuCuCuP-` |
| 22 | stack | 20, 21 | — | `CuCuCuCuCucr:CuCuCuCuCuP-` |
| 23 | crystal | 22 | r | `CuCuCuCuCucr:CuCuCuCuCucr` |
| 24 | rotate | 23 | 3 | `CuCucrCuCuCu:CuCucrCuCuCu` |
| 25 | cut | 24 | 0 | `CuCucr------:CuCucr------` |
| 26 | rotate | 25 | 4 | `cr------CuCu:cr------CuCu` |
| 27 | cut | 26 | 0 | `cr----------:cr----------` |
| 28 | rotate | 27 | 5 | `----------cr:----------cr` |
| 29 | base | — | — | `----------Cu` |
| 30 | stack | 28, 29 | — | `----------cr:----------cr:----------Cu` |
| 31 | rotate | 30 | 4 | `------cr----:------cr----:------Cu----` |
| 32 | swap | 18, 31 | 0 | `--CuCucr----:--P-crcr----:--CuCuCu----` |
| 33 | rotate | 32 | 2 | `------CuCucr:------P-crcr:------CuCuCu` |
| 34 | base | — | — | `CuP-CuCuCuCu` |
| 35 | crystal | 34 | r | `CucrCuCuCuCu` |
| 36 | rotate | 35 | 1 | `CuCucrCuCuCu` |
| 37 | cut | 36 | 0 | `CuCucr------` |
| 38 | rotate | 37 | 4 | `cr------CuCu` |
| 39 | cut | 38 | 0 | `cr----------` |
| 40 | rotate | 39 | 1 | `--cr--------` |
| 41 | base | — | — | `--Cu--------` |
| 42 | stack | 40, 41 | — | `--cr--------:--Cu--------` |
| 43 | rotate | 42 | 2 | `------cr----:------Cu----` |
| 44 | base | — | — | `Cu----------` |
| 45 | rotate | 44 | 2 | `----Cu------` |
| 46 | swap | 45, 43 | 0 | `----Cucr----:------Cu----` |
| 47 | rotate | 46 | 4 | `Cucr--------:--Cu--------` |
| 48 | swap | 47, 33 | 0 | `Cucr--CuCucr:--Cu--P-crcr:------CuCuCu` |
| 49 | base | — | — | `--Cu------Cu` |
| 50 | base | — | — | `--Cu------Cu` |
| 51 | stack | 49, 50 | — | `--Cu------Cu:--Cu------Cu` |
| 52 | base | — | — | `--Cu------Cu` |
| 53 | stack | 51, 52 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu` |
| 54 | base | — | — | `--Cu--------` |
| 55 | stack | 53, 54 | — | `--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------` |
| 56 | stack | 55, 48 | — | `CuCu--CuCuCu:--Cu--P---Cu:--Cu------Cu:--Cu--CuCuCu:--Cu--------` |
