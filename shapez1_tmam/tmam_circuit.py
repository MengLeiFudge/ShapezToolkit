"""只读解码一代存档，按游戏的引脚、导线颜色和隧道规则导出电路。"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

from .tmam_signals import FALSE, TRUE, from_saved

DIRECTIONS = ((0, -1), (1, 0), (0, 1), (-1, 0))
# local x、y、方向（上右下左）、是否输出。引脚顺序与游戏组件一致。
PORTS = {
    21: ((1, 1, 1, True), (0, 1, 3, True)),
    26: ((0, 2, 3, True),),
    31: ((0, 0, 0, True),), 33: ((0, 0, 0, True),),
    32: ((0, 0, 0, True), (0, 0, 3, False), (0, 0, 1, False)),
    34: ((0, 0, 0, True), (0, 0, 2, False)),
    37: ((0, 0, 3, False),),
    40: ((0, 0, 2, False),),
    38: ((0, 0, 0, True), (0, 0, 3, False), (0, 0, 2, False)),
    42: ((0, 0, 3, True), (0, 0, 1, True), (0, 0, 2, False)),
    44: ((0, 0, 0, True), (0, 0, 2, False)),
    49: ((0, 0, 1, True), (0, 0, 3, True)),
    50: ((0, 0, 0, True), (0, 0, 2, False), (0, 0, 1, False)),
    60: ((0, 0, 0, True), (0, 0, 1, False), (0, 0, 2, False)),
    61: ((0, 0, 2, False),),
}
for _code in (35, 36, 46):
    PORTS[_code] = PORTS[32]
for _code in (43, 45):
    PORTS[_code] = PORTS[42]
PORTS[51] = PORTS[50]
LOGIC_CODES = {32, 34, 35, 36, 38, 42, 43, 44, 45, 46, 50, 51, 60}

class MachineProfile(TypedDict):
    """指定存档的人工输入、启动开关和验收端坐标。"""

    input: tuple[int, int]
    enable: tuple[int, int]
    outputs: tuple[tuple[int, int], ...]
    checks: tuple[tuple[int, int], ...]


PROFILES: dict[str, MachineProfile] = {
    "XianYu-20221129": {"input": (7, 1), "enable": (20, 1), "outputs": ((49, -25), (64, -24), (73, -24), (78, -28)), "checks": ((49, -19), (63, -23), (72, -23), (79, -27))},
    "XianYu": {"input": (-293, -42), "enable": (-277, -32), "outputs": ((-274, -49),), "checks": ((-262, -57), (-248, -61), (-239, -61))},
    "CTMAM": {"input": (59, 56), "enable": (62, 7), "outputs": ((70, -43), (71, -42)), "checks": ((69, -19),)},
}


def _decompress(text: str) -> str:
    """解开游戏的 LZString URI 编码；读取六位字符流中的低位优先整数。"""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$"
    codes = [alphabet.index(c) for c in text.replace(" ", "+")]
    position = 0

    def bits(count: int) -> int:
        """读取 count 位，字典代码先写入的位具有较低权重。"""
        nonlocal position
        value = 0
        for i in range(count):
            if position >= len(codes) * 6:
                raise ValueError("存档压缩数据提前结束")
            value |= ((codes[position // 6] >> (5 - position % 6)) & 1) << i
            position += 1
        return value

    first = bits(2)
    if first == 2:
        return ""
    if first not in (0, 1):
        raise ValueError("存档压缩头无效")
    previous = chr(bits(8 if first == 0 else 16))
    dictionary = ["", "", "", previous]
    result = [previous]
    width, remaining = 3, 4
    while True:
        code = bits(width)
        if code == 2:
            # JavaScript 字符串以 UTF-16 码元编码，合并代理对再交给 JSON。
            return "".join(result).encode("utf-16-le", "surrogatepass").decode("utf-16-le")
        if code in (0, 1):
            dictionary.append(chr(bits(8 if code == 0 else 16)))
            code = len(dictionary) - 1
            remaining -= 1
        if remaining == 0:
            remaining = 1 << width
            width += 1
        if code < len(dictionary):
            entry = dictionary[code]
        elif code == len(dictionary):
            entry = previous + previous[0]
        else:
            raise ValueError("存档压缩字典代码无效")
        result.append(entry)
        dictionary.append(previous + entry[0])
        remaining -= 1
        previous = entry
        if remaining == 0:
            remaining = 1 << width
            width += 1


def read_save(path: Path) -> dict:
    """读取 .bin 或已解码 JSON。CRC 含游戏构建盐，本工具记录 SHA-256，不宣称验证 CRC。"""
    text = path.read_text(encoding="utf-8")
    if text.startswith("\x01"):
        text = _decompress(text[1:])
        if not text.startswith("crc32" + "-" * 27) or len(text) < 40:
            raise ValueError(f"存档校验头格式无效：{path}")
        text = text[40:]
    packed = json.loads(text)
    if not all(key in packed for key in ("keys", "values", "data")):
        return packed
    alphabet = "!#%&'()*+,-./:;<=>?@[]^_`{|}~" + "".join(chr(i) for i in range(165, 256)) + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = {char: i for i, char in enumerate(alphabet)}

    def index(value: str) -> int:
        """读取对象压缩表中的小端索引。"""
        return sum(digits[char] * len(alphabet) ** i for i, char in enumerate(value)) - 1

    def unpack(value):
        """恢复压缩字典的字段名和字符串值。"""
        if isinstance(value, list):
            return [unpack(item) for item in value]
        if isinstance(value, dict):
            return {packed["keys"][index(key)]: unpack(item) for key, item in value.items()}
        return packed["values"][index(value)] if isinstance(value, str) else value

    return unpack(packed["data"])


def extract_circuit(path: Path, name: str) -> dict:
    """导出输出端的完整反向依赖闭包；遇到实体物流反馈时拒绝将其伪装成常量。"""
    save = read_save(path)
    if save["version"] != 1010 or save.get("mods"):
        raise ValueError("当前端口表仅支持没有模组的一代 1010 存档")
    entities = save["dump"]["entities"]
    by_id = {e["uid"]: e["components"] for e in entities}
    pins, wires, tunnels, at = {}, {}, set(), defaultdict(list)
    for entity in entities:
        uid, components = entity["uid"], entity["components"]
        meta = components["StaticMapEntity"]
        x, y = meta["origin"]["x"], meta["origin"]["y"]
        code, turns = meta["code"], meta["rotation"] // 90
        if code in (27, 28, 29, 30, 52, 53, 54, 55):
            wires[(x, y)] = (uid, 1 if code < 52 else 2)
        elif code == 39:
            tunnels.add((x, y))
        if components.get("WiredPins", {}).get("slots") and code not in PORTS:
            raise ValueError(f"缺少建筑 {code} 的引脚定义，uid={uid}")
        for slot, (px, py, direction, output) in enumerate(PORTS.get(code, ())):
            for _ in range(turns):
                px, py = -py, px
            node = (uid, slot)
            pins[node] = ((x + px, y + py), (direction + turns) % 4, output)
            at[(x + px, y + py)].append(node)

    # 与 WireSystem 一样，从输出引脚开始深度优先搜索；网络第一次遇到的
    # 导线决定颜色，其他颜色不能借助交叉处的引脚被误合并。
    linked, linked_wires, networks = {}, {}, []
    for start, (_, _, output) in pins.items():
        if not output or start in linked:
            continue
        net_id = len(networks)
        providers = []
        pending, variant = [("pin", start)], None
        while pending:
            kind, item = pending.pop()
            if kind == "pin":
                if item in linked:
                    continue
                linked[item] = net_id
                pos, direction, ejector = pins[item]
                if ejector:
                    providers.append(item)
                directions = (direction,)
            else:
                if item in linked_wires or (variant is not None and wires[item][1] != variant):
                    continue
                linked_wires[item] = net_id
                variant = wires[item][1]
                pos, directions = item, range(4)
            for direction in directions:
                dx, dy = DIRECTIONS[direction]
                target = (pos[0] + dx, pos[1] + dy)
                while True:
                    if target in wires and target not in linked_wires and (variant is None or wires[target][1] == variant):
                        pending.append(("wire", target))
                    for other in at[target]:
                        if other not in linked and pins[other][1] == (direction + 2) % 4:
                            pending.append(("pin", other))
                    if target not in tunnels:
                        break
                    target = (target[0] + dx, target[1] + dy)
        networks.append(providers)

    profile = PROFILES[name]
    positions = {}
    for uid, components in by_id.items():
        meta = components["StaticMapEntity"]
        if meta["code"] in LOGIC_CODES | {31, 33}:
            positions[(meta["origin"]["x"], meta["origin"]["y"])] = uid
    input_uid = positions[profile["input"]]
    check_uids = [positions[pos] for pos in profile["checks"]]
    # 汇总全部候选输出，保留成功支路之间可能出现的信号冲突。
    output_uids = [positions[pos] for pos in profile["outputs"]]
    selected, needed = set(), output_uids + check_uids
    while needed:
        uid = needed.pop()
        if uid in selected:
            continue
        selected.add(uid)
        for node, (_, _, output) in pins.items():
            if node[0] == uid and not output and node in linked:
                needed.extend(provider[0] for provider in networks[linked[node]])
    if input_uid not in selected:
        raise ValueError(f"{name} 的输入不在输出依赖中")
    selected_nodes = [node for node in pins if node[0] in selected and pins[node][2]]
    node_index = {node: i for i, node in enumerate(selected_nodes)}
    used_nets = sorted({linked[node] for node in pins if node[0] in selected and not pins[node][2] and node in linked})
    net_index = {net: i for i, net in enumerate(used_nets)}
    gates, constants, initial = [], {}, []
    labels = []
    for uid, slot in selected_nodes:
        c = by_id[uid]
        meta = c["StaticMapEntity"]
        initial.append(from_saved(c["WiredPins"]["slots"][slot].get("value")))
        labels.append(f"{uid}:{slot}@{meta['origin']['x']},{meta['origin']['y']}")
    for uid in sorted(selected):
        c = by_id[uid]
        code = c["StaticMapEntity"]["code"]
        outputs = [node_index[(uid, slot)] for slot, port in enumerate(PORTS[code]) if port[3]]
        if code in LOGIC_CODES:
            inputs = [net_index[linked[(uid, slot)]] if (uid, slot) in linked else -1 for slot, port in enumerate(PORTS[code]) if not port[3]]
            gates.append({"uid": uid, "code": code, "inputs": inputs, "outputs": outputs})
        elif code == 31:
            constants[outputs[0]] = from_saved(c["ConstantSignal"].get("signal"))
        elif code == 33:
            constants[outputs[0]] = TRUE if c["Lever"]["toggled"] else FALSE
        elif code == 26:
            # 中枢当前目标在单次拆解期间固定。真实输入通过人工选择支路进入。
            constants[outputs[0]] = initial[outputs[0]]
        else:
            raise ValueError(f"输出依赖实体物流建筑 code={code}, uid={uid}；需要物流模型")
    return {
        "name": name, "save_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": str(path), "version": save["version"], "gates": gates,
        "networks": [[node_index[node] for node in networks[net]] for net in used_nets],
        "constants": constants, "initial": initial, "labels": labels,
        "input": node_index[(input_uid, 0)], "outputs": [node_index[(uid, 0)] for uid in output_uids],
        "checks": [node_index[(uid, 0)] for uid in check_uids],
        "enable": node_index[(positions[profile["enable"]], 0)],
        "entity_count": len(entities), "active_entities": len(selected),
    }
