# 一代谜题

获取 Steam 认证 token、下载一代谜题，并查询或导出本地资料。

## 文件位置

| 文件或目录 | 用途 |
|---|---|
| [puzzles.py](puzzles.py) | `refresh_token` 主动认证，`download_puzzle` 下载单个谜题 |
| [steam_login.cjs](steam_login.cjs) | 调用游戏自带 Electron Node 模式与 Greenworks 的认证桥接 |
| [puzzle_library.py](puzzle_library.py) | `find_puzzles` 本地查询，`export_puzzles` CSV 导出 |
| `data`（本机，不上传） | 根目录保存新下载的谜题 JSON |
| `data/common`（本机，不上传） | 普通历史谜题 |
| `data/puzzles_deleted`（本机，不上传） | 旧工具归类为已删除的历史谜题 |
| `data/catalog`（本机，不上传） | 历史 CSV 与本地导出清单 |
| `data/img`（本机，不上传） | 历史谜题图片 |
| `.local/shapez1-token.json` | 本机认证凭据，不纳入版本控制 |

目录名称保留旧工具当时的分类，不代表网站当前状态。本机游戏目录、token 文件和数据目录在 [common/settings.py](../common/settings.py) 中设置。

## 命令

在工具箱根目录执行：

```text
python main.py puzzles token
python main.py puzzles download 123 "Rb--Rb--:CyCrCyCr"
python main.py puzzles download 123 --refresh-token
python main.py puzzles show 100
python main.py puzzles show "SrSr----:RuRu----"
python main.py puzzles export
```

- `token`：主动获取并保存新 token。
- `download CODE...`：下载一个或多个谜题，支持数字 ID 和图形短代码。没有 token 时先获取，已有 token 时复用；加 `--refresh-token` 可在下载前更新。
- `show CODE`：显示本地谜题 JSON 和来源路径，不联网。短代码匹配多个谜题时全部显示。
- `export`：将普通谜题按 ID 去重、排序，默认导出到 `data/catalog/puzzles.csv`；用 `--output 文件.csv` 指定其他位置。保留历史工具的 20 列，缺失统计留空。

短代码以 `--` 开头时，先加参数分隔符，例如 `python main.py puzzles download -- "--Rb--Rb:CyCrCyCr"`；`show` 同样适用。

## 认证与本地资料

认证需要完整的一代游戏安装、已登录 Steam 和拥有谜题 DLC 的账号。默认游戏目录是 `D:\Steam\steamapps\common\shapez.io`。认证不创建游戏窗口，成功后才替换 token 文件，失败保留旧文件；控制台不显示 token。普通下载复用保存的凭据；认证被拒绝时运行 `token` 或加 `--refresh-token`。

本地查询和导出不需要 token。同一 ID 优先采用 `data/` 根目录最近下载的文件，其次采用 `common/`；查询还会查找 `puzzles_deleted/`，导出不包含这些已删除归档。认证桥接直连 `api.shapez.io`，网络受限时需要确保该地址可达。

## 程序调用

其他 Python 程序将工具箱根目录加入模块搜索路径后，可以调用：

- `shapez1_puzzles.puzzles.refresh_token(game_dir, token_file)`：获取新 token。
- `shapez1_puzzles.puzzles.download_puzzle(code, token_file, destination)`：使用已有 token 下载，返回 JSON 路径。
- `shapez1_puzzles.puzzle_library.find_puzzles(code, destination)`：返回匹配的 `(路径, JSON 对象)` 列表。
- `shapez1_puzzles.puzzle_library.export_puzzles(destination, output)`：导出 CSV 并返回数量。

导入模块本身不会认证、联网或写文件。
