# 项目知识库

## 概览

ShapezToolkit 是一、二代 Shapez 工具箱，核心使用 Python 标准库和 `argparse`。一代覆盖模组、谜题和 TMAM 存档解析，二代覆盖制造证书、原生电路蓝图与 Mari 主控模型。

## 结构

```text
.
├── main.py
├── common/                     # 本机路径、下载、原子写入
├── shapez1_mods/
├── shapez1_puzzles/
├── shapez1_tmam/                # 共用存档执行器及分机器分析
└── shapez2_tmam/
    ├── synthesis/              # 物理、构造与制造证书
    ├── circuits/               # 方法编译、原生电路与实体装配
    ├── mari/                   # 外部主控组合模型与接线提取
    ├── blueprints/             # 游戏可导入图册及配套接口
    ├── blueprint_web/          # 蓝图编解码、版本升级与单文件网页
    ├── docs/                   # 范围导览、论文与完整证明
    ├── examples/               # 代表配方及机器可读步骤
    └── reports/                # 静态网表规模与关键路径报告
```

## 去哪里找

| 任务 | 位置 | 说明 |
|---|---|---|
| 增加命令或修改参数 | [main.py](main.py) | `build_parser` 注册，`main` 分派，二代子命令委托各自 CLI |
| 修改路径或下载 I/O | [common/settings.py](common/settings.py)、[common/io.py](common/io.py) | 路径以仓库根为基准，临时文件与目标放在同一目录再替换 |
| 模组同步与清理 | [模组规则](shapez1_mods/AGENTS.md) | 网站、目录清单及 QQBot 三个入口 |
| 谜题查询、认证与导出 | [谜题说明](shapez1_puzzles/README.md) | `puzzle_library.py` 离线读库，`puzzles.py` 接认证和下载 |
| 一代拆解与存档验证 | [一代 TMAM 规则](shapez1_tmam/AGENTS.md) | 共用 tick 执行器，按机器选择入口 |
| 二代制造证书 | [合成规则](shapez2_tmam/synthesis/AGENTS.md) | 物理、构造、逆推、指令导出 |
| 原生蓝图及实体工道 | [电路规则](shapez2_tmam/circuits/AGENTS.md) | 网表、编译前后端、装配与时序 |
| 蓝图解析、升级与网页工具 | [网页工具说明](shapez2_tmam/blueprint_web/README.md) | 封装 1..5 编解码，迁移规则在 `data/migration.json` |
| 外部 Mari 主控 | [Mari 规则](shapez2_tmam/mari/AGENTS.md) | 组合方程、端口和原包提取 |
| 理论与工程证据 | [范围导览](shapez2_tmam/docs/README.md)、[整厂约定](shapez2_tmam/blueprints/整厂约定.md) | 论文源稿在 `docs/theory/`，完整推导及工程记录在 `docs/proofs/` |

## 代码地图

| 符号 | 类型 | 位置 | 引用 | 作用 |
|---|---|---|---|---|
| `CircuitModel` | 类 | [tmam_verify.py](shapez1_tmam/tmam_verify.py) | `solver.py`、`verify_v7f.py` | 一代增量 tick 执行与完整状态周期检测 |
| `Rules` | 类 | [physics.py](shapez2_tmam/synthesis/physics.py) | `recipe.py`、`construct.py`、`full_solver_circuit.py` | 参数化局部加工语义 |
| `Recipe` | 类 | [recipe.py](shapez2_tmam/synthesis/recipe.py) | `solver4.py`、`construct.py`、`orientation.py` | 展开制造树和消费式指令 |
| `Circuit` | 类 | [circuit.py](shapez2_tmam/circuits/circuit.py) | `full_solver_circuit.py`、`compiler_backend/_lower.py` | 门、输出引用和布局前网表 |
| `Wiring` | 类 | [blueprint.py](shapez2_tmam/mari/blueprint.py) | `circuits/circuit.py` 等 | 按原生端口几何追踪驱动源 |
| `Program` | 类 | [compiler_contract.py](shapez2_tmam/circuits/compiler_contract.py) | `compiler_frontend/__init__.py`、`compiler_backend/__init__.py` | 方法编译前端和后端共享的控制流 |
| `save_json` | 函数 | [io.py](common/io.py) | `mods.py`、`mod_library.py`、`mod_publish.py`、`puzzles.py` | UTF-8 JSON 同目录原子替换 |

