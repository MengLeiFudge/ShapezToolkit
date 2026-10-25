"""输入目标并导出局部构造证书；unknown 始终与不可制作区分。"""

import argparse
import json

from .construct import Constructor
from .physics import Rules


def main() -> int:
    """输出 JSON 制造步骤；退出码 0/2/3 分别为成功/不可制作/未覆盖。"""
    parser = argparse.ArgumentParser(description="四/六象限局部合成构造，尚非完整 TMAM 求解器")
    parser.add_argument("target", help="保留原层号的图形短代码")
    parser.add_argument("--quadrants", type=int, choices=(4, 6), default=4)
    args = parser.parse_args()
    rules = Rules(args.quadrants)
    try:
        target = rules.parse(args.target)
    except ValueError as error:
        parser.error(str(error))
    result = Constructor(rules).construct(target)
    document = {"status": result.status, "reason": result.reason, "target": target.to_key(),
                "quadrants": rules.quadrants, "height": rules.height,
                "steps": list(result.recipe.steps()) if result.recipe is not None else []}
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return {"solved": 0, "unsolvable": 2, "unknown": 3}[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
