"""从目标剥出可订购的单层，在放行配方前回放堆叠和末次结晶。"""

from ..synthesis.physics import Rules
from .circuit import Literal
from .layer_controller import PACKET_ADDRESS, PRODUCE, ROW_ADDRESS, RUN
from .layer_packet import layer_packet, select_layer
from .local_module import Module
from .production_line import TARGET
from .stage_memory import WRITE_BUS
from .stage_writer import writer
from .stream_controller import PROGRAM_ACCEPTED, PROGRAM_LENGTH, REPLAY_RESULT, advance, release
from .work_lane import COLORS


SCAFFOLD = 1_640_055


def order_rows():
    m = Module({'target': 1_600_000})
    pins = Rules(4).parse('P-P-P-P-')
    rows = []
    lower = 'target'
    for z in range(5):
        rest, top, raised, stripped, row = (f'{name}{z}' for name in ('rest','top','raised','stripped','row'))
        m.gate('VirtualUnstacker', (lower,), (rest, top))
        # 普通格和针落在托底上。纯晶体层全碎，留下的四针为该层占位。
        m.gate('VirtualStacker', (pins, top), (raised,))
        m.gate('VirtualUnstacker', (raised,), (None, stripped))
        m.gate('LogicGateCompare', (top, None), (f'exists{z}',), 'Bg==')
        m.gate('LogicGateIf', (stripped, f'exists{z}'), (row,))
        m.outputs[row] = 1_640_050 + z
        rows.append(row)
        lower = rest
    return m, rows


def stack_orders(source, rows):
    m = Module({row: source.outputs[row] for row in rows})
    acc = rows[-1]
    for i, row in enumerate(reversed(rows[:-1])):
        empty, result = f'empty{i}', f'assembled{i}'
        m.gate('LogicGateCompare', (acc, None), (empty,), 'AQ==')
        m.gate('LogicGateIf', (row, empty), (result,))
        m.gate('VirtualStacker', (acc, row), (result,))
        acc = result
    m.outputs[acc] = SCAFFOLD
    return m


def finish_recipe(target):
    m = Module({'target': target, 'scaffold': SCAFFOLD})
    m.gate('LogicGateCompare', ('target','scaffold'), ('direct',), 'AQ==')
    m.gate('LogicGateNot', ('direct',), ('needs_dye',))
    m.gate('LogicGateIf', ('scaffold','direct'), ('result',))
    m.gate('LogicGateIf', (9,'direct'), ('length',))
    for color in COLORS:
        dye = Literal('color:' + color)
        result, match, use = f'filled_{color}', f'match_{color}', f'use_{color}'
        m.gate('VirtualCrystalGenerator', ('scaffold',dye), (result,))
        m.gate('LogicGateCompare', ('target',result), (match,), 'AQ==')
        # 只要改变了一个格，目标在该格的颜色就唯一决定本次染料。
        m.gate('LogicGateAnd', ('needs_dye',match), (use,))
        m.gate('LogicGateIf', (dye,use), ('dye',))
    m.gate('LogicGateCompare', ('dye',None), ('crystal',), 'Bg==')
    m.gate('LogicGateIf', (10,'crystal'), ('length',))
    m.gate('VirtualCrystalGenerator', ('scaffold','dye'), ('recolored',))
    m.gate('LogicGateIf', ('recolored','crystal'), ('result',))
    m.gate('LogicGateOr', ('direct','crystal'), ('accepted',))
    m.outputs = {'result': REPLAY_RESULT, 'length': PROGRAM_LENGTH, 'accepted': PROGRAM_ACCEPTED,
                 'dye': WRITE_BUS['color']}
    return m


def build():
    source, rows = order_rows()
    target = source.inputs['target']
    selector = select_layer(source, rows)
    selector.inputs['address'] = WRITE_BUS['address']
    selector.gate('LogicGateIf', ('address',1), ('tag',))
    selector.outputs['tag'] = ROW_ADDRESS
    packet = layer_packet()
    packet.inputs['tag'] = ROW_ADDRESS
    packet.gate('LogicGateCompare', ('tag',9), ('last',), 'AQ==')
    for value, name in ((10,'opcode'),(0,'a'),(0,'destination')):
        packet.gate('LogicGateIf', (value,'last'), (name,))
    packet.outputs = {name: WRITE_BUS[name] for name in packet.outputs}
    packet.gate('LogicGateIf', ('tag',1), ('ordinal',))
    packet.outputs['ordinal'] = PACKET_ADDRESS
    outlet = Module({'target': target, 'produce': PRODUCE})
    outlet.gate('LogicGateIf', ('target','produce'), ('filter',))
    outlet.gate('LogicGateNot', ('produce',), ('discard',))
    outlet.gate('LogicGateIf', (0,'discard'), ('filter',))
    outlet.outputs['filter'] = TARGET
    modules = (source, stack_orders(source, rows), finish_recipe(target), selector, packet,
               advance(PACKET_ADDRESS), release(RUN, target, PRODUCE), writer(), outlet)
    islands = []
    for i, module in enumerate(modules):
        island = module.layout()['BP']['Entries'][0]
        island.update(X=3*(i//2), Z=i%2)
        islands.append(island)
    return {'V':1137,'BP':{'$type':'Island','BinaryVersion':1137,'Entries':islands}}
