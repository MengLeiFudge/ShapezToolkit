"""实体工道验收用的固定配方发送器。"""

from ...synthesis.physics import Rules
from ..circuit import Literal
from ..layer_controller import PRODUCE, RUN
from ..local_module import Module
from ..production_line import TARGET
from ..stage_memory import READBACK, STREAM_STATE, STREAM_SUCCESSOR, WRITE_BUS
from ..stage_writer import WRITE_ACK, WRITE_READY, WRITE_REQUEST, WRITE_RESET
from ..stream_controller import PROGRAM_ACCEPTED, PROGRAM_LENGTH, REPLAY_RESULT, STREAM_NEXT
from .changeover import CLEAN_CONFIRMED, ENABLE_FEED, LOADED, LOAD_PERMIT, TARGET_INPUT
from .interface import FIELDS, OPERATOR_INPUTS, ORDER_INPUTS, PACKET_TAG, WRITE_STATUS

ORDER_SELECT = 1_640_047
PAYLOAD = tuple(FIELDS)
ROWS_PER_BOARD = 2


def _order_metadata(orders, order_ids):
    module = Module({'order': ORDER_SELECT})
    rules = Rules(4, 5)
    for name, choice in order_ids.items():
        order = orders[name]
        selected = f'order{choice}'
        module.gate('LogicGateCompare', ('order', choice), (selected,), 'AQ==')
        for signal, value in (('target', rules.parse(order['target'])),
                              ('length', len(order['instructions'])), ('verified', 1)):
            module.gate('LogicGateIf', (value, selected), (signal,))
    module.outputs = {'target': TARGET_INPUT, 'length': PROGRAM_LENGTH, 'verified': PROGRAM_ACCEPTED}
    return module


def _rows(instructions):
    rules = Rules(4, 5)
    for address, packet in enumerate(instructions):
        values = tuple(rules.parse(packet[field]) if field == 'base' and packet[field] is not None
                       else packet[field] for field in PAYLOAD)
        yield address, values


def _publish(choice, rows, *, channels=FIELDS):
    module = Module({'order': ORDER_SELECT, 'address': WRITE_BUS['address']})
    module.gate('LogicGateCompare', ('order', choice), ('selected',), 'AQ==')
    for address, values in rows:
        module.gate('LogicGateCompare', ('address', address), (f'at{address}',), 'AQ==')
        module.gate('LogicGateAnd', (f'at{address}', 'selected'), (f'send{address}',))
        for name, value in zip(PAYLOAD, values):
            if value is not None:
                module.gate('LogicGateIf', (Literal(value), f'send{address}'), (name,))
                module.outputs[name] = channels[name]
    return module


def _confirm(choice, rows, packet_tag):
    module = Module({'order': ORDER_SELECT, 'address': WRITE_BUS['address'], **FIELDS})
    module.gate('LogicGateCompare', ('order', choice), ('selected',), 'AQ==')
    for address, values in rows:
        matched = 'selected'
        # 空信号也是字段值。先读回总线，避免旧数据尚未撤下时写入新地址。
        for name, value in (*zip(PAYLOAD, values), ('address', address)):
            match = f'{name}_match{address}'
            check = f'{name}_ok{address}'
            module.gate('LogicGateCompare', (name, Literal(value)), (match,), 'AQ==')
            module.gate('LogicGateAnd', (matched, match), (check,))
            matched = check
        module.gate('LogicGateIf', (address, matched), ('tag',))
    module.outputs = {'tag': packet_tag}
    return module


def _replay_result():
    # 验收订单在 Python 完整回放。将选中订单的目标单独回送为已校验的结果。
    module = Module({'target': TARGET_INPUT})
    module.gate('LogicGateIf', ('target', 1), ('result',))
    module.outputs = {'result': REPLAY_RESULT}
    return module


def build(orders, packet_tag: int) -> tuple[list[dict], dict]:
    reserved = {*WRITE_BUS.values(), *READBACK, STREAM_STATE, STREAM_SUCCESSOR, STREAM_NEXT, WRITE_READY,
                WRITE_REQUEST, WRITE_ACK, WRITE_RESET, PROGRAM_LENGTH, PROGRAM_ACCEPTED, REPLAY_RESULT,
                ORDER_SELECT, RUN, PRODUCE, TARGET, CLEAN_CONFIRMED, ENABLE_FEED, LOADED, LOAD_PERMIT, TARGET_INPUT}
    if type(packet_tag) is not int or not 1 <= packet_tag < 1 << 24 or packet_tag in reserved:
        raise ValueError(f'配方地址回读需要独占频道，收到 {packet_tag!r}')
    order_ids = {name: choice for choice, name in enumerate(orders, 1)}
    modules = [_order_metadata(orders, order_ids), _replay_result()]
    for name, choice in order_ids.items():
        rows = list(_rows(orders[name]['instructions']))
        for offset in range(0, len(rows), ROWS_PER_BOARD):
            batch = rows[offset:offset + ROWS_PER_BOARD]
            modules.extend((_publish(choice, batch), _confirm(choice, batch, packet_tag)))
    islands = []
    for index, module in enumerate(modules):
        island = module.layout()['BP']['Entries'][0]
        column, row = divmod(index, 4)
        island.update(X=3 * column, Y=18 + 3 * row)
        islands.append(island)
    interface = {'select': {'channel': ORDER_SELECT, 'orders': order_ids},
                 'write': {**WRITE_STATUS, 'payload': dict(FIELDS), 'packet_tag': packet_tag},
                 'control': {**OPERATOR_INPUTS, 'loaded': LOADED, **ORDER_INPUTS}}
    return islands, interface
