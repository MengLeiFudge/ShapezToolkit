"""六槽流水线按工段地址接收一条配方，保存到下一次换单。"""

from .local_module import Module


WRITE_BUS = {name: 1_640_000 + i for i, name in enumerate(
    ('address', 'phase', 'opcode', 'a', 'b', 'destination', 'base', 'color'))}


READBACK = (1_640_008, 1_640_009)
STREAM_STATE, STREAM_SUCCESSOR = 1_640_040, 1_640_041


def packet_memory(index, outputs, reply, *, stream=False):
    inputs = {name: WRITE_BUS[name] for name in ('address', 'phase', *outputs)}
    if stream:
        inputs['address'] = STREAM_STATE
    module = Module(inputs)
    if stream:
        module.gate('LogicGateCompare', ('address', index), ('preparing',), 'AQ==')
        module.gate('LogicGateCompare', ('address', -index-1), ('committing',), 'AQ==')
        module.gate('LogicGateOr', ('preparing', 'committing'), ('selected',))
        if reply == READBACK[0]:
            module.gate('LogicGateIf', (index, 'selected'), ('ordinal',))
            module.outputs['ordinal'] = WRITE_BUS['address']
        else:
            module.gate('LogicGateIf', (-index-1, 'preparing'), ('successor',))
            module.gate('LogicGateIf', (index+1, 'committing'), ('successor',))
            module.outputs['successor'] = STREAM_SUCCESSOR
    else:
        module.gate('LogicGateCompare', ('address', index), ('selected',), 'AQ==')
    module.gate('LogicGateCompare', ('phase', 1), ('write_only',), 'AQ==')
    module.gate('LogicGateCompare', ('phase', 2), ('overlap',), 'AQ==')
    module.gate('LogicGateOr', ('write_only', 'overlap'), ('writing',))
    module.gate('LogicGateAnd', ('writing', 'selected'), ('load',))
    module.gate('LogicGateAnd', ('write_only', 'selected'), ('release',))
    module.gate('LogicGateCompare', ('phase', 3), ('clear_all',), 'AQ==')
    module.gate('LogicGateOr', ('release', 'clear_all'), ('reset_feedback',))
    module.gate('LogicGateNot', ('reset_feedback',), ('retain',))
    module.gate('LogicGateCompare', ('phase', 0), ('holding',), 'AQ==')
    module.gate('LogicGateAnd', ('selected', 'holding'), ('read',))
    matches = []
    for name, channel in outputs.items():
        stored = 'saved_' + name
        module.gate('LogicGateIf', (name, 'load'), (stored,))
        module.gate('LogicGateIf', (stored, 'retain'), (stored,))
        module.outputs[stored] = channel
        match = 'matches_' + name
        module.gate('LogicGateCompare', (stored, name), (match,), 'AQ==')
        matches.append(match)
    module.gate('LogicGateAnd', tuple(matches[:2]), ('first_two',))
    module.gate('LogicGateAnd', ('first_two', matches[2]), ('verified',))
    module.gate('LogicGateIf', ('verified', 'read'), ('reply',))
    module.gate('LogicGateAnd', ('load', 'verified'), ('captured',))
    for phase_gate, code in (('write_only', 2), ('overlap', 3)):
        ready = 'ack_' + phase_gate
        module.gate('LogicGateAnd', ('captured', phase_gate), (ready,))
        module.gate('LogicGateIf', (code, ready), ('reply',))
    module.outputs['reply'] = reply
    return module.layout()['BP']['Entries'][0]
