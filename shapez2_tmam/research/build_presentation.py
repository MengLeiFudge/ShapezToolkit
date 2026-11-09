"""将同一份讲稿排成可编辑PPT和同布局PDF；格位只读取证明，不执行游戏物理。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Pt
from pptx.oxml.xmlchemy import OxmlElement
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 960, 540
INK, MUTED, TEAL = '172B40', '516579', '007F78'
BG, WHITE, LINE = 'F4F7FA', 'FFFFFF', 'D8E2EA'
FONT = 'Microsoft YaHei'


class Page:
    """共享点坐标、自动换行和尺寸检查，向两个文档输出同一版式。"""

    def __init__(self, slide, pdf, number):
        self.slide, self.pdf, self.number = slide, pdf, number

    def box(self, bounds, fill, line=None):
        """绘制可编辑矩形；坐标从页面左上角起算，单位为点。"""
        x, y, w, h = bounds
        shape = self.slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, *map(Pt, bounds))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(fill)
        if line:
            shape.line.color.rgb = RGBColor.from_string(line)
            shape.line.width = Pt(0.5)
        else:
            shape.line.fill.background()
        self.pdf.setFillColor('#' + fill)
        self.pdf.setStrokeColor('#' + (line or fill))
        self.pdf.setLineWidth(0.5)
        self.pdf.rect(x, HEIGHT - y - h, w, h, fill=1, stroke=bool(line))

    def text(self, bounds, content, size=18, color=INK, bold=False):
        """用嵌入PDF的中文字体测量换行；超出文本框时终止导出。"""
        x, y, w, h = bounds
        face = 'CJK-Bold' if bold else 'CJK'
        lines = []
        for paragraph in str(content).split('\n'):
            current = ''
            for char in paragraph:
                if current and pdfmetrics.stringWidth(current + char, face, size) > w - 4:
                    lines.append(current)
                    current = ''
                current += char
            lines.append(current)
        leading = size * 1.32
        if len(lines) * leading > h + 0.1:
            raise ValueError(f'第{self.number}页文本溢出：{content!r}，需要{len(lines)*leading:.1f}，仅有{h}')
        shape = self.slide.shapes.add_textbox(*map(Pt, bounds))
        tf = shape.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.word_wrap = False
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.name = FONT
            east_asian = OxmlElement('a:ea')
            east_asian.set('typeface', FONT)
            p.font._element.append(east_asian)
            p.font.size = Pt(size)
            p.font.bold = bold
            p.font.color.rgb = RGBColor.from_string(color)
            p.line_spacing = Pt(leading)
            p.space_before = p.space_after = Pt(0)
            self.pdf.setFont(face, size)
            self.pdf.setFillColor('#' + color)
            self.pdf.drawString(x, HEIGHT - y - size - i * leading, line)


def cards(page, items, top, bottom, columns=2):
    """按固定列数排布论证卡片；卡片编号表示阅读顺序。"""
    rows = (len(items) + columns - 1) // columns
    gap = 16
    width = (880 - gap * (columns - 1)) / columns
    height = (bottom - top - gap * (rows - 1)) / rows
    for i, (title, body) in enumerate(items):
        x, y = 40 + (i % columns) * (width + gap), top + (i // columns) * (height + gap)
        page.box((x, y, width, height), WHITE)
        page.box((x, y, 4, height), TEAL)
        page.text((x + 18, y + 14, width - 36, 54), f'{i+1:02d}  {title}', 19, TEAL, True)
        page.text((x + 18, y + 70, width - 36, height - 80), body, 18)


def matrix(grid):
    """把短代码或显式列坐标转换为自底向上的材料格，不折叠空层。"""
    if 'code' in grid:
        layers = grid['code'].split(':')
        width = len(layers[0]) // 2
        if any(len(layer) != 2 * width for layer in layers):
            raise ValueError(f'短代码层宽不一致：{grid["label"]}')
        cells = [[('C' if layer[q:q+1] == 'c' else 'P' if layer[q:q+1] == 'P'
                   else '.' if layer[q:q+2] == '--' else 'N')
                  for q in range(0, len(layer), 2)] for layer in layers]
    elif 'columns' in grid:
        width = len(grid['columns'])
        cells = [['.'] * width for _ in range(grid['height'])]
        for q, column in enumerate(grid['columns']):
            for material, zs in column.items():
                for z in zs:
                    if cells[z][q] != '.':
                        raise ValueError(f'同格多材料：{grid["label"]} {q=} {z=}')
                    cells[z][q] = material
    else:
        cells = [row.split() for row in reversed(grid['rows'])]
        width = len(cells[0])
    height = grid.get('height', len(cells))
    if height < len(cells):
        raise ValueError(f'图形超过指定高度：{grid["label"]}')
    cells.extend([['.'] * width for _ in range(height - len(cells))])
    return cells


def grids(page, items, with_cards):
    """绘制纵向格子，层号向上增长，象限号从左到右。"""
    available = 490 if with_cards else 880
    width = available / len(items)
    palette = {'N': ('DCE6EF', INK), 'C': ('8DDDD3', '005F5A'), 'P': ('FFD79E', '704000'), '.': (WHITE, MUTED)}
    for i, grid in enumerate(items):
        x = 40 + i * width
        page.text((x, 148, width - 16, 48), grid['label'], 17, TEAL, True)
        cells = matrix(grid)
        h, w = len(cells), len(cells[0])
        cell = min(35, 220 / h, (width - 55) / w)
        left = x + (width - w * cell) / 2 + 8
        top = 200
        for q in range(w):
            page.text((left + q*cell + 2, top - 20, cell, 20), str(q), 10, MUTED)
        for z, row in enumerate(cells):
            y = top + (h - z - 1) * cell
            page.text((left - 25, y + 2, 23, cell + 5), str(z), 10, MUTED)
            for q, material in enumerate(row):
                fill, fg = palette[material]
                page.box((left + q*cell, y, cell, cell), fill, LINE)
                if material != '.':
                    size = min(15, cell * .65)
                    page.text((left + q*cell + cell*.22, y + cell*.04, cell, cell + 5), material, size, fg, True)
        page.text((x + 3, 428, width - 18, 48), grid.get('caption', ''), 13, MUTED)
    if with_cards:
        for i, (title, body) in enumerate(with_cards):
            y = 165 + i * 145
            page.box((558, y, 362, 132), WHITE)
            page.text((574, y+12, 328, 30), title, 19, TEAL, True)
            page.text((574, y+48, 328, 80), body, 17)


def table(page, rows):
    """表格列宽按列数分配；正文保留足够行距。"""
    count = len(rows[0])
    ratios = {2: [.30, .70], 3: [.25, .34, .41], 4: [.27, .29, .18, .26]}[count]
    top, total = 150, 310
    header_h = 39
    row_h = (total - header_h) / (len(rows) - 1)
    for r, row in enumerate(rows):
        y = top if r == 0 else top + header_h + (r - 1) * row_h
        height = header_h if r == 0 else row_h
        x = 40
        for value, ratio in zip(row, ratios):
            width = 880 * ratio
            page.box((x, y, width, height), INK if r == 0 else WHITE if r % 2 else 'EAF0F5')
            size = 15 if count >= 3 else 17
            page.text((x+12, y+7, width-24, height-10), value, size, WHITE if r == 0 else INK, r == 0)
            x += width


def main():
    """读取已校订讲稿，导出PPT/PDF；字体路径可由命令行指定。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, default=Path('/mnt/c/Windows/Fonts/msyh.ttc'))
    parser.add_argument('--bold-font', type=Path, default=Path('/mnt/c/Windows/Fonts/msyhbd.ttc'))
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont('CJK', str(args.font), subfontIndex=0))
    pdfmetrics.registerFont(TTFont('CJK-Bold', str(args.bold_font), subfontIndex=0))
    data = json.loads((ROOT / 'slides.json').read_text(encoding='utf-8'))
    sources = {s['original']: s for s in json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))['sources']}
    prs = Presentation()
    prs.slide_width, prs.slide_height = Pt(WIDTH), Pt(HEIGHT)
    prs.core_properties.title = data['title']
    prs.core_properties.subject = 'TMAM模型、完整覆盖、构造与强制工序证明'
    prs.core_properties.author = 'ShapezToolkit'
    pdf = canvas.Canvas(str(ROOT / 'TMAM研究.pdf'), pagesize=(WIDTH, HEIGHT))
    pdf.setTitle(data['title'])
    pdf.setAuthor('ShapezToolkit')
    for number, content in enumerate(data['slides'], 1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        page = Page(slide, pdf, number)
        page.box((0, 0, WIDTH, HEIGHT), BG)
        page.box((0, 0, WIDTH, 7), TEAL)
        page.text((40, 22, 720, 22), f'TMAM  /  {content["section"]}', 12, TEAL, True)
        page.text((790, 22, 130, 22), content['status'], 12, TEAL, True)
        page.text((40, 53, 880, 46), content['title'], 26, INK, True)
        page.text((40, 105, 880, 48), content['lead'], 17, MUTED)
        layout = content['layout']
        if layout == 'cover':
            page.text((40, 205, 880, 75), '定义  →  定理  →  构造  →  下界  →  电路', 27, TEAL, True)
            cards(page, content['cards'], 310, 460, 3)
        elif layout == 'table':
            table(page, content['rows'])
        elif layout == 'grids':
            grids(page, content['grids'], content['cards'])
        elif layout == 'equation':
            page.box((40, 160, 880, 75), INK)
            page.text((60, 177, 840, 54), content['formula'], 22, WHITE, True)
            cards(page, content['cards'], 255, 465, 3)
        elif layout == 'flow':
            cards(page, content['cards'], 165, 465, 4)
        else:
            cards(page, content['cards'], 160, 465, 2 if len(content['cards']) == 4 else 3)
        if content['takeaway']:
            page.text((40, 481, 880, 27), content['takeaway'], 15, TEAL, True)
        refs = [sources[key] for key in content['sources']]
        page.text((40, 516, 810, 18), '参考卷章节：' + ' · '.join(s['id'] for s in refs) if refs else '论文式研究汇编 · 定义、证明与来源分层阅读', 9, MUTED)
        page.text((863, 513, 60, 22), f'{number:02d} / {len(data["slides"]):02d}', 11, MUTED)
        notes = content['notes'] + '\n\n参考：\n' + '\n'.join(
            f'{s["id"]} {s["title"]}\n{s["volume"]}#{s["anchor"]}\n原文标识：{s["original"]}' for s in refs)
        for grid in content['grids']:
            if 'code' in grid:
                notes += f'\n\n{grid["label"]} 短代码：\n{grid["code"]}'
        slide.notes_slide.notes_text_frame.text = notes
        pdf.showPage()
    prs.save(ROOT / 'TMAM研究.pptx')
    pdf.save()
    print(f'已导出 {len(data["slides"])} 页PPT与PDF；所有文本通过排版边界检查。')


if __name__ == '__main__':
    main()
