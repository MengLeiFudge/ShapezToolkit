# 6 象限 5 层

整体脉络见[研究 PPT](../research/TMAM研究.pptx)第 10–11 页及[论文第 5 节](../research/TMAM研究.md#5-六象限五层完备但不实用的基线)。模型采用相邻三列半切、单象限旋转、共同高度上限 5。

## 阅读路径

1. [三列无针环与不稳定交换输出](../research/proofs/03-general-construction.md#s03-02)：两份可制造半形拼接后可失稳，算法必须保留该原始输出。
2. [精确有限闭包](../research/proofs/03-general-construction.md#s03-01)：种子、双输入操作、制造证书和完整覆盖；原始结构上界为 `4^30−1`，未执行全量目录。
3. [三列释放](../research/proofs/03-general-construction.md#s03-03)及[递归外侧脚手架](../research/proofs/03-general-construction.md#s03-04)：共用局部制造流程，全部半形的紧凑覆盖仍缺。
4. [六象限低层来源改写](../research/proofs/07-reductions.md#s07-08)：五层目标不能强制三次深层晶体顶破；不等于 Pin 总数至多两次。

## 实现边界

[Python 合成模块](../synthesis/README.md)保留精确物理输出、来源凭据和局部制造证书。[六槽时序回放器](../research/proofs/08-circuits.md#s08-01)可以执行配方；它不包含完整六象限求解器。代表 H/V 的完整制造步骤见[例子目录](../examples/README.md)。

K 与稳定性都不能用于过滤全部可制作状态。堆叠约化仅在[卷 04](../research/proofs/04-stacking.md)给出的明确条件下成立；未覆盖状态保留真实双输入 Stack。完整有限覆盖不提供实用复杂度或游戏验收保证。

[研究总入口](../research/README.md) · [返回总目录](../README.md)
