"""六个物品寄存器顺序回放四/六象限制造指令，输入被消费，不复制实体。"""

import argparse
import json
from pathlib import Path

from .circuit import Circuit, Gate, Literal, Ref
from .half_circuit import _combine
from .operation_core import physical_results
from .sequential_circuit import clock, latch, select, timing_contract
from .synthesis.physics import Rules


PACKET_FIELDS = ("opcode", "a", "b", "destination", "base", "color", "request", "enable")


def _address(circuit: Circuit, address: Ref) -> list[Ref]:
    """六项一热地址；非0～5整数时没有选中项。"""
    return [circuit.add("LogicGateCompare", address, Literal(i), config="AQ==") for i in range(6)]


def _read(circuit: Circuit, values: tuple[Ref, ...], picks: list[Ref]) -> Ref:
    """地址一热时至多一个槽发布物品信号，空槽仍为空。"""
    branches = tuple(circuit.add("LogicGateIf", value, pick) for value, pick in zip(values, picks))
    circuit.aliases.append(branches)
    return branches[0]


def _base_valid(circuit: Circuit, source: Ref, quadrants: int) -> Ref:
    """基础供料必须恰为触地非空单层，且全部象限均不含晶体。"""
    split = circuit.add("VirtualUnstacker", source)
    top = Ref(split.node, 1)
    exists = circuit.add("LogicGateCompare", top, Literal(None), config="Bg==")
    single = circuit.add("LogicGateCompare", source, top, config="AQ==")
    crystal = Rules(quadrants).parse("cu" + "--" * (quadrants - 1))
    no_crystals = []
    rotated = source
    for q in range(quadrants):
        if quadrants == 6 and q >= 4:
            rotated = circuit.add("VirtualRotator", source if q == 4 else rotated)
        elif q:
            rotated = circuit.add("VirtualRotatorCCW", rotated)
        part = circuit.add("VirtualAnalyzer", rotated)
        no_crystals.append(circuit.add("LogicGateCompare", part, Literal(crystal), config="Bg=="))
    return _combine(circuit, "LogicGateAnd", [exists, single, *no_crystals])


