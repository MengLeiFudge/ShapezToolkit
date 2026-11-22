"""输入目标并导出制造证书；完整四象限逆推由 --complete 显式启用。"""

import argparse
import json

from .construct import Constructor
from .orientation import optimize_rotations
from .physics import Rules


def main(argv: list[str] | None = None) -> int:
    """输出 JSON 制造步骤；退出码 0/2/3 分别为成功/不可制作/未覆盖。"""
    parser = argparse.ArgumentParser(description="偶数象限合成：两象限直接判定，可选完整四象限五层尾部搜索")
    parser.add_argument("target", help="保留原层号的图形短代码")
    parser.add_argument("--quadrants", type=int, default=4, help="偶数象限数，至少2")
    parser.add_argument("--height", type=int, default=5, help="整个制造过程的层数上限，至少2")
    parser.add_argument("--complete", action="store_true", help="完整四象限逆推，最坏搜索时间很大")
    parser.add_argument("--instructions", action="store_true", help="另导出四/六象限五层、六寄存器的消费式加工指令")
    parser.add_argument("--production", action="store_true", help="四象限五层整厂用料和基础单层订单")
    args = parser.parse_args(argv)
    if args.production and (args.quadrants, args.height) != (4, 5):
        parser.error("--production 需要 --quadrants 4 --height 5")
    if args.complete and (args.quadrants != 4 or args.height != 5):
        parser.error("--complete 当前只支持 --quadrants 4 --height 5")
    if args.instructions and (args.quadrants not in (4, 6) or args.height != 5):
        parser.error("--instructions 当前只支持 --quadrants 4或6 --height 5")
    try:
        rules = Rules(args.quadrants, args.height)
        target = rules.parse(args.target)
    except ValueError as error:
        parser.error(str(error))
    if args.complete:
        from .solver4 import Solver4
        result = Solver4(rules).solve(target)
    else:
        result = Constructor(rules).construct(target)
    recipe = optimize_rotations(result.recipe) if result.recipe is not None else None
    document = {"status": result.status, "reason": result.reason, "target": target.to_key(),
                "quadrants": rules.quadrants, "height": rules.height,
                "steps": list(recipe.steps()) if recipe is not None else []}
    if args.production:
        from .production_bill import production_bill
        document["production"] = production_bill(recipe) if recipe is not None else None
    if args.instructions:
        document["instructions"] = list(recipe.instructions()) if recipe is not None else []
        document["register_count"] = 6
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return {"solved": 0, "unsolvable": 2, "unknown": 3}[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
