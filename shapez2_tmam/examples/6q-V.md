# 交换后不稳定的成品

独立制造两份H，第二份转三个象限，再交换。交换后不追加重力；新连接会在下一次加工时改变分组。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu`

共114步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

| 阶段 | 结果 |
|---|---|
| 每份H单独制造 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 第二份H旋转三个象限 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
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
| 15 | rotate | 14 | -2 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 16 | cut | 15 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 17 | rotate | 16 | -4 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 18 | base | — | — | `CuP-CuCuCuCu` |
| 19 | crystal | 18 | r | `CucrCuCuCuCu` |
| 20 | rotate | 19 | 1 | `CuCucrCuCuCu` |
| 21 | cut | 20 | 0 | `CuCucr------` |
| 22 | rotate | 21 | -1 | `Cucr------Cu` |
| 23 | rotate | 22 | -1 | `cr------CuCu` |
| 24 | cut | 23 | 0 | `cr----------` |
| 25 | rotate | 24 | 1 | `--cr--------` |
| 26 | rotate | 25 | -4 | `------cr----` |
| 27 | swap | 17, 26 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 28 | rotate | 27 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 29 | base | — | — | `----------Cu` |
| 30 | base | — | — | `----------P-` |
| 31 | stack | 29, 30 | — | `----------Cu:----------P-` |
| 32 | base | — | — | `----------Cu` |
| 33 | stack | 31, 32 | — | `----------Cu:----------P-:----------Cu` |
| 34 | base | — | — | `----------Cu` |
| 35 | stack | 33, 34 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 36 | base | — | — | `----------Cu` |
| 37 | stack | 35, 36 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 38 | swap | 28, 37 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 39 | rotate | 38 | -4 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 40 | cut | 39 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 41 | rotate | 40 | 4 | `Cu--------Cu:----------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 42 | rotate | 41 | -4 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 43 | base | — | — | `------Cu----` |
| 44 | base | — | — | `------Cu----` |
| 45 | stack | 43, 44 | — | `------Cu----:------Cu----` |
| 46 | base | — | — | `--CuCuCu----` |
| 47 | stack | 45, 46 | — | `------Cu----:------Cu----:--CuCuCu----` |
| 48 | base | — | — | `----Cu------` |
| 49 | stack | 47, 48 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------` |
| 50 | base | — | — | `--CuCu------` |
| 51 | stack | 49, 50 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| 52 | rotate | 51 | -4 | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 53 | swap | 42, 52 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 54 | rotate | 53 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 55 | cut | 54 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 56 | base | — | — | `P-CuCuCuCuCu` |
| 57 | crystal | 56 | r | `crCuCuCuCuCu` |
| 58 | base | — | — | `CuCuCuCuCuCu` |
| 59 | stack | 57, 58 | — | `crCuCuCuCuCu:CuCuCuCuCuCu` |
| 60 | base | — | — | `P-CuCuCuCuCu` |
| 61 | stack | 59, 60 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:P-CuCuCuCuCu` |
| 62 | crystal | 61 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu` |
| 63 | base | — | — | `P-CuCuCuCuCu` |
| 64 | stack | 62, 63 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 65 | crystal | 64 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 66 | base | — | — | `P-CuCuCuCuCu` |
| 67 | stack | 65, 66 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 68 | crystal | 67 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 69 | rotate | 68 | 2 | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 70 | cut | 69 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 71 | rotate | 70 | -2 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 72 | cut | 71 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 73 | rotate | 72 | -4 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 74 | base | — | — | `CuP-CuCuCuCu` |
| 75 | crystal | 74 | r | `CucrCuCuCuCu` |
| 76 | rotate | 75 | 1 | `CuCucrCuCuCu` |
| 77 | cut | 76 | 0 | `CuCucr------` |
| 78 | rotate | 77 | -1 | `Cucr------Cu` |
| 79 | rotate | 78 | -1 | `cr------CuCu` |
| 80 | cut | 79 | 0 | `cr----------` |
| 81 | rotate | 80 | 1 | `--cr--------` |
| 82 | rotate | 81 | -4 | `------cr----` |
| 83 | swap | 73, 82 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 84 | rotate | 83 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 85 | base | — | — | `----------Cu` |
| 86 | base | — | — | `----------P-` |
| 87 | stack | 85, 86 | — | `----------Cu:----------P-` |
| 88 | base | — | — | `----------Cu` |
| 89 | stack | 87, 88 | — | `----------Cu:----------P-:----------Cu` |
| 90 | base | — | — | `----------Cu` |
| 91 | stack | 89, 90 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 92 | base | — | — | `----------Cu` |
| 93 | stack | 91, 92 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 94 | swap | 84, 93 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 95 | rotate | 94 | -4 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 96 | cut | 95 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 97 | rotate | 96 | 4 | `Cu--------Cu:----------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 98 | rotate | 97 | -4 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 99 | base | — | — | `------Cu----` |
| 100 | base | — | — | `------Cu----` |
| 101 | stack | 99, 100 | — | `------Cu----:------Cu----` |
| 102 | base | — | — | `--CuCuCu----` |
| 103 | stack | 101, 102 | — | `------Cu----:------Cu----:--CuCuCu----` |
| 104 | base | — | — | `----Cu------` |
| 105 | stack | 103, 104 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------` |
| 106 | base | — | — | `--CuCu------` |
| 107 | stack | 105, 106 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| 108 | rotate | 107 | -4 | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 109 | swap | 98, 108 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 110 | rotate | 109 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 111 | cut | 110 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 112 | rotate | 111 | 3 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 113 | swap | 55, 112 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |
