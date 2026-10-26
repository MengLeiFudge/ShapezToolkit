# 两象限的连续前缀与上方跨列支撑

最高晶体以下先造两根连续柱；再用双普通格跨过较短列的空隙，最后补针。最高晶体上方允许这种间隙。

配置：2象限、6层上限。

目标（从底到顶，q0为每层最左格）：

`P-Cu:crP-:CuCu:cr--:CuCu:--P-`

共18步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为3，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 最高晶体以下前缀 | `P-Cu:crP-:CuCu:cr--` |
| 跨列普通上层 | `P-Cu:crP-:CuCu:cr--:CuCu` |
| 补针后的目标 | `P-Cu:crP-:CuCu:cr--:CuCu:--P-` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `P-Cu` |
| 1 | crystal | 0 | r | `crCu` |
| 2 | base | — | — | `CuCu` |
| 3 | stack | 1, 2 | — | `crCu:CuCu` |
| 4 | base | — | — | `P-Cu` |
| 5 | stack | 3, 4 | — | `crCu:CuCu:P-Cu` |
| 6 | crystal | 5 | r | `crCu:CuCu:crCu` |
| 7 | cut | 6 | 0 | `cr--:Cu--:cr--` |
| 8 | pin | 7 | — | `P---:cr--:Cu--:cr--` |
| 9 | base | — | — | `--Cu` |
| 10 | base | — | — | `--Cu` |
| 11 | pin | 10 | — | `--P-:--Cu` |
| 12 | stack | 9, 11 | — | `--Cu:--P-:--Cu` |
| 13 | swap | 8, 12 | 0 | `P-Cu:crP-:CuCu:cr--` |
| 14 | base | — | — | `CuCu` |
| 15 | stack | 13, 14 | — | `P-Cu:crP-:CuCu:cr--:CuCu` |
| 16 | base | — | — | `--P-` |
| 17 | stack | 15, 16 | — | `P-Cu:crP-:CuCu:cr--:CuCu:--P-` |
