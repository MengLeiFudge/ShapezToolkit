"""按原生端点和部件顺序盘点四象限五层整厂重布预算。"""

import argparse
from collections import Counter, defaultdict
import json
from math import ceil
from pathlib import Path

from ..mari.blueprint import Wiring, _kind
from ..mari.ports import OPERATIONS, PORTS
from .compiler_frontend.pin_candidate_closure import _radio_ports
from .compiler_backend.prefix_scan_wiring import _native_island
from .export_wiring_review import _diagram
from .foundations import foundation_tiles


# 每项先恢复算法边界，再安排板间连接。shared-space 是旧装箱桶。
_MIGRATION = {
    'controls': (1, '外接网关、整单状态和工道协议'),
    'tail-node-inputs': (2, '目标图形与四列上界；行和材料字在使用处生成'),
    'direct-root': (2, '目标、切向、四高度包、接受位与叶端参数'),
    'tail-search-workers': (3, '子目标、候选图形、游标包、判定；共享支撑扫描'),
    'pin-column-sample': (3, '四列材料字与候选四槽包；各列局部判定'),
    'pin-row-reader': (3, '冻结候选五行形状；各列解码留在本地'),
    'pin-rows-prefetch': (3, '并入读行状态，复用五行与有效位'),
    'pin-cap-plan': (3, '掩码、成员包、候选有效和继续信号'),
    'pin-cap-crystals': (3, '并入 Pin 图像判据，只传候选与结果'),
    'pin-landings': (3, '并入 Pin 图像判据，落点游标留在内部'),
    'tail-search': (4, '节点图形、深度、候选推进及完成/故障位'),
    'tail-frames-control': (4, '帧地址、图形对和读写确认'),
    'search-checkpoint': (4, '并入父帧存储，保存压缩候选游标'),
    'shared-space': (5, '按原计算及信号归属拆回各模块，单独估算剩余迁移量'),
}


def sample(path):
    platforms, entries, _, _, coverage = _diagram(path)
    if any(item[3] or item[4] for item in coverage):
        raise ValueError(f'{path} 存在未核定占地')
    tiles = sum(len(item[7]) for item in platforms)
    gates = sum(entry[5] in OPERATIONS for entry in entries)
    radios = sum(item[6] for item in coverage)
    if not gates:
        raise ValueError(f'{path} 没有可作估算的逻辑门')
    return {'name': path.stem, 'island_tiles': tiles, 'logic_gates': gates,
            'wired_cells_per_gate': (sum(item[0] for item in coverage) - radios) / gates,
            'buildable_cells_per_tile': sum(item[2] * 3 for item in coverage) / tiles}


def inventory(island, manifest, samples):
    boards = island['Entries']
    owner = tuple(part for part, count in manifest['parts'].items() for _ in range(count))
    if len(boards) != len(owner):
        raise ValueError('原生板数与接口表部件分段不符')
    inputs = set(manifest['inputs'].values()) | set(manifest['factory']['sends'].values())
    outputs = set(manifest['outputs'].values()) | set(manifest['factory']['receives'].values())
    send, receive = defaultdict(Counter), defaultdict(Counter)
    parts = {name: Counter(boards=n) for name, n in manifest['parts'].items()}
    short_links = Counter()
    short = {'Entries': []}
    for name, board in zip(owner, boards, strict=True):
        entries = board['B']['Entries']
        counts = Counter(map(_kind, entries))
        row = parts[name]
        row['island_tiles'] += len(foundation_tiles(board['T'], board.get('R', 0)))
        row['buildings'] += len(entries)
        row['logic_gates'] += sum(counts[k] for k in OPERATIONS)
        row['auxiliary_buildings'] += sum(count for k, count in counts.items() if k not in OPERATIONS
                                          and not PORTS[k][2] and k not in ('ConstantSignal', 'ControlledSignalReceiver',
                                          'ControlledSignalTransmitter', 'WireTransmitterReceiver', 'WireTransmitterSender'))
        row['receivers'] += counts['ControlledSignalReceiver']
        row['senders'] += counts['ControlledSignalTransmitter']
        for _, is_sender, channel, _ in _radio_ports(Wiring({'Entries': [board]})):
            (send if is_sender else receive)[channel][name] += 1
        short['Entries'].append({**board, 'B': {**board['B'], 'Entries': [entry for entry in entries
                                if _kind(entry) in ('WireTransmitterReceiver', 'WireTransmitterSender')]}})
    wiring = Wiring(short)
    for rx, tx in wiring.short_ports.items():
        source, sink = owner[wiring.sites[tx][0]], owner[wiring.sites[rx][0]]
        short_links[source, sink] += 1
    channels = []
    for channel in sorted(set(send) | set(receive) | inputs | outputs):
        tx, rx = send[channel], receive[channel]
        external = channel in inputs or channel in outputs
        if external:
            scope = 'external'
        elif not tx or not rx:
            scope = 'unmatched'
        elif len(set(tx) | set(rx)) > 1:
            scope = 'cross_part'
        else:
            scope = 'local'
        channels.append({'channel': channel, 'scope': scope, 'senders': dict(tx), 'receivers': dict(rx),
                         'external_input': channel in inputs, 'external_output': channel in outputs})
        for part in set(tx) | set(rx):
            parts[part][scope + '_channels'] += 1
            parts[part][scope + '_endpoints'] += tx[part] + rx[part]
    baseline = {'platforms': len(boards), 'island_cells': sum(p['island_tiles'] for p in parts.values()),
                'building_entries': sum(p['buildings'] for p in parts.values()),
                'global_receivers': sum(p['receivers'] for p in parts.values()),
                'global_transmitters': sum(p['senders'] for p in parts.values()), 'short_range_links': len(wiring.short_ports)}
    for name, actual in baseline.items():
        if actual != manifest[name]:
            raise ValueError(f'{name} 原生为 {actual}，接口表为 {manifest[name]}')
    # 样件已经计入导线、短距口及常量，取实测每岛格门数的高低值。
    density = sorted(s['logic_gates'] / s['island_tiles'] for s in samples)
    migration = []
    for name, row in parts.items():
        order, boundary = _MIGRATION.get(name, (5, '按实际依赖确认调用边界'))
        low = ceil(row['logic_gates'] / density[-1])
        high = ceil(row['logic_gates'] / density[0])
        growth = sum(count for pair, count in short_links.items() if name in pair and pair[0] != pair[1])
        migration.append({'part': name, **row, 'cross_part_short_channels': growth, 'sequence': order,
                          'planned_boundary': boundary, 'wired_tiles_low': low, 'wired_tiles_high': high})
    total = baseline['global_receivers'] + baseline['global_transmitters']
    gateways = len(inputs) + len(outputs)
    clocks = 2 * 6
    return {'baseline': baseline, 'parts': migration, 'channels': channels, 'samples': samples,
            'cross_part_short_pairs': [{'from': a, 'to': b, 'count': n} for (a, b), n in sorted(short_links.items()) if a != b],
            'budget': {'island_layer': 0, 'gateway_endpoints': gateways, 'clock_endpoints': clocks,
                       'total_radio_endpoints': gateways + clocks, 'old_radio_endpoints': total,
                       'radio_reduction': 1 - (gateways + clocks) / total,
                       'wired_tiles_low': sum(p['wired_tiles_low'] for p in migration),
                       'wired_tiles_high': sum(p['wired_tiles_high'] for p in migration)}}