def recipe_step(circuit: Circuit, values: tuple[Ref, ...], ack: Ref, status: Ref,
          packet: dict[str, Ref], quadrants: int = 4) -> tuple[Ref, ...]:
    """纯组合事务：合法新请求消费源槽并写一槽，错误只更新确认与状态。"""
    first_picks = _address(circuit, packet["a"])
    second_picks = _address(circuit, packet["b"])
    destinations = _address(circuit, packet["destination"])
    first = _read(circuit, values, first_picks)
    second = _read(circuit, values, second_picks)
    results = physical_results(circuit, first, second, packet["color"], quadrants)
    modes = {code: circuit.add("LogicGateCompare", packet["opcode"], Literal(code), config="AQ==")
             for code in (*range(1, 11), 14)}
    base = modes[14]
    binary = _combine(circuit, "LogicGateOr", [modes[code] for code in (7, 8, 9)])
    uses_first = _combine(circuit, "LogicGateOr", [modes[code] for code in range(1, 11)])
    valid_mode = circuit.add("LogicGateOr", base, uses_first)
    first_exists = circuit.add("LogicGateCompare", first, Literal(None), config="Bg==")
    second_exists = circuit.add("LogicGateCompare", second, Literal(None), config="Bg==")
    distinct = circuit.add("LogicGateCompare", packet["a"], packet["b"], config="Bg==")
    second_ok = _combine(circuit, "LogicGateAnd", [second_exists, distinct])
    second_ok = circuit.add("LogicGateOr", circuit.add("LogicGateNot", binary), second_ok)
    operands_ok = _combine(circuit, "LogicGateAnd", [uses_first, first_exists, second_ok])
    operands_ok = circuit.add("LogicGateOr", base, operands_ok)
    empty = [circuit.add("LogicGateCompare", value, Literal(None), config="AQ==") for value in values]
    free_destination = _combine(circuit, "LogicGateOr", [
        circuit.add("LogicGateAnd", pick, available) for pick, available in zip(destinations, empty)])
    same_first = circuit.add("LogicGateCompare", packet["destination"], packet["a"], config="AQ==")
    same_second = circuit.add("LogicGateCompare", packet["destination"], packet["b"], config="AQ==")
    reusable_first = circuit.add("LogicGateAnd", uses_first, same_first)
    reusable_second = circuit.add("LogicGateAnd", binary, same_second)
    destination_ok = _combine(circuit, "LogicGateOr", [free_destination, reusable_first, reusable_second])
    destination_ok = circuit.add("LogicGateAnd", destination_ok, _combine(circuit, "LogicGateOr", destinations))
    base_ok = circuit.add("LogicGateOr", circuit.add("LogicGateNot", base), _base_valid(circuit, packet["base"], quadrants))
    colors = [circuit.add("LogicGateCompare", packet["color"], Literal(f"color:{color}"), config="AQ==")
              for color in "rgbcmyw"]
    color_ok = circuit.add("LogicGateOr", circuit.add("LogicGateNot", modes[10]),
                           _combine(circuit, "LogicGateOr", colors))
    published = tuple(circuit.add("LogicGateIf", results[code], modes[code]) for code in range(1, 11))
    published += (circuit.add("LogicGateIf", packet["base"], base),)
    circuit.aliases.append(published)
    result = published[0]
    nonempty = circuit.add("LogicGateCompare", result, Literal(None), config="Bg==")
    valid = _combine(circuit, "LogicGateAnd", [valid_mode, operands_ok, destination_ok, base_ok, color_ok, nonempty])
    request_zero = circuit.add("LogicGateCompare", packet["request"], Literal(0), config="AQ==")
    request_one = circuit.add("LogicGateCompare", packet["request"], Literal(1), config="AQ==")
    request_valid = circuit.add("LogicGateOr", request_zero, request_one)
    changed = circuit.add("LogicGateXOr", packet["request"], ack)
    pending = _combine(circuit, "LogicGateAnd", [changed, request_valid, packet["enable"]])
    accepted = circuit.add("LogicGateAnd", pending, valid)
    next_values = []
    for value, first_pick, second_pick, destination in zip(values, first_picks, second_picks, destinations):
        consumed_first = circuit.add("LogicGateAnd", uses_first, first_pick)
        consumed_second = circuit.add("LogicGateAnd", binary, second_pick)
        consumed = circuit.add("LogicGateOr", consumed_first, consumed_second)
        consumed = circuit.add("LogicGateAnd", consumed, accepted)
        kept = circuit.add("LogicGateIf", value, circuit.add("LogicGateNot", consumed))
        write = circuit.add("LogicGateAnd", destination, accepted)
        next_values.append(select(circuit, write, result, kept))
    next_ack = select(circuit, pending, packet["request"], ack)
    code = select(circuit, valid, Literal(1), Literal(2))
    next_status = select(circuit, pending, code, status)
    return (*next_values, next_ack, next_status)


