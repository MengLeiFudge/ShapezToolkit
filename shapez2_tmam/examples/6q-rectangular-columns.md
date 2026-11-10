# 同层同色晶体的六列并行制造

前两层交错位置先用针占位，再统一红色结晶；第三层单独蓝色结晶，已有晶体颜色保持。完整六列逐层制造，无需切割、交换或旋转。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`crCucrCucrCu:CucrCucrCucr:cbCucbCucbCu`

共7步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为2，不含搜索状态及传输缓存；[槽数调度证明](../proofs/04-stacking.md#s04-19)。
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