def markdown(report):
    b = report['budget']
    old = report['baseline']
    lines = [
        '# 四象限五层整厂有线重构预算', '',
        f"原生蓝图 {old['platforms']:,} 块板、{old['island_cells']:,} 岛格、{old['building_entries']:,} 建筑，"
        f"全局收 / 发 {old['global_receivers']:,} / {old['global_transmitters']:,}，短距飞线 {old['short_range_links']:,} 对。", '',
        f"一期按单岛层 Z=0 排布。装箱前面积估算 {b['wired_tiles_low']}～{b['wired_tiles_high']} 岛格。",
        f"外接网关 {b['gateway_endpoints']} 个无线端点，共享时钟 {b['clock_endpoints']} 个无线端点，"
        f"合计 {b['total_radio_endpoints']} 个。按 {b['old_radio_endpoints']} 个旧端点算，计划削减 {b['radio_reduction']:.2%}。", '',
        '| 部件 | 板 | 岛格 | 建筑 | 逻辑门 | 收 / 发 | 部件内频道 / 端点 | 跨区频道 / 端点 | 外接频道 / 端点 | 单端频道 / 端点 | 跨区飞线 | 估算岛格 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for p in report['parts']:
        pairs = ' | '.join(f"{p.get(scope + '_channels', 0)} / {p.get(scope + '_endpoints', 0)}"
                           for scope in ('local', 'cross_part', 'external', 'unmatched'))
        lines.append(f"| {p['part']} | {p['boards']} | {p['island_tiles']} | {p['buildings']} | {p['logic_gates']} | "
                     f"{p['receivers']} / {p['senders']} | {pairs} | {p['cross_part_short_channels']} | "
                     f"{p['wired_tiles_low']}～{p['wired_tiles_high']} |")
    lines.extend(['', '同一跨区频道会计入两侧部件。跨区飞线按实际成对端点计。单端频道保留到迁移时逐条追踪。'
                  '`shared-space` 是装箱后的物理分组，跨该分组的频道仍须追到算法所有者。', '', '## 估算基准', '',
                  '| 已布样件 | 岛格 | 逻辑门 | 每岛格逻辑门 | 每门实占格（含本地导线） |',
                  '|---|---:|---:|---:|---:|'])
    for s in report['samples']:
        lines.append(f"| {s['name']} | {s['island_tiles']} | {s['logic_gates']} | "
                     f"{s['logic_gates'] / s['island_tiles']:.2f} | {s['wired_cells_per_gate']:.2f} |")
    lines.extend(['', '每部件保留现有逻辑门数，按样件的最高与最低实测每岛格门数折算并向上取整。'
                  '整厂外框、额外走廊、时钟分发和状态复用的面积在布局时另核。'
                  '估算覆盖原蓝图具备的计算规模，具体省门量以重编后的网表为准。', '',
                  '## 迁移顺序与板缝信号', '',
                  '宽解码保留在消费它的模块。板缝优先传原形状、按字段编码的整数、有效和握手状态。'
                  '实体协议的全部接收和发送由顶层网关处理，共享时钟在同一岛层有线分发。', '',
                  '| 阶段 | 部件 | 拟保留边界 |', '|---:|---|---|'])
    for p in sorted(report['parts'], key=lambda p: p['sequence']):
        lines.append(f"| {p['sequence']} | {p['part']} | {p['planned_boundary']} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='从整厂原生接线和已验证样件核算迁移预算')
    parser.add_argument('blueprint', type=Path)
    parser.add_argument('--sample', required=True, action='append', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.blueprint.with_suffix('.json').read_text(encoding='utf-8-sig'))
    report = inventory(_native_island(args.blueprint), manifest, [sample(p) for p in args.sample])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'factory-wired-budget.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (args.output_dir / 'factory-wired-budget.md').write_text(markdown(report), encoding='utf8')


if __name__ == '__main__':
    main()