def build_processor(channel_base: int | None = None, *, quadrants: int = 4) -> tuple[Circuit, dict]:
    """先核对无反馈步通路深度，再闭合九项主副状态和自动时钟。"""
    if quadrants not in (4, 6):
        raise ValueError("配方回放器需要四或六象限配置")
    if channel_base is None:
        channel_base = 1_025_000 if quadrants == 4 else 1_343_000
    if not 1 <= channel_base < (1 << 24) - 2048:
        raise ValueError("频道基址需要为实例保留后续2048个频道，并保持低于2^24")
    circuit = Circuit(channel_base + 32)
    packet = {name: circuit.add("ControlledSignalReceiver", Literal(channel_base + i))
              for i, name in enumerate(PACKET_FIELDS)}
    initial = (None,) * 6 + (0, 0, 0)
    reads = tuple(circuit.add("LogicGateIf", Literal(value), Literal(1)) for value in initial)
    next_state = recipe_step(circuit, reads[:6], reads[6], reads[7], packet, quadrants)
    # 此时所有状态入口仍为常量，只有组合DAG；下面仅闭合已计入的一级读入口。
    depth = circuit.settling_bound()["max_gate_depth"]
    # 提交截止到主组关写留2P−60tick，须严格超过12D+36tick。
    timing = clock(circuit, packet["enable"], phase_steps=max(8, depth // 2 + 5))
    reset = circuit.add("LogicGateNot", packet["enable"])
    master_load = circuit.add("LogicGateOr", timing.phases[0], reset)
    slave_load = circuit.add("LogicGateOr", timing.phases[2], reset)
    states = []
    for read, source, value in zip(reads, (*next_state, Literal(1)), initial):
        data = select(circuit, packet["enable"], source, Literal(value))
        master = latch(circuit, data, master_load)
        slave_data = select(circuit, packet["enable"], master, Literal(value))
        slave = latch(circuit, slave_data, slave_load)
        states.append(slave)
        circuit.gates[read.node] = Gate("LogicGateIf", (slave, Literal(1)))
    running = circuit.add("LogicGateAnd", packet["enable"], states[8])
    window = circuit.add("LogicGateAnd", timing.phases[3], running)
    channels = circuit.channel_map()
    if max(channels.values()) > channel_base + 2047:
        raise ValueError("六寄存器配方回放器超出其保留频道范围")
    return circuit, {
        "component": "six_register_recipe_processor", "quadrants": quadrants, "height": 5,
        "inputs": {name: channel_base + i for i, name in enumerate(PACKET_FIELDS)},
        "outputs": {"window": channels[window], "ack": channels[states[6]], "status": channels[states[7]],
                    "registers": [channels[value] for value in states[:6]]},
        "opcodes": {"1": "rotate_cw", "2": "rotate_ccw", "3": "rotate_half", "4": "cut_front",
                    "5": "cut_back", "6": "pin", "7": "stack(a lower, b upper)", "8": "swap_front_a",
                    "9": "swap_front_b", "10": "crystal", "14": "base"},
        "statuses": {"0": "复位后尚无请求", "1": "上个新请求已执行", "2": "上个新请求被拒，六个物品槽不变"},
        "gate_platforms": len(circuit.gates), "reserved_channels": [channel_base, channel_base + 2047],
        "step_max_gate_depth": depth, "timing": timing_contract(timing),
        "reset_protocol": "enable=0且request=0完成复位；再enable=1。等window首次上升后24tick，才提交首包request=1。",
        "submit_protocol": "每个window上升后24tick，在本阶段3开始后96tick之前让整包在输入接收器输出处稳定。每次仅翻转request一次，包保持到下一window确认ack=request；同请求不重复消费。",
        "register_protocol": "地址为整数0～5；base只能写空槽。单输入和双输入操作消费源槽，可复用被消费槽或写空槽；双输入地址须不同。颜色只启用rgbcmyw。",
        "error_protocol": "操作码、地址、原料或结果无效时确认请求并置status=2，不消费也不改写物品槽。request必须是0/1；其他值不确认。",
        "scope": "流式证书的虚拟回放与消费式寄存器调度；未包含候选搜索、角宏自动发令或目标可解性判定。",
        "proof": ("4q5l/recipe-registers.md；六槽上界只用于当前四象限构造和尾部。" if quadrants == 4
                  else "6q5l/recipe-processor.md；逐树检查六槽预算，不宣称全部六象限构造均满足。"),
        "verification": "组合步DAG深度及原生占地/端口静态编译；未执行指令、目标、反馈、测试或游戏",
    }


def main() -> int:
    """编译纯电路回放器及频道合同，不运行任何制造指令。"""
    parser = argparse.ArgumentParser(description="生成四/六象限的六寄存器配方回放器")
    parser.add_argument("--quadrants", type=int, choices=(4, 6), default=4)
    parser.add_argument("--channel-base", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit, report = build_processor(args.channel_base, quadrants=args.quadrants)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(circuit.encode() + "\n", encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"六寄存器配方回放器已编译：{args.output}；{report['gate_platforms']} 块平台。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
