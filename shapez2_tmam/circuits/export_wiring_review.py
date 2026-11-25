"""从原生电路蓝图生成逐层布置图、飞线端点和收发频道表。"""

import argparse
from collections import Counter
from html import escape
from itertools import product
import json
from pathlib import Path
from shutil import copyfile

from ..mari.blueprint import DIRECTIONS, PORTS, _kind, _rotate
from ..mari.signals import decode_constant
from .compiler_backend.prefix_scan_wiring import _native_wiring
from .foundations import FOUNDATION_CHUNKS, TILE_SIZE, foundation_origin, foundation_tiles, platform_ground, platform_interior


_LEVELS = 3
_SHORT = {"WireTransmitterSender", "WireTransmitterReceiver"}
_RADIOS = {"ControlledSignalReceiver", "ControlledSignalTransmitter", "WireGlobalTransmitterReceiver"}


def _position(wiring, index):
    board, x, y, level = wiring.sites[index]
    platform = wiring.platforms[board]
    return (x + TILE_SIZE * platform.get("X", 0), y + TILE_SIZE * platform.get("Y", 0),
            platform.get("Z", 0), level)


def _wire_segments(entry, kind):
    turns = entry.get("R", 0)
    segments = []
    for direction, x, y, level in PORTS[kind][2]:
        if entry["T"].endswith("Mirrored"):
            y, direction = -y, -direction % 4
        dx, dy = _rotate(x, y, turns)
        step_x, step_y = DIRECTIONS[(direction + turns) % 4]
        segments.append((dx + step_x / 2, dy + step_y / 2, level))
    return segments


def _building_cells(entry, kind):
    x, y, z = (entry.get(key, 0) for key in ("X", "Y", "L"))
    if kind in _RADIOS:
        return product(range(x - 1, x + 2), range(y - 1, y + 2), range(z, z + 3))
    if kind in ("Display2x2", "Display3x3"):
        return None
    if kind == "VirtualHalvesSwapper":
        dx, dy = _rotate(0, 1 if entry["T"].endswith("Mirrored") else -1, entry.get("R", 0))
        return ((x, y, z), (x + dx, y + dy, z))
    height = 1 + max((p[3] for p in PORTS[kind][2]), default=0)
    return ((x, y, z + dz) for dz in range(height))


def _diagram(path):
    wiring = _native_wiring(path)
    if not wiring.platforms:
        raise ValueError(f"{path.name} 没有电路平台")
    platforms = []
    for i, platform in enumerate(wiring.platforms, 1):
        chunks = FOUNDATION_CHUNKS.get(platform["T"])
        if chunks is None or platform.get("R", 0):
            raise ValueError(f"{path.name} 的 P{i} 使用不支持的电路平台或朝向")
        width, height = chunks
        dx, dy = foundation_origin(platform["T"])
        x = platform.get("X", 0) + dx
        y = platform.get("Y", 0) + dy
        count = len(platform["B"]["Entries"])
        platforms.append((i, x, y, platform.get("Z", 0), width, height, count, foundation_tiles(platform["T"])))
    ground = [platform_ground(p["T"]) for p in wiring.platforms]
    interior = [platform_interior(p["T"]) for p in wiring.platforms]
    occupied = [set() for _ in platforms]
    radio_cells = Counter()
    placement_errors = Counter()
    unknown_footprints = set()
    entries = []
    radio = []
    for i, (board, entry) in enumerate(wiring.entries):
        x, y, island, level = _position(wiring, i)
        kind = _kind(entry)
        footprint = _building_cells(entry, kind)
        offsets = None
        if footprint is None:
            unknown_footprints.add(board)
        else:
            _, local_x, local_y, _ = wiring.sites[i]
            offsets = []
            allowed = ground[board] if kind in _SHORT else interior[board]
            for cell in footprint:
                a, b, z = cell
                if (a, b) not in allowed or not 0 <= z < _LEVELS or cell in occupied[board]:
                    placement_errors[board] += 1
                else:
                    occupied[board].add(cell)
                    if kind in _RADIOS:
                        radio_cells[board] += 1
                    offsets.append((a - local_x, b - local_y, z - level))
            if offsets == [(0, 0, 0)]:
                offsets = 1
        color = "gate"
        parts = []
        if PORTS[kind][2]:
            parts = _wire_segments(entry, kind)
            color = "vertical" if any(dz for _, _, dz in parts) else "wire"
        elif kind in _SHORT:
            color = "short"
        elif kind in ("ControlledSignalTransmitter", "ControlledSignalReceiver"):
            color = "tx" if kind == "ControlledSignalTransmitter" else "rx"
            (source, _), = wiring.sources(i, 0)
            radio.append((board + 1, island, level, entry.get("X", 0), entry.get("Y", 0), color,
                          decode_constant(wiring.entries[source][1]["C"])))
        elif kind == "ConstantSignal":
            color = "constant"
        entries.append((x, y, island, level, color, kind, parts, offsets))
    links = [(_position(wiring, tx), _position(wiring, rx)) for rx, tx in wiring.short_ports.items()]
    coverage = [(len(cells), len({(x, y) for x, y, _ in cells}), len(ground[board]),
                 placement_errors[board], board in unknown_footprints, Counter(z for _, _, z in cells), radio_cells[board])
                for board, cells in enumerate(occupied)]
    return platforms, entries, links, radio, coverage


def _section(path, output_dir):
    platforms, entries, links, radio, coverage = _diagram(path)
    native = output_dir / path.name
    if path.resolve() != native.resolve():
        copyfile(path, native)
    interface = path.with_suffix(".json")
    files = f'<a href="{escape(path.name)}">原生蓝图</a>'
    if interface.is_file():
        copy = output_dir / interface.name
        if interface.resolve() != copy.resolve():
            copyfile(interface, copy)
        files += f' · <a href="{escape(interface.name)}">接口 JSON</a>'
    wires = Counter(entry[3] for entry in entries if entry[6])
    counts = Counter(entry[3] for entry in entries)
    layers = "".join(f"<tr><td>L{level}</td><td>{counts[level] - wires[level]}</td><td>{wires[level]}</td></tr>"
                     for level in range(_LEVELS))
    receivers = sum(line[5] == "rx" for line in radio)
    transmitters = len(radio) - receivers
    outer = tuple(max(p[i] + p[i + 3] for p in platforms) - min(p[i] for p in platforms) for i in (1, 2))
    footprint = len({(x + dx, y + dy) for _, x, y, _, _, _, _, tiles in platforms for dx, dy in tiles})
    sizes = Counter((p[4], p[5], len(p[7])) for p in platforms)
    summary = "、".join(f"{count} 块 {width}×{height}" + (" L 形" if tiles < width * height else "")
                       for (width, height, tiles), count in sorted(sizes.items()))
    island_cells = sum(len(p[7]) for p in platforms)
    capacity = 0
    board_rows = []
    for platform, (used, projected, ground_cells, errors, unknown, level_cells, wireless) in zip(platforms, coverage, strict=True):
        buildable = ground_cells * _LEVELS
        board, _, _, island, width, height, count, tiles = platform
        slots = len(tiles) * TILE_SIZE ** 2 * _LEVELS
        occupancy = count / slots
        capacity += slots
        if errors:
            verdict = f"占地冲突或越界（{errors} 格）"
        elif unknown:
            verdict = "待核对器件占地"
        else:
            verdict = "占格正常"
        radio_rate = f"{wireless / buildable:.2%}"
        rate = "待核算" if unknown else f"{used / buildable:.1%}"
        plan_rate = "待核算" if unknown else f"{projected / ground_cells:.1%}"
        cells = "—" if unknown else f"{used:,}"
        layer_columns = "".join(f"<td>{level_cells[z] / ground_cells:.1%}</td>" for z in range(_LEVELS))
        if unknown:
            layer_columns = "<td>—</td>" * _LEVELS
        board_rows.append(f"<tr><td>P{board}</td><td>Z{island}</td><td>{width}×{height}</td><td>{count:,}</td>"
                          f"<td>{occupancy:.1%}</td>{layer_columns}<td>{cells} / {buildable:,}</td>"
                          f"<td>{rate}</td><td>{plan_rate}</td><td>{radio_rate}</td><td>{verdict}</td></tr>")
    data = json.dumps({"platforms": platforms, "entries": entries, "links": links}, ensure_ascii=True)
    table = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in (*row[:5], "接收" if row[5] == "rx" else "发射", row[6]))
                    + "</tr>" for row in radio)
    return (f'<section><h2>{escape(path.stem)}</h2><p>{files}</p>'
            f'<p>{len(platforms)} 件平台 · {island_cells:,} 个 1×1 岛格 · {len(entries):,} 个建筑条目</p>'
            f'<p>{summary} · 投影占 {footprint} 岛格 · 外框 {outer[0]}×{outer[1]} 岛格 · '
            f'飞线 {len(links)} 对 · 全局接收 {receivers} · 全局发射 {transmitters}</p>'
            f'<p>总建筑占比 {len(entries) / capacity:.1%}</p>'
            '<details open><summary>逐块平台占地</summary><table><thead>'
            '<tr><th>平台</th><th>岛层</th><th>尺寸</th><th>建筑条目</th><th>建筑占比</th>'
            '<th>L0</th><th>L1</th><th>L2</th><th>三层已占 / 可建格</th><th>三层占地率</th>'
            '<th>俯视占地率</th><th>全局收发占地</th><th>放置检查</th></tr>'
            f'</thead><tbody>{"".join(board_rows)}</tbody></table></details>'
            '<table><thead><tr><th>建筑层</th><th>器件</th><th>线缆件</th></tr></thead>'
            f'<tbody>{layers}</tbody></table>'
            f'<div class="drawings"></div><script type="application/json">{data}</script>'
            '<details><summary>全局收发器的实际频道与板内坐标</summary><table><thead>'
            '<tr><th>板号</th><th>岛层</th><th>建筑层</th><th>X</th><th>Y</th><th>方向</th><th>频道</th></tr>'
            f'</thead><tbody>{table}</tbody></table></details></section>')


