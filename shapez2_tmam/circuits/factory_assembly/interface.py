"""六槽实体工道与上游配方发送器的频道表。"""

from ..layer_controller import RUN
from ..stage_memory import READBACK, WRITE_BUS
from ..stage_writer import WRITE_ACK, WRITE_READY, WRITE_REQUEST, WRITE_RESET
from ..stream_controller import PROGRAM_ACCEPTED, PROGRAM_LENGTH, REPLAY_RESULT
from .changeover import CLEAN_CONFIRMED, ENABLE_FEED, LOADED, TARGET_INPUT


PACKET_TAG = 1_640_046
FIELDS = {name: channel for name, channel in WRITE_BUS.items() if name not in ('address', 'phase')}
ORDER_INPUTS = {'target': TARGET_INPUT, 'length': PROGRAM_LENGTH,
                'replay_result': REPLAY_RESULT, 'accepted': PROGRAM_ACCEPTED}
OPERATOR_INPUTS = {'run': RUN, 'clean_confirmed': CLEAN_CONFIRMED, 'enable_feed': ENABLE_FEED}
WRITE_STATUS = {'address': WRITE_BUS['address'], 'phase': WRITE_BUS['phase'],
                'ready': WRITE_READY, 'request': WRITE_REQUEST, 'ack': WRITE_ACK}


def recipe_interface(count: int, packet_tag: int) -> dict:
    return {
        'controller_outputs': {**ORDER_INPUTS, 'payload': dict(FIELDS), 'packet_tag': packet_tag},
        'operator_outputs': dict(OPERATOR_INPUTS),
        'factory_outputs': {**WRITE_STATUS, 'loaded': LOADED, 'reset': WRITE_RESET,
                            'readback': {'operands': READBACK[0], 'materials': READBACK[1]}},
        'length': {'min': 1, 'max': count},
        'address_base': 0,
        'reset_phase': 3,
    }
