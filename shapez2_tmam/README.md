# 二代 TMAM：理论、实现与资料

先看[四篇理论论文](papers/README.md#理论论文)。总入口见[理论论文集索引](papers/README.md)；完整证明收拢为[九卷参考资料](papers/README.md#九卷参考证明)。[理论正文](papers/README.md)按“模型 → 覆盖 → 构造 → 下界”组织；实现资料和九卷完整证明分别从该入口进入。

## 按范围阅读

| 范围 | 入口 | 已有结果与边界 |
|---|---|---|
| 4 象限 5 层 | [4q5l](papers/4q5l.md) | 完整有限合成；统一双半形起点及有界 Pin/追加循环；游戏实用性尚未验收 |
| 6 象限 5 层 | [6q5l](papers/6q5l.md) | 精确有限闭包完备；紧凑全域求解及完整电路仍缺 |
| 偶数象限、任意高度 | [general](papers/general.md) | 四象限完整列与半形判据、重复下落族和强制词族；任意指定交替序列仍开放 |

目录名中 `q` 表示象限数，`l` 表示全过程的层数上限。基础输入为任意无晶体单层；每个定理还须满足对应参考卷的操作前提。理论覆盖、实用复杂度和具体存档验收分别记录。

## 目录结构

- `theory/`：理论论文及附录的 Markdown 正文。
- `papers/`：论文 PDF、范围入口和 PDF 生成器。
- `proofs/`：九卷完整证明与来源映射。
- `synthesis/`：Python 合成模型和制造证书。
- `blueprints/`：游戏电路蓝图及其接口说明。
- `examples/`：代表图形、短代码和逐步配方。
- `reports/`：静态元件与关键路径报告。
- `mari/`：Mari 主控模型。
- `data/`：本机原始资料和提取文本；保留其归档层级。

范围入口、理论正文和完整证明现在分别位于 `papers/`、`theory/` 和 `proofs/`，不再保留 `4q5l/`、`6q5l/`、`general/` 或 `research/` 这些重复入口目录。

## 程序、例子和蓝图

- [Python 合成入口](synthesis/README.md)：输出制造证书；局部构造失败与不可制作分开。
- [代表图形及完整配方](examples/README.md)：目标短代码、逐步中间产物、输入次序及物品槽。
- [游戏电路与蓝图](blueprints/README.md)：时序复用、寄存器、搜索和成功路径回放。
- [静态元件报告](reports/README.md)：建筑数量与关键路径；平台数、元件数和求解时间不混用。
- [Mari 主控模型](mari/README.md)：51 路指令及六候选逻辑；默认配置不全覆盖的证明见[参考卷 09](proofs/09-sources.md#s09-03)。

## 本机原始资料

`data/group_files/` 保存 QQ 群 `1163635014` 的 `s2-全图形自动化（TMAM）` 文件夹原件。同名条目放在 `duplicates/`，保留原名。阅读顺序见[资料索引](data/reading-index.md)；`data/manifest.json` 记录路径、字节数、SHA-256 和下载状态，`data/listing.json` 是当时的目录快照。

原件、清单和提取文本只留本机，不进入 Git。新克隆缺少这些资料时，须明确说明来源缺失。`Mari的TMAM.zip` 的文件清单与核对范围见[参考卷 09](proofs/09-sources.md#s09-01)。

下载通过 QQBot 本机接口：先查询 `GET /admin/api/artifacts/group-files`，再以当次文件 ID 调用 `POST /admin/api/artifacts/group-file-download`，取得 QQ 原生下载路径后复制到资料目录。接口合同见 QQBot 的 `astrbot_plugin_local_artifact_api/README.md`。
