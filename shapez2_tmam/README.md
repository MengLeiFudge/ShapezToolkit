# 二代 TMAM：理论、合成与原生电路

先看[六篇理论论文](docs/papers/README.md#理论论文)。总入口见[理论论文集索引](docs/papers/README.md)；完整证明收拢为[九卷参考资料](docs/papers/README.md#九卷参考证明)。[理论源码与编写规范](docs/theory/README.md)按“模型 → 四象限覆盖 → 偶数象限构造 → 级联与首轮强制词 → 交替重排与多窗口族 → 落地记录与容量下界”组织；工程实现、蓝图交付物和参考证明分别从下方入口进入。

## 按范围阅读

| 范围 | 入口 | 已有结果与边界 |
|---|---|---|
| 4 象限 5 层 | [4q5l](docs/4q5l.md) | 完整有限合成；统一双半形起点及有界 Pin/追加循环；游戏实用性尚未验收 |
| 6 象限 5 层 | [6q5l](docs/6q5l.md) | 精确有限闭包完备；紧凑全域求解及完整电路仍缺 |
| 偶数象限、任意高度 | [general](docs/general.md) | 四象限完整列与半形判据、重复下落族、多窗口强制词族与空间容量下界；任意指定交替序列仍开放 |

目录名中 `q` 表示象限数，`l` 表示全过程的层数上限。基础输入为任意无晶体单层；每个定理还须满足对应参考卷的操作前提。理论覆盖、实用复杂度和具体存档验收分别记录。

## 目录结构

| 目录 | 定位 | 内容 |
|---|---|---|
| [synthesis/](synthesis/README.md) | 代码包 | 通用偶数象限物理模型、角与脚手架构造、有界逆推与制造证书导出 |
| [circuits/](circuits/README.md) | 代码包 | 原生二代信号门网表、3×3 大平台装箱、时序控制、实体工道和单节货运站场的蓝图编译器 |
| [mari/](mari/README.md) | 代码包 | Mari 主控接线提取、组合方程与六候选求值模型 |
| [docs/](docs/README.md) | 理论与证明 | 范围导览（`4q5l` / `6q5l` / `general`）、`papers/`（六篇学术版 PDF 与研究索引）、`theory/`（论文 Markdown 源码与编写规范）、`proofs/`（九卷完整证明与来源映射）及 `assets/`（配图与长短代码） |
| [blueprints/](blueprints/README.md) | 导出产物 | 游戏 `SHAPEZ2-4` 蓝图册，按电路、实体、火车分目录，电路附频道与时序说明 |
| [examples/](examples/README.md) | 导出产物 | 代表图形与特殊机制的逐步文字配方（`.md`）、`json/`（机器可读步骤与六槽指令）及 `18q17l-cascade/` 分页图 |
| [reports/](reports/README.md) | 导出产物 | 完整四象限控制电路的静态元件规模与关键路径报告 |
| `data/` | 本机资料 | 群文件原件、清单与本地提取文本（Git 忽略，保留归档层级） |

## 常用入口

在仓库根目录可通过 `main.py` 统一调用：

```bash
# 通用合成器输出制造步骤或六槽指令
python main.py tmam2 synth "CuCu----:Cu------" --quadrants 4

# 查看或重新编译原生电路蓝图及网表报告
python main.py tmam2 blueprint --list
python main.py tmam2 blueprint --reports

# Mari 六候选主控模型求值
python main.py tmam2 mari CuCuCuCu

# 重新编译全部六篇理论论文 PDF（需安装 typst，见 pip install -e ".[docs]"）
python main.py tmam2 paper --all
```

* [Python 合成入口](synthesis/README.md)：输出制造证书；局部构造失败与不可制作分开。
* [原生电路编译器](circuits/README.md)与[蓝图连接说明](blueprints/README.md)：时序复用、寄存器、搜索和成功路径回放。
* [代表图形及完整配方](examples/README.md)：目标短代码、逐步中间产物、输入次序及物品槽。
* [静态元件报告](reports/README.md)：建筑数量与关键路径；平台数、元件数和求解时间不混用。
* [Mari 主控模型](mari/README.md)：51 路指令及六候选逻辑；默认配置不全覆盖的证明见[参考卷 09](docs/proofs/09-sources.md#s09-03)。

## 本机原始资料

`data/group_files/` 保存 QQ 群 `1163635014` 的 `s2-全图形自动化（TMAM）` 文件夹原件。同名条目放在 `duplicates/`，保留原名。阅读顺序见 `data/reading-index.md`；`data/manifest.json` 记录路径、字节数、SHA-256 和下载状态，`data/listing.json` 是当时的目录快照。

原件、清单和提取文本只留本机，不进入 Git。新克隆缺少这些资料时，须明确说明来源缺失。`Mari的TMAM.zip` 的文件清单与核对范围见[参考卷 09](docs/proofs/09-sources.md#s09-01)。

下载通过 QQBot 本机接口：先查询 `GET /admin/api/artifacts/group-files`，再以当次文件 ID 调用 `POST /admin/api/artifacts/group-file-download`，取得 QQ 原生下载路径后复制到资料目录。接口合同见 QQBot 的 `astrbot_plugin_local_artifact_api/README.md`。
