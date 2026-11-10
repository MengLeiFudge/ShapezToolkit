"""将 TMAM研究.md 排版为论文式 A4 PDF，不执行游戏模型。"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
)

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "TMAM研究.md"
OUTPUT = ROOT / "TMAM研究.pdf"
PAGE_W, PAGE_H = A4
NAVY = colors.HexColor("#172B40")
TEAL = colors.HexColor("#007F78")
MUTED = colors.HexColor("#516579")
PALE = colors.HexColor("#EEF4F7")
LINE = colors.HexColor("#CFDCE4")
FONT = "TMAM-CJK"
BOLD = "TMAM-CJK-Bold"
MONO = "TMAM-CJK-Mono"


def register_fonts() -> None:
    """注册中文字体；默认使用 Windows 微软雅黑集合的第一个字形。"""
    regular = "/mnt/c/Windows/Fonts/msyh.ttc"
    bold = "/mnt/c/Windows/Fonts/msyhbd.ttc"
    pdfmetrics.registerFont(TTFont(FONT, regular, subfontIndex=0))
    pdfmetrics.registerFont(TTFont(BOLD, bold, subfontIndex=0))
    pdfmetrics.registerFont(TTFont(MONO, regular, subfontIndex=0))


def anchor(text: str) -> str:
    """生成稳定的章节锚点，供目录和交叉引用使用。"""
    text = re.sub(r"<[^>]+>", "", text).lower().strip()
    text = "".join(c for c in text if c.isalnum() or c in "_-").replace(" ", "-")
    return text or "section"


def inline(text: str) -> str:
    """转换正文中的少量 Markdown 行内语法为 ReportLab 标记。"""
    text = html.escape(text, quote=False)
    code = []

    def save_code(match: re.Match[str]) -> str:
        code.append(match.group(1))
        return f"\x00CODE{len(code)-1}\x00"

    text = re.sub(r"`([^`]+)`", save_code, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    for index, value in enumerate(code):
        text = text.replace(f"\x00CODE{index}\x00", f'<font name="{MONO}">{value}</font>')
    return text


def line_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(inline(text), style)


class PaperDocTemplate(BaseDocTemplate):
    """提供页眉、页脚和两遍目录通知。"""

    def __init__(self, filename: str | Path, styles: dict[str, ParagraphStyle]):
        self.styles_map = styles
        frame = Frame(20 * mm, 18 * mm, PAGE_W - 40 * mm, PAGE_H - 35 * mm, id="paper")
        template = PageTemplate(id="paper", frames=[frame], onPage=self.draw_page)
        super().__init__(filename, pagesize=A4, pageTemplates=[template],
                         leftMargin=20 * mm, rightMargin=20 * mm,
                         topMargin=17 * mm, bottomMargin=18 * mm)

    def draw_page(self, canvas: Canvas, doc: BaseDocTemplate) -> None:
        canvas.saveState()
        if doc.page > 1:
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.4)
            canvas.line(20 * mm, PAGE_H - 13 * mm, PAGE_W - 20 * mm, PAGE_H - 13 * mm)
            canvas.setFont(FONT, 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(20 * mm, PAGE_H - 10 * mm, "Shapez 2 TMAM｜理论证明")
            canvas.drawRightString(PAGE_W - 20 * mm, 10 * mm, f"{doc.page}")
            canvas.drawString(20 * mm, 10 * mm, "理论论文｜基于操作模型与人工证明")
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        style = flowable.style.name
        if style not in {"PaperH1", "PaperH2"}:
            return
        level = 0 if style == "PaperH1" else 1
        text = flowable.getPlainText()
        key = anchor(text)
        self.canv.bookmarkPage(key)
        self.notify("TOCEntry", (level, text, self.page))


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "PaperTitle": ParagraphStyle("PaperTitle", parent=base["Title"], fontName=BOLD,
                                      fontSize=24, leading=31, textColor=NAVY,
                                      alignment=TA_CENTER, spaceAfter=8 * mm),
        "PaperSubtitle": ParagraphStyle("PaperSubtitle", parent=base["Normal"], fontName=FONT,
                                         fontSize=11, leading=17, textColor=MUTED,
                                         alignment=TA_CENTER, spaceAfter=5 * mm),
        "PaperH1": ParagraphStyle("PaperH1", parent=base["Heading1"], fontName=BOLD,
                                   fontSize=16, leading=22, textColor=NAVY,
                                   spaceBefore=10 * mm, spaceAfter=4 * mm,
                                   keepWithNext=True),
        "PaperH2": ParagraphStyle("PaperH2", parent=base["Heading2"], fontName=BOLD,
                                   fontSize=12.5, leading=18, textColor=TEAL,
                                   spaceBefore=6 * mm, spaceAfter=2.5 * mm,
                                   keepWithNext=True),
        "PaperBody": ParagraphStyle("PaperBody", parent=base["BodyText"], fontName=FONT,
                                     fontSize=9.6, leading=15.2, textColor=NAVY,
                                     alignment=TA_JUSTIFY, spaceAfter=2.7 * mm),
        "PaperBullet": ParagraphStyle("PaperBullet", parent=base["BodyText"], fontName=FONT,
                                       fontSize=9.4, leading=14.4, textColor=NAVY,
                                       leftIndent=5 * mm, firstLineIndent=0,
                                       spaceAfter=1.5 * mm),
        "PaperSmall": ParagraphStyle("PaperSmall", parent=base["BodyText"], fontName=FONT,
                                      fontSize=8.2, leading=12.2, textColor=MUTED,
                                      spaceAfter=2 * mm),
        "PaperCode": ParagraphStyle("PaperCode", parent=base["Code"], fontName=MONO,
                                     fontSize=8.3, leading=12.2, textColor=NAVY,
                                     leftIndent=5 * mm, rightIndent=5 * mm,
                                     borderColor=LINE, borderWidth=0.5,
                                     borderPadding=3 * mm, backColor=PALE,
                                     spaceBefore=1.5 * mm, spaceAfter=3 * mm),
        "PaperQuote": ParagraphStyle("PaperQuote", parent=base["BodyText"], fontName=FONT,
                                      fontSize=9.4, leading=14.5, textColor=MUTED,
                                      leftIndent=5 * mm, rightIndent=4 * mm,
                                      borderColor=TEAL, borderWidth=1, borderPadding=3 * mm,
                                      backColor=colors.HexColor("#F4FAF9"),
                                      spaceBefore=2 * mm, spaceAfter=4 * mm),
        "TOCHeading": ParagraphStyle("TOCHeading", parent=base["Heading1"], fontName=BOLD,
                                      fontSize=16, leading=22, textColor=NAVY,
                                      spaceAfter=6 * mm),
        "TOC0": ParagraphStyle("TOC0", parent=base["Normal"], fontName=BOLD,
                                fontSize=10.5, leading=16, textColor=NAVY),
        "TOC1": ParagraphStyle("TOC1", parent=base["Normal"], fontName=FONT,
                                fontSize=9.2, leading=14, leftIndent=7 * mm,
                                textColor=MUTED),
        "TableCell": ParagraphStyle("TableCell", parent=base["BodyText"], fontName=FONT,
                                     fontSize=8.1, leading=11.5, textColor=NAVY),
        "TableHead": ParagraphStyle("TableHead", parent=base["BodyText"], fontName=BOLD,
                                     fontSize=8.2, leading=11.5, textColor=colors.white),
    }


def table_flow(rows: list[list[str]], styles: dict[str, ParagraphStyle]):
    """把 Markdown 表格转换为可跨页的论文表格。"""
    if not rows:
        return []
    columns = len(rows[0])
    usable = PAGE_W - 40 * mm
    widths = [usable / columns] * columns
    data = []
    for row_index, row in enumerate(rows):
        values = row + [""] * (columns - len(row))
        style = styles["TableHead"] if row_index == 0 else styles["TableCell"]
        data.append([Paragraph(inline(value.strip()), style) for value in values[:columns]])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F9")]),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
    ])
    return [table, Spacer(1, 3 * mm)]


def parse_markdown(text: str, styles: dict[str, ParagraphStyle]):
    """解析本项目正文使用的 Markdown 子集。"""
    lines = text.replace("\r\n", "\n").splitlines()
    story = []
    index = 0
    first_h1 = True
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("```"):
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            story.append(Preformatted("\n".join(code_lines), styles["PaperCode"]))
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            if level == 1 and first_h1:
                first_h1 = False
                index += 1
                continue
            if level == 2:
                story.append(Paragraph(inline(title), styles["PaperH1"]))
            elif level >= 3:
                story.append(Paragraph(inline(title), styles["PaperH2"]))
            index += 1
            continue
        if line.startswith("> ") or line == ">":
            quote = []
            while index < len(lines) and (lines[index].startswith("> ") or lines[index] == ">"):

                quote.append(lines[index][2:] if lines[index].startswith("> ") else "")
                index += 1
            story.append(Paragraph(inline(" ".join(quote)), styles["PaperQuote"]))
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                    rows.append(cells)
                index += 1
            story.extend(table_flow(rows, styles))
            continue
        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            items = []
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            while index < len(lines):
                match = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.+)$", lines[index])
                if not match:
                    break
                items.append(ListItem(Paragraph(inline(match.group(1)), styles["PaperBullet"])))
                index += 1
            story.append(ListFlowable(items, bulletType="1" if ordered else "bullet",
                                      start="1", leftIndent=8 * mm,
                                      bulletFontName=FONT, bulletFontSize=8))
            story.append(Spacer(1, 2 * mm))
            continue
        if re.fullmatch(r"\s*---+\s*", line):
            story.append(HRFlowable(width="100%", thickness=0.7, color=LINE,
                                    spaceBefore=3 * mm, spaceAfter=4 * mm))
            index += 1
            continue
        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip():
            candidate = lines[index]
            if (candidate.startswith(("#", "> ", "|", "```")) or
                    re.match(r"^\s*(?:[-*]|\d+\.)\s+", candidate) or
                    re.fullmatch(r"\s*---+\s*", candidate)):
                break
            paragraph_lines.append(candidate.strip())
            index += 1
        story.append(line_paragraph(" ".join(paragraph_lines), styles["PaperBody"]))
    return story


def build(source: Path = SOURCE, output: Path = OUTPUT) -> None:
    register_fonts()
    styles = make_styles()
    source_text = source.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", source_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Shapez 2 TMAM"
    doc = PaperDocTemplate(str(output.resolve()), styles)
    toc = TableOfContents()
    toc.levelStyles = [styles["TOC0"], styles["TOC1"]]
    story = [
        Spacer(1, 34 * mm),
        Paragraph(inline(title), styles["PaperTitle"]),
        Paragraph("理论论文集｜模型、构造与证明", styles["PaperSubtitle"]),
        Spacer(1, 7 * mm),
        HRFlowable(width="55%", thickness=1.2, color=TEAL, hAlign="CENTER"),
        Spacer(1, 8 * mm),
        Paragraph("Shapez 2 TMAM", styles["PaperSubtitle"]),
        Paragraph("Shapez 2 TMAM · 理论证明整理版", styles["PaperSmall"]),
        Spacer(1, 26 * mm),
        Paragraph("阅读说明", styles["PaperH2"]),
        Paragraph("本文只保留理论定义、定理、构造和证明。操作实现、程序、电路、蓝图和外部资料不属于本论文正文。", styles["PaperBody"]),
        PageBreak(),
        Paragraph("目录", styles["TOCHeading"]),
        toc,
        PageBreak(),
    ]
    story.extend(parse_markdown(source_text, styles))
    doc.multiBuild(story)
    print(f"已生成论文式PDF：{output}，来源正文：{source}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.source, args.output)
