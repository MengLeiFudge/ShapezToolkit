"""按工段返回的后继读取可变长配方，核对最后一笔写入及目标回放。"""

from .local_module import Module
from .stage_memory import STREAM_STATE, STREAM_SUCCESSOR
from .stage_writer import WRITE_ACK, WRITE_READY, WRITE_REQUEST, WRITE_RESET


STREAM_NEXT = 1_640_042
PROGRAM_LENGTH = 1_640_043
REPLAY_RESULT = 1_640_044
PROGRAM_ACCEPTED = 1_640_045


def advance(packet_tag, length=PROGRAM_LENGTH):
    m = Module({'state': STREAM_STATE, 'successor': STREAM_SUCCESSOR, 'tag': packet_tag,
                'length': length, 'ready': WRITE_READY, 'ack': WRITE_ACK})
    m.gate('LogicGateCompare', ('state', 'tag'), ('tagged',), 'AQ==')
    m.gate('LogicGateCompare', ('state', 0), ('preparing',), 'Ag==')
    m.gate('LogicGateCompare', ('state', 'length'), ('in_range',), 'BA==')
    m.gate('LogicGateAnd', ('preparing', 'in_range'), ('live',))
    m.gate('LogicGateCompare', ('successor', 0), ('write_token',), 'BA==')
    m.gate('LogicGateAnd', ('live', 'tagged'), ('addressed',))
    m.gate('LogicGateAnd', ('addressed', 'write_token'), ('loaded',))
    m.gate('LogicGateAnd', ('loaded', 'ready'), ('begin',))
    m.gate('LogicGateCompare', ('state', 0), ('writing',), 'BA==')
    m.gate('LogicGateCompare', ('successor', 0), ('next_address',), 'Aw==')
    m.gate('LogicGateAnd', ('writing', 'next_address'), ('committing',))
    m.gate('LogicGateAnd', ('committing', 'ack'), ('stored',))
    m.gate('LogicGateOr', ('begin', 'stored'), ('step',))
    m.gate('LogicGateNot', ('step',), ('wait',))
    m.gate('LogicGateIf', ('state', 'wait'), ('next',))
    m.gate('LogicGateIf', ('successor', 'step'), ('next',))
    m.outputs = {'next': STREAM_NEXT}
    return m


def release(run, target, produce):
    m = Module({'run': run, 'target': target, 'result': REPLAY_RESULT, 'accepted': PROGRAM_ACCEPTED,
                'length': PROGRAM_LENGTH, 'next': STREAM_NEXT})
    m.gate('LogicGateCompare', ('target', None), ('present',), 'Bg==')
    m.gate('LogicGateCompare', ('target', 'result'), ('match',), 'AQ==')
    m.gate('LogicGateCompare', ('accepted', 1), ('success',), 'AQ==')
    m.gate('LogicGateCompare', ('length', 0), ('nonempty',), 'Aw==')
    m.gate('LogicGateCompare', ('length', 971), ('bounded',), 'BQ==')
    m.gate('LogicGateAnd', ('nonempty', 'bounded'), ('size_ok',))
    m.gate('LogicGateAnd', ('match', 'present'), ('replayed',))
    m.gate('LogicGateAnd', ('replayed', 'success'), ('verified',))
    m.gate('LogicGateAnd', ('verified', 'size_ok'), ('admitted',))
    m.gate('LogicGateAnd', ('run', 'admitted'), ('active',))
    m.gate('LogicGateNot', ('active',), ('reset',))
    m.gate('LogicGateIf', (0, 'reset'), ('state',))
    m.gate('LogicGateIf', ('next', 'active'), ('state',))
    m.gate('LogicGateCompare', ('state', 0), ('request',), 'BA==')
    m.gate('LogicGateCompare', ('state', 'length'), ('at_end',), 'AQ==')
    m.gate('LogicGateAnd', ('at_end', 'active'), ('produce',))
    m.outputs = {'state': STREAM_STATE, 'request': WRITE_REQUEST, 'reset': WRITE_RESET, 'produce': produce}
    return m
