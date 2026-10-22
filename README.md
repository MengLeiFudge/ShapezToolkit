# ShapezToolkit

Shapez 工具箱。根目录的 `main.py` 统一管理命令；每个功能目录放自己的 Python 程序、数据和说明。

## 按功能查找

| 目录 | 内容 |
|---|---|
| [shapez1_tmam](shapez1_tmam/README.md) | 图形结构拆解、存档电路验证、图形数据库和验证记录 |
| [shapez1_fmam](shapez1_fmam/README.md) | FMAM（Fast MAM），以尽快过关为目标；存档分析预留目录 |
| [shapez1_mmam](shapez1_mmam/README.md) | MMAM（Mini MAM），以尽量小的实体工厂制作图形为目标；存档分析预留目录 |
| [shapez1_mods](shapez1_mods/README.md) | mod.io 批量下载、本地版本整理、QQBot 群文件同步和模组包 |
| [shapez1_puzzles](shapez1_puzzles/README.md) | Steam token 获取、谜题下载、本地查询、CSV 导出和历史资料 |
| [common](common/README.md) | 本机路径设置、网络请求和文件写入等共用代码 |

## 使用入口

使用 Python 3.10 或更新版本，Python 部分仅依赖标准库。在项目根目录执行命令；在 IDE 中运行时选择 `main.py`，把子命令填入运行参数。

```text
python main.py mods update
python main.py puzzles show 100
python main.py tmam solve 123
python main.py --help
```

子命令、参数和程序调用方式见各功能目录的 README。路径在 [common/settings.py](common/settings.py) 中设置；默认数据保存在所属功能的 `data/` 中。

Git 仓库只包含源码、必要配置和说明文档。下载的模组、谜题、图形数据库、生成的验证记录以及本机凭据均留在本地，不上传。新克隆后，下载命令会创建所需目录；本地查询需先准备谜题文件，TMAM 存档验证需自行准备 `shapez1_tmam/data/shapes/shapes.json` 对照库。`tmam solve` 使用代码中的控制器，无需图形数据库。

TMAM 当前提供一代结构拆解和电路验证。图形渲染、网页入口及二代图形功能尚未实现。一代模组已接入 QQBot 群文件同步。

## 资料与历史

通用拆解说明在 [XianYu 拆解思路](shapez1_tmam/xianyu_20221129/logic.md)，具体输入案例与全量结果保存在本机 `shapez1_tmam/<机器目录>/verification/`，不纳入 Git。TMAM 按机器分别归类；原 `XianYu2` 为 `XianYu-20221129`，原 `CTMAM` 为 `BugFix-20210622`。BugFix 的漏解清单和存档差异见 [说明](shapez1_tmam/bugfix_20210622/README.md)。

旧 Java 工程及整理前的代码保存在 `.codex/trash/`；移动清单保存在 `.codex/drafts/`。这些是本机恢复资料，日常使用从上面的功能目录进入。旧 shapezTools 的谜题、图片和图形资料已归入对应功能目录。
