# 交换后不稳定的成品

独立制造两份H，选择输入方向再交换。交换后不追加重力；新连接会在下一次加工时改变分组。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu`

共89步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 11 | rotate | 10 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 12 | cut | 11 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 13 | rotate | 12 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 14 | base | — | — | `CuCuP-CuCuCu` |
| 15 | crystal | 14 | r | `CuCucrCuCuCu` |
| 16 | cut | 15 | 0 | `CuCucr------` |
| 17 | rotate | 16 | 1 | `--CuCucr----` |
| 18 | cut | 17 | 1 | `------cr----` |
| 19 | swap | 13, 18 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 20 | rotate | 19 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 21 | base | — | — | `----------Cu` |
| 22 | base | — | — | `----------Cu` |
| 23 | pin | 22 | — | `----------P-:----------Cu` |
| 24 | stack | 21, 23 | — | `----------Cu:----------P-:----------Cu` |
| 25 | base | — | — | `----------Cu` |
| 26 | stack | 24, 25 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 27 | base | — | — | `----------Cu` |
| 28 | stack | 26, 27 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 29 | swap | 20, 28 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 30 | rotate | 29 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 31 | cut | 30 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 32 | base | — | — | `----------Cu` |
| 33 | base | — | — | `----------Cu` |
| 34 | stack | 32, 33 | — | `----------Cu:----------Cu` |
| 35 | base | — | — | `------CuCuCu` |
| 36 | stack | 34, 35 | — | `----------Cu:----------Cu:------CuCuCu` |
| 37 | base | — | — | `--------Cu--` |
| 38 | stack | 36, 37 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--` |
| 39 | base | — | — | `------CuCu--` |
| 40 | stack | 38, 39 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 41 | swap | 31, 40 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 42 | rotate | 41 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 43 | cut | 42 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 44 | base | — | — | `CuCuP-CuCuCu` |
| 45 | base | — | — | `CuCuCuCuCuCu` |
| 46 | stack | 44, 45 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu` |
| 47 | base | — | — | `CuCuP-CuCuCu` |
| 48 | stack | 46, 47 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 49 | base | — | — | `CuCuP-CuCuCu` |
| 50 | stack | 48, 49 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 51 | base | — | — | `CuCuP-CuCuCu` |
| 52 | stack | 50, 51 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 53 | crystal | 52 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 54 | cut | 53 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 55 | rotate | 54 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 56 | cut | 55 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 57 | rotate | 56 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 58 | base | — | — | `CuCuP-CuCuCu` |
| 59 | crystal | 58 | r | `CuCucrCuCuCu` |
| 60 | cut | 59 | 0 | `CuCucr------` |
| 61 | rotate | 60 | 1 | `--CuCucr----` |
| 62 | cut | 61 | 1 | `------cr----` |
| 63 | swap | 57, 62 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 64 | rotate | 63 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 65 | base | — | — | `----------Cu` |
| 66 | base | — | — | `----------Cu` |
| 67 | pin | 66 | — | `----------P-:----------Cu` |
| 68 | stack | 65, 67 | — | `----------Cu:----------P-:----------Cu` |
| 69 | base | — | — | `----------Cu` |
| 70 | stack | 68, 69 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 71 | base | — | — | `----------Cu` |
| 72 | stack | 70, 71 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 73 | swap | 64, 72 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 74 | rotate | 73 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 75 | cut | 74 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 76 | base | — | — | `----------Cu` |
| 77 | base | — | — | `----------Cu` |
| 78 | stack | 76, 77 | — | `----------Cu:----------Cu` |
| 79 | base | — | — | `------CuCuCu` |
| 80 | stack | 78, 79 | — | `----------Cu:----------Cu:------CuCuCu` |
| 81 | base | — | — | `--------Cu--` |
| 82 | stack | 80, 81 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--` |
| 83 | base | — | — | `------CuCu--` |
| 84 | stack | 82, 83 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 85 | swap | 75, 84 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 86 | rotate | 85 | 1 | `Cu--CuCu----:Cu--P-------:Cu--CucrCuCu:----Cucr--Cu:----CucrCuCu` |
| 87 | cut | 86 | 1 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 88 | swap | 43, 87 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |
