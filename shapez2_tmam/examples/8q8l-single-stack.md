# 八象限八层的单次复杂堆叠

准备过程使用八层晶体塔，顶破后得到非K下料S。把q1两层普通柱一次堆上去；拆成两次堆叠会让框架重新分组并碎裂。

配置：8象限、8层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------`

共112步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为4，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

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
| 0 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 1 | crystal | 0 | r | `CuCuCucrCuCuCuCu` |
| 2 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 3 | stack | 1, 2 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu` |
| 4 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 5 | stack | 3, 4 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 6 | crystal | 5 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu` |
| 7 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 8 | stack | 6, 7 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 9 | crystal | 8 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 10 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 11 | stack | 9, 10 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 12 | crystal | 11 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 13 | cut | 12 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 14 | rotate | 13 | 5 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 15 | cut | 14 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 16 | rotate | 15 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 17 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 18 | crystal | 17 | r | `CuCuCucrCuCuCuCu` |
| 19 | cut | 18 | 0 | `CuCuCucr--------` |
| 20 | rotate | 19 | 1 | `--CuCuCucr------` |
| 21 | cut | 20 | 1 | `--------cr------` |
| 22 | swap | 16, 21 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 23 | rotate | 22 | 7 | `----crcr--------:----Cu----------:----cr----------:----cr----------:----cr----------` |
| 24 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 25 | crystal | 24 | r | `CuCuCucrCuCuCuCu` |
| 26 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 27 | stack | 25, 26 | — | `CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 28 | crystal | 27 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 29 | cut | 28 | 0 | `CuCuCucr--------:CuCuCucr--------` |
| 30 | rotate | 29 | 1 | `--CuCuCucr------:--CuCuCucr------` |
| 31 | cut | 30 | 1 | `--------cr------:--------cr------` |
| 32 | swap | 23, 31 | 0 | `----crcrcr------:----Cu--cr------:----cr----------:----cr----------:----cr----------` |
| 33 | rotate | 32 | 7 | `--crcrcr--------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 34 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 35 | crystal | 34 | r | `CuCuCucrCuCuCuCu` |
| 36 | cut | 35 | 0 | `CuCuCucr--------` |
| 37 | rotate | 36 | 1 | `--CuCuCucr------` |
| 38 | cut | 37 | 1 | `--------cr------` |
| 39 | swap | 33, 38 | 0 | `--crcrcrcr------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 40 | rotate | 39 | 7 | `crcrcrcr--------:Cu--cr----------:cr--------------:cr--------------:cr--------------` |
| 41 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 42 | crystal | 41 | r | `CuCuCucrCuCuCuCu` |
| 43 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 44 | stack | 42, 43 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu` |
| 45 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 46 | stack | 44, 45 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 47 | crystal | 46 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu` |
| 48 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 49 | stack | 47, 48 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 50 | crystal | 49 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 51 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 52 | stack | 50, 51 | — | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 53 | crystal | 52 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 54 | cut | 53 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 55 | rotate | 54 | 5 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 56 | cut | 55 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 57 | rotate | 56 | 3 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 58 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 59 | crystal | 58 | r | `CuCuCucrCuCuCuCu` |
| 60 | cut | 59 | 0 | `CuCuCucr--------` |
| 61 | rotate | 60 | 1 | `--CuCuCucr------` |
| 62 | cut | 61 | 1 | `--------cr------` |
| 63 | swap | 57, 62 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 64 | rotate | 63 | 7 | `----crcr--------:----Cu----------:----cr----------:----cr----------:----cr----------` |
| 65 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 66 | crystal | 65 | r | `CuCuCucrCuCuCuCu` |
| 67 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 68 | stack | 66, 67 | — | `CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 69 | crystal | 68 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 70 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 71 | stack | 69, 70 | — | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 72 | crystal | 71 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 73 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 74 | stack | 72, 73 | — | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 75 | crystal | 74 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 76 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 77 | stack | 75, 76 | — | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 78 | crystal | 77 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 79 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 80 | stack | 78, 79 | — | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 81 | crystal | 80 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 82 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 83 | stack | 81, 82 | — | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 84 | crystal | 83 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 85 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 86 | stack | 84, 85 | — | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 87 | crystal | 86 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 88 | cut | 87 | 0 | `CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 89 | rotate | 88 | 1 | `--CuCuCucr------:--CuCuCucr------:--CuCuCucr------:--CuCuCucr------:--CuCuCucr------:--CuCuCucr------:--CuCuCucr------:--CuCuCucr------` |
| 90 | cut | 89 | 1 | `--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------:--------cr------` |
| 91 | swap | 64, 90 | 0 | `----crcrcr------:----Cu--cr------:----cr--cr------:----cr--cr------:----cr--cr------:--------cr------:--------cr------:--------cr------` |
| 92 | rotate | 91 | 7 | `--crcrcr--------:--Cu--cr--------:--cr--cr--------:--cr--cr--------:--cr--cr--------:------cr--------:------cr--------:------cr--------` |
| 93 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 94 | crystal | 93 | r | `CuCuCucrCuCuCuCu` |
| 95 | cut | 94 | 0 | `CuCuCucr--------` |
| 96 | rotate | 95 | 1 | `--CuCuCucr------` |
| 97 | cut | 96 | 1 | `--------cr------` |
| 98 | swap | 92, 97 | 0 | `--crcrcrcr------:--Cu--cr--------:--cr--cr--------:--cr--cr--------:--cr--cr--------:------cr--------:------cr--------:------cr--------` |
| 99 | rotate | 98 | 3 | `--------crcrcrcr:--------Cu--cr--:--------cr--cr--:--------cr--cr--:--------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 100 | swap | 40, 99 | 0 | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:cr------cr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 101 | base | — | — | `--CuCuCu--------` |
| 102 | stack | 100, 101 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 103 | base | — | — | `----Cu----------` |
| 104 | stack | 102, 103 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 105 | base | — | — | `----CuCu--------` |
| 106 | stack | 104, 105 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr--CuCucr--cr--:------------cr--:------------cr--:------------cr--` |
| 107 | pin | 106 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:cr--Cu--cr------:cr--CuCucr------` |
| 108 | base | — | — | `--Cu------------` |
| 109 | base | — | — | `--Cu------------` |
| 110 | stack | 108, 109 | — | `--Cu------------:--Cu------------` |
| 111 | stack | 107, 110 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------` |
