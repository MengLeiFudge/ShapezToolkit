"""导出供外置主控接入的六槽生产线。"""

import argparse
import json
from pathlib import Path

from ..circuit import encode_document
from .interface import PACKET_TAG
from .layout import DIRECT_STACK_STAGES, assemble, assemble_direct_stack
from .recipe import MAX_STAGES


def build(count: int, *, handoff: bool = False, compact_dyes: bool = False) -> tuple[str, dict]:
    document, interfaces = assemble(count, packet_tag=PACKET_TAG, handoff=handoff, compact_dyes=compact_dyes)
    return _encode(count, document, interfaces)


def build_direct_stack(*, handoff: bool = False) -> tuple[str, dict]:
    document, interfaces = assemble_direct_stack(packet_tag=PACKET_TAG, handoff=handoff)
    return _encode(DIRECT_STACK_STAGES, document, interfaces)


def _encode(count, document, interfaces):
    return encode_document(document), {'stage_capacity': count, 'islands': len(document['BP']['Entries']),
                                       'interfaces': interfaces}


def main() -> int:
    parser = argparse.ArgumentParser(description='生成外置主控使用的六槽生产线')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--stages', type=int, help=f'通用实体工段数，1 至 {MAX_STAGES}')
    mode.add_argument('--direct-stack', action='store_true', help='九工段纯堆叠生产线')
    parser.add_argument('--handoff', action='store_true', help='用双回读确认写入后接管保持路')
    parser.add_argument('--compact-dyes', action='store_true', help='通用工段将结晶卸货和转接合在一块平台')
    parser.add_argument('--output', type=Path, required=True, help='原生 .spz2bp 文件，同名 JSON 保存接线和供货表')
    args = parser.parse_args()
    if args.output.suffix != '.spz2bp':
        parser.error('--output 需要 .spz2bp 文件路径')
    if args.direct_stack and args.compact_dyes:
        parser.error('--compact-dyes 只用于 --stages 通用工段')
    try:
        if args.direct_stack:
            blueprint, report = build_direct_stack(handoff=args.handoff)
        else:
            blueprint, report = build(args.stages, handoff=args.handoff, compact_dyes=args.compact_dyes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(blueprint + '\n', encoding='utf-8')
        args.output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                    encoding='utf-8')
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f'{report["stage_capacity"]} 工段，{report["islands"]} 个岛项目，原生编码 {len(blueprint)} 字符')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
