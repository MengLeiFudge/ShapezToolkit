# 交换后不稳定的成品

独立制造两份H，第二份转三个象限，再交换。交换后不追加重力；新连接会在下一次加工时改变分组。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu`

共112步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 30 | base | — | — | `----------Cu` |
| 31 | pin | 30 | — | `----------P-:----------Cu` |
| 32 | stack | 29, 31 | — | `----------Cu:----------P-:----------Cu` |
| 33 | base | — | — | `----------Cu` |
| 34 | stack | 32, 33 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 35 | base | — | — | `----------Cu` |
| 36 | stack | 34, 35 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 37 | swap | 28, 36 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 38 | rotate | 37 | -4 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 39 | cut | 38 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 40 | rotate | 39 | 4 | `Cu--------Cu:----------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 41 | rotate | 40 | -4 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 42 | base | — | — | `------Cu----` |
| 43 | base | — | — | `------Cu----` |
| 44 | stack | 42, 43 | — | `------Cu----:------Cu----` |
| 45 | base | — | — | `--CuCuCu----` |
| 46 | stack | 44, 45 | — | `------Cu----:------Cu----:--CuCuCu----` |
| 47 | base | — | — | `----Cu------` |
| 48 | stack | 46, 47 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------` |
| 49 | base | — | — | `--CuCu------` |
| 50 | stack | 48, 49 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| 51 | rotate | 50 | -4 | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 52 | swap | 41, 51 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 53 | rotate | 52 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 54 | cut | 53 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 55 | base | — | — | `P-CuCuCuCuCu` |
| 56 | crystal | 55 | r | `crCuCuCuCuCu` |
| 57 | base | — | — | `CuCuCuCuCuCu` |
| 58 | stack | 56, 57 | — | `crCuCuCuCuCu:CuCuCuCuCuCu` |
| 59 | base | — | — | `P-CuCuCuCuCu` |
| 60 | stack | 58, 59 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:P-CuCuCuCuCu` |
| 61 | crystal | 60 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu` |
| 62 | base | — | — | `P-CuCuCuCuCu` |
| 63 | stack | 61, 62 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 64 | crystal | 63 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 65 | base | — | — | `P-CuCuCuCuCu` |
| 66 | stack | 64, 65 | — | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:P-CuCuCuCuCu` |
| 67 | crystal | 66 | r | `crCuCuCuCuCu:CuCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu:crCuCuCuCuCu` |
| 68 | rotate | 67 | 2 | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 69 | cut | 68 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 70 | rotate | 69 | -2 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 71 | cut | 70 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 72 | rotate | 71 | -4 | `----cr------:----Cu------:----cr------:----cr------:----cr------` |
| 73 | base | — | — | `CuP-CuCuCuCu` |
| 74 | crystal | 73 | r | `CucrCuCuCuCu` |
| 75 | rotate | 74 | 1 | `CuCucrCuCuCu` |
| 76 | cut | 75 | 0 | `CuCucr------` |
| 77 | rotate | 76 | -1 | `Cucr------Cu` |
| 78 | rotate | 77 | -1 | `cr------CuCu` |
| 79 | cut | 78 | 0 | `cr----------` |
| 80 | rotate | 79 | 1 | `--cr--------` |
| 81 | rotate | 80 | -4 | `------cr----` |
| 82 | swap | 72, 81 | 0 | `----crcr----:----Cu------:----cr------:----cr------:----cr------` |
| 83 | rotate | 82 | 4 | `crcr--------:Cu----------:cr----------:cr----------:cr----------` |
| 84 | base | — | — | `----------Cu` |
| 85 | base | — | — | `----------Cu` |
| 86 | pin | 85 | — | `----------P-:----------Cu` |
| 87 | stack | 84, 86 | — | `----------Cu:----------P-:----------Cu` |
| 88 | base | — | — | `----------Cu` |
| 89 | stack | 87, 88 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 90 | base | — | — | `----------Cu` |
| 91 | stack | 89, 90 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 92 | swap | 83, 91 | 0 | `crcr------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 93 | rotate | 92 | -4 | `--Cucrcr----:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 94 | cut | 93 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 95 | rotate | 94 | 4 | `Cu--------Cu:----------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 96 | rotate | 95 | -4 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 97 | base | — | — | `------Cu----` |
| 98 | base | — | — | `------Cu----` |
| 99 | stack | 97, 98 | — | `------Cu----:------Cu----` |
| 100 | base | — | — | `--CuCuCu----` |
| 101 | stack | 99, 100 | — | `------Cu----:------Cu----:--CuCuCu----` |
| 102 | base | — | — | `----Cu------` |
| 103 | stack | 101, 102 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------` |
| 104 | base | — | — | `--CuCu------` |
| 105 | stack | 103, 104 | — | `------Cu----:------Cu----:--CuCuCu----:----Cu------:--CuCu------` |
| 106 | rotate | 105 | -4 | `----------Cu:----------Cu:------CuCuCu:--------Cu--:------CuCu--` |
| 107 | swap | 96, 106 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--Cu--:--CucrCuCu--` |
| 108 | rotate | 107 | 4 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--Cu----Cu:crCuCu----Cu` |
| 109 | cut | 108 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 110 | rotate | 109 | 3 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 111 | swap | 54, 110 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |
