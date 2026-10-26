"""导出固定代表构造的逐步配方；不枚举目标，也不运行完整搜索。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .corners import CornerBuilder
from .half_catalog import HalfCatalog
from .physics import EMPTY, PIN, Rules
from .recipe import Builder, Recipe


@dataclass(frozen=True)
class Example:
    """一个特殊机制及其实际加工树；里程碑用于阅读长配方。"""

    name: str
    title: str
    mechanism: str
    quadrants: int
    recipe: Recipe
    milestones: tuple[tuple[str, Recipe], ...] = ()


def corner_examples() -> list[Example]:
    """每种间隙或顶破构造分支取一个固定主列，并保留必要辅助列。"""
    builder = Builder(Rules(4))
    corners = CornerBuilder(builder)
    cases = (
        ("N-C--", "单次融合删除", "先把普通格提高到间隙顶部，以针隔开辅助支撑，切掉辅助晶体后普通格回落。"),
        ("-N-CC", "悬空普通格与连续双晶体", "两次转交支撑，顶破远侧晶体脊；主列最终为-N-CC。"),
        ("N-N-C", "双普通格间隙", "两次转交支撑并顶破，保留两个相隔一层的普通格及顶层晶体。"),
        ("P-N-C", "地面针与晶体间隙", "来源底部辅助晶体被顶破删除，地面补针，保留高处普通格与晶体。"),
        ("--N-C", "两层空底", "通过侧面支撑保留悬空普通格，顶破后形成两层空底的主列。"),
        ("-N--C", "两格高间隙", "使用双针支撑尾部，保留普通格和顶层晶体之间的两格间隙。"),
    )
    materials = {"-": EMPTY, "N": "Cu", "P": PIN, "C": "cr"}
    examples = []
    for index, (word, title, mechanism) in enumerate(cases, 1):
        recipe = corners.build(tuple(materials[cell] for cell in word), 0, 1)
        if recipe is None:
            raise RuntimeError(f"已证明的代表角构造没有生成配方：{word}")
        examples.append(Example(f"4q-{index}-{word}", title, mechanism, 4, recipe))
    return examples


def wide_half_examples() -> list[Example]:
    """展开六象限非K半形H及两份H交换得到的非稳定输出V。"""
    builder = Builder(Rules(6))
    spine = builder.dense_column(("cr", "Cu", "cr", "cr", "cr"), 0)
    fuse = builder.dense_column(("cr",), 1)
    support = builder.column(("Cu", PIN, "Cu", "Cu", "Cu"), 5)
    assert support is not None
    prepared = builder.join(builder.join(spine, fuse, 4), support, 0)
    released = builder.window(prepared, 4)
    scaffold = None
    for columns in ((3,), (3,), (1, 2, 3), (2,), (1, 2)):
        layer = builder.base(tuple("Cu" if q in columns else EMPTY for q in range(6)))
        scaffold = layer if scaffold is None else builder.apply("stack", scaffold, layer)
    assert scaffold is not None
    merged = builder.join(released, scaffold, 4)
    half = builder.window(merged, 0)
    expected = builder.rules.parse("Cu----------:------------:crCuCu------:cr--Cu------:crCuCu------")
    if half.result != expected:
        raise RuntimeError("六象限代表构造未产生证明中的H；不能导出该配方")
    catalog = HalfCatalog(builder)
    catalog.add(half)
    whole = catalog.join(builder.rules.parse("Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu"))
    if whole is None:
        raise RuntimeError("已登记H的半形凭据，仍未构造出V")
    milestones = (("独立柱拼成准备形S", prepared), ("切掉q1辅助晶体得到A", released),
                  ("无晶体阶梯B", scaffold), ("A与B拼接", merged), ("切出非K半形H", half))
    return [
        Example("6q-H", "可制造的非K稳定半形", "晶体框架与内部普通格互相阻挡；支撑环不通地面，也不含针。", 6, half, milestones),
        Example("6q-V", "交换后不稳定的成品", "独立制造两份H，第二份转三个象限，再交换。交换后不追加重力；新连接会在下一次加工时改变分组。", 6, whole,
                (("每份H单独制造", half), ("第二份H旋转三个象限", whole.inputs[1]), ("最终交换输出V", whole))),
    ]


def export(example: Example, output: Path) -> tuple[str, str, int]:
    """输出消费式步骤及全部中间图形码；同一配方引用展开为独立物品。"""
    steps = list(example.recipe.steps())
    document = {"name": example.name, "title": example.title, "mechanism": example.mechanism,
                "quadrants": example.quadrants, "height": 5, "target": example.recipe.result.to_key(),
                "evidence": "按既有证明构造并由Python加工模型计算中间产物；未在游戏或Mod中验证。",
                "milestones": [{"name": name, "result": recipe.result.to_key()} for name, recipe in example.milestones],
                "steps": steps}
    stem = output / example.name
    stem.with_suffix(".json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {example.title}", "", example.mechanism, "", f"配置：{example.quadrants}象限、五层上限。",
             "", "目标（从底到顶，q0为每层最左格）：", "", f"`{example.recipe.result.to_key()}`", "",
             f"共{len(steps)}步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。",
             "同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。", "",
             "[操作与方向说明](README.md)；本配方未在游戏中验证。", ""]
    if example.milestones:
        lines += ["## 关键阶段", "", "| 阶段 | 结果 |", "|---|---|"]
        lines += [f"| {name} | `{recipe.result.to_key()}` |" for name, recipe in example.milestones]
        lines.append("")
    lines += ["## 完整步骤", "", "| 编号 | 加工 | 输入编号 | 参数 | 产物 |", "|---:|---|---|---|---|"]
    for step in steps:
        inputs = ", ".join(str(index) for index in step["inputs"]) or "—"
        parameter = "—" if step["parameter"] is None else str(step["parameter"])
        lines.append(f"| {step['id']} | {step['operation']} | {inputs} | {parameter} | `{step['result']}` |")
    stem.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return example.name, example.title, len(steps)


def main() -> int:
    """一次导出八个固定例子，供用户手工复现特殊制造机制。"""
    parser = argparse.ArgumentParser(description="导出四象限间隙及六象限非K/非稳定代表图形的制造步骤")
    parser.add_argument("--output", type=Path, required=True, help="代表配方的输出目录")
    args = parser.parse_args()
    examples = corner_examples() + wide_half_examples()
    args.output.mkdir(parents=True, exist_ok=True)
    for example in examples:
        name, title, count = export(example, args.output)
        print(f"{name}：{title}，{count}步 → {args.output / (name + '.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
