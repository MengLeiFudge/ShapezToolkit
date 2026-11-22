"""协调配方写入、生产放行和换单排空。"""

from ..layer_controller import PRODUCE, RUN
from ..local_module import Module
from ..production_line import TARGET
from ..stream_controller import PROGRAM_LENGTH, advance, release
from ..stage_writer import writer

TARGET_INPUT = 1_600_000
LOADED = 1_640_057
LOAD_PERMIT = 1_640_058
ENABLE_FEED = 1_640_059
CLEAN_CONFIRMED = 1_640_060


def controls(count: int, packet_tag: int) -> list[dict]:
    permit = Module({'run': RUN, 'clean': CLEAN_CONFIRMED, 'length': PROGRAM_LENGTH})
    permit.gate('LogicGateCompare', ('run', 1), ('requested',), 'AQ==')
    permit.gate('LogicGateCompare', ('clean', 1), ('cleared',), 'AQ==')
    permit.gate('LogicGateCompare', ('length', count), ('fits',), 'BQ==')
    permit.gate('LogicGateAnd', ('requested', 'cleared'), ('admitted',))
    permit.gate('LogicGateAnd', ('admitted', 'fits'), ('armed',))
    permit.outputs = {'armed': LOAD_PERMIT}

    outlet = Module({'loaded': LOADED, 'feed': ENABLE_FEED, 'target': TARGET_INPUT})
    outlet.gate('LogicGateCompare', ('feed', 1), ('enabled',), 'AQ==')
    outlet.gate('LogicGateAnd', ('loaded', 'enabled'), ('produce',))
    outlet.gate('LogicGateNot', ('produce',), ('discard',))
    outlet.gate('LogicGateIf', ('target', 'produce'), ('filter',))
    outlet.gate('LogicGateIf', (0, 'discard'), ('filter',))
    outlet.outputs = {'produce': PRODUCE, 'filter': TARGET}

    modules = (permit, advance(packet_tag), release(LOAD_PERMIT, TARGET_INPUT, LOADED), writer(), outlet)
    islands = []
    for i, module in enumerate(modules):
        island = module.layout()['BP']['Entries'][0]
        island.update(X=3 * i, Y=12)
        islands.append(island)
    return islands
