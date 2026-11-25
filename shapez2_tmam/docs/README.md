# 二代 TMAM 理论与证明文档库

本目录按职责清晰划分为范围导览、理论论文 Markdown 源码、编译后的学术版 PDF、九卷完整参考证明及配图资料。

## 按范围导览（跨理论与工程入口）

- [4 象限 5 层（4q5l）](4q5l.md)：完整有限合成、Mari 对照、Python 模型与原生四帧电路蓝图入口。
- [6 象限 5 层（6q5l）](6q5l.md)：精确有限闭包、不稳定交换输出、三列脚手架与六槽回放器边界。
- [偶数象限与任意高度（general）](general.md)：一般偶数宽度构造、级联下落族、强制工序词参数族、落地容量下界与开放主命题。

## 子目录分工

| 子目录 | 内容 |
|---|---|
| [papers/](papers/README.md) | 研究汇编与结论导航、六篇 A4 学术版论文 PDF 及编译器 [build_paper_pdf.py](papers/build_paper_pdf.py) |
| [theory/](theory/README.md) | 六篇理论论文的 Markdown 源码（纯理论定义、构造与证明）及**论文编写与 PDF 编译规范** |
| [proofs/](proofs/README.md) | 按主题收拢的九卷完整参考证明（含电路与外部资料卷）及 134 篇原专题映射 [sources.json](proofs/sources.json) |
| `assets/` | 证明与示例引用的示意图（SVG / PNG）及长短代码文本 |

主线阅读建议从 [研究汇编与结论导航](papers/README.md) 开始；工程实现与蓝图资料返回 [二代 TMAM 总目录](../README.md)。

## 更新 Shapez 2 反编译源码

本机反编译源码位于 `D:\project\shapez\DecompiledSource`，与 `ShapezToolkit` 同级。每个程序集对应一个子目录，例如 `Game.Content.Features\ShapeLogic.cs`。Steam 更新游戏后，在 Git Bash 中用 `ilspycmd` 从安装目录重新导出。已验证的 `ilspycmd` 版本为 `9.1.0.7988`。如果 Steam 库在其他位置，调整 `managed`。

```bash
(
  set -e
  shopt -s nullglob
  managed='D:/Steam/steamapps/common/shapez 2/shapez 2_Data/Managed'
  stage='D:/project/shapez/DecompiledSource.refresh'
  dlls=("$managed"/*.dll)
  if ((${#dlls[@]} == 0)); then
    printf '在 %s 找不到程序集\n' "$managed" >&2
    exit 1
  fi

  mkdir -- "$stage"
  for dll in "${dlls[@]}"; do
    name=${dll##*/}
    name=${name%.dll}
    ilspycmd --disable-updatecheck -p -r "$managed" -o "$stage/$name" "$dll"
    test -s "$stage/$name/$name.csproj"
  done
)
```

命令成功后，将旧 `DecompiledSource` 移到 `.codex/trash/`，再把 `DecompiledSource.refresh` 改名为 `DecompiledSource`。将旧目录中的 `_TextAssets` 移回新目录，其中存放单独从 `resources.assets` 提取的 JSON。查阅新版本的游戏逻辑时，按需记录游戏 `version`、Steam `buildid` 和相关 DLL 的 SHA-256，格式见[卷 01 的来源记录](proofs/01-foundations.md#s01-09-h18)。
