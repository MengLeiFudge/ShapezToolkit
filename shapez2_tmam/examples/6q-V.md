# 交换后不稳定的成品

独立制造两份H，选择输入方向再交换。交换后不追加重力；新连接会在下一次加工时改变分组。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu`

共91步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 每份H单独制造 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 交换的第二份输入 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 最终交换输出V | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |

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
| 22 | base | — | — | `----------P-` |
| 23 | stack | 21, 22 | — | `----------Cu:----------P-` |
| 24 | base | — | — | `----------Cu` |
| 25 | stack | 23, 24 | — | `----------Cu:----------P-:----------Cu` |
| 26 | base | — | — | `----------Cu` |
| 27 | stack | 25, 26 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 28 | base | — | — | `----------Cu` |
| 29 | stack | 27, 28 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 30 | swap | 20, 29 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 31 | rotate | 30 | 5 | `cr------Cucr:--------P-Cu:--------Cucr:--------Cucr:--------Cucr` |
| 32 | cut | 31 | 1 | `--------CuCu:--------P---:--------Cucr:--------Cucr:--------Cucr` |
| 33 | base | — | — | `----Cu------` |
| 34 | base | — | — | `----Cu------` |
| 35 | stack | 33, 34 | — | `----Cu------:----Cu------` |
| 36 | base | — | — | `CuCuCu------` |
| 37 | stack | 35, 36 | — | `----Cu------:----Cu------:CuCuCu------` |
| 38 | base | — | — | `--Cu--------` |
| 39 | stack | 37, 38 | — | `----Cu------:----Cu------:CuCuCu------:--Cu--------` |
| 40 | base | — | — | `CuCu--------` |
| 41 | stack | 39, 40 | — | `----Cu------:----Cu------:CuCuCu------:--Cu--------:CuCu--------` |
| 42 | swap | 32, 41 | 1 | `----Cu--CuCu:----Cu--P---:CuCuCu--Cucr:--Cu----Cucr:CuCu----Cucr` |
| 43 | rotate | 42 | 1 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 44 | cut | 43 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 45 | base | — | — | `CuCuP-CuCuCu` |
| 46 | base | — | — | `CuCuCuCuCuCu` |
| 47 | stack | 45, 46 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu` |
| 48 | base | — | — | `CuCuP-CuCuCu` |
| 49 | stack | 47, 48 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 50 | base | — | — | `CuCuP-CuCuCu` |
| 51 | stack | 49, 50 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 52 | base | — | — | `CuCuP-CuCuCu` |
| 53 | stack | 51, 52 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 54 | crystal | 53 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 55 | cut | 54 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 56 | rotate | 55 | 1 | `--CuCucr----:--CuCuCu----:--CuCucr----:--CuCucr----:--CuCucr----` |
| 57 | cut | 56 | 1 | `------cr----:------Cu----:------cr----:------cr----:------cr----` |
| 58 | rotate | 57 | 5 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 59 | base | — | — | `CuCuP-CuCuCu` |
| 60 | crystal | 59 | r | `CuCucrCuCuCu` |
| 61 | cut | 60 | 0 | `CuCucr------` |
| 62 | rotate | 61 | 1 | `--CuCucr----` |
| 63 | cut | 62 | 1 | `------cr----` |
| 64 | swap | 58, 63 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 65 | rotate | 64 | 1 | `------crcr--:------Cu----:------cr----:------cr----:------cr----` |
| 66 | base | — | — | `----Cu------` |
| 67 | base | — | — | `----P-------` |
| 68 | stack | 66, 67 | — | `----Cu------:----P-------` |
| 69 | base | — | — | `----Cu------` |
| 70 | stack | 68, 69 | — | `----Cu------:----P-------:----Cu------` |
| 71 | base | — | — | `----Cu------` |
| 72 | stack | 70, 71 | — | `----Cu------:----P-------:----Cu------:----Cu------` |
| 73 | base | — | — | `----Cu------` |
| 74 | stack | 72, 73 | — | `----Cu------:----P-------:----Cu------:----Cu------:----Cu------` |
| 75 | swap | 65, 74 | 1 | `----Cucrcr--:----P-Cu----:----Cucr----:----Cucr----:----Cucr----` |
| 76 | rotate | 75 | 5 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 77 | cut | 76 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 78 | base | — | — | `----------Cu` |
| 79 | base | — | — | `----------Cu` |
| 80 | stack | 78, 79 | — | `----------Cu:----------Cu` |
| 81 | base | — | — | `------CuCuCu` |
| 82 | stack | 80, 81 | — | `----------Cu:----------Cu:------CuCuCu` |
| 83 | base | — | — | `--------Cu--` |
| 84 | stack | 82, 83 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--` |
| 85 | base | — | — | `------CuCu--` |
| 86 | stack | 84, 85 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 87 | swap | 77, 86 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 88 | rotate | 87 | 1 | `Cu--CuCu----:Cu--P-------:Cu--CucrCuCu:----Cucr--Cu:----CucrCuCu` |
| 89 | cut | 88 | 1 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 90 | swap | 44, 89 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |
