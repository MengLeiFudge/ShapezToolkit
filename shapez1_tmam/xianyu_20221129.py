"""XianYu-20221129 拆解器：逐 tick 选择部件，按加工模板制件，再尝试四种堆叠顺序。

控制器忠实保留存档的反馈与延迟；加工模板写成普通 Python 表达式。
求解不读取可制作图形数据库，也不需要游戏或原始存档。
"""

from dataclasses import dataclass
from functools import lru_cache

from . import xianyu_20221129_controller as controller
from .tmam_signals import FALSE, describe, from_key, from_structure, operate, to_key, valid_structure
from .tmam_verify import CircuitModel


@dataclass(frozen=True)
class Plan:
    """可执行的加工树；叶子只允许一层原料，堆叠参数依次为底部、顶部。"""

    value: int
    operation: str
    inputs: tuple["Plan", ...] = ()

    def as_dict(self) -> dict:
        return {"operation": self.operation, "shape": to_key(self.value),
                "inputs": [item.as_dict() for item in self.inputs]}


def raw(value: int) -> Plan:
    """以准备好的单层原料为叶子；角块可通过切割、旋转和同层拼合得到。"""
    key = to_key(value)
    if key is None or ":" in key:
        raise ValueError("加工树的原料必须是非空单层图形")
    return Plan(value, "raw")


def stack(bottom: Plan, top: Plan) -> Plan:
    return Plan(operate(50, bottom.value, top.value)[0], "stack", (bottom, top))


def rotate(piece: Plan, turns: int = 1) -> Plan:
    for _ in range(turns % 4):
        piece = Plan(operate(44, piece.value)[0], "rotate_cw", (piece,))
    return piece


def right_half(piece: Plan) -> Plan:
    return Plan(operate(42, piece.value)[1], "cut_right", (piece,))


@lru_cache(maxsize=4096)
def decode_recipe(recipe: int) -> Plan:
    """将指令翻译为加工树；标记层是控制信息，不能作为成品材料堆进去。

    指令 = 一或两层载荷 : 模板标记 : 朝向标记。
    朝向层中唯一的 R 决定逆时针转数，四个位置依次为右上、右下、左下、左上。
    存档先把载荷顺时针转三次，制件后再恢复朝向。
    """
    key = to_key(recipe)
    if key is None:
        raise ValueError("没有图形指令")
    layers = key.split(":")
    if len(layers) not in (3, 4):
        raise ValueError(f"指令层数不正确：{key}")
    payload, marker, direction = layers[:-2], layers[-2], layers[-1]
    directions = ("RuCuCuCu", "CuRuCuCu", "CuCuRuCu", "CuCuCuRu")
    if direction not in directions:
        raise ValueError(f"未知朝向标记：{direction}")
    turns = -directions.index(direction)
    value = from_key(":".join(payload))
    if marker == "SuSuSuSu":
        return rotate(raw(value), turns)

    # (103,-4)：统一把载荷转三次；此时左右两半分别成为两列。
    for _ in range(3):
        value = operate(44, value)[0]
    left, right = operate(42, value)
    support = raw(from_key("--RuRu--"))

    if marker in ("CrCrCrCr", "CbCbCbCb"):
        # 两个单层半片搭在同一支架的两侧。改变堆叠先后即可改变悬空方向。
        a = stack(raw(right), support)
        b = stack(support, raw(left))
        piece = stack(a, b) if marker == "CrCrCrCr" else stack(b, a)
        canonical = right_half(rotate(piece))
    elif marker in ("RrRrRrRr", "RbRbRbRb"):
        # 三层交错角。存档以四层圆填充再拆掉三层来读取底层；这里只读载荷底层。
        # UNSTACK 只解释指令，不是制造工序；交给 raw 的仍然都是单层原料。
        if marker == "RrRrRrRr":
            left_rest, left_top = operate(45, left)
            right_key = to_key(right)
            if right_key is None:
                raise ValueError("Rr 指令缺少右列")
            a = stack(support, raw(left_rest))
            b = stack(raw(from_key(right_key.split(":")[0])), support)
            c = stack(raw(left_top), support)
        else:
            right_rest, right_top = operate(45, right)
            left_key = to_key(left)
            if left_key is None:
                raise ValueError("Rb 指令缺少左列")
            a = stack(raw(right_rest), support)
            b = stack(support, raw(from_key(left_key.split(":")[0])))
            c = stack(raw(right_top), support)
        canonical = right_half(rotate(stack(stack(a, b), c)))
    elif marker in ("WrWrWrWr", "WbWbWbWb"):
        # 两列各两角的模板。红、蓝采用不同堆叠顺序和最后一片的放置方向。
        left_rest, left_top = operate(45, left)
        right_rest, right_top = operate(45, right)
        if marker == "WrWrWrWr":
            upper = stack(stack(support, raw(right_top)), stack(raw(left_top), support))
            lower = stack(stack(support, raw(right_rest)), stack(raw(left_rest), support))
            canonical = right_half(rotate(stack(lower, upper)))
        else:
            a = stack(raw(left_rest), support)
            b = stack(raw(right_rest), support)
            c = stack(raw(left_top), support)
            lower = rotate(stack(a, stack(b, c)))
            upper = stack(rotate(raw(right_top)), raw(from_key("----RuRu")))
            canonical = right_half(stack(lower, upper))
    else:
        raise ValueError(f"未知加工模板：{marker}")
    return rotate(canonical, turns)


def assembly_candidates(parts: tuple[int, ...]) -> tuple[int, ...]:
    """对应四条实际支路。空值旁路只放在存档具有旁路的位置，不能任意视作单位元。"""
    a, b, c, d, e = parts

    def s(bottom: int, top: int) -> int:
        return operate(50, bottom, top)[0]

    def optional(bottom: int, top: int) -> int:
        return s(bottom, top) if top else bottom

    de = optional(d, e)
    return (
        optional(a, optional(b, optional(c, de))),
        s(s(a, b), optional(c, de)),
        s(s(a, s(b, c)), de),
        optional(optional(optional(a, b), c), de),
    )


ASSEMBLY_TREES = (
    (0, (1, (2, (3, 4)))),
    ((0, 1), (2, (3, 4))),
    ((0, (1, 2)), (3, 4)),
    (((0, 1), 2), (3, 4)),
)


def assemble_plans(parts: tuple[Plan | None, ...], tree) -> Plan | None:
    """为已经通过实际支路核对的组合生成加工树，省去不存在的尾部部件。"""
    if isinstance(tree, int):
        return parts[tree]
    bottom, top = (assemble_plans(parts, branch) for branch in tree)
    if bottom is None:
        return top
    if top is None:
        return bottom
    return stack(bottom, top)


def build_controller() -> tuple[CircuitModel, dict[str, int]]:
    """把有名字的同步方程接到已核对游戏语义的 tick 执行器。"""
    slots = {name: index for index, (name, _) in enumerate(controller.INITIAL)}
    networks = []
    network_ids = {}
    gates = []
    for outputs, operation, *inputs in controller.EQUATIONS:
        pins = []
        for providers in inputs:
            if not providers:
                pins.append(-1)
                continue
            if providers not in network_ids:
                network_ids[providers] = len(networks)
                networks.append([slots[name] for name in providers])
            pins.append(network_ids[providers])
        gates.append({"code": operation, "inputs": pins, "outputs": [slots[name] for name in outputs]})
    initial = [value for _, value in controller.INITIAL]
    circuit = {
        "name": "XianYu-20221129", "save_sha256": controller.SAVE_SHA256,
        "gates": gates, "networks": networks, "initial": initial,
        "constants": {slots[name]: initial[slots[name]] for name in controller.CONSTANTS},
        "input": slots["target"], "enable": slots["enabled"],
        "outputs": [slots[f"output_{i}"] for i in range(1, 5)],
        "checks": [slots[f"check_{i}"] for i in range(1, 5)],
    }
    return CircuitModel(circuit), slots


