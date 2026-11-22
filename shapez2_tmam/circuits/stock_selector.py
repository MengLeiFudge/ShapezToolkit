"""按整片图形信号从 C/R/S 混合车和 W 来线中领取一条原料流。"""

import argparse
import json
from pathlib import Path

from ..synthesis.physics import Rules
from .circuit import constant, encode_document
from .slot_streams import SlotStreams
from .slot_stream_ports import trace, transport_paths


STOCK_CHANNEL = 1_645_000
SOURCES = ((-12, 0), (-12, 1), (-12, 2), (8, 0))
ROWS = (-12, -5, 2, 9)


def stock_selector(channel=STOCK_CHANNEL):
    lane = SlotStreams()
    rx = lane.station(channel, 6, -16)
    lane.put('WireDefaultForward', 4, -16)
    lane.put('WireDefault1UpForward', 3, -16, rotation=2)
    lane.put('WireDefaultLeft', 2, -16, 1, 2)
    rules = Rules(4)
    for i, (part, (y, z), row) in enumerate(zip('CRSW', SOURCES, ROWS)):
        lane.put('BeltPortReceiver', -18, y, z, config='AA==')
        lane.straight(-17, -14, y, z)
        if y == row:
            lane.put('BeltDefaultForward', -14, row, z)
        else:
            lane.put('BeltDefaultLeft', -14, y, z, mirrored=True)
            for yy in range(y+1, row):
                lane.put('BeltDefaultForward', -14, yy, z, 1)
            lane.put('BeltDefaultLeft', -14, row, z, 1)
        lane.straight(-13, -5, row, z)
        lane.put(f'Lift{z}DownForward' if z else 'BeltDefaultForward', -5, row, z)
        lane.straight(-4, 8, row)
        gate = lane.put('BeltFilterDefault', 8, row)
        # 整片匹配才向过滤器送整数1。其他原料的控制端为空，物品保持在入口。
        enable = lane.put('LogicGateIf', 8, row+2, rotation=3)
        lane.put('WireDefaultForward', 8, row+1, rotation=1)
        one = lane.put('ConstantSignalDefault', 8, row+3, rotation=3, config=constant(1))
        eq = lane.put('LogicGateCompare', 7, row+2, config='AQ==')
        key = lane.put('ConstantSignalDefault', 7, row+3, rotation=3, config=constant(rules.parse((part+'u')*4)))
        lane.put('WireDefaultLeft', 7, row+1, mirrored=True)
        lane.put('WireDefault1UpForward', 6, row+1, rotation=2)
        for x in (3, 4, 5):
            lane.put('WireDefaultForward', x, row+1, 1)
        lane.pins.extend(((gate,0,enable),(enable,0,one),(enable,1,eq),(eq,0,rx),(eq,1,key)))
        lane.straight(9, 22, row)
        if i == 0:
            lane.put('BeltDefaultLeft', 22, row, mirrored=True)
        elif i == 3:
            lane.put('Merger2To1L', 22, row)
        else:
            lane.put('Merger2To1L', 22, row, rotation=1, mirrored=True)
        if i < 3:
            for yy in range(row+1, ROWS[i+1]):
                lane.put('BeltDefaultForward', 22, yy, rotation=1)
    lane.straight(23, 37, ROWS[-1])
    lane.put('BeltPortSender', 37, ROWS[-1], config='KAAAAAA=')
    for yy in range(-15, ROWS[-1]+2):
        if yy == ROWS[-1]+1:
            lane.put('WireDefaultLeft', 2, yy, 1, 1)
        elif yy-1 in ROWS:
            lane.put('WireDefaultJunction', 2, yy, 1)
        else:
            lane.put('WireDefaultForward', 2, yy, 1, 1)
    route_dyes(lane)
    island = lane.finish()
    paths = transport_paths(island)
    outlet = (37, ROWS[-1], 0, 2)
    for y,z in SOURCES:
        if trace(paths, (-17,y,z,2), {outlet}, set()) != outlet:
            raise ValueError('所选整片未接入领料出口')
    return island


def route_dyes(lane):
    # 西南四个带位用两层分别供给七色染料和制针染料。
    for z, dests in ((2, (-12, -11, -10, -9)), (1, (8, 9, 10, 11))):
        for i, dest in enumerate(dests):
            source, turn = 28+i, 26+i
            lane.put('FluidPortReceiver', -18, source, z, config='AA==')
            lane.straight(-17, turn, source, z, pipe=True)
            lane.put('PipeLeft', turn, source, z)
            for yy in range(dest+1, source):
                lane.put('PipeForward', turn, yy, z, 3)
            lane.put('PipeLeft', turn, dest, z, 3, mirrored=True)
            lane.straight(turn+1, 33, dest, z, pipe=True)
            rise = z == 1 and i < 3
            lane.put('PipeUpForward' if rise else 'PipeForward', 33, dest, z)
            lane.straight(34, 37, dest, z+rise, pipe=True)
            lane.put('FluidPortSender', 37, dest, z+rise, config='KAAAAAA=')
