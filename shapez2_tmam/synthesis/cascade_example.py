"""导出十八象限十七层的三次级联配方、短代码和逐步格子图。"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .construct import Constructor
from .examples import Example, export
from .physics import EMPTY, PIN, Rules, Shape


NAME = "18q17l-cascade"
OPERATIONS = {"base": "基础供料", "stack": "堆叠", "crystal": "结晶",
              "rotate": "旋转", "cut": "切割", "swap": "交换", "pin": "顶针"}


def cascade_example() -> Example:
    """从稳定半形D制造S，再用三份真实纯C上料依次触发下落。"""
    rules = Rules(18, 17)
    constructor = Constructor(rules)
    builder = constructor.builder
    cells = {(0, 0): "Su", (0, 8): "Su"}
    for j in range(1, 4):
        bottom, right, inner = 20 - 6 * j, 2 * j + 2, 2 * j
        for z in range(bottom, bottom + 3):
            cells[z, 0] = cells[z, right] = "cr"
        for q in range(1, right):
            cells[bottom, q] = "Su"
        cells[bottom + 1, inner] = "Su"
        cells[bottom + 2, inner] = cells[bottom + 2, inner + 1] = "Su"
        if j > 1:
            cells[bottom + 3, 0] = cells[bottom + 4, 0] = "Su"
    target = rules.fold(cells)
    assert target is not None
    prepared = constructor.half(target)
    if prepared is None:
        raise RuntimeError("三次级联的稳定准备形D未取得通用半形制造配方")
    trigger = builder.base(tuple("Su" if q == 1 else EMPTY for q in range(18)))
    result = builder.apply("stack", prepared, trigger)
    milestones = [("稳定准备形 D", prepared), ("级联起点 S", result)]
    pure_crystal = builder.apply("crystal", builder.base((PIN,) * 18), parameter="r")
    for number, remaining in ((1, 12), (2, 6), (3, 0)):
        result = builder.apply("stack", result, pure_crystal)
        count = sum(cell[0] == "c" for row in result.result.layers for cell in row)
        if count != remaining:
            raise RuntimeError(f"第{number}次下落得到{count}颗晶体，与证明中的{remaining}颗不符；停止导出")
        milestones.append((f"第{number}次下落结果", result))
    return Example(NAME, "十八象限十七层：三次下落才稳定",
                   "先用递归脚手架制造三个稳定支撑环D，追加q1单格普通料得到S；"
                   "随后连续三次堆叠单层纯红晶体，晶体数依次为18、12、6、0。",
                   18, result, tuple(milestones))


class GridImages:
    """以固定格距绘制全部18列和17层，空层与空列保留原位置。"""

    def __init__(self, font: Path):
        """加载四种字号，分页绘图复用字体对象。"""
        self.fonts = {size: ImageFont.truetype(str(font), size) for size in (12, 15, 18, 22)}

    def panel(self, shape: Shape, title: str, subtitle: str, cell_size: int) -> Image.Image:
        """绘制一个带坐标、材料字母和晶体数的图形卡片。"""
        width, height = 18 * cell_size + 66, 17 * cell_size + 106
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width - 1, height - 1), outline="#d8dee6", width=2)
        draw.text((12, 8), title, font=self.fonts[18], fill="#172a40")
        draw.text((12, 34), subtitle, font=self.fonts[12], fill="#526477")
        left, top = 38, 76
        for q in range(18):
            draw.text((left + (q + .5) * cell_size, top - 12), str(q),
                      font=self.fonts[12], fill="#687989", anchor="mm")
        for z in range(17):
            y = top + (16 - z) * cell_size
            draw.text((25, y + cell_size / 2), str(z), font=self.fonts[12], fill="#687989", anchor="mm")
            for q in range(18):
                cell = shape.layers[z][q] if z < len(shape.layers) else EMPTY
                x = left + q * cell_size
                fill, label = "#fafbfd", ""
                if cell == PIN:
                    fill, label = "#7476bd", "P"
                elif cell != EMPTY:
                    fill = "#ff3864" if cell[0] == "c" else "#a6b9c9"
                    label = "C" if cell[0] == "c" else cell[0]
                draw.rectangle((x, y, x + cell_size - 1, y + cell_size - 1), fill=fill, outline="#edf0f4")
                if label:
                    draw.text((x + cell_size / 2, y + cell_size / 2), label,
                              font=self.fonts[15], fill="white", anchor="mm")
        crystals = sum(cell[0] == "c" for row in shape.layers for cell in row)
        draw.text((12, height - 24), f"17层 × 18象限  |  晶体 {crystals}  |  层号从0开始",
                  font=self.fonts[12], fill="#526477")
        return image

    def overview(self, stages: list[dict], output: Path) -> None:
        """输出单阶段PNG及带操作箭头的纵向总览，保持标准朝向。"""
        rules = Rules(18, 17)
        subtitles = ("从基础料制造；完整步骤见分页图", "D + q1单格方块；本次不合并新接触",
                     "S + 单层纯晶体；顶级碎裂", "上一步 + 单层纯晶体；中级碎裂",
                     "上一步 + 单层纯晶体；底级碎裂，达到稳定")
        cards = []
        for index, (stage, subtitle) in enumerate(zip(stages, subtitles, strict=True)):
            card = self.panel(rules.parse(stage["result"]), f"#{index} {stage['name']}", subtitle, 24)
            card.save(output / f"stage-{index}.png")
            cards.append(card)
        width, height = cards[0].size
        image = Image.new("RGB", (width + 32, len(cards) * (height + 66) + 62), "#f5f7fb")
        draw = ImageDraw.Draw(image)
        draw.text((16, 14), "三次下落级联 · 制作与加工总览", font=self.fonts[22], fill="#172a40")
        for index, card in enumerate(cards):
            y = 62 + index * (height + 66)
            image.paste(card, (16, y))
            if index + 1 < len(cards):
                x, arrow_top = (width + 32) // 2, y + height + 10
                draw.line((x, arrow_top, x, arrow_top + 36), fill="#5c45ee", width=3)
                draw.polygon(((x - 7, arrow_top + 28), (x + 7, arrow_top + 28), (x, arrow_top + 40)), fill="#5c45ee")
        image.save(output / "overview.png")

    def pages(self, steps: list[dict], output: Path) -> list[str]:
        """每页九步；输入编号、参数和产物朝向来自同一份消费式配方。"""
        rules = Rules(18, 17)
        files = []
        for start in range(0, len(steps), 9):
            cards = []
            for step in steps[start:start + 9]:
                inputs = ",".join(str(value) for value in step["inputs"]) or "无"
                parameter = "无" if step["parameter"] is None else str(step["parameter"])
                card = self.panel(rules.parse(step["result"]), f"步骤 {step['id']} · {OPERATIONS[step['operation']]}",
                                  f"输入编号 {inputs}  |  参数 {parameter}", 18)
                cards.append(card)
            width, height = cards[0].size
            image = Image.new("RGB", (3 * (width + 12) + 12, 3 * (height + 12) + 62), "#f5f7fb")
            draw = ImageDraw.Draw(image)
            draw.text((12, 10), f"完整制作过程 · 步骤 {start}–{start + len(cards) - 1} / 共{len(steps)}步",
                      font=self.fonts[22], fill="#172a40")
            for index, card in enumerate(cards):
                image.paste(card, (12 + index % 3 * (width + 12), 50 + index // 3 * (height + 12)))
            name = f"steps-{start // 9 + 1:03d}.png"
            image.save(output / name)
            files.append(name)
        return files


def main() -> int:
    """生成此固定代表的文字、JSON和PNG交付物，不运行搜索或其他代表。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="examples输出目录")
    parser.add_argument("--font", type=Path, default=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                        help="支持中文的字体文件")
    args = parser.parse_args()
    renderer = GridImages(args.font)
    example = cascade_example()
    args.output.mkdir(parents=True, exist_ok=True)
    export(example, args.output)
    document = json.loads((args.output / f"{NAME}.json").read_text(encoding="utf-8"))
    assets = args.output / NAME
    assets.mkdir(exist_ok=True)
    stages = document["milestones"]
    renderer.overview(stages, assets)
    pages = renderer.pages(document["steps"], assets)
    codes = [(stage["name"], stage["result"]) for stage in stages]
    codes += [("启动料：q1单格方块", EMPTY + "Su" + EMPTY * 16),
              ("纯晶体准备：整圈单层针", PIN * 18), ("每次下落上料：单层纯红晶体", "cr" * 18)]
    (assets / "shortcodes.txt").write_text("\n\n".join(f"{name}\n{key}" for name, key in codes) + "\n", encoding="utf-8")
    lines = ["# 三次下落：短代码和格子制作图", "",
             "配置为18象限、17层上限。每格代表一个象限；列从左到右为q0至q17，层从下到上为0至16。",
             "红色C为晶体；灰蓝S为普通方块、C为普通圆块；紫色P为针。格子颜色用来区分材料，不表示全部加工颜色。",
             "短代码按底层到顶层排列，冒号分层；空底层和中间空层必须保留。", "",
             "![制作与三次下落总览](overview.png)", "", "## 制作顺序", "",
             "1. 按下方完整步骤图，从无晶体单层基础料制造稳定准备形D。",
             "2. 把q1单格方块堆到D上，得到级联起点S。",
             "3. 准备一层18格针，用红色结晶得到单层纯红晶体。",
             "4. 连续三次把一份纯晶体层作为上料堆到当前物品上，晶体数依次18→12→6→0。每次重新准备一份上料。", "",
             f"完整配方共{len(document['steps'])}步，物品槽峰值{document['register_count']}；含供料，不是最短路径。",
             f"[完整文字步骤](../{NAME}.md) · [全部步骤JSON](../{NAME}.json) · [一行式短代码文本](shortcodes.txt)", "",
             "Stack输入顺序为下料、上料。Rotate参数按象限计，一格为20°。Cut出口0留q0至q8、出口1留q9至q17。",
             "Swap出口0取第一输入前半和第二输入后半，出口1反之。使用后的输入物品消耗，未选出口弃置。",
             "基础供料必须按对应格子准备；其余加工不要省略。分页图与完整文字步骤朝向一致，总览显示标准朝向。", "",
             "## 各阶段短代码", ""]
    for name, key in codes:
        lines += [f"### {name}", "", "```text", key, "```", ""]
    lines += ["## 全部制作步骤格子图", "", "每页九步，先从左到右，再从上到下。输入编号对应先前步骤的产物。", ""]
    for number, page in enumerate(pages, 1):
        lines += [f"### 第{number}页", "", f"![第{number}页制作步骤]({page})", ""]
    lines += ["## 依据", "", "[级联构造证明](../../proofs/05-cascades.md#s05-01)。固定配方及中间产物由本地模型导出，未在游戏或Mod中验证。", ""]
    (assets / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(document['steps'])}步，{document['register_count']}槽，{len(pages)}页格子图 → {assets / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
