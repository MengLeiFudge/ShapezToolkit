"""编译纯堆叠工段的两块地址读取板。"""

from pathlib import Path

from ...synthesis import direct_stack
from ..compiler_backend.fields import compile_fields
from ..compiler_frontend import compile_field_methods, compile_method
from .interface import ORDER_INPUTS, WRITE_STATUS
from .submit_bridge import CANDIDATE_FIELDS


def _has_step(address: int, length: int) -> bool:
    return (address >= 0) & (address < length) & (address < 9)


def _is_stack(address: int) -> bool:
    return ((address == 2) | (address == 4)) | ((address == 6) | (address == 8))


def _uses_operands(address: int, length: int) -> bool:
    return _has_step(address, length) & _is_stack(address)


def _opcode(address: int, length: int) -> int:
    if _is_stack(address):
        return 7
    return 14


def _lower(address: int, length: int) -> int:
    return 0


def _upper(address: int, length: int) -> int:
    return 1


def _destination(address: int, length: int) -> int:
    if (address == 0) | _is_stack(address):
        return 0
    return 1


def build() -> dict[str, tuple[dict, dict]]:
    address_inputs = {'address': WRITE_STATUS['address'], 'length': ORDER_INPUTS['length']}
    fields = {'opcode': '_opcode', 'a': '_lower', 'b': '_upper', 'destination': '_destination'}
    methods, conditions = compile_field_methods(__file__, fields, publish_when={
        'opcode': '_has_step', 'a': '_uses_operands', 'b': '_uses_operands', 'destination': '_has_step',
    })
    numbers = compile_fields(methods, publish_when=conditions, input_channels=address_inputs,
                             output_channels={name: CANDIDATE_FIELDS[name] for name in fields})

    # 在原方法的源码目录解析相对导入，让深度查询和读层共用一张网表。
    path = Path(direct_stack.__file__)
    source = path.read_text(encoding='utf-8') + '''
from .direct_recipe import direct_recipe_base_depth


def direct_base_for_address(target: Shape | None, address: int, length: int) -> Shape | None:
    return direct_base_at_depth(target, direct_recipe_base_depth(address, length))
'''
    program = compile_method(source, 'direct_base_for_address', filename=str(path))
    base = compile_fields({'base': program}, input_channels={'target': ORDER_INPUTS['target'], **address_inputs},
                          output_channels={'base': CANDIDATE_FIELDS['base']})
    return {'direct-recipe-fields': numbers, 'direct-base-for-address': base}
