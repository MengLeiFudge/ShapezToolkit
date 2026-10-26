# 八象限八层的单次复杂堆叠

准备过程使用八层晶体塔，顶破后得到非K下料S。把q1两层普通柱一次堆上去；拆成两次堆叠会让框架重新分组并碎裂。

配置：8象限、8层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------`

共142步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

| 阶段 | 结果 |
|---|---|
| 八层准备形 | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:cr------cr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 添加框架后的D | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr--CuCucr--cr--:------------cr--:------------cr--:------------cr--` |
| 顶破后的S | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:cr--Cu--cr------:cr--CuCucr------` |
| 双层普通上料 | `--Cu------------:--Cu------------` |
| 一次堆叠成品 | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 1 | crystal | 0 | r | `crCuCuCuCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu` |
| 4 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 5 | stack | 3, 4 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:P-CuCuCuCuCuCuCu` |
| 6 | crystal | 5 | r | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu` |
| 7 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 8 | stack | 6, 7 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:P-CuCuCuCuCuCuCu` |
| 9 | crystal | 8 | r | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu` |
| 10 | base | — | — | `P-CuCuCuCuCuCuCu` |
| 11 | stack | 9, 10 | — | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:P-CuCuCuCuCuCuCu` |
| 12 | crystal | 11 | r | `crCuCuCuCuCuCuCu:CuCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu:crCuCuCuCuCuCuCu` |
| 13 | rotate | 12 | 3 | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 14 | cut | 13 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 15 | rotate | 14 | -3 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 16 | cut | 15 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 17 | rotate | 16 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 18 | base | — | — | `CuP-CuCuCuCuCuCu` |
| 19 | crystal | 18 | r | `CucrCuCuCuCuCuCu` |
| 20 | rotate | 19 | 2 | `CuCuCucrCuCuCuCu` |
| 21 | cut | 20 | 0 | `CuCuCucr--------` |
| 22 | rotate | 21 | -2 | `Cucr--------CuCu` |
| 23 | rotate | 22 | -1 | `cr--------CuCuCu` |
| 24 | cut | 23 | 0 | `cr--------------` |
| 25 | rotate | 24 | 1 | `--cr------------` |
| 26 | rotate | 25 | 3 | `--------cr------` |
| 27 | swap | 17, 26 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 28 | rotate | 27 | -3 | `crcr------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 29 | rotate | 28 | 2 | `----crcr--------:----Cu----------:----cr----------:----cr----------:----cr----------` |
| 30 | base | — | — | `CuCuP-CuCuCuCuCu` |
| 31 | crystal | 30 | r | `CuCucrCuCuCuCuCu` |
| 32 | base | — | — | `CuCuP-CuCuCuCuCu` |
| 33 | stack | 31, 32 | — | `CuCucrCuCuCuCuCu:CuCuP-CuCuCuCuCu` |
| 34 | crystal | 33 | r | `CuCucrCuCuCuCuCu:CuCucrCuCuCuCuCu` |
| 35 | rotate | 34 | 1 | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 36 | cut | 35 | 0 | `CuCuCucr--------:CuCuCucr--------` |
| 37 | rotate | 36 | -1 | `CuCucr--------Cu:CuCucr--------Cu` |
| 38 | rotate | 37 | -2 | `cr--------CuCuCu:cr--------CuCuCu` |
| 39 | cut | 38 | 0 | `cr--------------:cr--------------` |
| 40 | rotate | 39 | 2 | `----cr----------:----cr----------` |
| 41 | rotate | 40 | 2 | `--------cr------:--------cr------` |
| 42 | swap | 29, 41 | 0 | `----crcrcr------:----Cu--cr------:----cr----------:----cr----------:----cr----------` |
| 43 | rotate | 42 | -2 | `crcrcr----------:Cu--cr----------:cr--------------:cr--------------:cr--------------` |
| 44 | rotate | 43 | 1 | `--crcrcr--------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 45 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 46 | crystal | 45 | r | `CuCuCucrCuCuCuCu` |
| 47 | cut | 46 | 0 | `CuCuCucr--------` |
| 48 | rotate | 47 | -3 | `cr--------CuCuCu` |
| 49 | cut | 48 | 0 | `cr--------------` |
| 50 | rotate | 49 | 3 | `------cr--------` |
| 51 | rotate | 50 | 1 | `--------cr------` |
| 52 | swap | 44, 51 | 0 | `--crcrcrcr------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 53 | rotate | 52 | -1 | `crcrcrcr--------:Cu--cr----------:cr--------------:cr--------------:cr--------------` |
| 54 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 55 | crystal | 54 | r | `CuCuCuCucrCuCuCu` |
| 56 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 57 | stack | 55, 56 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu` |
| 58 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 59 | stack | 57, 58 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCuP-CuCuCu` |
| 60 | crystal | 59 | r | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu` |
| 61 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 62 | stack | 60, 61 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCuP-CuCuCu` |
| 63 | crystal | 62 | r | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu` |
| 64 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 65 | stack | 63, 64 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCuP-CuCuCu` |
| 66 | crystal | 65 | r | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu` |
| 67 | rotate | 66 | -1 | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 68 | cut | 67 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 69 | rotate | 68 | 1 | `--CuCuCucr------:--CuCuCuCu------:--CuCuCucr------:--CuCuCucr------:--CuCuCucr------` |
| 70 | rotate | 69 | -4 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 71 | cut | 70 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 72 | rotate | 71 | 4 | `--------cr------:--------Cu------:--------cr------:--------cr------:--------cr------` |
| 73 | rotate | 72 | -1 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 74 | base | — | — | `CuCuCuCuCuP-CuCu` |
| 75 | crystal | 74 | r | `CuCuCuCuCucrCuCu` |
| 76 | rotate | 75 | -2 | `CuCuCucrCuCuCuCu` |
| 77 | cut | 76 | 0 | `CuCuCucr--------` |
| 78 | rotate | 77 | 2 | `----CuCuCucr----` |
| 79 | rotate | 78 | -5 | `cr--------CuCuCu` |
| 80 | cut | 79 | 0 | `cr--------------` |
| 81 | rotate | 80 | 5 | `----------cr----` |
| 82 | rotate | 81 | -1 | `--------cr------` |
| 83 | swap | 73, 82 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 84 | rotate | 83 | 1 | `--------crcr----:--------Cu------:--------cr------:--------cr------:--------cr------` |
| 85 | rotate | 84 | -2 | `----crcr--------:----Cu----------:----cr----------:----cr----------:----cr----------` |
| 86 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 87 | crystal | 86 | r | `CuCuCuCuCuCucrCu` |
| 88 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 89 | stack | 87, 88 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 90 | crystal | 89 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 91 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 92 | stack | 90, 91 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 93 | crystal | 92 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 94 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 95 | stack | 93, 94 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 96 | crystal | 95 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 97 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 98 | stack | 96, 97 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 99 | crystal | 98 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 100 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 101 | stack | 99, 100 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 102 | crystal | 101 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 103 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 104 | stack | 102, 103 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 105 | crystal | 104 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 106 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 107 | stack | 105, 106 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 108 | crystal | 107 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 109 | rotate | 108 | -3 | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 110 | cut | 109 | 0 | `CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 111 | rotate | 110 | 3 | `------CuCuCucr--:------CuCuCucr--:------CuCuCucr--:------CuCuCucr--:------CuCuCucr--:------CuCuCucr--:------CuCuCucr--:------CuCuCucr--` |
| 112 | rotate | 111 | -6 | `cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 113 | cut | 112 | 0 | `cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------` |
| 114 | rotate | 113 | 6 | `------------cr--:------------cr--:------------cr--:------------cr--:------------cr--:------------cr--:------------cr--:------------cr--` |
| 115 | rotate | 114 | -2 | `--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------` |
| 116 | swap | 85, 115 | 0 | `----crcrcr------:----Cu--cr------:----cr--cr------:----cr--cr------:----cr--cr------:--------cr------:--------cr------:--------cr------` |
| 117 | rotate | 116 | 2 | `--------crcrcr--:--------Cu--cr--:--------cr--cr--:--------cr--cr--:--------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 118 | rotate | 117 | -3 | `--crcrcr--------:--Cu--cr--------:--cr--cr--------:--cr--cr--------:--cr--cr--------:------cr--------:------cr--------:------cr--------` |
| 119 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 120 | crystal | 119 | r | `CuCuCuCuCuCuCucr` |
| 121 | rotate | 120 | -4 | `CuCuCucrCuCuCuCu` |
| 122 | cut | 121 | 0 | `CuCuCucr--------` |
| 123 | rotate | 122 | 4 | `--------CuCuCucr` |
| 124 | rotate | 123 | -7 | `cr--------CuCuCu` |
| 125 | cut | 124 | 0 | `cr--------------` |
| 126 | rotate | 125 | 7 | `--------------cr` |
| 127 | rotate | 126 | -3 | `--------cr------` |
| 128 | swap | 118, 127 | 0 | `--crcrcrcr------:--Cu--cr--------:--cr--cr--------:--cr--cr--------:--cr--cr--------:------cr--------:------cr--------:------cr--------` |
| 129 | rotate | 128 | 3 | `--------crcrcrcr:--------Cu--cr--:--------cr--cr--:--------cr--cr--:--------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 130 | swap | 53, 129 | 0 | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:cr------cr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 131 | base | — | — | `--CuCuCu--------` |
| 132 | stack | 130, 131 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 133 | base | — | — | `----Cu----------` |
| 134 | stack | 132, 133 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 135 | base | — | — | `----CuCu--------` |
| 136 | stack | 134, 135 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr--CuCucr--cr--:------------cr--:------------cr--:------------cr--` |
| 137 | pin | 136 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:cr--Cu--cr------:cr--CuCucr------` |
| 138 | base | — | — | `--Cu------------` |
| 139 | base | — | — | `--Cu------------` |
| 140 | stack | 138, 139 | — | `--Cu------------:--Cu------------` |
| 141 | stack | 137, 140 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------` |
