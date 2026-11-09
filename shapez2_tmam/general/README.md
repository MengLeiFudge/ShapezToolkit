# 偶数象限与任意高度

先读[研究 PPT](../research/TMAM研究.pptx)第 14–32 页及[论文第 6–7 节](../research/TMAM研究.md#6-一般偶数象限与任意高度)。`n` 只取偶数，`H` 限制整个准备和制造过程；旋转粒度、半切规则和单次重力顺序必须随模型明确。

## 按证明主线阅读

| 主线 | 入口 | 边界 |
|---|---|---|
| 物理与支撑 | [卷 01](../research/proofs/01-foundations.md) | 通用 Q/J；四象限任意 H 的 `R⊆K`；更宽图形可非 K、可不稳定 |
| 四象限列与半形 | [完整 S 列构造](../research/proofs/02-four-quadrants.md#s02-11)、[零尾 Pin 闭包](../research/proofs/02-four-quadrants.md#s02-14) | 理论已闭合；完整构造及全高度闭包尚未接入 Python |
| 一般列与脚手架 | [卷 03](../research/proofs/03-general-construction.md) | n≥6 的列条件 A 充要；局部构造不等于全图紧凑分解 |
| 堆叠与上料 | [卷 04](../research/proofs/04-stacking.md) | 安全范围、来源摘要和实体制造证书必须同时保留 |
| 重复下落 | [卷 05](../research/proofs/05-cascades.md) | 固定八象限可需任意有限 k 轮；最小偶数宽度仍在 6 与 8 之间 |
| 强制工序 | [卷 06](../research/proofs/06-forced-words.md) | PS^k、PS^kP、T₂/T₃、PPP 和次数谱；一般指定序列仍开放 |
| 反例与约化 | [卷 07](../research/proofs/07-reductions.md) | 区分固定来源下界、全局最小性及条件重排 |

## 最终命题

给定任意有限正整数序列 `(a1,b1,a2,b2,...)`，能否选择偶数 `n`、共同 `H` 和目标 T，使所有合法最后 Swap 来源都无法绕过指定的 Pin/单层 Stack 阶段？

[主命题与量词](../research/proofs/06-forced-words.md#s06-01)仍未证明或证伪。四象限的[PSPSPS 重排反证](../research/proofs/06-forced-words.md#s06-11)只否定强阶段版本，且可能增加一次 Stack；不能外推到可变偶数宽度，也不能据此否定最短总步数版本。

局部时钟、三座塔或指定来源的成功路线不足以证明全局强制。尚缺多个支撑交接的全来源串接论证，以及排除改换切向、提前上料和窗口合并的方法。

## 实现与来源

[Python 模型](../synthesis/README.md)支持明确参数下的局部操作与制造证书。[具体例子](../examples/README.md)保留短代码和逐步产物。[外部资料核对](../research/proofs/09-sources.md)区分已吸收的列构造、局部公式与仍缺全文的上界主张。

游戏源码入口为 `D:\project\shapez\DecompiledSource\Game.Content.Features` 的 `ShapeLogic` 与 `ShapeOperationStack/PushPin/SwapHalves/Rotate`；来源指纹见[卷 01](../research/proofs/01-foundations.md#s01-09-h18)。具体 Mod 仍须核对操作规则，不能只替换 n/H。

后续证明直接更新对应参考卷，稳定章节锚点保持不变；[来源映射](../research/sources.json)保留旧文件定位。摘要、PPT 与工程状态分别同步。

[研究总入口](../research/README.md) · [返回总目录](../README.md)
