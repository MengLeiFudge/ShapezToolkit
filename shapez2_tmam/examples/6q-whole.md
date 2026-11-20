# 六象限完整目标：通用脚手架拼出双环

两侧均由通用角和普通脚手架制造H，再共用双半形入口拼接。最终双环重新分组后不稳定，拼接后直接输出，不追加重力；本例不代表全部六象限已覆盖。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu`

共109步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../docs/proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 第一半形 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 两半形拼接成品 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |

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
| 13 | base | — | — | `----------Cu` |
| 14 | base | — | — | `----------P-` |
| 15 | stack | 13, 14 | — | `----------Cu:----------P-` |
| 16 | base | — | — | `----------Cu` |
| 17 | stack | 15, 16 | — | `----------Cu:----------P-:----------Cu` |
| 18 | base | — | — | `----------Cu` |
| 19 | stack | 17, 18 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 20 | base | — | — | `----------Cu` |
| 21 | stack | 19, 20 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 22 | swap | 12, 21 | 0 | `cr--------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 23 | rotate | 22 | 5 | `--------Cucr:--------P-Cu:--------Cucr:--------Cucr:--------Cucr` |
| 24 | base | — | — | `CuP-P-CuCuCu` |
| 25 | crystal | 24 | r | `CucrcrCuCuCu` |
| 26 | cut | 25 | 0 | `Cucrcr------` |
| 27 | rotate | 26 | 5 | `crcr------Cu` |
| 28 | cut | 27 | 0 | `crcr--------` |
| 29 | base | — | — | `CuCu--------` |
| 30 | stack | 28, 29 | — | `crcr--------:CuCu--------` |
| 31 | base | — | — | `CuCu--------` |
| 32 | stack | 30, 31 | — | `crcr--------:CuCu--------:CuCu--------` |
| 33 | base | — | — | `CuCu--------` |
| 34 | stack | 32, 33 | — | `crcr--------:CuCu--------:CuCu--------:CuCu--------` |
| 35 | base | — | — | `CuCu--------` |
| 36 | stack | 34, 35 | — | `crcr--------:CuCu--------:CuCu--------:CuCu--------:CuCu--------` |
| 37 | swap | 23, 36 | 1 | `crcr----Cucr:CuCu----P-Cu:CuCu----Cucr:CuCu----Cucr:CuCu----Cucr` |
| 38 | rotate | 37 | 5 | `cr----Cucrcr:Cu----P-CuCu:Cu----CucrCu:Cu----CucrCu:Cu----CucrCu` |
| 39 | cut | 38 | 1 | `------CuCuCu:------P-----:------CucrCu:------CucrCu:------CucrCu` |
| 40 | rotate | 39 | 1 | `Cu------CuCu:--------P---:Cu------Cucr:Cu------Cucr:Cu------Cucr` |
| 41 | cut | 40 | 1 | `--------CuCu:--------P---:--------Cucr:--------Cucr:--------Cucr` |
| 42 | base | — | — | `----Cu------` |
| 43 | base | — | — | `----Cu------` |
| 44 | stack | 42, 43 | — | `----Cu------:----Cu------` |
| 45 | base | — | — | `CuCuCu------` |
| 46 | stack | 44, 45 | — | `----Cu------:----Cu------:CuCuCu------` |
| 47 | base | — | — | `--CuCu------` |
| 48 | stack | 46, 47 | — | `----Cu------:----Cu------:CuCuCu------:--CuCu------` |
| 49 | base | — | — | `CuCuCu------` |
| 50 | stack | 48, 49 | — | `----Cu------:----Cu------:CuCuCu------:--CuCu------:CuCuCu------` |
| 51 | swap | 41, 50 | 1 | `----Cu--CuCu:----Cu--P---:CuCuCu--Cucr:--CuCu--Cucr:CuCuCu--Cucr` |
| 52 | rotate | 51 | 1 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--CuCu--Cu:crCuCuCu--Cu` |
| 53 | cut | 52 | 0 | `Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------` |
| 54 | base | — | — | `CuCuP-CuCuCu` |
| 55 | base | — | — | `CuCuCuCuCuCu` |
| 56 | stack | 54, 55 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu` |
| 57 | base | — | — | `CuCuP-CuCuCu` |
| 58 | stack | 56, 57 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 59 | base | — | — | `CuCuP-CuCuCu` |
| 60 | stack | 58, 59 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 61 | base | — | — | `CuCuP-CuCuCu` |
| 62 | stack | 60, 61 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 63 | crystal | 62 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 64 | cut | 63 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 65 | rotate | 64 | 1 | `--CuCucr----:--CuCuCu----:--CuCucr----:--CuCucr----:--CuCucr----` |
| 66 | cut | 65 | 1 | `------cr----:------Cu----:------cr----:------cr----:------cr----` |
| 67 | base | — | — | `----Cu------` |
| 68 | base | — | — | `----P-------` |
| 69 | stack | 67, 68 | — | `----Cu------:----P-------` |
| 70 | base | — | — | `----Cu------` |
| 71 | stack | 69, 70 | — | `----Cu------:----P-------:----Cu------` |
| 72 | base | — | — | `----Cu------` |
| 73 | stack | 71, 72 | — | `----Cu------:----P-------:----Cu------:----Cu------` |
| 74 | base | — | — | `----Cu------` |
| 75 | stack | 73, 74 | — | `----Cu------:----P-------:----Cu------:----Cu------:----Cu------` |
| 76 | swap | 66, 75 | 1 | `----Cucr----:----P-Cu----:----Cucr----:----Cucr----:----Cucr----` |
| 77 | rotate | 76 | 5 | `--Cucr------:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 78 | base | — | — | `CuCuCuCuP-P-` |
| 79 | crystal | 78 | r | `CuCuCuCucrcr` |
| 80 | cut | 79 | 1 | `------Cucrcr` |
| 81 | rotate | 80 | 5 | `----Cucrcr--` |
| 82 | cut | 81 | 1 | `------crcr--` |
| 83 | base | — | — | `------CuCu--` |
| 84 | stack | 82, 83 | — | `------crcr--:------CuCu--` |
| 85 | base | — | — | `------CuCu--` |
| 86 | stack | 84, 85 | — | `------crcr--:------CuCu--:------CuCu--` |
| 87 | base | — | — | `------CuCu--` |
| 88 | stack | 86, 87 | — | `------crcr--:------CuCu--:------CuCu--:------CuCu--` |
| 89 | base | — | — | `------CuCu--` |
| 90 | stack | 88, 89 | — | `------crcr--:------CuCu--:------CuCu--:------CuCu--:------CuCu--` |
| 91 | swap | 77, 90 | 0 | `--Cucrcrcr--:--P-CuCuCu--:--CucrCuCu--:--CucrCuCu--:--CucrCuCu--` |
| 92 | rotate | 91 | 5 | `Cucrcrcr----:P-CuCuCu----:CucrCuCu----:CucrCuCu----:CucrCuCu----` |
| 93 | cut | 92 | 0 | `CuCuCu------:P-----------:CucrCu------:CucrCu------:CucrCu------` |
| 94 | rotate | 93 | 1 | `--CuCuCu----:--P---------:--CucrCu----:--CucrCu----:--CucrCu----` |
| 95 | cut | 94 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 96 | base | — | — | `----------Cu` |
| 97 | base | — | — | `----------Cu` |
| 98 | stack | 96, 97 | — | `----------Cu:----------Cu` |
| 99 | base | — | — | `------CuCuCu` |
| 100 | stack | 98, 99 | — | `----------Cu:----------Cu:------CuCuCu` |
| 101 | base | — | — | `--------CuCu` |
| 102 | stack | 100, 101 | — | `----------Cu:----------Cu:------CuCuCu:--------CuCu` |
| 103 | base | — | — | `------CuCuCu` |
| 104 | stack | 102, 103 | — | `----------Cu:----------Cu:------CuCuCu:--------CuCu:------CuCuCu` |
| 105 | swap | 95, 104 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--CuCu:--CucrCuCuCu` |
| 106 | rotate | 105 | 1 | `Cu--CuCu----:Cu--P-------:Cu--CucrCuCu:Cu--Cucr--Cu:Cu--CucrCuCu` |
| 107 | cut | 106 | 1 | `------Cu----:------------:------crCuCu:------cr--Cu:------crCuCu` |
| 108 | swap | 53, 107 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu` |
