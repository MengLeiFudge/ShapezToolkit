# 共同针前缀与交错后缀的并行制造

先制造三层红蓝晶体核心，再一次顶针补齐六列地面针，最后追加交错普通格和针的一层。永久针在全部结晶完成后加入。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`P-P-P-P-P-P-:crCucrCucrCu:CucrCucrCucr:cbCucbCucbCu:CuP-CuP-CuP-`

共10步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为2，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-CuP-CuP-Cu` |
| 1 | base | — | — | `CuP-CuP-CuP-` |
| 2 | stack | 0, 1 | — | `P-CuP-CuP-Cu:CuP-CuP-CuP-` |
| 3 | crystal | 2 | r | `crCucrCucrCu:CucrCucrCucr` |
| 4 | base | — | — | `P-CuP-CuP-Cu` |
| 5 | stack | 3, 4 | — | `crCucrCucrCu:CucrCucrCucr:P-CuP-CuP-Cu` |
| 6 | crystal | 5 | b | `crCucrCucrCu:CucrCucrCucr:cbCucbCucbCu` |
| 7 | pin | 6 | — | `P-P-P-P-P-P-:crCucrCucrCu:CucrCucrCucr:cbCucbCucbCu` |
| 8 | base | — | — | `CuP-CuP-CuP-` |
| 9 | stack | 7, 8 | — | `P-P-P-P-P-P-:crCucrCucrCu:CucrCucrCucr:cbCucbCucbCu:CuP-CuP-CuP-` |