class XianYu20221129:
    """独立求解每个输入；失败输入的循环状态不会污染下一个输入。"""

    def __init__(self, max_ticks: int = 4096):
        self.model, self.slots = build_controller()
        self.max_ticks = max_ticks
        circuit = self.model.circuit
        self.disabled = {circuit["enable"]: FALSE}
        reset = self.model.run(circuit["initial"][circuit["input"]], max_ticks,
                               overrides=self.disabled, trace=True)
        if reset["status"] != "fixed":
            raise RuntimeError("XianYu-20221129 关闭开关后未稳定")
        self.reset_slots = reset["final_slots"]
        comparisons = {slot: gate for gate in circuit["gates"] for slot in gate["outputs"]}
        self.candidate_nets = [comparisons[slot]["inputs"][1] for slot in circuit["checks"]]

    def solve(self, shape: int, *, include_events: bool = False) -> dict:
        """执行真实选择逻辑，再用普通 Python 加工树复核所得部件和最终图形。

        1. 关闭开关换输入，保留反馈寄存器的真实复位过程。
        2. 开启开关：工作层轮转、选择模板、移除角块、更新指令与部件寄存器。
        3. 四条堆叠支路都不匹配时，反馈重新加载目标并继续下一种状态。
        4. 只接受固定点或完整周期中的持续成功；瞬间相等不算完成。
        """
        target = from_structure(shape)
        if not valid_structure(shape):
            raise ValueError("请输入非空、无空中间层的 16 位结构编号")
        ready = self.model.run(target, self.max_ticks, initial=self.reset_slots,
                               overrides=self.disabled, trace=True)
        if ready["status"] != "fixed":
            raise RuntimeError("XianYu-20221129 换输入时未稳定")
        watched = ("recipe_register", "phase_register", "retry_pulse")
        result = self.model.run(target, self.max_ticks, initial=ready["final_slots"],
                                trace=True, watch=tuple(self.slots[name] for name in watched))
        final = result["final_slots"]
        parts = tuple(final[self.slots[f"part_{i}"]] for i in range(1, 6))
        report = {key: result[key] for key in ("success", "status", "ticks", "period")}
        report.update(shape=shape, target=to_key(target))
        if include_events:
            report["events"] = [{"tick": tick, **{name: describe(value) for name, value in zip(watched, values)}}
                                for tick, values in result["events"]]
        if not result["success"]:
            return report

        # 每个最终部件都必须能由本次指令实际制出，不能用数据库或直接把多层部件当原料。
        recipes = {}
        for _, values in result["events"]:
            recipe = values[0]
            if not recipe:
                continue
            plan = decode_recipe(recipe)
            recipes[plan.value] = (recipe, plan)
        if any(part and part not in recipes for part in parts):
            raise RuntimeError("最终部件没有对应的加工指令")
        candidates = assembly_candidates(parts)
        for candidate, net in zip(candidates, self.candidate_nets):
            actual = {final[slot] for slot in self.model.providers[net]} - {0}
            if actual != ({candidate} if candidate else set()):
                raise RuntimeError("Python 候选堆叠与电路分支不一致")
        matches = [i for i, value in enumerate(candidates) if value == target]
        if not matches:
            raise RuntimeError("Python 堆叠顺序未能复现电路输出")
        plans = tuple(recipes[part][1] if part else None for part in parts)
        assembly = matches[0]
        plan = assemble_plans(plans, ASSEMBLY_TREES[assembly])
        if plan is None or plan.value != target:
            raise RuntimeError("加工树未能还原目标")
        report.update(
            parts=[{"shape": to_key(part), "recipe": to_key(recipes[part][0])} if part else None for part in parts],
            assembly=assembly + 1, plan=plan.as_dict(),
        )
        return report
