"""按实际层号将目标的一列变为五层材料标记，空底层和空中间层各占一位。"""

from .circuit import Literal
from .local_module import Module


QUADRANT, RUN, ALIGNED, REMAINING, ACCUMULATOR, WORD = range(1_655_030, 1_655_036)
LABEL_WORD = 1_655_049
CALL = dict(zip(('remaining','acc','top','rest','take','done'), range(1_655_036,1_655_042)))


def orient(target):
    m = Module({'target':target, 'q':QUADRANT})
    shape = 'target'
    for q in range(4):
        if q:
            turn = f'turn{q}'
            m.gate('VirtualRotatorCCW', (shape,), (turn,))
            shape = turn
        m.gate('LogicGateCompare', ('q',q), (f'at{q}',), 'AQ==')
        m.gate('LogicGateIf', (shape,f'at{q}'), ('aligned',))
    m.outputs = {'aligned':ALIGNED}
    return m


def read_height():
    m = Module({'remaining':REMAINING, 'acc':ACCUMULATOR})
    m.gate('VirtualCrystalGenerator', ('remaining',Literal('color:r')), ('dense',))
    m.gate('LogicGateCompare', ('acc',None), ('first',), 'AQ==')
    m.gate('LogicGateIf', ('dense','first'), ('joined',))
    m.gate('VirtualStacker', ('dense','acc'), ('joined',))
    for source,flag in (('joined','take'),('acc','done')):
        current = source
        for i in range(4):
            lower = f'{source}{i}'
            m.gate('VirtualUnstacker', (current,), (lower,None))
            current = lower
        m.gate('LogicGateCompare', (current,None), (flag,), 'Bg==')
    m.gate('VirtualUnstacker', ('remaining',), ('rest','top'))
    # 本轮的形状、累积字和高度判断同时返回，调用方只读同一拍的参数。
    for n in ('remaining','acc'):
        m.gate('LogicGateIf', (n,1), ('echo_'+n,))
    m.outputs = {('echo_'+n if n in ('remaining','acc') else n):c for n,c in CALL.items()}
    return m


def advance_column(rules):
    m = Module({**CALL, 'aligned':ALIGNED, 'run':RUN})
    m.gate('LogicGateIf', ('top','take'), ('selected',))
    m.gate('VirtualAnalyzer', ('selected',), ('part','color'))
    for i,(part,token) in enumerate(((None,'C'),('P-','S'),('cu','W'))):
        key = None if part is None else rules.parse(part+'------')
        m.gate('LogicGateCompare', ('part',key), (f'kind{i}',), 'AQ==')
        m.gate('LogicGateIf', (rules.parse(token+'u------'),f'kind{i}'), ('symbol',))
    m.gate('LogicGateOr', ('kind0','kind1'), ('nonordinary',))
    m.gate('LogicGateOr', ('nonordinary','kind2'), ('special',))
    m.gate('LogicGateNot', ('special',), ('ordinary',))
    m.gate('LogicGateIf', (rules.parse('Ru------'),'ordinary'), ('symbol',))
    m.gate('LogicGateCompare', ('acc',None), ('first',), 'AQ==')
    m.gate('VirtualPainter', ('part','color'), ('painted',))
    m.gate('LogicGateIf', ('painted','ordinary'), ('label',))
    m.gate('VirtualPainter', (rules.parse('Cu------'),'color'), ('tinted',))
    m.gate('LogicGateIf', ('tinted','kind2'), ('label',))
    m.gate('LogicGateIf', (rules.parse('Cu------'),'nonordinary'), ('label',))
    m.gate('VirtualRotator', ('label',), ('turn1',))
    m.gate('VirtualRotator', ('turn1',), ('opposite',))
    m.gate('VirtualStacker', ('symbol','opposite'), ('pair',))
    m.gate('LogicGateIf', ('pair','first'), ('longer',))
    m.gate('VirtualStacker', ('pair','acc'), ('longer',))
    m.gate('LogicGateNot', ('done',), ('more',))
    m.gate('LogicGateAnd', ('more','run'), ('step',))
    m.gate('LogicGateIf', ('longer','step'), ('next_acc',))
    m.gate('LogicGateAnd', ('done','run'), ('hold',))
    m.gate('LogicGateIf', ('acc','hold'), ('next_acc',))
    m.gate('LogicGateIf', ('rest','take'), ('next_rem',))
    m.gate('LogicGateNot', ('take',), ('skip',))
    m.gate('LogicGateIf', ('remaining','skip'), ('next_rem',))
    m.gate('LogicGateIf', ('next_rem','run'), ('remaining_out',))
    m.gate('LogicGateNot', ('run',), ('reset',))
    m.gate('LogicGateIf', ('aligned','reset'), ('remaining_out',))
    m.outputs = {'next_acc':ACCUMULATOR, 'remaining_out':REMAINING}
    return m


def result():
    m = Module({'acc':CALL['acc'], 'done':CALL['done'], 'run':RUN})
    m.gate('LogicGateAnd', ('done','run'), ('return',))
    m.gate('LogicGateIf', ('acc','return'), ('pair',))
    m.gate('VirtualHalfCutter', ('pair',), ('word',))
    m.gate('VirtualRotator', ('pair',), ('turn',))
    m.gate('VirtualRotator', ('turn',), ('opposite',))
    m.gate('VirtualHalfCutter', ('opposite',), ('labels',))
    m.outputs = {'word':WORD, 'labels':LABEL_WORD}
    return m
