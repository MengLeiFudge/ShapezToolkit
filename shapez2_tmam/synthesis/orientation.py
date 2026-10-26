"""固定制造骨架的朝向动态规划；只按已证旋转关系变换证书，不重复物理结算。"""

from .physics import Shape
from .recipe import Recipe


def optimize_rotations(source: Recipe) -> Recipe:
    """在原非旋转消费树上最小化净旋转表项，保持目标及物品槽需求。"""
    n = len(source.result.layers[0])
    if n < 2 or n % 2:
        raise ValueError("配方朝向优化需要至少两个偶数象限")
    states: dict[Recipe, tuple[Recipe, ...]] = {}
    pending = [(source, False)]
    while pending:
        node, ready = pending.pop()
        if node in states:
            continue
        if not ready:
            pending.append((node, True))
            pending.extend((child, False) for child in reversed(node.inputs))
            continue
        if node.operation == "rotate":
            if not isinstance(node.parameter, int):
                raise ValueError("旋转配方需要整数象限参数")
            states[node] = tuple(states[node.inputs[0]][(r + node.parameter) % n] for r in range(n))
            continue
        shapes = tuple(Shape(tuple(row[-r:] + row[:-r] for row in node.result.layers)) for r in range(n))
        if node.operation == "base":
            states[node] = tuple(Recipe("base", shape, height=node.height) for shape in shapes)
            continue
        if node.operation in ("cut", "swap"):
            if node.parameter not in (0, 1):
                raise ValueError("切割和交换配方需要出口0或1")
            directions = (0, n // 2)
        elif node.operation in ("pin", "crystal", "stack"):
            directions = range(n)
        else:
            raise ValueError(f"尚未证明此加工的朝向变换：{node.operation!r}")
        candidates: dict[Shape, tuple[Recipe, int]] = {}
        for r in directions:
            parameter = node.parameter
            if node.operation in ("cut", "swap") and r:
                assert isinstance(parameter, int)
                parameter = 1 - parameter
            candidate = Recipe(node.operation, shapes[r], tuple(states[child][r] for child in node.inputs),
                               parameter, node.height)
            previous = candidates.get(candidate.result)
            if previous is None or candidate.step_count < previous[0].step_count:
                candidates[candidate.result] = (candidate, r)
        best, direction = min(candidates.values(), key=lambda item: item[0].step_count)
        oriented = []
        for r, shape in enumerate(shapes):
            direct = candidates.get(shape)
            if direct is not None and direct[0].step_count <= best.step_count + 1:
                oriented.append(direct[0])
            else:
                oriented.append(Recipe("rotate", shape, (best,), (r - direction) % n, node.height))
        states[node] = tuple(oriented)
    return states[source][0]
