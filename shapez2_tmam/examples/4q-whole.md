# 四象限完整目标：共用双半形制造

两种角加工在同一完整目标内调用；按同一半形程序制造两侧后拼合。这是统一整图流程的一个输入，角的差异不再计为整图类别。

配置：4象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`--P-CuCu:CuCu--P-:--CucrCu:--P---Cu:crCu--Cu`

共139步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../proofs/04-stacking.md#s04-19)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 第一半形 | `--P-----:CuCu----:--Cu----:--P-----:crCu----` |
| 两半形拼接成品 | `--P-CuCu:CuCu--P-:--CucrCu:--P---Cu:crCu--Cu` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-P-CuCu` |
| 1 | base | — | — | `P-P-CuCu` |
| 2 | stack | 0, 1 | — | `P-P-CuCu:P-P-CuCu` |
| 3 | base | — | — | `CuCuCuCu` |
| 4 | stack | 2, 3 | — | `P-P-CuCu:P-P-CuCu:CuCuCuCu` |
| 5 | base | — | — | `P-CuCuCu` |
| 6 | stack | 4, 5 | — | `P-P-CuCu:P-P-CuCu:CuCuCuCu:P-CuCuCu` |
| 7 | crystal | 6 | r | `crcrCuCu:crcrCuCu:CuCuCuCu:crCuCuCu` |
| 8 | cut | 7 | 0 | `crcr----:crcr----:CuCu----:crCu----` |
| 9 | base | — | — | `--Cu----` |
| 10 | stack | 8, 9 | — | `crcr----:crcr----:CuCu----:crCu----:--Cu----` |
| 11 | base | — | — | `------Cu` |
| 12 | base | — | — | `------Cu` |
| 13 | stack | 11, 12 | — | `------Cu:------Cu` |
| 14 | base | — | — | `------Cu` |
| 15 | stack | 13, 14 | — | `------Cu:------Cu:------Cu` |
| 16 | base | — | — | `------Cu` |
| 17 | stack | 15, 16 | — | `------Cu:------Cu:------Cu:------Cu` |
| 18 | base | — | — | `------Cu` |
| 19 | stack | 17, 18 | — | `------Cu:------Cu:------Cu:------Cu:------Cu` |
| 20 | swap | 10, 19 | 0 | `crcr--Cu:crcr--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 21 | rotate | 20 | 1 | `Cucrcr--:Cucrcr--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 22 | cut | 21 | 0 | `Cu------:Cu------:CuCu----:Cucr----:Cu------` |
| 23 | base | — | — | `----Cu--` |
| 24 | base | — | — | `----Cu--` |
| 25 | stack | 23, 24 | — | `----Cu--:----Cu--` |
| 26 | base | — | — | `----Cu--` |
| 27 | stack | 25, 26 | — | `----Cu--:----Cu--:----Cu--` |
| 28 | base | — | — | `----Cu--` |
| 29 | stack | 27, 28 | — | `----Cu--:----Cu--:----Cu--:----Cu--` |
| 30 | base | — | — | `----Cu--` |
| 31 | stack | 29, 30 | — | `----Cu--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 32 | swap | 22, 31 | 0 | `Cu--Cu--:Cu--Cu--:CuCuCu--:CucrCu--:Cu--Cu--` |
| 33 | rotate | 32 | 3 | `--Cu--Cu:--Cu--Cu:CuCu--Cu:crCu--Cu:--Cu--Cu` |
| 34 | cut | 33 | 0 | `--Cu----:--Cu----:CuCu----:crCu----:--Cu----` |
| 35 | base | — | — | `CuP-CuCu` |
| 36 | base | — | — | `CuP-CuCu` |
| 37 | stack | 35, 36 | — | `CuP-CuCu:CuP-CuCu` |
| 38 | crystal | 37 | r | `CucrCuCu:CucrCuCu` |
| 39 | cut | 38 | 0 | `Cucr----:Cucr----` |
| 40 | rotate | 39 | 3 | `cr----Cu:cr----Cu` |
| 41 | cut | 40 | 0 | `cr------:cr------` |
| 42 | rotate | 41 | 3 | `------cr:------cr` |
| 43 | base | — | — | `------Cu` |
| 44 | stack | 42, 43 | — | `------cr:------cr:------Cu` |
| 45 | swap | 34, 44 | 0 | `--Cu--cr:--Cu--cr:CuCu--Cu:crCu----:--Cu----` |
| 46 | rotate | 45 | 1 | `cr--Cu--:cr--Cu--:CuCuCu--:--crCu--:----Cu--` |
| 47 | cut | 46 | 0 | `cr------:cr------:CuCu----:--cr----` |
| 48 | base | — | — | `--P-----` |
| 49 | base | — | — | `--P-----` |
| 50 | stack | 48, 49 | — | `--P-----:--P-----` |
| 51 | base | — | — | `--P-----` |
| 52 | stack | 50, 51 | — | `--P-----:--P-----:--P-----` |
| 53 | base | — | — | `--Cu----` |
| 54 | stack | 52, 53 | — | `--P-----:--P-----:--P-----:--Cu----` |
| 55 | base | — | — | `CuP-CuCu` |
| 56 | base | — | — | `CuP-CuCu` |
| 57 | stack | 55, 56 | — | `CuP-CuCu:CuP-CuCu` |
| 58 | base | — | — | `CuP-CuCu` |
| 59 | stack | 57, 58 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 60 | base | — | — | `CuP-CuCu` |
| 61 | stack | 59, 60 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 62 | base | — | — | `CuP-CuCu` |
| 63 | stack | 61, 62 | — | `CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu:CuP-CuCu` |
| 64 | crystal | 63 | r | `CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu:CucrCuCu` |
| 65 | cut | 64 | 0 | `Cucr----:Cucr----:Cucr----:Cucr----:Cucr----` |
| 66 | rotate | 65 | 1 | `--Cucr--:--Cucr--:--Cucr--:--Cucr--:--Cucr--` |
| 67 | cut | 66 | 1 | `----cr--:----cr--:----cr--:----cr--:----cr--` |
| 68 | swap | 54, 67 | 0 | `--P-cr--:--P-cr--:--P-cr--:--Cucr--:----cr--` |
| 69 | rotate | 68 | 1 | `----P-cr:----P-cr:----P-cr:----Cucr:------cr` |
| 70 | swap | 47, 69 | 0 | `cr--P-cr:cr--P-cr:CuCuP-cr:--crCucr:------cr` |
| 71 | pin | 70 | — | `P---P-P-:CuCuP---:----P---:----P---:--crCu--` |
| 72 | base | — | — | `P-------` |
| 73 | stack | 71, 72 | — | `P---P-P-:CuCuP---:P---P---:----P---:--crCu--` |
| 74 | base | — | — | `P-------` |
| 75 | stack | 73, 74 | — | `P---P-P-:CuCuP---:P---P---:P---P---:--crCu--` |
| 76 | base | — | — | `Cu------` |
| 77 | stack | 75, 76 | — | `P---P-P-:CuCuP---:P---P---:P---P---:CucrCu--` |
| 78 | cut | 77 | 0 | `P-------:CuCu----:P-------:P-------:Cucr----` |
| 79 | base | — | — | `----P-Cu` |
| 80 | base | — | — | `----CuCu` |
| 81 | stack | 79, 80 | — | `----P-Cu:----CuCu` |
| 82 | base | — | — | `----CuCu` |
| 83 | stack | 81, 82 | — | `----P-Cu:----CuCu:----CuCu` |
| 84 | base | — | — | `----P-Cu` |
| 85 | stack | 83, 84 | — | `----P-Cu:----CuCu:----CuCu:----P-Cu` |
| 86 | base | — | — | `----CuCu` |
| 87 | stack | 85, 86 | — | `----P-Cu:----CuCu:----CuCu:----P-Cu:----CuCu` |
| 88 | swap | 78, 87 | 0 | `P---P-Cu:CuCuCuCu:P---CuCu:P---P-Cu:CucrCuCu` |
| 89 | rotate | 88 | 3 | `--P-CuP-:CuCuCuCu:--CuCuP-:--P-CuP-:crCuCuCu` |
| 90 | cut | 89 | 0 | `--P-----:CuCu----:--Cu----:--P-----:crCu----` |
| 91 | base | — | — | `CuP-CuCu` |
| 92 | base | — | — | `CuCuCuCu` |
| 93 | stack | 91, 92 | — | `CuP-CuCu:CuCuCuCu` |
| 94 | base | — | — | `CuP-CuCu` |
| 95 | stack | 93, 94 | — | `CuP-CuCu:CuCuCuCu:CuP-CuCu` |
| 96 | crystal | 95 | r | `CucrCuCu:CuCuCuCu:CucrCuCu` |
| 97 | cut | 96 | 0 | `Cucr----:CuCu----:Cucr----` |
| 98 | rotate | 97 | 3 | `cr----Cu:Cu----Cu:cr----Cu` |
| 99 | cut | 98 | 0 | `cr------:Cu------:cr------` |
| 100 | base | — | — | `------Cu` |
| 101 | base | — | — | `------P-` |
| 102 | stack | 100, 101 | — | `------Cu:------P-` |
| 103 | base | — | — | `------Cu` |
| 104 | stack | 102, 103 | — | `------Cu:------P-:------Cu` |
| 105 | base | — | — | `------Cu` |
| 106 | stack | 104, 105 | — | `------Cu:------P-:------Cu:------Cu` |
| 107 | base | — | — | `------Cu` |
| 108 | stack | 106, 107 | — | `------Cu:------P-:------Cu:------Cu:------Cu` |
| 109 | swap | 99, 108 | 0 | `cr----Cu:Cu----P-:cr----Cu:------Cu:------Cu` |
| 110 | rotate | 109 | 1 | `Cucr----:P-Cu----:Cucr----:Cu------:Cu------` |
| 111 | base | — | — | `CuP-CuCu` |
| 112 | crystal | 111 | r | `CucrCuCu` |
| 113 | cut | 112 | 0 | `Cucr----` |
| 114 | rotate | 113 | 1 | `--Cucr--` |
| 115 | cut | 114 | 1 | `----cr--` |
| 116 | base | — | — | `----Cu--` |
| 117 | stack | 115, 116 | — | `----cr--:----Cu--` |
| 118 | base | — | — | `----Cu--` |
| 119 | stack | 117, 118 | — | `----cr--:----Cu--:----Cu--` |
| 120 | base | — | — | `----Cu--` |
| 121 | stack | 119, 120 | — | `----cr--:----Cu--:----Cu--:----Cu--` |
| 122 | base | — | — | `----Cu--` |
| 123 | stack | 121, 122 | — | `----cr--:----Cu--:----Cu--:----Cu--:----Cu--` |
| 124 | swap | 110, 123 | 0 | `Cucrcr--:P-CuCu--:CucrCu--:Cu--Cu--:Cu--Cu--` |
| 125 | cut | 124 | 0 | `CuCu----:P-------:Cucr----:Cu------:Cu------` |
| 126 | base | — | — | `----CuCu` |
| 127 | base | — | — | `----P-Cu` |
| 128 | stack | 126, 127 | — | `----CuCu:----P-Cu` |
| 129 | base | — | — | `----CuCu` |
| 130 | stack | 128, 129 | — | `----CuCu:----P-Cu:----CuCu` |
| 131 | base | — | — | `----CuCu` |
| 132 | stack | 130, 131 | — | `----CuCu:----P-Cu:----CuCu:----CuCu` |
| 133 | base | — | — | `----CuCu` |
| 134 | stack | 132, 133 | — | `----CuCu:----P-Cu:----CuCu:----CuCu:----CuCu` |
| 135 | swap | 125, 134 | 0 | `CuCuCuCu:P---P-Cu:CucrCuCu:Cu--CuCu:Cu--CuCu` |
| 136 | rotate | 135 | 1 | `CuCuCuCu:CuP---P-:CuCucrCu:CuCu--Cu:CuCu--Cu` |
| 137 | cut | 136 | 1 | `----CuCu:------P-:----crCu:------Cu:------Cu` |
| 138 | swap | 90, 137 | 0 | `--P-CuCu:CuCu--P-:--CucrCu:--P---Cu:crCu--Cu` |
