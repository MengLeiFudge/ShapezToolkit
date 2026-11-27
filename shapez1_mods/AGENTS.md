# 一代模组

批量同步 mod.io 当前发布文件，整理本地 ZIP，并将已确认的清单交给 QQBot。

## 去哪里找

| 任务 | 入口 | 核对点 |
|---|---|---|
| 分页和重试 | [mods.py](mods.py) 的 `iter_mods`、`with_retries` | 分页偏移、重复 ID、临时错误分类 |
| 下载和复用 | [mods.py](mods.py) 的 `sync_mod`、`sync_mods` | 当前文件指针、包校验和逐项状态 |
| 本地清理 | [mod_library.py](mod_library.py) 的 `clean_library`、`clean_mods` | 在可恢复目录保留移包记录 |
| 群文件发布 | [mod_publish.py](mod_publish.py) 的 `publish_mods` | `current-mods.json`、逐项应答与同步记录 |
| 命令与目录约定 | [运行说明](README.md) | `download` 同步网站，`clean` 依据已有清单整理 |

## 约定

- 模组 ID 和上传文件 ID 分开保存。展示和群文件名仍用 `模组名_版本.zip`。
- 当前版本取网站 `modfile` 指针。下载地址过期时重新获取同一文件 ID 的地址。
- 远端大小和 MD5 用于下载完整性。ZIP 内部文件名与内容哈希用于本机去重。发布清单带 ZIP SHA-256。
- 校验完成才替换或登记当前文件。同名异内容先写入 `.pending`，由清理阶段确认归属。
- `download-state.json` 记录下载结果，`current-mods.json` 是发布输入，`qqbot-last-run.json` 记录机器人应答。`update` 保留下载失败退出码，已确认的包仍可同步。
- QQBot 管理远端上传、确认和旧版删除。发布端逐项请求并核对 ID 与返回值。
- 分页失败终止列表读取，单包失败保留记录并继续。重试只依据 `RequestError.retryable` 对临时错误开放。

## 禁止事项

- 弃用判定只接受作者在名称、标签或自身说明中的明确标记。更新时间和请求失败均留作状态信息。
- 损坏的清单应报错。归属不明或无法读取的历史包留在原处。
- 清理用 `data/trash/` 和 `moves.json` 保留可恢复记录。发布请求结果不确定时停止并保存进度，交由机器人恢复确认。
- 发布路径须解析到 `downloads/` 下的实际文件。清单中的模组 ID 必须有效且唯一。
