# 交换后不稳定的成品

独立制造两份H，选择输入方向再交换。交换后不追加重力；新连接会在下一次加工时改变分组。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu`

共104步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

| 阶段 | 结果 |
|---|---|
| 每份H单独制造 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 交换的第二份输入 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 最终交换输出V | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCuCuCu:CuCuCuCuCuCu` |
| 4 | base | — | — | `P-CuCuCuCuCu` |
| 5 | stack | 3, 4 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:P-CuCuCuCuCu` |
| 6 | crystal | 5 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu` |
| 7 | base | — | — | `P-CuCuCuCuCu` |
| 8 | stack | 6, 7 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 9 | crystal | 8 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 10 | base | — | — | `P-CuCuCuCuCu` |
| 11 | stack | 9, 10 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 12 | crystal | 11 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 13 | rotate | 12 | 2 | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 14 | cut | 13 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 15 | rotate | 14 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 16 | cut | 15 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 17 | rotate | 16 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 18 | base | — | — | `CuP-CuCuCuCu` |
| 19 | crystal | 18 | r | `CucrCuCuCuCu` |
| 20 | rotate | 19 | 1 | `CuCucrCuCuCu` |
| 21 | cut | 20 | 0 | `CuCucr------` |
| 22 | rotate | 21 | 4 | `cr------CuCu` |
| 23 | cut | 22 | 0 | `cr----------` |
| 24 | rotate | 23 | 3 | `------cr----` |
| 25 | swap | 17, 24 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 26 | rotate | 25 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 27 | base | — | — | `----------Cu` |
| 28 | base | — | — | `----------Cu` |
| 29 | pin | 28 | — | `----------P-:----------Cu` |
| 30 | stack | 27, 29 | — | `----------Cu:----------P-:----------Cu` |
| 31 | base | — | — | `----------Cu` |
| 32 | stack | 30, 31 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 33 | base | — | — | `----------Cu` |
| 34 | stack | 32, 33 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 35 | swap | 26, 34 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 36 | rotate | 35 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 37 | cut | 36 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 38 | base | — | — | `------Cu----` |
| 39 | base | — | — | `------Cu----` |
| 40 | stack | 38, 39 | — | `------Cu----:------Cu----` |
| 41 | base | — | — | `--CuCuCu----` |
| 42 | stack | 40, 41 | — | `------Cu----:------Cu----:--CuCuCu----` |
| 43 | base | — | — | `----Cu------` |
| 44 | stack | 42, 43 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------` |
| 45 | base | — | — | `--CuCu------` |
| 46 | stack | 44, 45 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| 47 | rotate | 46 | 2 | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 48 | swap | 37, 47 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 49 | rotate | 48 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 50 | cut | 49 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 51 | base | — | — | `P-CuCuCuCuCu` |
| 52 | crystal | 51 | r | `crCuCuCuCuCu` |
| 53 | base | — | — | `CuCuCuCuCuCu` |
| 54 | stack | 52, 53 | — | `crCuCuCuCuCu:CuCuCuCuCuCu` |
| 55 | base | — | — | `P-CuCuCuCuCu` |
| 56 | stack | 54, 55 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:P-CuCuCuCuCu` |
| 57 | crystal | 56 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu` |
| 58 | base | — | — | `P-CuCuCuCuCu` |
| 59 | stack | 57, 58 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 60 | crystal | 59 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 61 | base | — | — | `P-CuCuCuCuCu` |
| 62 | stack | 60, 61 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 63 | crystal | 62 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 64 | rotate | 63 | 2 | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 65 | cut | 64 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 66 | rotate | 65 | 4 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 67 | cut | 66 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 68 | rotate | 67 | 2 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 69 | base | — | — | `CuP-CuCuCuCu` |
| 70 | crystal | 69 | r | `CucrCuCuCuCu` |
| 71 | rotate | 70 | 1 | `CuCucrCuCuCu` |
| 72 | cut | 71 | 0 | `CuCucr------` |
| 73 | rotate | 72 | 4 | `cr------CuCu` |
| 74 | cut | 73 | 0 | `cr----------` |
| 75 | rotate | 74 | 3 | `------cr----` |
| 76 | swap | 68, 75 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 77 | rotate | 76 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 78 | base | — | — | `----------Cu` |
| 79 | base | — | — | `----------Cu` |
| 80 | pin | 79 | — | `----------P-:----------Cu` |
| 81 | stack | 78, 80 | — | `----------Cu:----------P-:----------Cu` |
| 82 | base | — | — | `----------Cu` |
| 83 | stack | 81, 82 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 84 | base | — | — | `----------Cu` |
| 85 | stack | 83, 84 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 86 | swap | 77, 85 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 87 | rotate | 86 | 2 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 88 | cut | 87 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 89 | base | — | — | `------Cu----` |
| 90 | base | — | — | `------Cu----` |
| 91 | stack | 89, 90 | — | `------Cu----:------Cu----` |
| 92 | base | — | — | `--CuCuCu----` |
| 93 | stack | 91, 92 | — | `------Cu----:------Cu----:--CuCuCu----` |
| 94 | base | — | — | `----Cu------` |
| 95 | stack | 93, 94 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------` |
| 96 | base | — | — | `--CuCu------` |
| 97 | stack | 95, 96 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| 98 | rotate | 97 | 2 | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 99 | swap | 88, 98 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 100 | rotate | 99 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 101 | cut | 100 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 102 | rotate | 101 | 3 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 103 | swap | 50, 102 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |
