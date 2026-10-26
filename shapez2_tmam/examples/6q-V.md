# 交换后不稳定的成品

独立制造两份H，选择输入方向再交换。交换后不追加重力；新连接会在下一次加工时改变分组。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu`

共95步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 1 | crystal | 0 | r | `CuCucrCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `CuCucrCuCuCu:CuCuCuCuCuCu` |
| 4 | base | — | — | `CuCuP-CuCuCu` |
| 5 | stack | 3, 4 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 6 | crystal | 5 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu` |
| 7 | base | — | — | `CuCuP-CuCuCu` |
| 8 | stack | 6, 7 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCuP-CuCuCu` |
| 9 | crystal | 8 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 10 | base | — | — | `CuCuP-CuCuCu` |
| 11 | stack | 9, 10 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCuP-CuCuCu` |
| 12 | crystal | 11 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 13 | cut | 12 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 14 | rotate | 13 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 15 | cut | 14 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 16 | rotate | 15 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 17 | base | — | — | `CuCuP-CuCuCu` |
| 18 | crystal | 17 | r | `CuCucrCuCuCu` |
| 19 | cut | 18 | 0 | `CuCucr------` |
| 20 | rotate | 19 | 1 | `--CuCucr----` |
| 21 | cut | 20 | 1 | `------cr----` |
| 22 | swap | 16, 21 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 23 | rotate | 22 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 24 | base | — | — | `----------Cu` |
| 25 | base | — | — | `----------Cu` |
| 26 | pin | 25 | — | `----------P-:----------Cu` |
| 27 | stack | 24, 26 | — | `----------Cu:----------P-:----------Cu` |
| 28 | base | — | — | `----------Cu` |
| 29 | stack | 27, 28 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 30 | base | — | — | `----------Cu` |
| 31 | stack | 29, 30 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 32 | swap | 23, 31 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 33 | rotate | 32 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 34 | cut | 33 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 35 | base | — | — | `----------Cu` |
| 36 | base | — | — | `----------Cu` |
| 37 | stack | 35, 36 | — | `----------Cu:----------Cu` |
| 38 | base | — | — | `------CuCuCu` |
| 39 | stack | 37, 38 | — | `----------Cu:----------Cu:------CuCuCu` |
| 40 | base | — | — | `--------Cu--` |
| 41 | stack | 39, 40 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--` |
| 42 | base | — | — | `------CuCu--` |
| 43 | stack | 41, 42 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 44 | swap | 34, 43 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 45 | rotate | 44 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 46 | cut | 45 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 47 | base | — | — | `CuCuP-CuCuCu` |
| 48 | crystal | 47 | r | `CuCucrCuCuCu` |
| 49 | base | — | — | `CuCuCuCuCuCu` |
| 50 | stack | 48, 49 | — | `CuCucrCuCuCu:CuCuCuCuCuCu` |
| 51 | base | — | — | `CuCuP-CuCuCu` |
| 52 | stack | 50, 51 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 53 | crystal | 52 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu` |
| 54 | base | — | — | `CuCuP-CuCuCu` |
| 55 | stack | 53, 54 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCuP-CuCuCu` |
| 56 | crystal | 55 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 57 | base | — | — | `CuCuP-CuCuCu` |
| 58 | stack | 56, 57 | — | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCuP-CuCuCu` |
| 59 | crystal | 58 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 60 | cut | 59 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 61 | rotate | 60 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 62 | cut | 61 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 63 | rotate | 62 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 64 | base | — | — | `CuCuP-CuCuCu` |
| 65 | crystal | 64 | r | `CuCucrCuCuCu` |
| 66 | cut | 65 | 0 | `CuCucr------` |
| 67 | rotate | 66 | 1 | `--CuCucr----` |
| 68 | cut | 67 | 1 | `------cr----` |
| 69 | swap | 63, 68 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 70 | rotate | 69 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 71 | base | — | — | `----------Cu` |
| 72 | base | — | — | `----------Cu` |
| 73 | pin | 72 | — | `----------P-:----------Cu` |
| 74 | stack | 71, 73 | — | `----------Cu:----------P-:----------Cu` |
| 75 | base | — | — | `----------Cu` |
| 76 | stack | 74, 75 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 77 | base | — | — | `----------Cu` |
| 78 | stack | 76, 77 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 79 | swap | 70, 78 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 80 | rotate | 79 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 81 | cut | 80 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 82 | base | — | — | `----------Cu` |
| 83 | base | — | — | `----------Cu` |
| 84 | stack | 82, 83 | — | `----------Cu:----------Cu` |
| 85 | base | — | — | `------CuCuCu` |
| 86 | stack | 84, 85 | — | `----------Cu:----------Cu:------CuCuCu` |
| 87 | base | — | — | `--------Cu--` |
| 88 | stack | 86, 87 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--` |
| 89 | base | — | — | `------CuCu--` |
| 90 | stack | 88, 89 | — | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 91 | swap | 81, 90 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 92 | rotate | 91 | 1 | `Cu--CuCu----:Cu--P-------:Cu--CucrCuCu:----Cucr--Cu:----CucrCuCu` |
| 93 | cut | 92 | 1 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 94 | swap | 46, 93 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |
