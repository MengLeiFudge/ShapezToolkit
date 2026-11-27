"""将已证的单角构造编为共享指令后缀，普通块和结晶染料保留原层引用。"""

from itertools import product

from ..synthesis.corners import CornerBuilder
from ..synthesis.physics import EMPTY, PIN, Rules
from ..synthesis.recipe import Builder
from .pin_column_book import MATERIALS, TOKENS


LABELS = 'gbcmy'


def angle_program(rules):
    corners = CornerBuilder(Builder(rules))
    entry = {}
    nodes = []
    intern = {}
    for materials in product(MATERIALS, repeat=5):
        if not any(c!=EMPTY for c in materials) or not corners.admissible(materials):
            continue
        column = tuple('R'+LABELS[z] if c=='Cu' else 'c'+LABELS[z] if c=='cr' else c
                       for z,c in enumerate(materials))
        corner = corners.build(column,0,-1)
        if corner is None:
            raise ValueError(f'通过列判据的非空角缺少制造程序 {materials}')
        pc = 0
        for packet in reversed(list(corner.instructions(4))):
            # 此列的五种保留标签互异，也与辅助 Cu、cr 不同。实体读包时再代入目标标签。
            base = packet['base']
            if base is not None and any(base[i:i+2] not in (EMPTY,PIN,'Cu',*('R'+c for c in LABELS)) for i in range(0,8,2)):
                raise ValueError(f'基础层出现无法重绑定的角标签 {base}')
            key = (packet['opcode'],packet['a'],packet['b'],packet['destination'],base,packet['color'],pc)
            if key not in intern:
                nodes.append(key)
                intern[key] = len(nodes)
            pc = intern[key]
        word = rules.parse(':'.join(TOKENS[c]+'u------' for c in materials))
        entry[word] = pc
    return entry,nodes
