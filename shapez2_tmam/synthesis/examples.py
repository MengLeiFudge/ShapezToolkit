"""导出固定代表构造的逐步配方；不枚举目标，也不运行完整搜索。"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .construct import Constructor
from .corners import CornerBuilder
from .half_catalog import HalfCatalog
from .orientation import optimize_rotations
from .physics import EMPTY, PIN, Rules
from .recipe import Builder, Recipe
from .stack_reduction import ordinary_stack, single_stack
from .stack_plan import StackCatalog, stack_plan


@dataclass(frozen=True)
class Example:
    """一个特殊机制及其实际加工树；里程碑用于阅读长配方。"""

    name: str
    title: str
    mechanism: str
    quadrants: int
    recipe: Recipe
    milestones: tuple[tuple[str, Recipe], ...] = ()


def whole_shape_examples() -> list[Example]:
    """固定完整目标共用双半形入口；四象限是完整主流程代表，六象限仅示范已覆盖域。"""
    examples = []
    for n, name, title, key in (
        (4, "4q-whole", "四象限完整目标：共用双半形制造",
         "--P-CuCu:CuCu--P-:--CucrCu:--P---Cu:crCu--Cu"),
        (6, "6q-whole", "六象限完整目标：通用脚手架拼出双环",
         "Cu----Cu----:------------:crCuCucrCuCu:cr--Cucr--Cu:crCuCucrCuCu"),
    ):
        constructor = Constructor(Rules(n))
        target = constructor.rules.parse(key)
        recipe = constructor.paired_halves(target, 0)
        if recipe is None:
            raise RuntimeError("固定完整代表未取得双半形制造证书")
        half = constructor.rules.fold({pos: cell for pos, cell in constructor.rules.cells(target).items()
                                      if pos[1] < n // 2})
        assert half is not None
        first = constructor.half(half)
        assert first is not None
        mechanism = ("两种角加工在同一完整目标内调用；按同一半形程序制造两侧后拼合。"
                     "这是统一整图流程的一个输入，角的差异不再计为整图类别。" if n == 4 else
                     "两侧均由通用角和普通脚手架制造H，再共用双半形入口拼接。"
                     "最终双环重新分组后不稳定，拼接后直接输出，不追加重力；本例不代表全部六象限已覆盖。")
        examples.append(Example(name, title, mechanism, n, recipe,
                                (("第一半形", first), ("两半形拼接成品", recipe))))
    return examples


def tail_pin_example() -> Example:
    """零尾Pin已由两侧悬空N排除；从明确双半形起点导出一次Pin配方。"""
    constructor = Constructor(Rules(4))
    source = constructor.rules.parse("Cu--cr--:crCucrCu:----cr--:----cr--:----cr--")
    prepared = constructor.paired_halves(source, 0)
    if prepared is None:
        raise RuntimeError("一次尾部Pin代表没有取得双半形起点")
    result = constructor.builder.apply("pin", prepared)
    target = constructor.rules.parse("P---P---:Cu------:crCu--Cu")
    if result.result != target:
        raise RuntimeError("一次尾部Pin没有产生两侧悬空N的完整目标")
    return Example("4q-required-tail-pin", "四象限完整目标：一次尾部顶针不可省",
                   "先拼接两个稳定半形，再顶破q2辅助晶体塔。两侧悬空N都必须在零尾起点中，"
                   "但任何两列分割都会使其中一侧失去晶体支撑，所以目标不能只由双半形加普通料追加得到。",
                   4, result, (("双半形起点", prepared), ("一次尾部Pin成品", result)))


def multicrystal_half_example() -> Example:
    """用同一个递归脚手架制造含两根晶体列的环，再拼接两份完整半形。"""
    constructor = Constructor(Rules(6))
    target = constructor.rules.parse(
        "Cu----Cu----:------------:crCuCucrCuCu:cr--crcr--cr:crCuCucrCuCu")
    result = constructor.paired_halves(target, 0)
    if result is None:
        raise RuntimeError("多晶体列双环未取得递归脚手架制造证书")
    half = constructor.rules.parse("Cu----------:------------:crCuCu------:cr--cr------:crCuCu------")
    prepared = constructor.half(half)
    assert prepared is not None
    return Example("6q-multicrystal-loop", "六象限完整目标：多晶体列共用脚手架",
                   "把H内侧的普通格改为晶体，两个不同晶体组仍互相支撑。脚手架逐列接管支撑，"
                   "反向反复调用同一角程序；两份半形最后拼接，不追加重力。",
                   6, result, (("两个晶体组互相支撑的半形", prepared), ("双半形拼接成品", result)))


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
    exchange = whole.inputs[0] if whole.operation == "rotate" else whole
    settled = ordinary_stack(builder, whole, builder.rules.parse("CuCuCuCuCuCu:----CuCu--Cu:--CuCu--CuCu"))
    if settled is None:
        raise RuntimeError("V再次堆叠的代表目标未取得单次普通追加配方")
    column = builder.column(("Cu", "Cu"), 3)
    assert column is not None
    lower = builder.apply("stack", half, column)
    pin_tail = single_stack(builder, lower, builder.rules.parse("Cu----CuCu--:------Cu----:crCuCuP-----:cr--Cu------:crCuCu------"))
    if pin_tail is None:
        raise RuntimeError("六象限针尾代表未取得单次堆叠配方")
    stack_catalog = StackCatalog(builder)
    stack_catalog.add(half)
    turned = builder.apply("rotate", half, parameter=3)
    stack_catalog.add(turned)
    compact = stack_catalog.construct(builder.rules.parse("Cu----Cu----:------------:------crCuCu:------cr--Cu:------crCuCu"))
    if compact is None:
        raise RuntimeError("六象限上料摘要未生成代表配方")
    column = builder.column(("Cu", "Cu"), 5)
    assert column is not None
    interleaved_lower = builder.apply("stack", half, column)
    interleaved = single_stack(builder, interleaved_lower, builder.rules.parse(
        "Cu----Cu--Cu:----------Cu:crCuCu----Cu:cr--Cu----P-:crCuCu----Cu"))
    if interleaved is None:
        raise RuntimeError("六象限紧凑交错上料未生成代表配方")
    milestones = (("独立柱拼成准备形S", prepared), ("切掉q1辅助晶体得到A", released),
                  ("无晶体阶梯B", scaffold), ("A与B拼接", merged), ("切出非K半形H", half))
    return [
        Example("6q-H", "可制造的非K稳定半形", "晶体框架与内部普通格互相阻挡；支撑环不通地面，也不含针。", 6, half, milestones),
        Example("6q-V", "交换后不稳定的成品", "独立制造两份H，选择输入方向再交换。交换后不追加重力；新连接会在下一次加工时改变分组。", 6, whole,
                (("每份H单独制造", half), ("交换的第二份输入", exchange.inputs[1]), ("最终交换输出V", whole))),
        Example("6q-V-stack", "不稳定成品再次加工后的变化", "以V作下料，追加q3单格普通料。下料本次重新分组，悬空晶体破碎，普通格落下；新增普通格落在q3第二层。", 6, settled,
                (("加工前的V", whole), ("上料", settled.inputs[1]), ("一次堆叠后的成品", settled))),
        Example("6q-pin-tail", "非K下料追加普通格和针尾", "H旁先准备q3两层普通柱；一次堆叠同时加入q4地面普通格与q3第三层针。独立下落把上料缩成一层N/P基础料，无需辅助晶体。", 6, pin_tail,
                (("已有非K下料", lower), ("紧凑基础上料", pin_tail.inputs[1]), ("一次堆叠成品", pin_tail))),
        Example("6q-upper-summary", "复杂上料等价替换为单格基础料",
                "H作上料时，悬空框架永远留在高度上限外；对任意下料仅留下q0普通格。用一份单格基础料替代整个H的上料准备，再堆到原下料。", 6, compact,
                (("原本考虑的复杂上料H", half), ("已有旋转半形下料", turned), ("等价基础上料", compact.inputs[1]),
                 ("堆叠成品", compact))),
        Example("6q-compact-interleaved", "非K下料上的紧凑交错上料",
                f"H旁准备q5两层普通柱；目标新增q3地面普通格及q5的NPN高尾。先让新增格独立下落，得到{interleaved.inputs[1].step_count}步准备的三层无晶体上料，再一次堆到原下料。",
                6, interleaved, (("已有非K下料", interleaved_lower), ("紧凑无晶体上料", interleaved.inputs[1]),
                                 ("一次堆叠成品", interleaved))),
    ]


def multiblock_summary_example() -> Example:
    """含辅助C的四块上料，按摘要改用唯一无C载体。"""
    builder = Builder(Rules(6))
    source = builder.independent_columns(builder.rules.parse(
        "cr----Cu----:cr----P-----:cr----Cu----:Cu----------"))
    assert source is not None
    lower = builder.base(("Cu", EMPTY, EMPTY, EMPTY, EMPTY, EMPTY))
    catalog = StackCatalog(builder)
    catalog.add(source)
    catalog.add(lower)
    result = catalog.construct(builder.rules.parse("Cu----Cu----:Cu----P-----:------Cu----"))
    if result is None:
        raise RuntimeError("六象限多块摘要未生成无晶体替换配方")
    return Example("6q-multiblock-summary", "多块复杂上料替换为无晶体载体",
                   "原上料q0为CCCN、q3为NPN；辅助C抬高后全碎。摘要落地时四块不合并，改用q0地面N和q3的NPN，五步准备后堆到q0单N下料。",
                   6, result, (("原复杂上料", source), ("同摘要无晶体上料", result.inputs[1]),
                               ("一次堆叠成品", result)))


def crystal_summary_example() -> Example:
    """无同摘要无C载体时，缩短辅助C前缀，保持任意下料上的效果。"""
    builder = Builder(Rules(6))
    source = builder.independent_columns(builder.rules.parse(
        "Cucr--Cu----:--cr--P-----:--cr--Cu----:--Cu--------"))
    lower = builder.column(("Cu",) * 3, 1)
    assert source is not None and lower is not None
    catalog = StackCatalog(builder)
    catalog.add(source)
    catalog.add(lower)
    result = catalog.construct(builder.rules.parse("CuCu--Cu----:--Cu--P-----:--Cu--Cu----:--Cu--------"))
    if result is None:
        raise RuntimeError("六象限含晶体摘要未生成紧凑替换配方")
    return Example("6q-crystal-summary", "含晶体上料按摘要缩短辅助前缀",
                   "原上料q0为单N、q1为CCCN、q3为NPN；无C落地会粘合q0/q1。保留块及列内次序，把q1缩成CN，其余不变，再堆到q1三层普通柱。替换对任意下料都等效。",
                   6, result, (("原复杂上料", source), ("原下料", lower),
                               ("同摘要紧凑上料", result.inputs[1]), ("一次堆叠成品", result)))


def colored_summary_example() -> Example:
    """六个独立普通块改用两层交错载体，避免规范序引入六层阶梯。"""
    builder = Builder(Rules(6))
    source = builder.independent_columns(builder.rules.parse(
        "Cucrcrcrcrcr:--CucrcrcrCu:----Cucrcr--:------Cucr--:--------Cu--"))
    assert source is not None
    catalog = StackCatalog(builder)
    catalog.add(source)
    result = catalog.uppers[stack_plan(builder.rules, source.result)]
    if result.result != builder.rules.parse("CucrCucrCucr:--Cu--Cu--Cu"):
        raise RuntimeError("六象限同秩着色未产生两层交错上料")
    return Example("6q-colored-summary", "同秩块交错排列，五层上料缩成两层",
                   "原五层上料在每列各释放一个独立普通格。按象限编号保序需六层，超过上限；同秩块两色交错后只需两层。底层用普通格与针交错供料并结晶，再追加奇数列普通格，共四步；作为上料对任意下料均与原物品等效。",
                   6, result, (("原五层上料", source), ("两层交错上料", result)))


def interleaved_stack_example() -> Example:
    """紧凑上料会横向粘合，改用带独立NPN列的补C载体。"""
    builder = Builder(Rules(6))
    lower = builder.column(("Cu",) * 3, 1)
    assert lower is not None
    materials = {"-": EMPTY, "N": "Cu", "P": PIN}
    rows = ("NN-N--", "-N-P--", "-N-N--", "-N----")
    target = builder.rules.parse(":".join("".join(materials[cell] for cell in row) for row in rows))
    result = single_stack(builder, lower, target)
    if result is None:
        raise RuntimeError("六象限补C交错上料未生成代表配方")
    return Example("6q-crystal-interleaved", "补晶体载体保留交错普通格与针",
                   "q1三层普通柱作下料；追加q0地面N、q1第四层N及q3的NPN。紧凑候选会把q0/q1粘合，故用q0单N、q1的CCCN与q3的NPN组成上料，辅助C在一次堆叠中碎裂。",
                   6, result, (("原下料", lower), ("补C交错上料", result.inputs[1]), ("一次堆叠成品", result)))


def packed_stack_example() -> Example:
    """旧两种载体均失败的交错上料；列内压紧后只在列底补晶体。"""
    builder = Builder(Rules(6))
    lower = builder.noncrystal(builder.rules.parse(
        "--Cu----Cu--:--Cu----Cu--:--Cu----Cu--:--Cu--------"))
    assert lower is not None
    materials = {"-": EMPTY, "N": "Cu", "P": PIN}
    rows = ("NN-NN-", "-N-PN-", "-N--N-", "-N-NN-", "-N----")
    target = builder.rules.parse(":".join("".join(materials[cell] for cell in row) for row in rows))
    result = single_stack(builder, lower, target)
    if result is None:
        raise RuntimeError("六象限列内压紧上料未生成代表配方")
    return Example("6q-packed-columns", "列内压紧后用晶体前缀对齐普通块",
                   "q1四层柱与q4三层柱作下料。自由下落会粘错q0/q1，原位补C会产生q3的N-P-C-N；改把q3压成NPN，q4用CCN与其顶端对齐，再一次堆叠。",
                   6, result, (("原下料", lower), ("压紧后的三层上料", result.inputs[1]), ("一次堆叠成品", result)))


def layered_stack_example() -> Example:
    """NPN与NN共享底顶普通块，保留针下C间隙解除全列压紧的冲突。"""
    builder = Builder(Rules(6))
    lower = builder.noncrystal(builder.rules.parse(
        "--Cu------Cu:--Cu------Cu:--Cu------Cu:--Cu--------"))
    assert lower is not None
    materials = {"-": EMPTY, "N": "Cu", "P": PIN}
    rows = ("NN-NNN", "-N-P-N", "-N---N", "-N-NNN", "-N----")
    target = builder.rules.parse(":".join("".join(materials[cell] for cell in row) for row in rows))
    result = single_stack(builder, lower, target)
    if result is None:
        raise RuntimeError("六象限针下间隙载体未生成代表配方")
    return Example("6q-layer-constraints", "用针下晶体间隙解除上料对齐冲突",
                   "q1四层柱与q5三层柱作下料。q3的NPN与q4的NN共享底顶普通块，不能同时全列压紧；改造NPN、NCN、CCN三列并对齐顶端，辅助C在一次堆叠中碎裂。",
                   6, result, (("原下料", lower), ("保留针下晶体间隙的三层上料", result.inputs[1]), ("一次堆叠成品", result)))


def pin_prefix_stack_example() -> Example:
    """初始针固定触地，使PNN可以补成PNCN并与邻列NPN对齐。"""
    builder = Builder(Rules(6))
    lower = builder.noncrystal(builder.rules.parse(
        "--Cu--CuCu--:--Cu----Cu--:--Cu--------:--Cu--------"))
    assert lower is not None
    materials = {"-": EMPTY, "N": "Cu", "P": PIN}
    rows = ("NN-NN-", "-N-PN-", "-N-NN-", "-N--P-", "-N-NN-")
    target = builder.rules.parse(":".join("".join(materials[cell] for cell in row) for row in rows))
    result = single_stack(builder, lower, target)
    if result is None:
        raise RuntimeError("六象限触地针前缀上料未生成代表配方")
    return Example("6q-ground-pin-prefix", "固定触地针前缀以保留中间晶体",
                   "已有q1四层柱、q3地面N及q4两层柱；上料把q3做成P-N-C-N、q4做成C-N-P-N。q3初始针触地，使其中间晶体可制造，并让两列普通块对齐。",
                   6, result, (("原下料", lower), ("触地针前缀的四层上料", result.inputs[1]), ("一次堆叠成品", result)))


def two_quadrant_example() -> Example:
    """两象限六层：先拼连续晶体以下前缀，再让普通上层跨列支撑。"""
    rules = Rules(2, 6)
    expected = rules.parse("P-Cu:crP-:CuCu:cr--:CuCu:--P-")
    result = Constructor(rules).construct(expected).recipe
    if result is None or result.result != expected:
        raise RuntimeError("两象限完整构造未产生代表目标；不能导出该配方")
    bridged = result.inputs[0]
    prefix = bridged.inputs[0]
    return Example("2q6l-crystal-prefix", "两象限的连续前缀与上方跨列支撑",
                   "最高晶体以下先造两根连续柱；再用双普通格跨过较短列的空隙，最后补针。最高晶体上方允许这种间隙。",
                   2, result, (("最高晶体以下前缀", prefix), ("跨列普通上层", bridged), ("补针后的目标", result)))


def pin_framed_rectangle_example() -> Example:
    """五层矩形用共同针前缀及交错N/P后缀包住同色段核心。"""
    rules = Rules(6)
    target = rules.parse("P-P-P-P-P-P-:crCucrCucrCu:CucrCucrCucr:cbCucbCucbCu:CuP-CuP-CuP-")
    result = Builder(rules).rectangular_columns(target)
    if result is None or result.result != target:
        raise RuntimeError("六象限带针矩形未生成并行制造代表配方")
    return Example("6q-pin-framed-rectangle", "共同针前缀与交错后缀的并行制造",
                   "先制造三层红蓝晶体核心，再一次顶针补齐六列地面针，最后追加交错普通格和针的一层。永久针在全部结晶完成后加入。",
                   6, result)


def grouped_columns_example() -> Example:
    """半面混色不能整体结晶时，仍合并相邻同模板的两列。"""
    rules = Rules(6)
    target = rules.parse("CuSrCuCuCuCu:crcrcbCuCuCu")
    result = Builder(rules).independent_columns(target)
    if result is None or result.result != target:
        raise RuntimeError("六象限相邻列分组未生成代表配方")
    return Example("6q-grouped-columns", "半面混色时合并相邻兼容列",
                   "q0/q1普通部件不同，但晶体层均为红色，两列一起制造；q2单独蓝色结晶。另一半面直接堆叠普通料，最后交换拼合。",
                   6, result)


def rectangular_example() -> Example:
    """同色的多行晶体共用结晶加工，六列三层直接制造。"""
    rules = Rules(6)
    target = rules.parse("crCucrCucrCu:CucrCucrCucr:cbCucbCucbCu")
    result = Builder(rules).rectangular_columns(target)
    if result is None or result.result != target:
        raise RuntimeError("六象限同色层未生成并行列代表配方")
    return Example("6q-rectangular-columns", "同层同色晶体的六列并行制造",
                   "前两层交错位置先用针占位，再统一红色结晶；第三层单独蓝色结晶，已有晶体颜色保持。完整六列逐层制造，无需切割、交换或旋转。",
                   6, result)


def replicated_stack_example() -> Example:
    """四象限间隙构造扩张到八象限，复制块边界相对q0偏移一列。"""
    rules = Rules(8)
    small = Rules(4).parse("CuCu----:--P-----:crCu----:--Cu----:--Cu----")
    expanded = rules.parse(":".join("".join(cell * 2 for cell in row) for row in small.layers))
    target = rules.rotate(expanded, 1)
    source = Constructor(Rules(4)).construct(small).recipe
    assert source is not None
    builder = Builder(rules)
    result = builder.apply("rotate", builder.replicate(source), parameter=1)
    if result is None or result.result != target:
        raise RuntimeError("八象限复制商图未生成间隙代表配方")
    return Example("8q-replicated-gap", "把四象限晶体间隙配方提升到八象限",
                   "目标每两列相同，复制块从q1开始。先压回四象限求角构造，再逐节点复制象限并把旋转参数乘二，最后恢复目标方向。中间图形由已证操作对应直接扩张。",
                   8, result)


def protected_half_example() -> Example:
    """展开八象限W_4；内块两侧列顶封住后续普通块的粘合入口。"""
    builder = Builder(Rules(8))
    spine = builder.dense_column(("cr", "Cu", "cr", "cr", "cr"), 0)
    fuse = builder.dense_column(("cr",), 1)
    support = builder.column(("Cu", PIN, "Cu", "Cu", "Cu"), 7)
    assert support is not None
    prepared = builder.join(builder.join(spine, fuse, 5), support, 0)
    released = builder.window(prepared, 5)
    scaffold = None
    for columns in ((4,), (4,), (1, 2, 3, 4), (2,), (1, 2, 3)):
        layer = builder.base(tuple("Cu" if q in columns else EMPTY for q in range(8)))
        scaffold = layer if scaffold is None else builder.apply("stack", scaffold, layer)
    assert scaffold is not None
    merged = builder.join(released, scaffold, 5)
    result = builder.window(merged, 0)
    expected = builder.rules.parse(
        "Cu--------------:----------------:crCuCuCu--------:cr--Cu----------:crCuCuCu--------")
    if result.result != expected:
        raise RuntimeError("八象限受保护普通块构造未产生W_4；不能导出该配方")
    return Example("8q-protected-loop", "普通内块受列顶保护的悬空环",
                   "外组与q2第四层普通块互相支撑；内块两侧q1、q3列顶均在第五层，后续从上方加料无法粘到内块。它不属于K，但可安全逐层追加。",
                   8, result, (("独立柱准备形", prepared), ("切掉牺牲晶体的A", released),
                               ("带q2内块的脚手架", scaffold), ("切掉外侧支撑前", merged), ("受保护悬空环W_4", result)))


def general_stack_example() -> Example:
    """八象限八层的非K下料；双层普通上料必须保持同一次堆叠。"""
    builder = Builder(Rules(8, 8))
    columns = (("cr", "Cu", "cr", "cr", "cr"), ("cr",), ("cr", "cr"), ("cr",),
               ("cr", "Cu", "cr", "cr", "cr"), ("cr",), ("cr",) * 8, ("cr",))
    shape = builder.rules.fold({(z, q): cell for q, column in enumerate(columns) for z, cell in enumerate(column)})
    assert shape is not None
    seed = builder.independent_columns(shape)
    assert seed is not None
    frame = seed
    for mask in ((1, 2, 3), (2,), (2, 3)):
        frame = builder.apply("stack", frame, builder.base(tuple("Cu" if q in mask else EMPTY for q in range(8))))
    lower = builder.apply("pin", frame)
    materials = {"-": EMPTY, "N": "Cu", "P": PIN, "C": "cr"}
    rows = ("PPPPPPPP", "N---N---", "--------", "CNNNC---", "CNN-C---", "CNNNC---")
    target = builder.rules.parse(":".join("".join(materials[cell] for cell in row) for row in rows))
    result = single_stack(builder, lower, target)
    if result is None:
        raise RuntimeError("八象限八层代表未取得单次堆叠配方")
    return Example("8q8l-single-stack", "八象限八层的单次复杂堆叠",
                   "准备过程使用八层晶体塔，顶破后得到非K下料S。把q1两层普通柱一次堆上去；拆成两次堆叠会让框架重新分组并碎裂。",
                   8, result, (("八层准备形", seed), ("添加框架后的D", frame), ("顶破后的S", lower),
                               ("双层普通上料", result.inputs[1]), ("一次堆叠成品", result)))


def export(example: Example, output: Path, *, instructions: bool = False) -> tuple[str, str, int]:
    """输出消费式步骤及全部中间图形码；同一配方引用展开为独立物品。"""
    recipe = optimize_rotations(example.recipe)
    steps = list(recipe.steps())
    document = {"name": example.name, "title": example.title, "mechanism": example.mechanism,
                "quadrants": example.quadrants, "height": example.recipe.height, "target": example.recipe.result.to_key(),
                "register_count": example.recipe.register_count,
                "evidence": "依据局部物理与已证配方变换生成中间产物；未在游戏或Mod中验证。",
                "milestone_orientation": "关键阶段按原构造的标准朝向示意，实际方向与物品编号见steps。" if example.milestones else None,
                "milestones": [{"name": name, "result": recipe.result.to_key()} for name, recipe in example.milestones],
                "steps": steps}
    stem = output / example.name
    stem.with_suffix(".json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if instructions and example.quadrants in (4, 6) and recipe.height == 5:
        packets = list(recipe.instructions())
        packet_document = {"name": example.name, "quadrants": example.quadrants, "height": recipe.height,
                           "target": recipe.result.to_key(), "source_steps": len(steps),
                           "register_budget": 6, "register_count": recipe.register_count,
                           "packet_count": len(packets), "instructions": packets,
                           "verification": "从已交付制造树编译消费式指令；未执行回放、反馈模拟或游戏。"}
        stem.with_suffix(".instructions.json").write_text(
            json.dumps(packet_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {example.title}", "", example.mechanism, "", f"配置：{example.quadrants}象限、{example.recipe.height}层上限。",
             "", "目标（从底到顶，q0为每层最左格）：", "", f"`{example.recipe.result.to_key()}`", "",
             f"共{len(steps)}步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。",
             f"物品槽峰值为{example.recipe.register_count}，不含搜索状态及传输缓存；[槽数调度证明](../research/proofs/04-stacking.md#s04-19)。",
             "同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。", "",
             "[操作与方向说明](README.md)；本配方未在游戏中验证。", ""]
    if example.milestones:
        lines += ["## 关键阶段", "", "以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。",
                  "", "| 阶段 | 结果 |", "|---|---|"]
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
    """导出固定例子，供用户手工复现特殊制造机制。"""
    parser = argparse.ArgumentParser(description="导出二/四/六/八象限代表图形的制造步骤")
    parser.add_argument("--output", type=Path, required=True, help="代表配方的输出目录")
    parser.add_argument("--instructions", action="store_true", help="另为四/六象限五层代表生成六槽指令包；其他配置仅导出步骤")
    args = parser.parse_args()
    examples = whole_shape_examples() + corner_examples() + wide_half_examples()
    examples.extend((tail_pin_example(), multicrystal_half_example(), interleaved_stack_example(), general_stack_example()))
    examples.extend((protected_half_example(), two_quadrant_example(), packed_stack_example(),
                     layered_stack_example(), pin_prefix_stack_example(), replicated_stack_example(), rectangular_example(),
                     pin_framed_rectangle_example(), grouped_columns_example(), multiblock_summary_example(),
                     crystal_summary_example(), colored_summary_example()))
    args.output.mkdir(parents=True, exist_ok=True)
    for example in examples:
        name, title, count = export(example, args.output, instructions=args.instructions)
        print(f"{name}：{title}，{count}步，{example.recipe.register_count}个物品槽 → {args.output / (name + '.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
