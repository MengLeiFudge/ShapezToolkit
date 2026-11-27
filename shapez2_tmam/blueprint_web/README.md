# 二代蓝图网页工具

离线解析、升级并编辑二代蓝图（`.spz2bp`），最终交付单文件 HTML，双击即用。

当前完成阶段 1：编解码与升级骨架，命令行可用；3D 预览与建筑级编辑在后续阶段。

## 命令

从仓库根运行。

| 用途 | 命令 |
|---|---|
| 查看结构与统计 | `python main.py tmam2 web --decode 蓝图.spz2bp` |
| 升级到本机最新版本 | `python main.py tmam2 web --upgrade 蓝图.spz2bp --output-dir 输出目录` |
| 批量核对解析、往返与升级 | `python main.py tmam2 web --verify .codex/sources/blueprints` |

`--upgrade` 不给 `--output-dir` 时写到输入文件旁的 `upgraded/`，逐文件打印报告行。

## 覆盖范围

- 封装 1..5 全部可读。封装 1..4 没有追加数据段，蓝图图标留在 `BP.Icon`；封装 5 起图标作为追加数据写在 base64 之后、`_<长度>$` 之前。
- 升级目标固定为本机最新版：`V = 1138`、封装 5，对应 1.2.0-rc3。
- 升级只改已经确定的部分：`V` 与 `RecommendedVersion`、岛定义改名与轨合并器互换、旧蓝图缺失的岛条目 `Z`、1.2 已取消的 `BinaryVersion`、图标搬进追加数据。

## 规则来源

`data/migration.json` 的每条规则都来自反编译源码，涉及四类：

| 规则 | 源码 |
|---|---|
| 封装常量与导出公式 | `Game.Core.Blueprint.Serialization.BlueprintFormat`、`BlueprintExporter.Export` |
| 岛定义改名、轨合并器互换、原点偏移 | `Game.Orchestration.GameMigrators` 及其 `IIslandDefinitionIdMigrator` 实现 |
| 图标搬进追加数据 | `BlueprintIconEmbeddedToAppendedV4ToV5FormatMigrator`、`BlueprintLegacyIconDeserializer` |
| 建筑与岛状态的字节串分叉 | 各数据序列化器里的 `visitor.Version < GameVersion.X` 判断 |

## 尚未实现

未实现的迁移不会静默通过，升级报告里以 `unsupported` 列出并说明影响：

- 1098 及更早的旧岛配置字节串（轨节点、太空带节点、太空管节点）。
- 1099..1113 的岛配置字节串布局，1114 之后整体更换。
- 建筑与岛状态字节串在 1114、1116、1121、1127、1128、1131、1132、1137 等分叉上的旧布局解码。
- 列车生产器原点后移一格，需要生产器 id 清单。
