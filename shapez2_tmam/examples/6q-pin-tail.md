# 非K下料追加普通格和针尾

H旁先准备q3两层普通柱；一次堆叠同时加入q4地面普通格与q3第三层针。独立下落把上料缩成一层N/P基础料，无需辅助晶体。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----CuCu--:------Cu----:crCuCuP-----:cr--Cu------:crCuCu------`

共61步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

| 阶段 | 结果 |
|---|---|
| 已有非K下料 | `Cu----Cu----:------Cu----:crCuCu------:cr--Cu------:crCuCu------` |
| 紧凑基础上料 | `------P-Cu--` |
| 一次堆叠成品 | `Cu----CuCu--:------Cu----:crCuCuP-----:cr--Cu------:crCuCu------` |

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
| 55 | base | — | — | `------Cu----` |
| 56 | base | — | — | `------Cu----` |
| 57 | stack | 55, 56 | — | `------Cu----:------Cu----` |
| 58 | stack | 54, 57 | — | `Cu----Cu----:------Cu----:crCuCu------:cr--Cu------:crCuCu------` |
| 59 | base | — | — | `------P-Cu--` |
| 60 | stack | 58, 59 | — | `Cu----CuCu--:------Cu----:crCuCuP-----:cr--Cu------:crCuCu------` |
