"""手写逐层补料方法的中间表示，供后端单独编译。"""

from ..compiler_contract import (
    BOOL, INT, SHAPE, Apply, Bind, Block, Branch, Call, Constant, Function,
    Jump, Program, Reference, Return, Variable,
)


def layer_program(entry: str) -> Program:
    lower, upper, result = (Reference(name) for name in ("lower", "upper", "result"))
    upper_empty, lower_empty = (Reference(name) for name in ("upper_empty", "lower_empty"))
    empty = Constant(SHAPE, None)
    append_layer = Function("append_layer", (Variable("lower", SHAPE), Variable("upper", SHAPE)), SHAPE,
                            (Variable(upper_empty.name, BOOL), Variable(lower_empty.name, BOOL),
                             Variable(result.name, SHAPE)), (
        Block("entry", (Apply(upper_empty.name, "eq", (upper, empty)),),
              Branch(upper_empty, "return_lower", "check_lower")),
        Block("return_lower", (), Return(lower)),
        Block("check_lower", (Apply(lower_empty.name, "eq", (lower, empty)),),
              Branch(lower_empty, "return_upper", "stack")),
        Block("return_upper", (), Return(upper)),
        Block("stack", (Apply(result.name, "stack", (lower, upper)),), Return(result)),
    ), 3)

    index = Reference("index")
    take = Reference("take")
    rows = tuple(Variable(f"row{i}", SHAPE) for i in range(5))
    dispatch = tuple(Block(f"choose_{i}", (Apply(take.name, "eq", (index, Constant(INT, i))),),
                           Branch(take, f"append_{i}", f"choose_{i+1}" if i < 3 else "append_4"))
                     for i in range(4))
    body = tuple(Block(f"append_{i}", (
        Call(lower.name, append_layer.name, (lower, Reference(row.name))),
        Apply(index.name, "add", (index, Constant(INT, 1))),
    ), Jump("loop")) for i, row in enumerate(rows))
    # 初始化与返回各一次，六次循环条件，五次循环体，分派分别访问 1、2、3、4、4 个块。
    append_five = Function("append_five", (Variable(lower.name, SHAPE), *rows), SHAPE,
                           (Variable(index.name, INT), Variable(take.name, BOOL)), (
        Block("entry", (Bind(index.name, Constant(INT, 0)),), Jump("loop")),
        Block("loop", (Apply(take.name, "lt", (index, Constant(INT, 5))),),
              Branch(take, "choose_0", "return")),
        *dispatch, *body,
        Block("return", (), Return(lower)),
    ), 27)
    return Program(entry, (append_layer, append_five))
