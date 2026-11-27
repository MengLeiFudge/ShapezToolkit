"""将单角指令的层号引用还原为实际基础料和染料。"""

from ..synthesis.physics import Rules
from .circuit import Literal
from .goal_column import LABEL_WORD
from .local_module import Module


PAYLOAD = 1_655_050
ORDER, COLOR = 1_655_051, 1_655_052
FIELDS = tuple(range(1_655_053,1_655_057))


def lookup_label(base, dye, labels):
    m = Module({'base':base,'dye':dye,'labels':LABEL_WORD})
    rules = Rules(4)
    for operand in ('base','dye'):
        m.gate('VirtualAnalyzer', (operand,), (operand+'_type',operand+'_color'))
        m.gate('LogicGateCompare', (operand+'_type',rules.parse('Ru------')), (operand+'_ref',), 'AQ==')
        m.gate('LogicGateIf', (operand+'_color',operand+'_ref'), ('height',))
    word = 'labels'
    for i,label in reversed(list(enumerate(labels))):
        lower, row = f'below{i}', f'row{i}'
        m.gate('VirtualUnstacker', (word,), (lower,row))
        m.gate('LogicGateCompare', ('height',Literal('color:'+label)), (f'at{i}',), 'AQ==')
        m.gate('LogicGateIf', (row,f'at{i}'), ('payload',))
        word = lower
    m.outputs = {'payload':PAYLOAD}
    return m


def material_order(base,dye,templates):
    rules = Rules(4)
    m = Module({'base':base,'dye':dye,'payload':PAYLOAD})
    pairs = [(rules.parse(row),rules.parse('--'+row[2:]) if row[2:]!='------' else None)
             for row in sorted(templates) if row.startswith('R')]
    if any('R' in row[2:] for row in templates):
        raise ValueError('单角基础料模板的动态普通格仅可位于 q0')
    m.lookup('base','rest',pairs)
    m.gate('VirtualAnalyzer', ('base',), ('base_type',None))
    m.gate('LogicGateCompare', ('base_type',rules.parse('Ru------')), ('replace',), 'AQ==')
    m.gate('LogicGateNot', ('replace',), ('static',))
    m.gate('LogicGateCompare', ('base',rules.parse('SuSuSuSu')), ('base_used',), 'Bg==')
    m.gate('LogicGateAnd', ('base_used','static'), ('direct',))
    m.gate('LogicGateIf', ('base','direct'), ('order',))
    m.gate('LogicGateCompare', ('rest',None), ('only',), 'AQ==')
    m.gate('LogicGateAnd', ('only','replace'), ('single',))
    m.gate('LogicGateIf', ('payload','single'), ('order',))
    m.gate('VirtualStacker', ('rest','payload'), ('order',))
    m.gate('VirtualAnalyzer', ('dye',), ('dye_type',None))
    m.gate('LogicGateCompare', ('dye_type',rules.parse('Ru------')), ('inherit',), 'AQ==')
    m.gate('VirtualAnalyzer', ('payload',), (None,'color'))
    m.gate('LogicGateIf', ('color','inherit'), ('fluid',))
    m.gate('LogicGateCompare', ('dye',rules.parse('Cr------')), ('red',), 'AQ==')
    m.gate('LogicGateIf', (Literal('color:r'),'red'), ('fluid',))
    m.outputs = {'order':ORDER,'fluid':COLOR}
    return m


def header_reader(header, digits, fields):
    rules = Rules(4)
    m = Module({'header':header})
    current = 'header'
    for i in range(max(fields)+1):
        if i:
            turned = f'turn{i}'
            m.gate('VirtualRotatorCCW', (current,), (turned,))
            current = turned
        if i not in fields:
            continue
        m.gate('VirtualHalfCutter', (current,), (f'half{i}',))
        m.gate('VirtualRotator', (f'half{i}',), (f'shift{i}',))
        m.gate('VirtualHalfCutter', (f'shift{i}',), (f'token{i}',))
        for n in (tuple(range(1,11))+(14,) if i==0 else range(4)):
            token = '--'+'CR'[n//8]+digits[n%8]+'----'
            m.gate('LogicGateCompare', (f'token{i}',rules.parse(token)), (f'f{i}_{n}',), 'AQ==')
            m.gate('LogicGateIf', (n,f'f{i}_{n}'), (f'field{i}',))
        m.outputs[f'field{i}'] = FIELDS[i]
    return m
