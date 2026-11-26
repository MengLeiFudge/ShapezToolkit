# 一代模组

从 mod.io 批量同步一代模组，整理本地版本，并通过 QQBot 同步指定群文件夹。

## 文件位置

| 文件或目录 | 用途 |
|---|---|
| [mods.py](mods.py) | `sync_mods`：网站列表、下载、重试与校验 |
| [mod_library.py](mod_library.py) | `clean_mods`：版本清理、重复识别和当前版本清单 |
| [mod_publish.py](mod_publish.py) | `publish_mods`：调用 QQBot 本地发布接口 |
| `data/downloads`（本机，不上传） | 模组 ZIP，沿用 `模组名_版本.zip` |
| `data/catalog`（本机，不上传） | 原 CSV、Excel、下载状态、当前版本与群同步结果 |
| `data/trash`（本机，不上传） | 清理时移出的重复、旧版和明确废弃包及移动记录 |

路径在 [common/settings.py](../common/settings.py) 的 `MOD_DIR` 中设置。

## 命令

在工具箱根目录执行：

```text
python main.py mods update
python main.py mods publish
python main.py mods download
python main.py mods clean
```

- `update`：批量下载网站当前版本，再同步群文件；个别下载失败时仍同步已确认的包，退出码保留下载失败结果。
- `publish`：整理已有本地包并同步群文件，不访问 mod.io。
- `download`：下载未明确废弃的模组，每个模组保留一个已确认的当前包。
- `clean`：依据已有清单整理本地文件，不联网。

其他 Python 程序可导入 `shapez1_mods.mods.sync_mods(destination, progress=print)`、`shapez1_mods.mod_library.clean_mods(destination, progress=print)` 和 `shapez1_mods.mod_publish.publish_mods(destination)`。导入本身不会联网或写文件。

## 下载与版本

`download` 和 `update` 从环境变量 `SHAPEZ1_MODIO_API_KEY` 读取 mod.io **API access** 的 Key。列表、当前文件及下载地址通过 `https://u-32147295.modapi.io/v1` 查询，ZIP 使用 API 返回的下载地址获取。

模组 ID 标识模组，文件 ID 标识网站上的上传文件。两者写入清单，不加到 ZIP 文件名中。最新版本取网站的当前文件指针，不按作者填写的版本号排序。

完整的同版本文件通过大小和 MD5 校验后复用。新包先下载到临时位置，校验成功后才替换旧版；不同模组出现文件名冲突时报告错误并保留原文件。

列表请求和单项任务遇到连接中断、超时、临时 HTTP 错误或文件校验失败时，最多尝试 4 次，重试前等待 2、4、8 秒。证书、元数据和磁盘错误直接报告；下载地址失效时重新获取一次地址。单项最终失败后继续处理其他模组，写入 `data/catalog/download-state.json`；列表最终失败则停止。再次运行会复用已完成文件。

明确废弃、重复和已替换的旧包移入 `data/trash/mods-<时间>/`，`moves.json` 记录原路径、目标和 SHA-256。重复识别采用 ZIP 内部文件名和内容哈希。只有作者在名称、标签或自身说明中明确标记 Deprecated、已弃用或不再工作才判为废弃；更新时间早或下载失败不作为依据。无法确认版本的历史包和无法读取的 ZIP 会保留并报告，不加入当前版本上传清单。

## QQBot 群文件同步

先启动 QQBot 云栖，再执行 `update` 或 `publish`。目标固定为群 `1163635014` 的 `s1-MOD-官方模组网站` 文件夹；目录必须已经存在且名称唯一。工具调用本机 `127.0.0.1:8080/admin/api/artifacts/shapez1-mods`，上传名称仍为 `模组名_版本.zip`。

`data/catalog/current-mods.json` 记录已确认的当前包，路径相对于本功能的 `data/`。机器人按模组 ID 关联群文件，独立核对 SHA-256；新版上传成功并确认唯一远端文件后才移除已跟踪的旧版。明确废弃的模组也只清理机器人已跟踪的文件，首次同步不会接管手工上传的历史文件。单包上限为 64 MiB，不发送额外群聊公告。

同步结果保存在 `data/catalog/qqbot-last-run.json`。上传失败可单独重新执行 `publish`。机器人保留未完成的 `pending` 状态；已有成功回执时继续确认，没有回执或无法唯一确认时停止并要求核对现场，避免重复上传。确认失败会保留旧版。
