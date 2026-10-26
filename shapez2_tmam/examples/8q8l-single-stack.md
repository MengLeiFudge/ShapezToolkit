# 八象限八层的单次复杂堆叠

准备过程使用八层晶体塔，顶破后得到非K下料S。把q1两层普通柱一次堆上去；拆成两次堆叠会让框架重新分组并碎裂。

配置：8象限、8层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------`

共98步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
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
| 1 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 2 | stack | 0, 1 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu` |
| 3 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 4 | stack | 2, 3 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu` |
| 5 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 6 | stack | 4, 5 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu:CuCuCuP-CuCuCuCu` |
| 7 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 8 | stack | 6, 7 | — | `CuCuCuP-CuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCuP-CuCuCuCu:CuCuCuP-CuCuCuCu:CuCuCuP-CuCuCuCu` |
| 9 | crystal | 8 | r | `CuCuCucrCuCuCuCu:CuCuCuCuCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 10 | cut | 9 | 0 | `CuCuCucr--------:CuCuCuCu--------:CuCuCucr--------:CuCuCucr--------:CuCuCucr--------` |
| 11 | rotate | 10 | 1 | `--CuCuCucr------:--CuCuCuCu------:--CuCuCucr------:--CuCuCucr------:--CuCuCucr------` |
| 12 | cut | 11 | 1 | `--------cr------:--------Cu------:--------cr------:--------cr------:--------cr------` |
| 13 | rotate | 12 | 7 | `------cr--------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 14 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 15 | crystal | 14 | r | `CuCuCucrCuCuCuCu` |
| 16 | cut | 15 | 0 | `CuCuCucr--------` |
| 17 | rotate | 16 | 1 | `--CuCuCucr------` |
| 18 | cut | 17 | 1 | `--------cr------` |
| 19 | swap | 13, 18 | 0 | `------crcr------:------Cu--------:------cr--------:------cr--------:------cr--------` |
| 20 | rotate | 19 | 7 | `----crcr--------:----Cu----------:----cr----------:----cr----------:----cr----------` |
| 21 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 22 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 23 | stack | 21, 22 | — | `CuCuCuP-CuCuCuCu:CuCuCuP-CuCuCuCu` |
| 24 | crystal | 23 | r | `CuCuCucrCuCuCuCu:CuCuCucrCuCuCuCu` |
| 25 | cut | 24 | 0 | `CuCuCucr--------:CuCuCucr--------` |
| 26 | rotate | 25 | 1 | `--CuCuCucr------:--CuCuCucr------` |
| 27 | cut | 26 | 1 | `--------cr------:--------cr------` |
| 28 | swap | 20, 27 | 0 | `----crcrcr------:----Cu--cr------:----cr----------:----cr----------:----cr----------` |
| 29 | rotate | 28 | 7 | `--crcrcr--------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 30 | base | — | — | `CuCuCuP-CuCuCuCu` |
| 31 | crystal | 30 | r | `CuCuCucrCuCuCuCu` |
| 32 | cut | 31 | 0 | `CuCuCucr--------` |
| 33 | rotate | 32 | 1 | `--CuCuCucr------` |
| 34 | cut | 33 | 1 | `--------cr------` |
| 35 | swap | 29, 34 | 0 | `--crcrcrcr------:--Cu--cr--------:--cr------------:--cr------------:--cr------------` |
| 36 | rotate | 35 | 7 | `crcrcrcr--------:Cu--cr----------:cr--------------:cr--------------:cr--------------` |
| 37 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 38 | base | — | — | `CuCuCuCuCuCuCuCu` |
| 39 | stack | 37, 38 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu` |
| 40 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 41 | stack | 39, 40 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCuP-` |
| 42 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 43 | stack | 41, 42 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 44 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 45 | stack | 43, 44 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 46 | crystal | 45 | r | `CuCuCuCuCuCuCucr:CuCuCuCuCuCuCuCu:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr` |
| 47 | cut | 46 | 1 | `--------CuCuCucr:--------CuCuCuCu:--------CuCuCucr:--------CuCuCucr:--------CuCuCucr` |
| 48 | rotate | 47 | 1 | `cr--------CuCuCu:Cu--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 49 | cut | 48 | 0 | `cr--------------:Cu--------------:cr--------------:cr--------------:cr--------------` |
| 50 | rotate | 49 | 7 | `--------------cr:--------------Cu:--------------cr:--------------cr:--------------cr` |
| 51 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 52 | crystal | 51 | r | `CuCuCuCuCuCuCucr` |
| 53 | cut | 52 | 1 | `--------CuCuCucr` |
| 54 | rotate | 53 | 1 | `cr--------CuCuCu` |
| 55 | cut | 54 | 0 | `cr--------------` |
| 56 | swap | 50, 55 | 1 | `cr------------cr:--------------Cu:--------------cr:--------------cr:--------------cr` |
| 57 | rotate | 56 | 7 | `------------crcr:------------Cu--:------------cr--:------------cr--:------------cr--` |
| 58 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 59 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 60 | stack | 58, 59 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 61 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 62 | stack | 60, 61 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 63 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 64 | stack | 62, 63 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 65 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 66 | stack | 64, 65 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 67 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 68 | stack | 66, 67 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 69 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 70 | stack | 68, 69 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 71 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 72 | stack | 70, 71 | — | `CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-:CuCuCuCuCuCuCuP-` |
| 73 | crystal | 72 | r | `CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr:CuCuCuCuCuCuCucr` |
| 74 | cut | 73 | 1 | `--------CuCuCucr:--------CuCuCucr:--------CuCuCucr:--------CuCuCucr:--------CuCuCucr:--------CuCuCucr:--------CuCuCucr:--------CuCuCucr` |
| 75 | rotate | 74 | 1 | `cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu:cr--------CuCuCu` |
| 76 | cut | 75 | 0 | `cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------:cr--------------` |
| 77 | swap | 57, 76 | 1 | `cr----------crcr:cr----------Cu--:cr----------cr--:cr----------cr--:cr----------cr--:cr--------------:cr--------------:cr--------------` |
| 78 | rotate | 77 | 7 | `----------crcrcr:----------Cu--cr:----------cr--cr:----------cr--cr:----------cr--cr:--------------cr:--------------cr:--------------cr` |
| 79 | base | — | — | `CuCuCuCuCuCuCuP-` |
| 80 | crystal | 79 | r | `CuCuCuCuCuCuCucr` |
| 81 | cut | 80 | 1 | `--------CuCuCucr` |
| 82 | rotate | 81 | 1 | `cr--------CuCuCu` |
| 83 | cut | 82 | 0 | `cr--------------` |
| 84 | swap | 78, 83 | 1 | `cr--------crcrcr:----------Cu--cr:----------cr--cr:----------cr--cr:----------cr--cr:--------------cr:--------------cr:--------------cr` |
| 85 | rotate | 84 | 7 | `--------crcrcrcr:--------Cu--cr--:--------cr--cr--:--------cr--cr--:--------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 86 | swap | 36, 85 | 0 | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:cr------cr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 87 | base | — | — | `--CuCuCu--------` |
| 88 | stack | 86, 87 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr------cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 89 | base | — | — | `----Cu----------` |
| 90 | stack | 88, 89 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr------cr--cr--:------------cr--:------------cr--:------------cr--` |
| 91 | base | — | — | `----CuCu--------` |
| 92 | stack | 90, 91 | — | `crcrcrcrcrcrcrcr:Cu--cr--Cu--cr--:crCuCuCucr--cr--:cr--Cu--cr--cr--:cr--CuCucr--cr--:------------cr--:------------cr--:------------cr--` |
| 93 | pin | 92 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:cr--Cu--cr------:cr--CuCucr------` |
| 94 | base | — | — | `--Cu------------` |
| 95 | base | — | — | `--Cu------------` |
| 96 | stack | 94, 95 | — | `--Cu------------:--Cu------------` |
| 97 | stack | 93, 96 | — | `P-P-P-P-P-P-P-P-:Cu------Cu------:----------------:crCuCuCucr------:crCuCu--cr------:crCuCuCucr------` |
