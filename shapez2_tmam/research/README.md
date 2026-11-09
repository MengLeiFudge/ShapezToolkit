# TMAM 研究汇编

这里是 Shapez 2 TMAM 理论、构造和电路资料的统一入口。正文按论文顺序阅读，参考卷保留完整证明。

## 先看这三份

1. [论文式正文](TMAM研究.md)：定义、主定理、代表构造、强制工序边界和工程状态。
2. [演示文稿](TMAM研究.pptx)：43 页、16:9、格子图和表格均为可编辑对象；PowerPoint 备注包含证明要点与来源。
3. [同版 PDF](TMAM研究.pdf)：适合连续阅读和打印；[43 页总览图](overview.png)可用于快速定位章节。

演示与 PDF 均由 [slides.json](slides.json) 和 [build_presentation.py](build_presentation.py) 生成。修改讲稿时先改 `slides.json`，再运行：

```bash
PYTHONPATH=/tmp/tmam-presentation-deps python shapez2_tmam/research/build_presentation.py
```

依赖为 `python-pptx 1.0.2`、`reportlab 5.1.0`；示例路径是本机隔离安装目录。其他环境可安装到自己的 Python 环境后直接运行。中文字体默认读取 Windows 微软雅黑；可用 `--font`、`--bold-font` 指定支持中文的 TrueType 字体。该命令只排版文档。

## 结论导航

| 范围 | 当前结论 | 入口 |
|---|---|---|
| 4 象限 5 层 | 完整有限合成与覆盖证明；整图按零尾 Pin / 必须尾 Pin 两类共用主程序 | [论文第 4 节](TMAM研究.md#4-四象限五层完整覆盖定理) |
| 6 象限 5 层 | 保留真实操作输出的精确有限闭包完备；`4^30−1` 是状态上界，不是实用电路 | [论文第 5 节](TMAM研究.md#5-六象限五层完备但不实用的基线) |
| 4 象限任意高度 | `R⊆K`、完整 S 列与半形判据、零尾 Pin 来源闭包已证；程序接入仍未完成 | [论文第 6 节](TMAM研究.md#6-一般偶数象限与任意高度) |
| 偶数象限任意高度 | 列级构造、级联族、若干强制词族已证；任意指定交替序列仍未证明或证伪 | [论文第 7 节](TMAM研究.md#7-已证的强制工序与原命题边界) |

## 九卷参考证明

参考卷是按主题合并的完整正文。每个原文件的标题、原始路径、SHA-256 和章节锚点都记录在 [sources.json](sources.json)；正文中的 `sXX-YY` 锚点用于从旧引用定位到合并卷。

1. [模型、不变量与物理闭包](proofs/01-foundations.md)
2. [四象限的完整合成与来源判定](proofs/02-four-quadrants.md)
3. [六象限与一般偶数象限构造](proofs/03-general-construction.md)
4. [堆叠约化与上料构造](proofs/04-stacking.md)
5. [重复下落与空间构造](proofs/05-cascades.md)
6. [全局强制工序与精确下界](proofs/06-forced-words.md)
7. [顶破约化与候选排除](proofs/07-reductions.md)
8. [时序电路、程序与实现记录](proofs/08-circuits.md)
9. [Mari 与外部研究记录](proofs/09-sources.md)

## 收拢策略

134 篇专题已合并为 9 卷，原专题从工作目录移入本机 `.codex/trash/tmam-paper/` 归档；Git 历史也保留迁移前全文。现有 Markdown 链接已经指向新卷及对应章节。蓝图内的旧 `proof` 字符串作为历史来源标识保留，可由 `sources.json` 解析。

后续完整证明直接维护参考卷；论文正文负责连贯论述，`slides.json` 负责演示要点与讲者备注。修改结论时同步对应摘要，不再恢复零散专题副本。`sources.json` 中 SHA-256 标识迁移前原件，不是后续编辑后的卷校验值。

## 证据边界

本文档和参考卷使用源码静态核对与人工证明。网表数字来自已有静态报告。未运行游戏、Mod、物理模拟、全量状态枚举、浏览器或测试；因此“理论完备”“静态电路规模”和“游戏内验收”保持分开。
