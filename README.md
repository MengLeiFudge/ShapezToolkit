# ShapezToolkit

Shapez 工具箱。根目录的 `main.py` 统一管理命令；每个功能目录放置自身的 Python 包、说明和本机数据。

## 按功能查找

| 目录 | 内容 |
|---|---|
| [shapez1_tmam](shapez1_tmam/README.md) | 一代 TMAM：图形结构拆解、存档电路逐 tick 验证、图形对照库与验证记录 |
| [shapez1_mods](shapez1_mods/README.md) | 一代模组：mod.io 批量下载、本地版本清理与 QQBot 群文件同步 |
| [shapez1_puzzles](shapez1_puzzles/README.md) | 一代谜题：Steam token 获取、谜题下载、本地查询与 CSV 导出 |
| [shapez2_tmam](shapez2_tmam/README.md) | 二代 TMAM：理论论文与九卷证明、通用偶数象限合成器、原生电路蓝图编译器、Mari 主控模型与[蓝图网页工具](shapez2_tmam/blueprint_web/README.md) |
| [common](common/README.md) | 本机路径设置、网络请求与原子文件写入等共用代码 |

> 后续规划的一代 FMAM（Fast MAM，过关耗时导向）与 MMAM（Mini MAM，最小实体规模导向）在确定待分析存档后，再按同一规范单独建立 `shapez1_fmam/`、`shapez1_mmam/` 目录。

## 使用入口

核心功能使用 Python 3.10 或更新版本，仅依赖标准库（重排二代论文 PDF 或渲染级联步骤图时需安装可选依赖 `pip install -e ".[docs]"`）。在项目根目录执行命令；在 IDE 中运行时选择 `main.py` 并填入对应子命令：

```text
python main.py mods update
python main.py puzzles show 100
python main.py tmam solve 123
python main.py tmam2 synth "CuCu----:Cu------" --quadrants 4
python main.py tmam2 mari CuCuCuCu
python main.py tmam2 blueprint --list
python main.py tmam2 web --decode 蓝图.spz2bp
python main.py --help
```

子命令、参数和 Python 模块调用方式见各功能目录的 README。本机路径在 [common/settings.py](common/settings.py) 中设置；默认下载和运行数据保存在所属功能的 `data/` 下。

Git 仓库只包含源码、蓝图/示例交付物、理论文档和必要配置。下载的模组、谜题、图形数据库、存档验证结果、二代群文件原件及本机凭据均留在本地，不纳入版本控制。新克隆后，下载命令会自动创建所需目录；本地谜题查询需先准备谜题文件，一代 TMAM 存档验证需自行准备 `shapez1_tmam/data/shapes/shapes.json`。`tmam solve` 与 `tmam2 synth` 直接运行代码中的构造与求解逻辑，无需外部数据库。

## 格式化与静态检查

在仓库根目录运行以下命令。格式化时把 `main.py` 换成你要整理的文件。

```bash
uvx ruff format main.py
uvx ruff format --check main.py
uvx ruff check --no-cache .
uvx ty check
```

Ruff 按 `pyproject.toml` 检查 Python 3.10 语法、无效控制流和未定义名称。GitHub Actions 在推送和拉取请求时运行同一条 Ruff 静态检查。格式化与 `ty` 类型检查可单独运行。

## 研究摘要与资料说明

* **一代 TMAM**：按机器分别归类，通用拆解思路见 [XianYu 拆解思路](shapez1_tmam/xianyu_20221129/logic.md)（原 `XianYu2` 现名 `XianYu-20221129`，原 `CTMAM` 现名 `BugFix-20210622`）。BugFix 漏解清单和存档差异见 [BugFix 说明](shapez1_tmam/bugfix_20210622/README.md)。
* **二代 TMAM**：理论与九卷完整证明汇总于 [二代理论与证明库](shapez2_tmam/docs/README.md)。针对外部 Mari 主控，已建立 51 路组合方程模型并找到 [整层空隙反例](shapez2_tmam/docs/proofs/09-sources.md#s09-03)，证明原包默认配置不全覆盖；虚拟匹配不代表实体成品，详见 [Mari 模型说明](shapez2_tmam/mari/README.md)。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
