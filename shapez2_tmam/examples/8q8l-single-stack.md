# 八象限八层的单次复杂堆叠

准备过程使用八层晶体塔，顶破后得到非K下料S。把q1两层普通柱一次堆上去；拆成两次堆叠会让框架重新分组并碎裂。

配置：8象限、8层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------`

共125步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
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
| 15 | rotate | 14 | 5 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 16 | cut | 15 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 17 | rotate | 16 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 18 | base | — | — | `CuP-CuCuCuCuCuCu` |
| 19 | crystal | 18 | r | `CucrCuCuCuCuCuCu` |
| 20 | rotate | 19 | 2 | `CuCuCucrCuCuCuCu` |
| 21 | cut | 20 | 0 | `CuCuCucr--------` |
| 22 | rotate | 21 | 5 | `cr--------CuCuCu` |
| 23 | cut | 22 | 0 | `cr--------------` |
| 24 | rotate | 23 | 4 | `--------cr------` |
| 25 | swap | 17, 24 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 26 | rotate | 25 | 7 | `----crcr--------:----Cu----------:----cr----------:----cr----------:----cr----------` |
| 27 | base | — | — | `CuCuP-CuCuCuCuCu` |
| 28 | crystal | 27 | r | `CuCucrCuCuCuCuCu` |
| 29 | base | — | — | `CuCuP-CuCuCuCuCu` |
| 30 | stack | 28, 29 | — | `CuCucrCuCuCuCuCu:CuCuP-CuCuCuCuCu` |
| 31 | crystal | 30 | r | `CuCucrCuCuCuCuCu:CuCucrCuCuCuCuCu` |
| 32 | rotate | 31 | 1 | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 33 | cut | 32 | 0 | `CuCuCucr--------:CuCuCucr--------` |
| 34 | rotate | 33 | 5 | `cr--------CuCuCu:cr--------CuCuCu` |
| 35 | cut | 34 | 0 | `cr--------------:cr--------------` |
| 36 | rotate | 35 | 4 | `--------cr------:--------cr------` |
| 37 | swap | 26, 36 | 0 | `----crcrcr------:----Cu--cr------:----cr----------:----cr----------:----cr----------` |
| 38 | rotate | 37 | 7 | `--crcrcr--------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 39 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 40 | crystal | 39 | r | `CuCuCucrCuCuCuCu` |
| 41 | cut | 40 | 0 | `CuCuCucr--------` |
| 42 | rotate | 41 | 5 | `cr--------CuCuCu` |
| 43 | cut | 42 | 0 | `cr--------------` |
| 44 | rotate | 43 | 4 | `--------cr------` |
| 45 | swap | 38, 44 | 0 | `--crcrcrcr------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 46 | rotate | 45 | 7 | `crcrcrcr--------:Cu--cr----------:cr--------------:cr--------------:cr--------------` |
| 47 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 48 | crystal | 47 | r | `CuCuCuCucrCuCuCu` |
| 49 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 50 | stack | 48, 49 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu` |
| 51 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 52 | stack | 50, 51 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCuP-CuCuCu` |
| 53 | crystal | 52 | r | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu` |
| 54 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 55 | stack | 53, 54 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCuP-CuCuCu` |
| 56 | crystal | 55 | r | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu` |
| 57 | base | — | — | `CuCuCuCuP-CuCuCu` |
| 58 | stack | 56, 57 | — | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCuP-CuCuCu` |
| 59 | crystal | 58 | r | `CuCuCuCucrCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu:CuCuCuCucrCuCuCu` |
| 60 | rotate | 59 | 7 | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 61 | cut | 60 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 62 | rotate | 61 | 5 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 63 | cut | 62 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 64 | rotate | 63 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 65 | base | — | — | `CuCuCuCuCuP-CuCu` |
| 66 | crystal | 65 | r | `CuCuCuCuCucrCuCu` |
| 67 | rotate | 66 | 6 | `CuCuCucrCuCuCuCu` |
| 68 | cut | 67 | 0 | `CuCuCucr--------` |
| 69 | rotate | 68 | 5 | `cr--------CuCuCu` |
| 70 | cut | 69 | 0 | `cr--------------` |
| 71 | rotate | 70 | 4 | `--------cr------` |
| 72 | swap | 64, 71 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 73 | rotate | 72 | 7 | `----crcr--------:----Cu----------:----cr----------:----cr----------:----cr----------` |
| 74 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 75 | crystal | 74 | r | `CuCuCuCuCuCucrCu` |
| 76 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 77 | stack | 75, 76 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 78 | crystal | 77 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 79 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 80 | stack | 78, 79 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 81 | crystal | 80 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 82 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 83 | stack | 81, 82 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 84 | crystal | 83 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 85 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 86 | stack | 84, 85 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 87 | crystal | 86 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 88 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 89 | stack | 87, 88 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 90 | crystal | 89 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 91 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 92 | stack | 90, 91 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 93 | crystal | 92 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 94 | base | — | — | `CuCuCuCuCuCuP-Cu` |
| 95 | stack | 93, 94 | — | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCuP-Cu` |
| 96 | crystal | 95 | r | `CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu:CuCuCuCuCuCucrCu` |
| 97 | rotate | 96 | 5 | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 98 | cut | 97 | 0 | `CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 99 | rotate | 98 | 5 | `cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 100 | cut | 99 | 0 | `cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------` |
| 101 | rotate | 100 | 4 | `--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------` |
| 102 | swap | 73, 101 | 0 | `----crcrcr------:----Cu--cr------:----cr--cr------:----cr--cr------:----cr--cr------:--------cr------:--------cr------:--------cr------` |
| 103 | rotate | 102 | 7 | `--crcrcr--------:--Cu--cr--------:--cr--cr--------:--cr--cr--------:--cr--cr--------:------cr--------:------cr--------:------cr--------` |
| 104 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 105 | crystal | 104 | r | `CuCuCuCuCuCuCucr` |
| 106 | rotate | 105 | 4 | `CuCuCucrCuCuCuCu` |
| 107 | cut | 106 | 0 | `CuCuCucr--------` |
| 108 | rotate | 107 | 5 | `cr--------CuCuCu` |
| 109 | cut | 108 | 0 | `cr--------------` |
| 110 | rotate | 109 | 4 | `--------cr------` |
| 111 | swap | 103, 110 | 0 | `--crcrcrcr------:--Cu--cr--------:--cr--cr--------:--cr--cr--------:--cr--cr--------:------cr--------:------cr--------:------cr--------` |
| 112 | rotate | 111 | 3 | `--------crcrcrcr:--------Cu--cr--:--------cr--cr--:--------cr--cr--:--------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 113 | swap | 46, 112 | 0 | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:cr------cr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 114 | base | — | — | `--CuCuCu--------` |
| 115 | stack | 113, 114 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 116 | base | — | — | `----Cu----------` |
| 117 | stack | 115, 116 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 118 | base | — | — | `----CuCu--------` |
| 119 | stack | 117, 118 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr--CuCucr--cr--:------------cr--:------------cr--:------------cr--` |
| 120 | pin | 119 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:cr--Cu--cr------:cr--CuCucr------` |
| 121 | base | — | — | `--Cu------------` |
| 122 | base | — | — | `--Cu------------` |
| 123 | stack | 121, 122 | — | `--Cu------------:--Cu------------` |
| 124 | stack | 120, 123 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------` |
