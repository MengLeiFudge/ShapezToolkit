# 二代 TMAM 模型、理论与资料

理论按象限数和层数上限分为三部分。目录名中的 `q` 表示象限数，`l` 表示层数上限。基础输入按任意不含晶体的单层图形处理；每个结论还须满足所属文档的加工规则前提。

| 范围 | 入口 | 内容 |
|---|---|---|
| 4 象限 5 层 | [4q5l](4q5l/README.md) | 覆盖性、K 支撑闭包、堆叠约化、单列分类、顶针逆向特例，以及 Mari 的 TMAM 蓝图资料 |
| 6 象限 5 层 | [6q5l](6q5l/README.md) | 独立的六象限范围与待证问题；半形为三列，四象限的证明不能直接套用 |
| x 象限 y 层 | [general](general/README.md) | 参数化规则、通用列内不变量、八象限八层反例、不稳定输出和 rank 研究边界 |

通用证明集中在 `general/`，两个固定范围通过链接引用。一般范围中的反例不自动否定固定范围的定理；固定范围的闭包和数量上界也不自动推广到其他范围。Mari 主控的六候选逻辑已写成 [Python 模型](mari/README.md)，入口为 `python main.py tmam2 solve <图形短代码>`。模型计算虚拟重建和 51 路指令；全覆盖仍未证明，实体产线也未完成核查。具体结论见 [Mari 调查记录](4q5l/mari-tmam.md)。

## 共用的本机资料

`data/group_files/` 保存从 QQ 群 `1163635014` 的 `s2-全图形自动化（TMAM）` 文件夹下载的原件。文件保留原名；同名条目放在 `duplicates/` 子目录中，避免覆盖。所有范围共用这些原件。

本机阅读顺序和分类定义见[资料阅读索引](data/reading-index.md)。`data/manifest.json` 记录各文件的相对路径、字节数、SHA-256 和下载状态；`data/listing.json` 是下载时的目录快照，其中的协议文件 ID 是临时值。原件、清单和提取文本均只留在本机，不进入 Git。

`Mari的TMAM.zip` 已归入四象限五层的实现资料，原包仍保存在共用目录。包内文件及静态核对范围见[Mari 蓝图记录](4q5l/mari-tmam.md)。

群文件通过 QQBot 的本机接口读取：先查询 `GET /admin/api/artifacts/group-files`，再用当次文件 ID 请求 `POST /admin/api/artifacts/group-file-download`，取得 QQ 原生下载后的本机缓存路径，并复制到资料目录。接口由云栖 AstrBot 提供，地址和调用合同见 QQBot 的 `astrbot_plugin_local_artifact_api/README.md`。
