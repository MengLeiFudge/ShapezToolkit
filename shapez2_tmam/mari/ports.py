"""Mari 主控使用的信号端口表，按游戏原始端口索引排列。

每个端口为 (方向, x, y, z)，方向从东起顺时针。资源来自 resources.assets
SHA-256 4a2b93cd7d359162cb06df9e64025eb139eefa91fdbfc9b5191a3073b7840bd8。
镜像由提取器翻转 y 与南北方向，不改变端口索引。
"""

OUT = ((0, 0, 0, 0),)
WEST = ((2, 0, 0, 0),)
NORTH_SOUTH = ((3, 0, 0, 0), (1, 0, 0, 0))
WEST_NORTH = ((2, 0, 0, 0), (3, 0, 0, 0))
EAST_NORTH = ((0, 0, 0, 0), (3, 0, 0, 0))

# 规范化建筑类型 -> (输出端口, 输入端口, 导线接点)。
PORTS = {
    "BeltFilter": ((), ((1, 0, 0, 0),), ()),
    "Button": (OUT, (), ()),
    "ConstantSignal": (OUT, (), ()),
    "ControlledSignalReceiver": (((0, 1, 0, 0),), ((3, 0, -1, 0),), ()),
    "ControlledSignalTransmitter": ((), ((3, 0, -1, 0), (2, -1, 0, 0)), ()),
    "Display": ((), WEST, ()),
    "Display2x2": ((), WEST, ()),
    "Display3x3": ((), WEST, ()),
    "Label": ((), (), ()),
    "LogicGateAnd": (OUT, NORTH_SOUTH, ()),
    "LogicGateCompare": (OUT, NORTH_SOUTH, ()),
    "LogicGateIf": (OUT, WEST_NORTH, ()),
    "LogicGateNot": (OUT, WEST, ()),
    "LogicGateOr": (OUT, NORTH_SOUTH, ()),
    "LogicGateXOr": (OUT, NORTH_SOUTH, ()),
    "VirtualAnalyzer": (EAST_NORTH, WEST, ()),
    "VirtualCrystalGenerator": (OUT, WEST_NORTH, ()),
    "VirtualHalfCutter": (OUT, WEST, ()),
    "VirtualHalvesSwapper": (((0, 0, 0, 0), (0, 0, -1, 0)),
                             ((2, 0, 0, 0), (2, 0, -1, 0)), ()),
    "VirtualPainter": (OUT, WEST_NORTH, ()),
    "VirtualPinPusher": (OUT, WEST, ()),
    "VirtualRotatorCCW": (OUT, WEST, ()),
    "VirtualRotator": (OUT, WEST, ()),
    "VirtualStacker": (OUT, WEST_NORTH, ()),
    "VirtualUnstacker": (EAST_NORTH, WEST, ()),
    "Wire1UpBackward": ((), (), ((2, 0, 0, 0), (2, 0, 0, 1))),
    "Wire1UpForward": ((), (), ((2, 0, 0, 0), (0, 0, 0, 1))),
    "Wire1UpLeft": ((), (), ((2, 0, 0, 0), (3, 0, 0, 1))),
    "Wire2UpBackward": ((), (), ((2, 0, 0, 0), (2, 0, 0, 2))),
    "Wire2UpForward": ((), (), ((2, 0, 0, 0), (0, 0, 0, 2))),
    "Wire2UpLeft": ((), (), ((2, 0, 0, 0), (3, 0, 0, 2))),
    "WireBridge": ((), (), ((0, 0, 0, 0), (2, 0, 0, 0), (1, 0, 0, 0), (3, 0, 0, 0))),
    "WireCross": ((), (), ((2, 0, 0, 0), (1, 0, 0, 0), (0, 0, 0, 0), (3, 0, 0, 0))),
    "WireForward": ((), (), ((2, 0, 0, 0), (0, 0, 0, 0))),
    "WireJunction": ((), (), ((0, 0, 0, 0), (1, 0, 0, 0), (3, 0, 0, 0))),
    "WireLeft": ((), (), ((2, 0, 0, 0), (3, 0, 0, 0))),
    "WireGlobalTransmitterReceiver": (((0, 1, 0, 0),), (), ()),
    "WireTransmitterReceiver": (OUT, (), ()),
    "WireTransmitterSender": ((), WEST, ()),
}

OPERATIONS = {
    "LogicGateAnd": "and", "LogicGateCompare": "compare", "LogicGateIf": "if",
    "LogicGateNot": "not", "LogicGateOr": "or", "LogicGateXOr": "xor",
    "VirtualAnalyzer": "analyze", "VirtualCrystalGenerator": "crystal",
    "VirtualHalfCutter": "cut_right", "VirtualHalvesSwapper": "swap",
    "VirtualPainter": "paint", "VirtualPinPusher": "pin", "VirtualRotatorCCW": "rotate_ccw",
    "VirtualRotator": "rotate", "VirtualStacker": "stack", "VirtualUnstacker": "unstack",
}