_HEADER = """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>TMAM 电路审阅</title>
<style>
body { font: 16px/1.6 system-ui, sans-serif; background: #f3f5f8; color: #172437; margin: 24px auto; padding: 0 16px; max-width: 1120px }
section { background: white; padding: 16px 20px; margin: 20px 0; border: 1px solid #ccd5e0 }
section p { margin: 6px 0 } a { color: #1556ae } summary { cursor: pointer }
.drawings { display: flex; flex-wrap: wrap; gap: 14px; margin: 12px 0 }
figure { margin: 0; max-width: 100% } canvas { display: block; max-width: 100%; height: auto; border: 1px solid #a6b7c9 }
figcaption { color: #394a60; padding-top: 3px } table { border-collapse: collapse } th,td { padding: 4px 12px; border-bottom: 1px solid #d2dae3; text-align: right }
.legend { display: flex; flex-wrap: wrap; gap: 14px } .chip { display: inline-block; width: .85em; height: .85em; margin-right: .3em; border-radius: 2px }
</style><body><h1>TMAM 电路审阅</h1>
<p>三层占地率按实占格 ÷ 可建格计算。俯视占地率合并三层投影，同一个平面格只计一次。建筑占比按条目数计算。岛层 Z 区分叠放的平台，建筑层 L 区分平台内部三层。浅色底格显示各层的实际占用范围。把鼠标放到图上可读取建筑类型和坐标。</p>
<div class="legend" id="legend"></div>
"""
_SCRIPT = """<script>
const chunk = 20;
const colors = {wire:'#7daaa4',vertical:'#f29639',gate:'#f3eeeb',constant:'#8c9db5',short:'#9cef5c',tx:'#ff5972',rx:'#63b3ff'};
const names = {wire:'板内导线',vertical:'换层线',gate:'逻辑或虚拟加工',constant:'常量',short:'飞线',tx:'全局发射',rx:'全局接收'};
for (const [key, name] of Object.entries(names)) {
  const span = document.createElement('span');
  const chip = document.createElement('i');
  chip.className = 'chip'; chip.style.backgroundColor = colors[key];
  span.append(chip, name); document.querySelector('#legend').append(span);
}
function draw(container, platforms, entries, links, island, layer) {
  const minX = Math.min(...platforms.map(p => p[1])) * chunk;
  const minY = Math.min(...platforms.map(p => p[2])) * chunk;
  const width = Math.max(...platforms.map(p => p[1] + p[4])) * chunk - minX;
  const height = Math.max(...platforms.map(p => p[2] + p[5])) * chunk - minY;
  const scale = Math.min(7, 870 / width, 570 / height);
  const figure = document.createElement('figure');
  const canvas = document.createElement('canvas');
  canvas.width = Math.ceil(scale * width); canvas.height = Math.ceil(scale * height);
  const ctx = canvas.getContext('2d');
  const xAt = x => (x - minX) * scale;
  const yAt = y => (y - minY) * scale;
  const segment = (x1,y1,x2,y2) => {
    ctx.beginPath(); ctx.moveTo(xAt(x1), yAt(y1)); ctx.lineTo(xAt(x2), yAt(y2)); ctx.stroke();
  };
  ctx.fillStyle = '#101a27'; ctx.fillRect(0,0,canvas.width,canvas.height);
  for (const [id, bx, by, , , , , tiles] of platforms) {
    ctx.lineWidth = 1;
    for (const [dx,dy] of tiles) {
      const x = xAt((bx + dx) * chunk), y = yAt((by + dy) * chunk), side = scale * chunk;
      ctx.fillStyle = '#1b2c3d'; ctx.fillRect(x,y,side,side);
      ctx.strokeStyle = '#839ab2'; ctx.strokeRect(x,y,side,side);
    }
    ctx.fillStyle = '#b8cadd'; ctx.font = '12px sans-serif';
    ctx.fillText(`P${id}`, xAt(bx * chunk)+4, yAt(by * chunk)+14);
  }
  ctx.globalAlpha = .27;
  for (const [x,y,,level,color,kind,parts,footprint] of entries) {
    ctx.fillStyle = colors[color];
    if (footprint === 1 && level === layer) ctx.fillRect(xAt(x), yAt(y), scale, scale);
    else if (Array.isArray(footprint)) {
      for (const [dx,dy,dz] of footprint) {
        if (level + dz === layer) ctx.fillRect(xAt(x+dx), yAt(y+dy), scale, scale);
      }
    }
  }
  ctx.globalAlpha = 1;
  const cells = new Map();
  for (const [x,y,,level,color,kind,parts] of entries) {
    if (level !== layer) continue;
    cells.set(`${x},${y}`, kind);
    ctx.strokeStyle = ctx.fillStyle = colors[color];
    if (parts.length) {
      ctx.lineWidth = color === 'vertical' ? 1.8 : 1.05;
      for (const [dx,dy] of parts) segment(x+.5,y+.5,x+.5+dx,y+.5+dy);
    } else {
      ctx.fillRect(xAt(x+.14), yAt(y+.14), scale*.72, scale*.72);
    }
  }
  ctx.strokeStyle = colors.short; ctx.lineWidth = 1.8; ctx.setLineDash([4,3]);
  for (const [tx,rx] of links) {
    if (tx[2] === island && rx[2] === island && tx[3] === layer && rx[3] === layer)
      segment(tx[0]+.5,tx[1]+.5,rx[0]+.5,rx[1]+.5);
  }
  ctx.setLineDash([]);
  canvas.onmousemove = event => {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((event.clientX-rect.left)*canvas.width/rect.width/scale + minX);
    const y = Math.floor((event.clientY-rect.top)*canvas.height/rect.height/scale + minY);
    const kind = cells.get(`${x},${y}`);
    canvas.title = kind ? `${kind}　(${x}, ${y})` : `(${x}, ${y})`;
  };
  const label = document.createElement('figcaption');
  label.textContent = `岛层 Z${island} · 建筑层 L${layer} · ${cells.size} 个建筑`;
  figure.append(canvas,label); container.append(figure);
}
for (const section of document.querySelectorAll('section')) {
  const {platforms,entries,links} = JSON.parse(section.querySelector('script').textContent);
  for (const island of new Set(platforms.map(p => p[3]))) {
    const boards = platforms.filter(p => p[3] === island);
    const buildings = entries.filter(e => e[2] === island);
    for (const layer of [0,1,2]) draw(section.querySelector('.drawings'),boards,buildings,links,island,layer);
  }
}
</script></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="从已有原生电路生成逐层布置图和实际收发器清单")
    parser.add_argument("blueprints", nargs="+", type=Path, help="原生电路蓝图文件")
    parser.add_argument("--output-dir", required=True, type=Path, help="审阅图和原生蓝图的输出目录")
    args = parser.parse_args()
    if len({path.name.casefold() for path in args.blueprints}) != len(args.blueprints):
        parser.error("输入蓝图文件名须互不重复")
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        sections = [_section(path, args.output_dir) for path in args.blueprints]
        index = args.output_dir / "index.html"
        index.write_text(_HEADER + "\n".join(sections) + _SCRIPT, encoding="utf-8")
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(f"已导出 {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
