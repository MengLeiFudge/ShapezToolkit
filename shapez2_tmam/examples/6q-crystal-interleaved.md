# 补晶体载体保留交错普通格与针

q1三层普通柱作下料；追加q0地面N、q1第四层N及q3的NPN。紧凑候选会把q0/q1粘合，故用q0单N、q1的CCCN与q3的NPN组成上料，辅助C在一次堆叠中碎裂。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`CuCu--Cu----:--Cu--P-----:--Cu--Cu----:--Cu--------`

共31步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

| 阶段 | 结果 |
|---|---|
| 原下料 | `--Cu--------:--Cu--------:--Cu--------` |
| 补C交错上料 | `Cucr--Cu----:--cr--P-----:--cr--Cu----:--Cu--------` |
| 一次堆叠成品 | `CuCu--Cu----:--Cu--P-----:--Cu--Cu----:--Cu--------` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `CuP-CuCuCuCu` |
| 1 | crystal | 0 | r | `CucrCuCuCuCu` |
| 2 | base | — | — | `CuP-CuCuCuCu` |
| 3 | stack | 1, 2 | — | `CucrCuCuCuCu:CuP-CuCuCuCu` |
| 4 | crystal | 3 | r | `CucrCuCuCuCu:CucrCuCuCuCu` |
| 5 | base | — | — | `CuP-CuCuCuCu` |
| 6 | stack | 4, 5 | — | `CucrCuCuCuCu:CucrCuCuCuCu:CuP-CuCuCuCu` |
| 7 | crystal | 6 | r | `CucrCuCuCuCu:CucrCuCuCuCu:CucrCuCuCuCu` |
| 8 | rotate | 7 | 1 | `CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 9 | cut | 8 | 0 | `CuCucr------:CuCucr------:CuCucr------` |
| 10 | rotate | 9 | 4 | `cr------CuCu:cr------CuCu:cr------CuCu` |
| 11 | cut | 10 | 0 | `cr----------:cr----------:cr----------` |
| 12 | rotate | 11 | 1 | `--cr--------:--cr--------:--cr--------` |
| 13 | base | — | — | `--Cu--------` |
| 14 | stack | 12, 13 | — | `--cr--------:--cr--------:--cr--------:--Cu--------` |
| 15 | rotate | 14 | 2 | `------cr----:------cr----:------cr----:------Cu----` |
| 16 | base | — | — | `Cu----------` |
| 17 | rotate | 16 | 2 | `----Cu------` |
| 18 | swap | 17, 15 | 0 | `----Cucr----:------cr----:------cr----:------Cu----` |
| 19 | rotate | 18 | 4 | `Cucr--------:--cr--------:--cr--------:--Cu--------` |
| 20 | base | — | — | `------Cu----` |
| 21 | base | — | — | `------Cu----` |
| 22 | pin | 21 | — | `------P-----:------Cu----` |
| 23 | stack | 20, 22 | — | `------Cu----:------P-----:------Cu----` |
| 24 | swap | 19, 23 | 0 | `Cucr--Cu----:--cr--P-----:--cr--Cu----:--Cu--------` |
| 25 | base | — | — | `--Cu--------` |
| 26 | base | — | — | `--Cu--------` |
| 27 | stack | 25, 26 | — | `--Cu--------:--Cu--------` |
| 28 | base | — | — | `--Cu--------` |
| 29 | stack | 27, 28 | — | `--Cu--------:--Cu--------:--Cu--------` |
| 30 | stack | 29, 24 | — | `CuCu--Cu----:--Cu--P-----:--Cu--Cu----:--Cu--------` |