## 约定

- 功能源码、说明及默认工作数据以各包为边界。配置入口见 `common/settings.py`，`.gitignore` 记录本机下载、存档对照和中间资料的保留范围。
- 二代蓝图按通用火车、配料、实体、电路分册。频道和采样以对应蓝图的同名 JSON 为准。
- 理论完备性、网表与几何静态检查、虚拟回放、实机出货分别记录。验收条件见 [整厂约定](shapez2_tmam/blueprints/整厂约定.md)。
- `.codex/` 为本机 AI 工作区，根目录仅允许 `README.md` 与 `drafts/`、`tests/`、`tmp/`、`sources/`、`trash/` 五个固定子目录：进行中草稿写 `drafts/`，一次性探针、实验与本机临时工具脚本写 `tests/<主题>/`，可重建运行产物写 `tmp/<主题>/` 并优先同名覆盖，外部参考摘录放 `sources/`，废弃缓冲放 `trash/`。`sources/` 超 250 MiB 或 `.codex/` 总量超 512 MiB 时先整理再继续写入；细则见 [.codex/README.md](.codex/README.md)。

## 禁止事项

- 本机 token、下载缓存、原始存档与群文件原件留在 Git 忽略范围。CLI 和网络错误文案保留凭据遮蔽。
- 保持配套蓝图和接口表同源。`--reports` 的逻辑门、关键路径及理论时序只用于对应静态网表。
- 论文源码中避免未配对的 `$`、公式内的反引号，以及用代码块排公式。语法与字体质检见 [论文编写规范](shapez2_tmam/docs/theory/README.md)。
- 禁止在 `.codex/` 根目录新建白名单外的文件夹或散落文件（含按日期、任务名、哈希或随机后缀命名的目录），禁止在 `.codex/` 内残留整仓拷贝与依赖安装目录，禁止把 `.spz2bp`、`.sig`、`.log` 等生成物堆入 `drafts/`；规则外顶层项会被 [codex_gc.ps1](scripts/codex_gc.ps1) 清除。

## 独特风格

- 中文 README 与源码说明沿用游戏短代码、原生建筑标识、频道与象限命名。二代文件名中的 `q` 指象限数，`l` 指过程层数上限。
- 遇到旧专题证明路径，按 [sources.json](shapez2_tmam/docs/proofs/sources.json) 定位迁移后的完整参考卷锚点。

## 命令

从仓库根运行。参数以 `main.py` 或对应模块入口为准。

| 用途 | 命令 |
|---|---|
| 命令帮助 | `python main.py --help` |
| 一代离线谜题查询、结构拆解 | `python main.py puzzles show 100`、`python main.py tmam solve 123` |
| 二代制造证书与 Mari 模型 | `python main.py tmam2 synth "CuCu----:Cu------" --quadrants 4`、`python main.py tmam2 mari CuCuCuCu` |
| 蓝图目标、编译与静态报告 | `python main.py tmam2 blueprint --list`、`python main.py tmam2 blueprint decoder-4q5l`、`python main.py tmam2 blueprint --reports` |
| 蓝图解析与升级 | `python main.py tmam2 web --decode 蓝图.spz2bp`、`python main.py tmam2 web --upgrade 蓝图.spz2bp`、`python main.py tmam2 web --verify 目录` |
| 论文排版 | `pip install -e ".[docs]"` 后运行 `python main.py tmam2 paper --all` |
| `.codex` 巡检与回收 | `powershell -ExecutionPolicy Bypass -File scripts/codex_gc.ps1`（加 `-Apply` 执行删除） |

本地格式化、Ruff 检查和 `ty` 类型检查的命令见 [开发命令](README.md#格式化与静态检查)。Python 兼容下限由 [pyproject.toml](pyproject.toml) 声明。

## 注意

- 以 `--` 开头的图形短代码需要前置独立的 `--` 终止参数解析。适用入口见对应 README。
- `mods update` 和 `mods publish` 会同步群文件。谜题认证使用 Windows 上已登录的 Steam，会替换本机 token。
- 一代 `tmam verify` 需要原始存档与本机图形对照库。`tmam solve` 使用仓库内的转录与加工树。
