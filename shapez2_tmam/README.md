# Shapez 2 TMAM

二代全图形自动化资料与拆解研究。基础输入按任意不含结晶的单层图形处理，包括所需的普通图形、颜色和顶针组合；多层结构及结晶结构的构造需要单独说明。

## 本机资料

`data/group_files/` 保存从 QQ 群 `1163635014` 的 `s2-全图形自动化（TMAM）` 文件夹下载的原件。文件保留原名；同名条目放在 `duplicates/` 子目录中，避免覆盖。

本机阅读顺序和分类定义见 [资料阅读索引](data/reading-index.md)。

`data/manifest.json` 记录每个文件的相对路径、字节数、SHA-256 和下载状态。`data/listing.json` 是本次目录快照，其中的协议文件 ID 是临时值。原件、清单和提取文本均只留在本机，不进入 Git。

群文件通过 QQBot 的本机接口读取：先查询 `GET /admin/api/artifacts/group-files`，再用当次文件 ID 请求 `POST /admin/api/artifacts/group-file-download`，取得 QQ 原生下载后的本机缓存路径，并复制到资料目录。接口由云栖 AstrBot 提供，地址和调用合同见 QQBot 的 `astrbot_plugin_local_artifact_api/README.md`。

## 研究范围

研究重点包括半形与角的可制作性、顶针推送引起的结晶破碎、失去支撑后的跌落，以及带颜色结晶的构造。文档中的分类结论、蓝图实际实现和可制作性证明分别记录；资料下载完成不代表机器通过全图形验证。

覆盖性、颜色消除、顶针次数上界与循环支撑边界见 [覆盖性研究](coverage-research.md)。
