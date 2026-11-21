# 二代 TMAM 理论与证明文档库

本目录按职责清晰划分为范围导览、理论论文 Markdown 源码、编译后的学术版 PDF、九卷完整参考证明及配图资料。

## 按范围导览（跨理论与工程入口）

- [4 象限 5 层（4q5l）](4q5l.md)：完整有限合成、Mari 对照、Python 模型与原生四帧电路蓝图入口。
- [6 象限 5 层（6q5l）](6q5l.md)：精确有限闭包、不稳定交换输出、三列脚手架与六槽回放器边界。
- [偶数象限与任意高度（general）](general.md)：一般偶数宽度构造、级联下落族、强制工序词参数族、落地容量下界与开放主命题。

## 子目录分工

| 子目录 | 内容 |
|---|---|
| [papers/](papers/README.md) | 研究汇编与结论导航、六篇 A4 学术版论文 PDF 及编译器 [build_paper_pdf.py](papers/build_paper_pdf.py) |
| [theory/](theory/README.md) | 六篇理论论文的 Markdown 源码（纯理论定义、构造与证明）及**论文编写与 PDF 编译规范** |
| [proofs/](proofs/README.md) | 按主题收拢的九卷完整参考证明（含电路与外部资料卷）及 134 篇原专题映射 [sources.json](proofs/sources.json) |
| `assets/` | 证明与示例引用的示意图（SVG / PNG）及长短代码文本 |

主线阅读建议从 [研究汇编与结论导航](papers/README.md) 开始；工程实现与蓝图资料返回 [二代 TMAM 总目录](../README.md)。
