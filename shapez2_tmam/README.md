# 二代 TMAM 模型、理论与资料

理论按象限数和层数上限分为三部分。目录名中的 `q` 表示象限数，`l` 表示层数上限。基础输入按任意不含晶体的单层图形处理；每个结论还须满足所属文档的加工规则前提。

| 范围 | 入口 | 内容 |
|---|---|---|
| 4 象限 5 层 | [4q5l](4q5l/README.md) | [统一合成与覆盖证明](4q5l/synthesis.md)：半形目录、有界顶针/堆叠尾部、实体配方展开；另含 Mari 资料与漏解证明 |
| 6 象限 5 层 | [6q5l](6q5l/README.md) | [统一合成与覆盖证明](6q5l/synthesis.md)：精确操作配方目录；另有非 K 半形与不稳定可制作输出的完整构造 |
| x 象限 y 层 | [general](general/README.md) | [无限构造族](general/wide-half-loops.md)：所有偶数 n≥6、H≥5 的不稳定输出；固定偶数参数的有限合成保证及结构压缩研究 |

四象限与六象限已有有限搜索合成方式的人工覆盖证明，尚无实用复杂度保证，也未运行全量目录计算。一般研究限定偶数象限，按明确参数与操作约定继续推进；固定范围的结构约化不能默认跨范围成立。

四象限的[电路化简化](4q5l/compact-synthesis.md)包含堆叠段至多五份上料、局部最短配方和尾部旋转归并。[Python 堆叠模块](stacking.py)提供逐层与最短两种规划；无晶体目标可直接从基础原料合成；含晶体的完整逆推及四帧电路控制已有首版，搜索规模和耗时仍须压缩。

Mari 主控的六候选逻辑另有 [Python 模型](mari/README.md)，入口为 `python main.py tmam2 solve <图形短代码>`。模型计算虚拟重建和 51 路指令；[整层空隙反例](4q5l/mari-empty-layer.md)已证明默认配置的六候选算法不全覆盖。新合成方法另有[Python 合成入口](synthesis/README.md)及[原生电路部件](blueprints/README.md)；[完整四象限电路](4q5l/full-tail-circuit.md)已接四帧搜索及成功路径重放，尚未通过实用性能验收，六象限完整实现仍缺。具体原机结论见 [Mari 调查记录](4q5l/mari-tmam.md)。

当前按“理论→Python→建筑与时序统计→走线”推进。跨参数化简包括[K下料的n²+1种基础块](general/conditional-stacking.md)、[交换的半形凭据](general/swap-witnesses.md)、[任意下料不新增针时的直接上料构造](general/ordinary-stack.md)、[新增针尾推广](general/pin-tail-stack.md)及[任意堆叠的输入摘要](general/stack-summaries.md)；[Python物理与局部构造](general/python-model.md)已支持偶数n≥2、H≥2，尚不构成实用完整六象限或通用求解器。[网表报告](reports/README.md)可直接统计非线缆建筑，不生成走线；[十二个特殊图形配方](examples/README.md)提供完整步骤，供手工在游戏中复现。

## 共用的本机资料

`data/group_files/` 保存从 QQ 群 `1163635014` 的 `s2-全图形自动化（TMAM）` 文件夹下载的原件。文件保留原名；同名条目放在 `duplicates/` 子目录中，避免覆盖。所有范围共用这些原件。

本机阅读顺序和分类定义见[资料阅读索引](data/reading-index.md)。`data/manifest.json` 记录各文件的相对路径、字节数、SHA-256 和下载状态；`data/listing.json` 是下载时的目录快照，其中的协议文件 ID 是临时值。原件、清单和提取文本均只留在本机，不进入 Git。

`Mari的TMAM.zip` 已归入四象限五层的实现资料，原包仍保存在共用目录。包内文件及静态核对范围见[Mari 蓝图记录](4q5l/mari-tmam.md)。

群文件通过 QQBot 的本机接口读取：先查询 `GET /admin/api/artifacts/group-files`，再用当次文件 ID 请求 `POST /admin/api/artifacts/group-file-download`，取得 QQ 原生下载后的本机缓存路径，并复制到资料目录。接口由云栖 AstrBot 提供，地址和调用合同见 QQBot 的 `astrbot_plugin_local_artifact_api/README.md`。
