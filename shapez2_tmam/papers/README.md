# TMAM 研究汇编

这里是 Shapez 2 TMAM 理论、构造和电路资料的统一入口。正文按论文顺序阅读，参考卷保留完整证明。

## 理论论文

四篇论文均为 A4 连续排版，正文包含定理、构造、证明和适用边界；不混入 Python、电路、蓝图、建筑数量或外部资料。

1. [理论 I：模型、物理结算与列内不变量](TMAM理论I-模型与不变量.pdf)
2. [理论 II：四象限五层的完整合成](TMAM理论II-四象限五层合成.pdf)
3. [理论 III：一般偶数象限的列构造与循环支撑](TMAM理论III-一般偶数象限构造.pdf)
4. [理论 IV：重复下落与强制工序](TMAM理论IV-级联与强制工序.pdf)

论文正文源文件位于 [theory/](../theory/)；使用 [build_paper_pdf.py](build_paper_pdf.py) 重新排版单篇：

```bash
PYTHONPATH=/tmp/tmam-presentation-deps python shapez2_tmam/papers/build_paper_pdf.py --source shapez2_tmam/theory/02-four-quadrants.md --output shapez2_tmam/papers/TMAM理论II-四象限五层合成.pdf
```

依赖为 `reportlab 5.1.0`；中文字体默认读取 Windows 微软雅黑。该命令只排版理论正文。

## 结论导航

| 范围 | 当前结论 | 入口 |
|---|---|---|
| 4 象限 5 层 | 完整有限合成与覆盖证明；整图按零尾 Pin / 必须尾 Pin 两类共用主程序 | [论文第 4 节](TMAM理论II-四象限五层合成.pdf) |
| 6 象限 5 层 | 保留真实操作输出的精确有限闭包完备；`4^30−1` 是状态上界，不是实用电路 | [论文第 5 节](TMAM理论III-一般偶数象限构造.pdf) |
| 4 象限任意高度 | `R⊆K`、完整 S 列与半形判据、零尾 Pin 来源闭包已证；程序接入仍未完成 | [论文第 6 节](TMAM理论III-一般偶数象限构造.pdf) |
| 偶数象限任意高度 | 列级构造、级联族、若干强制词族已证；任意指定交替序列仍未证明或证伪 | [论文第 7 节](TMAM理论IV-级联与强制工序.pdf) |

## 九卷参考证明

参考卷是按主题合并的完整正文。每个原文件的标题、原始路径、SHA-256 和章节锚点都记录在 [sources.json](../proofs/sources.json)；正文中的 `sXX-YY` 锚点用于从旧引用定位到合并卷。

1. [模型、不变量与物理闭包](../proofs/01-foundations.md)
2. [四象限的完整合成与来源判定](../proofs/02-four-quadrants.md)
3. [六象限与一般偶数象限构造](../proofs/03-general-construction.md)
4. [堆叠约化与上料构造](../proofs/04-stacking.md)
5. [重复下落与空间构造](../proofs/05-cascades.md)
6. [全局强制工序与精确下界](../proofs/06-forced-words.md)
7. [顶破约化与候选排除](../proofs/07-reductions.md)
8. [时序电路、程序与实现记录](../proofs/08-circuits.md)
9. [Mari 与外部研究记录](../proofs/09-sources.md)

## 收拢策略

134 篇专题已合并为 9 卷，原专题从工作目录移入本机 `.codex/trash/tmam-paper/` 归档；Git 历史也保留迁移前全文。四篇理论论文从这些证明中按定理依赖拆出。现有 Markdown 链接已经指向新卷及对应章节。蓝图内的旧 `proof` 字符串作为历史来源标识保留，可由 `sources.json` 解析。

后续完整证明直接维护参考卷；论文正文负责连贯论述，`build_paper_pdf.py` 负责从正文重新排版。修改结论时同步正文和对应参考卷，不再恢复零散专题副本。

## 证据边界

本文档和参考卷使用源码静态核对与人工证明。网表数字来自已有静态报告。未运行游戏、Mod、物理模拟、全量状态枚举、浏览器或测试；因此“理论完备”“静态电路规模”和“游戏内验收”保持分开。
