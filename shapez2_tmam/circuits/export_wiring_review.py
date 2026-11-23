"""从原生电路蓝图生成逐层布置图、飞线端点和收发频道表。"""

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
from shutil import copyfile

from ..mari.blueprint import DIRECTIONS, PORTS, _kind, _rotate
from ..mari.signals import decode_constant
from .compiler_backend.prefix_scan_wiring import _native_wiring


_TILE_SIZE = 20


def _position(wiring, index):
    board, x, y, level = wiring.sites[index]
    platform = wiring.platforms[board]
    return (x + _TILE_SIZE * platform.get("X", 0), y + _TILE_SIZE * platform.get("Y", 0),
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


def _diagram(path):
    wiring = _native_wiring(path)
    platforms = [(i + 1, p.get("X", 0), p.get("Y", 0), p.get("Z", 0)) for i, p in enumerate(wiring.platforms)]
    if not platforms or any(p["T"] != "Foundation_3x3" or p.get("R", 0) for p in wiring.platforms):
        raise ValueError(f"{path.name} 需要未旋转的 3×3 电路平台")
    entries = []
    radio = []
    for i, (board, entry) in enumerate(wiring.entries):
        x, y, island, level = _position(wiring, i)
        kind = _kind(entry)
        color = "gate"
        parts = []
        if PORTS[kind][2]:
            parts = _wire_segments(entry, kind)
            color = "vertical" if any(dz for _, _, dz in parts) else "wire"
        elif kind in ("WireTransmitterSender", "WireTransmitterReceiver"):
            color = "short"
        elif kind in ("ControlledSignalTransmitter", "ControlledSignalReceiver"):
            color = "tx" if kind == "ControlledSignalTransmitter" else "rx"
            (source, _), = wiring.sources(i, 0)
            radio.append((board + 1, island, level, entry.get("X", 0), entry.get("Y", 0), color,
                          decode_constant(wiring.entries[source][1]["C"])))
        elif kind == "ConstantSignal":
            color = "constant"
        entries.append((x, y, island, level, color, kind, parts))
    links = [(_position(wiring, tx), _position(wiring, rx)) for rx, tx in wiring.short_ports.items()]
    return platforms, entries, links, radio


def _section(path, output_dir):
    platforms, entries, links, radio = _diagram(path)
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
                     for level in range(3))
    receivers = sum(line[5] == "rx" for line in radio)
    transmitters = len(radio) - receivers
    outer = (max(p[1] for p in platforms) - min(p[1] for p in platforms) + 3,
             max(p[2] for p in platforms) - min(p[2] for p in platforms) + 3)
    footprint = 9 * len({(x, y) for _, x, y, _ in platforms})
    data = json.dumps({"platforms": platforms, "entries": entries, "links": links}, ensure_ascii=True)
    table = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in (*row[:5], "接收" if row[5] == "rx" else "发射", row[6]))
                    + "</tr>" for row in radio)
    return (f'<section><h2>{escape(path.stem)}</h2><p>{files}</p>'
            f'<p>{len(platforms)} 块 3×3 · 投影占 {footprint} 岛格 · 外框 {outer[0]}×{outer[1]} 岛格 · '
            f'飞线 {len(links)} 对 · 全局接收 {receivers} · 全局发射 {transmitters}</p>'
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
<p>按原生蓝图坐标画出平台、建筑和导线。岛层 Z 区分叠放的平台，建筑层 L 区分平台内部三层。把鼠标放到图上可读取建筑类型和坐标。</p>
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
  const minX = Math.min(...platforms.map(p => p[1])) * chunk - 30;
  const minY = Math.min(...platforms.map(p => p[2])) * chunk - 30;
  const width = Math.max(...platforms.map(p => p[1])) * chunk + 30 - minX;
  const height = Math.max(...platforms.map(p => p[2])) * chunk + 30 - minY;
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
  for (const [id, bx, by] of platforms) {
    const x = bx * chunk - 30, y = by * chunk - 30;
    ctx.fillStyle = '#1b2c3d'; ctx.fillRect(xAt(x), yAt(y), scale * 60, scale * 60);
    ctx.strokeStyle = '#344d62'; ctx.lineWidth = 1;
    for (const d of [20, 40]) { segment(x+d,y,x+d,y+60); segment(x,y+d,x+60,y+d); }
    ctx.strokeStyle = '#839ab2'; ctx.strokeRect(xAt(x), yAt(y), scale * 60, scale * 60);
    ctx.fillStyle = '#b8cadd'; ctx.font = '12px sans-serif'; ctx.fillText(`P${id}`, xAt(x)+4, yAt(y)+14);
  }
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
