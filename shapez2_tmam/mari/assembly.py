"""将 Brain P80 的最终拼合电路写成可直接推导的加工表达式。

输入是四个已完成的角和五层 Hybrid 载荷。角本身的可制造性由前级 CMAM
决定；本模块不把多层角当作合法原料，也不把虚拟拼合当作实体完成。
"""

from .signals import Signal, merge, operate, truthy


def _stack_with_bypass(lower: Signal, upper: Signal) -> Signal:
    """复现 P80 的 XOR + 双 IF + 堆叠器；保留 Conflict 与 Null 的区别。"""
    bypass = merge((lower, upper)) if truthy(lower) != truthy(upper) else None
    stacked = operate("stack", (lower, upper))[0]
    return merge((bypass, stacked))


def assemble(corners: tuple[Signal, ...], hybrids: tuple[Signal, ...],
             swap_order: Signal, pin_claw: Signal) -> Signal:
    """按原端口顺序拼合四角、可选顶针，再依次追加五层 Hybrid。

    corners 依次来自 P18、P35、P49、P68；hybrids 对应 P86 的
    CwCbCu--、CwCcCu--、CwCmCu--、CwCyCu--、CwCwCu-- 五个频道。
    """
    if len(corners) != 4 or len(hybrids) != 5:
        raise ValueError("Mari 拼合需要四个角和五个 Hybrid 层载荷")
    # P80 (20,26)、(19,26/25)、(20,22/21)：第三、第四角组成第一半形。
    c = operate("rotate", (corners[2],))[0]
    d = operate("rotate", (corners[3],))[0]
    d = operate("rotate", (d,))[0]
    first = operate("swap", (c, d))[0]
    first = operate("rotate", (first,))[0]

    # P80 (26,26/25)、(25,26)、(26,22)、(25,21/20/19)：另一对角。
    a = operate("rotate", (corners[0],))[0]
    a = operate("rotate", (a,))[0]
    b = operate("rotate", (corners[1],))[0]
    second = operate("swap", (a, b))[1]
    for _ in range(3):
        second = operate("rotate", (second,))[0]

    # 原电路只判断 order==1；其他信号走相反支路，不能自行加一个 order==2 前提。
    if swap_order == 1:
        claw = operate("swap", (second, first))[0]
    else:
        for _ in range(2):
            first = operate("rotate", (first,))[0]
            second = operate("rotate", (second,))[0]
        claw = operate("swap", (second, first))[1]
        claw = operate("rotate", (claw,))[0]

    # P80 (25,12)、(26,11/12)；随后五级可旁路堆叠的下料始终是累计结果。
    if truthy(pin_claw):
        claw = operate("pin", (claw,))[0]
    result = claw
    for layer in hybrids:
        result = _stack_with_bypass(result, layer)
    return result
