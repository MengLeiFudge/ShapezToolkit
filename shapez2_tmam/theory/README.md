# TMAM 理论论文

这里保存四篇理论论文及附录的正文；对应 PDF 位于 `../papers/`。内容按理论依赖拆分，不包含 Python、电路、蓝图、建筑数量或走线。

| 论文 | 正文 | PDF | 内容 |
|---|---|---|---|
| I | [模型、物理结算与列内不变量](01-model-and-invariants.md) | [PDF](../papers/TMAM理论I-模型与不变量.pdf) | 操作模型、一次结算、支撑、Q/J、不变量 |
| II | [四象限五层的完整合成](02-four-quadrants.md) | [PDF](../papers/TMAM理论II-四象限五层合成.pdf) | 半形闭包、顶针逆像、堆叠约化、完整覆盖 |
| III | [一般偶数象限的列构造与循环支撑](03-even-constructions.md) | [PDF](../papers/TMAM理论III-一般偶数象限构造.pdf) | 列充要条件、三列释放、脚手架、非 K 半形 |
| IV | [重复下落与强制工序](04-cascades-and-forced-words.md) | [PDF](../papers/TMAM理论IV-级联与强制工序.pdf) | 级联族、强制词、全局下界、未决命题 |
| IV-A | [交替工序约化](04-appendix-forced-sequence.md) | [PDF](../papers/TMAM理论IV附录-交替工序约化.pdf) | 四象限八次 Pin 上界、三列结算稳定性、六象限首步与跨半条件 |

## 阅读方法

I 是公用基础。II 解决四象限五层，III 研究参数化偶数象限，IV 研究重复结算和全局操作顺序。IV 附录研究工序约化，完整证明对应参考卷 06 的[地面占用界](../proofs/06-forced-words.md#s06-12)与[三列稳定性及首步跨半条件](../proofs/06-forced-words.md#s06-13)。其余正文保留所选原证明章节及原始来源路径，便于回到参考卷核对。

“未决”只表示论文中明确没有证明或证伪的命题，不等于缺少已给出的构造族或局部下界。
