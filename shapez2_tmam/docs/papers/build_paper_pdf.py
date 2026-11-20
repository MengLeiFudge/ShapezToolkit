"""将二代 TMAM 理论 Markdown 编译为学术论文式 A4 PDF（基于 Typst 排版引擎）。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import typst

ROOT = Path(__file__).resolve().parent
THEORY_DIR = ROOT.parent / "theory"
PAPERS: tuple[tuple[str, str, str], ...] = (
    ("01-model-and-invariants.md", "TMAM理论I-模型与不变量.pdf", "Shapez 2 TMAM 形式化理论系列 · 第一篇"),
    ("02-four-quadrants.md", "TMAM理论II-四象限五层合成.pdf", "Shapez 2 TMAM 形式化理论系列 · 第二篇"),
    ("03-even-constructions.md", "TMAM理论III-一般偶数象限构造.pdf", "Shapez 2 TMAM 形式化理论系列 · 第三篇"),
    ("04-cascades-and-forced-words.md", "TMAM理论IV-级联与强制工序.pdf", "Shapez 2 TMAM 形式化理论系列 · 第四篇"),
    ("04-appendix-forced-sequence.md", "TMAM理论IV附录-交替工序约化.pdf", "Shapez 2 TMAM 形式化理论系列 · 第四篇附录"),
)
SOURCE = THEORY_DIR / PAPERS[0][0]
OUTPUT = ROOT / PAPERS[0][1]

LATEX_SYMBOLS: tuple[tuple[str, str], ...] = (
    (r"\Longleftrightarrow", "⇔"),
    (r"\Leftrightarrow", "⇔"),
    (r"\Longrightarrow", "⇒"),
    (r"\Longleftarrow", "⇐"),
    (r"\leftrightarrow", "↔"),
    (r"\rightarrow", "→"),
    (r"\leftarrow", "←"),
    (r"\subseteq", "⊆"),
    (r"\subsetneq", "⊊"),
    (r"\supseteq", "⊇"),
    (r"\setminus", "∖"),
    (r"\varnothing", "∅"),
    (r"\emptyset", "∅"),
    (r"\varepsilon", "ε"),
    (r"\varphi", "φ"),
    (r"\implies", "⇒"),
    (r"\Rightarrow", "⇒"),
    (r"\Leftarrow", "⇐"),
    (r"\mapsto", "↦"),
    (r"\notin", "∉"),
    (r"\subset", "⊂"),
    (r"\supset", "⊃"),
    (r"\forall", "∀"),
    (r"\exists", "∃"),
    (r"\lfloor", "⌊"),
    (r"\rfloor", "⌋"),
    (r"\lceil", "⌈"),
    (r"\rceil", "⌉"),
    (r"\langle", "⟨"),
    (r"\rangle", "⟩"),
    (r"\cdots", "⋯"),
    (r"\ldots", "…"),
    (r"\vdots", "⋮"),
    (r"\dots", "…"),
    (r"\times", "×"),
    (r"\cdot", "·"),
    (r"\simeq", "≃"),
    (r"\approx", "≈"),
    (r"\equiv", "≡"),
    (r"\cong", "≅"),
    (r"\propto", "∝"),
    (r"\sim", "∼"),
    (r"\leq", "≤"),
    (r"\geq", "≥"),
    (r"\neq", "≠"),
    (r"\iff", "⇔"),
    (r"\colon", ":"),
    (r"\square", "square.stroked"),
    (r"\mid", "mid(|)"),
    (r"\lvert", "|"),
    (r"\rvert", "|"),
    (r"\bigcup", "union.big"),
    (r"\bigcap", "inter.big"),
    (r"\cap", "∩"),
    (r"\cup", "∪"),
    (r"\neg", "¬"),
    (r"\lnot", "¬"),
    (r"\land", "∧"),
    (r"\lor", "∨"),
    (r"\le", "≤"),
    (r"\ge", "≥"),
    (r"\ne", "≠"),
    (r"\in", "∈"),
    (r"\to", "→"),
    (r"\pm", "±"),
    (r"\infty", "∞"),
    (r"\partial", "∂"),
    (r"\ell", "ℓ"),
    (r"\top", "⊤"),
    (r"\bot", "⊥"),
    (r"\sum", "sum"),
    (r"\prod", "product"),
    (r"\max", "max"),
    (r"\min", "min"),
    (r"\log", "log"),
    (r"\gcd", "gcd"),
    (r"\bmod", "mod"),
    (r"\pmod", "mod"),
    (r"\quad", "quad"),
    (r"\qquad", "wide"),
    (r"\,", "thin"),
    (r"\;", "med"),
    (r"\!", ""),
    (r"\alpha", "α"),
    (r"\beta", "β"),
    (r"\gamma", "γ"),
    (r"\Gamma", "Γ"),
    (r"\delta", "δ"),
    (r"\Delta", "Δ"),
    (r"\epsilon", "ε"),
    (r"\zeta", "ζ"),
    (r"\eta", "η"),
    (r"\theta", "θ"),
    (r"\Theta", "Θ"),
    (r"\kappa", "κ"),
    (r"\lambda", "λ"),
    (r"\Lambda", "Λ"),
    (r"\mu", "μ"),
    (r"\nu", "ν"),
    (r"\xi", "ξ"),
    (r"\Xi", "Ξ"),
    (r"\pi", "π"),
    (r"\Pi", "Π"),
    (r"\rho", "ρ"),
    (r"\sigma", "σ"),
    (r"\Sigma", "Σ"),
    (r"\tau", "τ"),
    (r"\upsilon", "υ"),
    (r"\Upsilon", "Υ"),
    (r"\phi", "φ"),
    (r"\Phi", "Φ"),
    (r"\chi", "χ"),
    (r"\psi", "ψ"),
    (r"\Psi", "Ψ"),
    (r"\omega", "ω"),
    (r"\Omega", "Ω"),
)

TYPST_MATH_KEYWORDS: frozenset[str] = frozenset(
    {
        "cal",
        "bb",
        "bold",
        "sqrt",
        "overline",
        "hat",
        "tilde",
        "cases",
        "sum",
        "product",
        "max",
        "min",
        "log",
        "gcd",
        "mod",
        "quad",
        "wide",
        "thin",
        "med",
        "space",
        "mid",
        "union",
        "inter",
        "big",
        "square",
        "stroked",
    }
)

THM_PLAIN_RE = re.compile(r"^\*\*(定理|引理|命题|推论)\s*([^。：:*]*)[。：:]\*\*\s*(.*)$", re.DOTALL)
THM_DEF_RE = re.compile(r"^\*\*(定义|公理|性质|反例|例|注记|注|约定)\s*([^。：:*]*)[。：:]\*\*\s*(.*)$", re.DOTALL)
PROOF_START_RE = re.compile(r"^\*\*(证明|构造与证明|制造凭据)([^*。：:]*)[。：:]\*\*\s*(.*)$", re.DOTALL)


def _extract_paired(text: str, start: int, open_ch: str, close_ch: str) -> tuple[str, int] | None:
    """从 start 处的左定界符提取配对内容及结束下标。"""
    if start >= len(text) or text[start] != open_ch:
        return None
    depth = 0
    idx = start
    while idx < len(text):
        ch = text[idx]
        if ch == "\\" and idx + 1 < len(text):
            idx += 2
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start + 1 : idx], idx + 1
        idx += 1
    return None


def _extract_braced(text: str, start: int) -> tuple[str, int] | None:
    """从 start 处的 '{' 提取配对花括号内容及结束下标。"""
    return _extract_paired(text, start, "{", "}")


def _replace_unary_macro(expr: str, macro: str, wrapper: str) -> str:
    """将 \\macro{...} 递归替换为 wrapper(...)。"""
    out: list[str] = []
    i = 0
    needle = "\\" + macro
    while i < len(expr):
        pos = expr.find(needle, i)
        if pos == -1:
            out.append(expr[i:])
            break
        after = pos + len(needle)
        if after < len(expr) and expr[after].isalpha():
            out.append(expr[i:after])
            i = after
            continue
        out.append(expr[i:pos])
        k = after
        while k < len(expr) and expr[k].isspace():
            k += 1
        braced = _extract_braced(expr, k)
        if braced is None:
            out.append(needle)
            i = after
        else:
            inner, nxt = braced
            inner_conv = _convert_math_body(inner)
            if wrapper == "QUOTE":
                escaped = inner.replace("\\", "\\\\").replace('"', '\\"')
                out.append(f' "{escaped}" ')
            else:
                out.append(f" {wrapper}({inner_conv}) ")
            i = nxt
    return "".join(out)


def _replace_frac(expr: str) -> str:
    """将 \\frac{a}{b} 递归替换为 (a) / (b)。"""
    out: list[str] = []
    i = 0
    needle = r"\frac"
    while i < len(expr):
        pos = expr.find(needle, i)
        if pos == -1:
            out.append(expr[i:])
            break
        after = pos + len(needle)
        if after < len(expr) and expr[after].isalpha():
            out.append(expr[i:after])
            i = after
            continue
        out.append(expr[i:pos])
        k = after
        while k < len(expr) and expr[k].isspace():
            k += 1
        first = _extract_braced(expr, k)
        if first is None:
            out.append(needle)
            i = after
            continue
        num, k2 = first
        while k2 < len(expr) and expr[k2].isspace():
            k2 += 1
        second = _extract_braced(expr, k2)
        if second is None:
            out.append(needle)
            i = after
            continue
        den, nxt = second
        num_c = _convert_math_body(num)
        den_c = _convert_math_body(den)
        out.append(f"({num_c}) / ({den_c})")
        i = nxt
    return "".join(out)


def _replace_scripts(expr: str) -> str:
    """将上下标统一转换为显式括号组 _(...) 与 ^(...)，防止 h_D(q) 或 F^r(X) 把圆括号吸入角标。"""
    out: list[str] = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "\\" and i + 1 < len(expr):
            out.append(expr[i : i + 2])
            i += 2
            continue
        if ch in ("_", "^"):
            k = i + 1
            while k < len(expr) and expr[k].isspace():
                k += 1
            if k >= len(expr):
                out.append(ch)
                break
            if expr[k] == "{":
                paired = _extract_paired(expr, k, "{", "}")
                if paired is not None:
                    inner, nxt = paired
                    out.append(f"{ch}({_convert_math_body(inner)})")
                    i = nxt
                    continue
            elif expr[k] == "(":
                paired = _extract_paired(expr, k, "(", ")")
                if paired is not None:
                    inner, nxt = paired
                    out.append(f"{ch}({_convert_math_body(inner)})")
                    i = nxt
                    continue
            elif expr.startswith("@@TXT", k):
                end_tok = expr.find("@@", k + 5)
                if end_tok != -1:
                    nxt = end_tok + 2
                    out.append(f"{ch}({expr[k:nxt]})")
                    i = nxt
                    continue
            elif expr[k] == "\\" and k + 1 < len(expr):
                m = k + 1
                if expr[m].isalpha():
                    while m < len(expr) and expr[m].isalpha():
                        m += 1
                else:
                    m += 1
                inner_c = _convert_math_body(expr[k:m])
                out.append(f"{ch}({inner_c})")
                i = m
                continue
            else:
                out.append(f"{ch}({expr[k]})")
                i = k + 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _escape_top_level_commas(s: str) -> str:
    """在 Typst cases(...) 单行内部将顶层逗号转义为 \\,，保留括号内部的函数参数逗号。"""
    out: list[str] = []
    depth = 0
    in_quote = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            out.append(s[i : i + 2])
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
            out.append(ch)
            i += 1
            continue
        if not in_quote:
            if ch in ("(", "[", "{"):
                depth += 1
            elif ch in (")", "]", "}") and depth > 0:
                depth -= 1
            elif ch == "," and depth == 0:
                out.append(r"\,")
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _convert_math_body(expr: str) -> str:
    """递归转换数学表达式主体，不包裹外层 $ 定界符。"""
    s = expr.strip()

    # 先转换并暂存 \begin{cases}...\end{cases}，避免外层二次转义破坏内部 \/ 与 \,
    cases_slots: list[str] = []

    def _stash_cases(m: re.Match[str]) -> str:
        raw_rows = re.split(r"\\\\", m.group(1))
        conv_rows: list[str] = []
        for row in raw_rows:
            row_s = row.strip()
            if not row_s:
                continue
            parts = row_s.split("&")
            conv_parts = [_escape_top_level_commas(_convert_math_body(p)) for p in parts]
            conv_rows.append(" quad & ".join(conv_parts))
        tok = f"@@CASES{len(cases_slots)}@@"
        cases_slots.append(f"cases({', '.join(conv_rows)})")
        return tok

    s = re.sub(r"\\begin\{cases\}(.*?)\\end\{cases\}", _stash_cases, s, flags=re.DOTALL)
    s = re.sub(r"\\begin\{(aligned|align\*?)\}", "", s)
    s = re.sub(r"\\end\{(aligned|align\*?)\}", "", s)
    s = re.sub(r"\\(?:left|right|[bB]igg?)(?![A-Za-z])", "", s)

    # 先提取文本与算子名宏，保护内部字符不被后续数学替换污染
    text_slots: list[str] = []

    def _stash_quote(kind_expr: str) -> str:
        for macro in ("text", "mathrm", "operatorname", "textbf"):
            out: list[str] = []
            i = 0
            needle = "\\" + macro
            while i < len(kind_expr):
                pos = kind_expr.find(needle, i)
                if pos == -1:
                    out.append(kind_expr[i:])
                    break
                after = pos + len(needle)
                if after < len(kind_expr) and kind_expr[after].isalpha():
                    out.append(kind_expr[i:after])
                    i = after
                    continue
                out.append(kind_expr[i:pos])
                k = after
                while k < len(kind_expr) and kind_expr[k].isspace():
                    k += 1
                braced = _extract_braced(kind_expr, k)
                if braced is None:
                    out.append(needle)
                    i = after
                else:
                    inner, nxt = braced
                    escaped = inner.strip().replace("\\", "\\\\").replace('"', '\\"')
                    token = f"@@TXT{len(text_slots)}@@"
                    if macro == "textbf":
                        text_slots.append(f'bold("{escaped}")')
                    else:
                        text_slots.append(f'"{escaped}"')
                    out.append(token)
                    i = nxt
            kind_expr = "".join(out)
        return kind_expr

    s = _stash_quote(s)
    s = s.replace(r"\{", "@@LBRACE@@").replace(r"\}", "@@RBRACE@@")
    s = s.replace(r"\\", " @@NL@@ ")
    # LaTeX 中的裸 '/' 表示行内斜线，仅 \frac{a}{b} 表示上下分式
    s = s.replace("/", "@@SLASH@@")

    s = _replace_frac(s)
    for macro, wrapper in (("mathcal", "cal"), ("mathbb", "bb"), ("mathbf", "bold"), ("sqrt", "sqrt"), ("overline", "overline"), ("hat", "hat"), ("tilde", "tilde")):
        s = _replace_unary_macro(s, macro, wrapper)
    s = _replace_scripts(s)

    for latex_cmd, typst_sym in LATEX_SYMBOLS:
        if latex_cmd[-1].isalpha():
            s = re.sub(re.escape(latex_cmd) + r"(?![A-Za-z])", lambda _, r=typst_sym: f" {r} ", s)
        else:
            s = s.replace(latex_cmd, f" {typst_sym} ")

    s = s.replace(r"\ ", " space ")
    # 剩余花括号组转圆括号组
    s = s.replace("{", "(").replace("}", ")")

    # 将 LaTeX 中连写的单字母变量乘积（如 DDD, CC, PP, nH）拆分为单字母，保留占位符与 Typst 关键字
    def _split_juxtaposed_vars(m: re.Match[str]) -> str:
        word = m.group(1)
        if word in TYPST_MATH_KEYWORDS or word.startswith(("TXT", "CASES")) or word in ("LBRACE", "RBRACE", "SLASH", "NL"):
            return word
        return " ".join(word)

    s = re.sub(r"(?<!@)\b([A-Za-z]{2,})\b(?!@)", _split_juxtaposed_vars, s)

    s = s.replace("@@LBRACE@@", "{").replace("@@RBRACE@@", "}")
    s = s.replace("@@SLASH@@", r"\/")
    s = s.replace("@@NL@@", "\\")
    for idx, val in enumerate(text_slots):
        s = s.replace(f"@@TXT{idx}@@", val)
    for idx, val in enumerate(cases_slots):
        s = s.replace(f"@@CASES{idx}@@", val)
    return re.sub(r"[ \t]+", " ", s).strip()


def latex_to_typst_math(expr: str, *, display: bool = False) -> str:
    """将本项目 Markdown 使用的 LaTeX 数学子集转换为 Typst 数学表达式。"""
    s = _convert_math_body(expr)
    return f"$ {s} $" if display else f"${s}$"


def escape_typst_text(text: str) -> str:
    """转义普通散文中的 Typst 敏感语法字符。"""
    text = text.replace("\\n", "")
    out: list[str] = []
    for ch in text:
        if ch in ("\\", "#", "*", "_", "`", "$", "<", ">", "@", "[", "]", "~"):
            out.append("\\" + ch)
        else:
            out.append(ch)
    res = "".join(out)
    res = res.replace("//", "\\/\\/").replace("/*", "\\/\\*")
    return res


def render_inline(text: str) -> str:
    """解析行内代码、行内公式、粗体、斜体与超链接并输出 Typst 标记。"""
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        # 1. 行内代码 `...`
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                raw_body = text[i + 1 : end]
                escaped = raw_body.replace("\\", "\\\\").replace('"', '\\"')
                tokens.append(f'#raw("{escaped}")')
                i = end + 1
                continue
        # 2. 行内公式 $...$
        if text[i] == "$" and (i + 1 < n and text[i + 1] != "$"):
            end = i + 1
            while end < n:
                if text[end] == "\\" and end + 1 < n:
                    end += 2
                    continue
                if text[end] == "$":
                    break
                end += 1
            if end < n and text[end] == "$":
                math_src = text[i + 1 : end]
                tokens.append(latex_to_typst_math(math_src, display=False))
                i = end + 1
                continue
        # 3. 粗体 **...**
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                inner = render_inline(text[i + 2 : end])
                tokens.append(f"#strong[{inner}]")
                i = end + 2
                continue
        # 4. Markdown 链接 [label](url) -> 保留可读文字
        if text[i] == "[":
            close_b = text.find("]", i + 1)
            if close_b != -1 and close_b + 1 < n and text[close_b + 1] == "(":
                close_p = text.find(")", close_b + 2)
                if close_p != -1:
                    label = text[i + 1 : close_b]
                    tokens.append(render_inline(label))
                    i = close_p + 1
                    continue
        # 5. 普通文本片段
        nxt = i + 1
        while nxt < n and text[nxt] not in ("`", "$", "*", "["):
            nxt += 1
        tokens.append(escape_typst_text(text[i:nxt]))
        i = nxt
    return "".join(tokens)


def _strip_heading_number(title: str) -> str:
    """移除标题前手工填写的 '1.' 或 '2.1' 序号，交由 Typst 统一自动编号。"""
    return re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title.strip())


def _split_table_row(line: str) -> list[str]:
    """切分 Markdown 表格单行单元格，忽略 $...$ 行内公式与 `...` 行内代码中的竖线 '|'。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    cells: list[str] = []
    cur: list[str] = []
    in_math = False
    in_code = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            cur.append(s[i : i + 2])
            i += 2
            continue
        if ch == "`" and not in_math:
            in_code = not in_code
            cur.append(ch)
            i += 1
            continue
        if ch == "$" and not in_code:
            in_math = not in_math
            cur.append(ch)
            i += 1
            continue
        if ch == "|" and not in_math and not in_code:
            cells.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def _render_table(rows: list[list[str]]) -> str:
    """将 Markdown 表格渲染为学术三线表（booktabs 风格）。"""
    if not rows:
        return ""
    ncols = max(len(r) for r in rows)
    norm_rows = [r + [""] * (ncols - len(r)) for r in rows]
    max_lens = [max(len(r[c].strip()) for r in norm_rows) for c in range(ncols)]
    # 短列使用 auto，宽文本列使用 1fr 自动折行以防溢出页面
    col_specs = []
    align_specs = []
    for max_len in max_lens:
        if max_len <= 18 or ncols >= 4:
            col_specs.append("auto")
        else:
            col_specs.append("1fr")
        align_specs.append("center" if max_len <= 8 else "left")

    breakable = "false" if len(norm_rows) <= 9 else "true"
    lines = [
        f"#table-fig({breakable}, figure(",
        "  kind: table,",
        "  supplement: none,",
        "  table(",
        f"    columns: ({', '.join(col_specs)}),",
        f"    align: ({', '.join(align_specs)}),",
        "    inset: (x: 7pt, y: 5.5pt),",
        "    stroke: none,",
        "    table.hline(stroke: 1.0pt + black),",
    ]
    header_cells = ", ".join(f"[#strong[{render_inline(cell.strip())}]]" for cell in norm_rows[0][:ncols])
    lines.append(f"    table.header({header_cells}),")
    lines.append("    table.hline(stroke: 0.5pt + black),")
    for row in norm_rows[1:]:
        body_cells = ", ".join(f"[{render_inline(cell.strip())}]" for cell in row[:ncols])
        lines.append(f"    {body_cells},")
    lines.append("    table.hline(stroke: 1.0pt + black),")
    lines.append("  )")
    lines.append("))")
    return "\n".join(lines)


def _render_code_block(code_lines: list[str], lang: str) -> str:
    """将网格示意或伪代码框渲染为等宽居中/缩进学术代码框。"""
    body = "\n".join(code_lines).rstrip()
    escaped = body.replace("\\", "\\\\").replace('"', '\\"')
    breakable = "false" if len(code_lines) <= 22 else "true"
    return (
        f"#block(breakable: {breakable}, width: 100%, inset: (x: 10pt, y: 7pt), "
        f"stroke: (left: 1.4pt + luma(150), top: 0.35pt + luma(210), bottom: 0.35pt + luma(210), right: 0.35pt + luma(210)), "
        f"fill: luma(250), above: 0.85em, below: 0.85em)[\n"
        f"  #set par(first-line-indent: 0em, leading: 0.58em)\n"
        f'  #raw(block: true, "{escaped}")\n'
        f"]"
    )


def markdown_to_typst(source_text: str, series_label: str) -> str:
    """解析整篇理论 Markdown，输出完整可编译的 Typst 学术论文源码。"""
    lines = source_text.replace("\r\n", "\n").splitlines()
    title = "Shapez 2 TMAM 理论论文"
    abstract_body: str | None = None
    keywords_body: str | None = None

    blocks: list[tuple[str, object]] = []
    idx = 0
    n = len(lines)
    first_h1 = True

    while idx < n:
        line = lines[idx]
        stripped = line.strip()
        if not stripped:
            idx += 1
            continue

        # 顶层标题
        if first_h1 and stripped.startswith("# "):
            title = stripped[2:].strip()
            first_h1 = False
            idx += 1
            continue

        # 跳过旧式“理论论文正文”或“章节说明”套话
        if stripped in ("**理论论文正文**", "理论论文正文"):
            idx += 1
            continue
        if stripped == "## 章节说明":
            idx += 1
            while idx < n and not lines[idx].startswith("## "):
                idx += 1
            continue

        # 旧式“## 文献章节 k：xxx.md”转为温和的来源题注，不再充当重复一级大标题
        lit_match = re.match(r"^##\s+文献章节\s*\d+[：:]\s*(.+)$", stripped)
        if lit_match:
            idx += 1
            continue

        # 数学行间公式块 $$ ... $$
        if stripped.startswith("$$"):
            if stripped.endswith("$$") and len(stripped) > 4:
                blocks.append(("math", stripped[2:-2].strip()))
                idx += 1
                continue
            idx += 1
            math_lines = []
            while idx < n and not lines[idx].strip().startswith("$$"):
                math_lines.append(lines[idx])
                idx += 1
            if idx < n:
                idx += 1
            blocks.append(("math", "\n".join(math_lines)))
            continue

        # 围栏代码块 ```...```
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            idx += 1
            code_lines = []
            while idx < n and not lines[idx].strip().startswith("```"):
                code_lines.append(lines[idx])
                idx += 1
            if idx < n:
                idx += 1
            blocks.append(("code", (code_lines, lang)))
            continue

        # 各级章节标题
        h_match = re.match(r"^(#{2,5})\s+(.+?)\s*#*$", stripped)
        if h_match:
            hashes, raw_h = h_match.groups()
            level = len(hashes) - 1  # ## -> 1, ### -> 2, #### -> 3
            if raw_h == "文献来源与参考卷索引":
                blocks.append(("unnumbered_h1", raw_h))
            else:
                blocks.append(("heading", (min(level, 3), _strip_heading_number(raw_h))))
            idx += 1
            continue

        # 水平分隔线
        if re.fullmatch(r"---+", stripped):
            idx += 1
            continue

        # 表格
        if stripped.startswith("|"):
            tbl_rows: list[list[str]] = []
            while idx < n and lines[idx].strip().startswith("|"):
                cells = _split_table_row(lines[idx])
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    tbl_rows.append(cells)
                idx += 1
            blocks.append(("table", tbl_rows))
            continue

        # 引用块 > ...
        if stripped.startswith(">"):
            q_lines = []
            while idx < n and lines[idx].strip().startswith(">"):
                q_line = re.sub(r"^>\s?", "", lines[idx].strip())
                q_lines.append(q_line)
                idx += 1
            blocks.append(("quote", " ".join(q_lines)))
            continue

        # 有序或无序列表
        list_m = re.match(r"^(\s*)(?:([-*])|(\d+)\.)\s+(.+)$", line)
        if list_m:
            ordered = list_m.group(3) is not None
            items: list[str] = []
            while idx < n:
                m = re.match(r"^(\s*)(?:([-*])|(\d+)\.)\s+(.+)$", lines[idx])
                if not m or (m.group(3) is not None) != ordered:
                    break
                item_parts = [m.group(4).strip()]
                idx += 1
                while idx < n and lines[idx].startswith("  ") and not re.match(r"^\s*(?:[-*]|\d+\.)\s+", lines[idx]):
                    if not lines[idx].strip():
                        break
                    item_parts.append(lines[idx].strip())
                    idx += 1
                items.append(" ".join(item_parts))
            blocks.append(("list", (ordered, items)))
            continue

        # 普通段落（合并连续文本行）
        para_lines = [stripped]
        idx += 1
        while idx < n and lines[idx].strip():
            cand = lines[idx].strip()
            if (
                cand.startswith(("#", "|", "```", "$$", ">", "---"))
                or re.match(r"^(?:[-*]|\d+\.)\s+", cand)
            ):
                break
            para_lines.append(cand)
            idx += 1
        para = " ".join(para_lines)

        # 提取顶层摘要与关键词
        abs_m = re.match(r"^\*\*摘要[。：:]?\*\*\s*(.*)$", para)
        if abs_m and abstract_body is None and not blocks:
            abstract_body = abs_m.group(1).strip()
            continue
        kw_m = re.match(r"^\*\*关键词[。：:]?\*\*\s*(.*)$", para)
        if kw_m and keywords_body is None and len(blocks) <= 1:
            keywords_body = kw_m.group(1).strip()
            continue

        blocks.append(("para", para))

    # 二次扫描：将 **定理/引理/定义...** 与多段 **证明。** ... 证毕。 结构化封装
    body_out: list[str] = []
    b_idx = 0
    total_b = len(blocks)

    while b_idx < total_b:
        btype, bval = blocks[b_idx]
        if btype == "heading":
            lvl, htext = bval  # type: ignore[misc]
            eqs = "=" * int(lvl)
            body_out.append(f"{eqs} {render_inline(htext)}\n")
            b_idx += 1
            continue
        if btype == "unnumbered_h1":
            body_out.append(f"#heading(level: 1, numbering: none)[{render_inline(str(bval))}]\n")
            b_idx += 1
            continue
        if btype == "math":
            body_out.append(latex_to_typst_math(str(bval), display=True) + "\n")
            b_idx += 1
            continue
        if btype == "code":
            c_lines, c_lang = bval  # type: ignore[misc]
            body_out.append(_render_code_block(c_lines, c_lang) + "\n")
            b_idx += 1
            continue
        if btype == "table":
            body_out.append(_render_table(bval) + "\n")  # type: ignore[arg-type]
            b_idx += 1
            continue
        if btype == "quote":
            body_out.append(f"#quote-env[{render_inline(str(bval))}]\n")
            b_idx += 1
            continue
        if btype == "list":
            ordered, items = bval  # type: ignore[misc]
            marker = "+" if ordered else "-"
            list_lines = ["#block(above: 0.65em, below: 0.65em)["]
            for it in items:
                list_lines.append(f"  {marker} {render_inline(it)}")
            list_lines.append("]\n")
            body_out.append("\n".join(list_lines))
            b_idx += 1
            continue

        # 段落：检查是否为定理类、定义类或证明起点
        para_str = str(bval)
        m_plain = THM_PLAIN_RE.match(para_str)
        if m_plain:
            kind, suffix, rest = m_plain.groups()
            head = f"{kind} {suffix.strip()}".strip()
            body_out.append(f"#thm-plain[{render_inline(head)}][{render_inline(rest)}]\n")
            b_idx += 1
            continue

        m_def = THM_DEF_RE.match(para_str)
        if m_def:
            kind, suffix, rest = m_def.groups()
            head = f"{kind} {suffix.strip()}".strip()
            body_out.append(f"#thm-def[{render_inline(head)}][{render_inline(rest)}]\n")
            b_idx += 1
            continue

        m_proof = PROOF_START_RE.match(para_str)
        if m_proof:
            p_kind, p_note, p_rest = m_proof.groups()
            p_head = f"{p_kind}{p_note}".strip()
            # 收集证明体直到遇到“证毕。”、“□”或下一个章节/定理/证明
            proof_parts: list[str] = []

            def _strip_qed(s: str) -> tuple[str, bool]:
                for qed_tok in ("证毕。", "证毕", "引理得证。", "命题得证。", "定理得证。", r"$\square$", "□"):
                    if s.rstrip().endswith(qed_tok):
                        cleaned = s.rstrip()[: -len(qed_tok)].rstrip()
                        return cleaned, True
                return s, False

            first_clean, ended = _strip_qed(p_rest)
            proof_parts.append(render_inline(first_clean))
            ended_in_list = False
            b_idx += 1

            while not ended and b_idx < total_b:
                nt, nv = blocks[b_idx]
                if nt in ("heading", "unnumbered_h1"):
                    break
                if nt == "para":
                    ns = str(nv)
                    if THM_PLAIN_RE.match(ns) or THM_DEF_RE.match(ns) or PROOF_START_RE.match(ns):
                        break
                    nclean, ended = _strip_qed(ns)
                    proof_parts.append("\n\n" + render_inline(nclean))
                    ended_in_list = False
                    b_idx += 1
                elif nt == "math":
                    proof_parts.append("\n" + latex_to_typst_math(str(nv), display=True) + "\n")
                    ended_in_list = False
                    b_idx += 1
                elif nt == "table":
                    proof_parts.append("\n" + _render_table(nv) + "\n")  # type: ignore[arg-type]
                    ended_in_list = False
                    b_idx += 1
                elif nt == "list":
                    ord_flag, l_items = nv  # type: ignore[misc]
                    mk = "+" if ord_flag else "-"
                    ll = ["\n#block(above: 0.45em, below: 0.45em)["]
                    for idx_i, it in enumerate(l_items):
                        if idx_i == len(l_items) - 1:
                            it_clean, ended = _strip_qed(it)
                            if ended:
                                ll.append(f"  {mk} {render_inline(it_clean)}#h(1fr)$square.stroked$")
                                ended_in_list = True
                            else:
                                ll.append(f"  {mk} {render_inline(it_clean)}")
                        else:
                            ll.append(f"  {mk} {render_inline(it)}")
                    ll.append("]\n")
                    proof_parts.append("\n".join(ll))
                    b_idx += 1
                elif nt == "code":
                    cl, clang = nv  # type: ignore[misc]
                    proof_parts.append("\n" + _render_code_block(cl, clang) + "\n")
                    ended_in_list = False
                    b_idx += 1
                else:
                    break

            joined_proof = "".join(proof_parts).strip()
            qed_tail = "" if ended_in_list else "#h(1fr)$square.stroked$"
            body_out.append(f"#proof-env[{render_inline(p_head)}][{joined_proof}{qed_tail}]\n")
            continue

        # 跨小节长证明末尾收束句：保留收束语并在行末右对齐补齐证毕墓碑符 □
        stripped_para = para_str.rstrip()
        if stripped_para.endswith("证毕。") or re.search(r"(?:定理|引理|命题|推论)\s*[\d.]*\s*得证。$", stripped_para):
            if stripped_para.endswith("证毕。"):
                trimmed = stripped_para[: -len("证毕。")].rstrip()
                body_out.append(f"{render_inline(trimmed)}#h(1fr)$square.stroked$\n")
            else:
                body_out.append(f"{render_inline(stripped_para)}#h(1fr)$square.stroked$\n")
            b_idx += 1
            continue

        body_out.append(render_inline(para_str) + "\n")
        b_idx += 1

    escaped_title = render_inline(title)
    escaped_series = escape_typst_text(series_label)
    header_short = escape_typst_text(title)

    abstract_typst = ""
    if abstract_body:
        kw_line = ""
        if keywords_body:
            kw_line = f"\n  #v(0.35em)\n  #noindent[*关键词：*{render_inline(keywords_body)}]"
        abstract_typst = f"""
#v(0.8em)
#pad(x: 1.8em)[
  #set text(size: 9.5pt)
  #set par(leading: 0.72em, first-line-indent: 0em, justify: true)
  *摘要：*{render_inline(abstract_body)}{kw_line}
]
"""

    preamble = f"""// 自动由 build_paper_pdf.py 生成的 Typst 学术论文稿
#set document(title: "{escape_typst_text(title)}")
#set page(
  paper: "a4",
  margin: (top: 25mm, bottom: 25mm, left: 25mm, right: 25mm),
  header: context {{
    if counter(page).get().first() > 1 [
      #set text(font: ("New Computer Modern", "KaiTi", "SimSun"), size: 8.8pt, fill: luma(80))
      #grid(
        columns: (1fr, auto),
        align: (left, right),
        [{header_short}],
        [{escaped_series}],
      )
      #v(-0.55em)
      #line(length: 100%, stroke: 0.4pt + luma(140))
    ]
  }},
  footer: context [
    #set text(font: "New Computer Modern", size: 9.5pt)
    #align(center)[#counter(page).display("1")]
  ],
)

#set text(
  font: ("New Computer Modern", "SimSun"),
  lang: "zh",
  region: "cn",
  size: 10.5pt,
  fill: black,
)

#set par(
  justify: true,
  leading: 0.84em,
  spacing: 1.05em,
  first-line-indent: (amount: 2em, all: true),
)

#set heading(numbering: (..nums) => {{
  let n = nums.pos()
  if n.len() <= 3 {{
    numbering("1.1", ..n)
  }}
}})

#show heading: it => {{
  set par(first-line-indent: 0em)
  set text(font: ("New Computer Modern", "SimHei"), weight: "bold")
  if it.level == 1 {{
    v(1.35em, weak: true)
    text(size: 13.5pt)[#it]
    v(0.75em, weak: true)
  }} else if it.level == 2 {{
    v(1.05em, weak: true)
    text(size: 11.5pt)[#it]
    v(0.55em, weak: true)
  }} else {{
    v(0.85em, weak: true)
    text(size: 10.5pt)[#it]
    v(0.45em, weak: true)
  }}
}}

#show strong: set text(font: ("New Computer Modern", "SimHei"), weight: "bold")
#show math.equation: set text(font: ("New Computer Modern Math", "SimSun"), size: 10.5pt)
#show math.equation.where(block: true): set block(above: 0.85em, below: 0.85em)
#show raw: set text(font: ("Consolas", "DejaVu Sans Mono", "NSimSun", "SimSun"), size: 9pt)
#show figure.where(kind: table): set block(above: 0.95em, below: 0.95em, breakable: true)

#let table-fig(brk, body) = {{
  show figure.where(kind: table): set block(breakable: brk)
  body
}}

#let noindent(body) = {{
  set par(first-line-indent: 0em)
  body
}}

#let thm-plain(head, body) = block(breakable: true, width: 100%, above: 0.9em, below: 0.9em)[
  #set par(first-line-indent: 0em)
  #strong[#head.]#h(0.45em)#text(font: ("New Computer Modern", "KaiTi", "SimSun"))[#body]
]

#let thm-def(head, body) = block(breakable: true, width: 100%, above: 0.9em, below: 0.9em)[
  #set par(first-line-indent: 0em)
  #strong[#head.]#h(0.45em)#body
]

#let proof-env(head, body) = block(breakable: true, width: 100%, above: 0.7em, below: 0.95em)[
  #set par(first-line-indent: (amount: 2em, all: false))
  #text(font: ("New Computer Modern", "KaiTi", "SimHei"), weight: "bold")[#head.]#h(0.45em)#body
]

#let quote-env(body) = block(
  breakable: true,
  width: 100%,
  inset: (left: 1em, right: 0.6em, y: 0.45em),
  stroke: (left: 1.5pt + luma(120)),
  above: 0.8em,
  below: 0.8em,
)[
  #set par(first-line-indent: 0em)
  #set text(font: ("New Computer Modern", "KaiTi", "SimSun"), size: 9.8pt)
  #body
]

// 首页学术论文版头
#align(center)[
  #set par(first-line-indent: 0em, leading: 0.65em)
  #text(font: ("New Computer Modern", "SimSun"), size: 9.5pt, fill: luma(70))[{escaped_series}]
  #v(0.55em)
  #text(font: ("New Computer Modern", "SimHei"), size: 17.5pt, weight: "bold")[{escaped_title}]
  #v(0.5em)
  #text(font: ("New Computer Modern", "KaiTi", "SimSun"), size: 10.5pt)[ShapezToolkit 理论研究组]
]
{abstract_typst}
#v(0.6em)
#line(length: 100%, stroke: 0.5pt + luma(120))
#v(0.2em)
"""
    return preamble + "\n" + "\n".join(body_out)


def build(source: Path = SOURCE, output: Path = OUTPUT, series_label: str | None = None) -> None:
    """读取理论 Markdown，转译为 Typst 并编译输出 A4 PDF。"""
    if series_label is None:
        matched = next((label for src, _, label in PAPERS if src == source.name), "Shapez 2 TMAM 形式化理论论文")
        series_label = matched
    source_text = source.read_text(encoding="utf-8")
    typst_source = markdown_to_typst(source_text, series_label)
    pdf_bytes, warnings = typst.compile_with_warnings(typst_source.encode("utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pdf_bytes)
    warn_note = f"（警告 {len(warnings)} 条：{warnings}）" if warnings else ""
    print(f"已编译学术版 PDF：{output}（{len(pdf_bytes) // 1024} KB）<- {source}{warn_note}")


def main(argv: list[str] | None = None) -> int:
    """命令行入口：支持单篇编译或 --all 全量编译。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE, help="理论 Markdown 源文件路径")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="导出 PDF 路径")
    parser.add_argument("--all", action="store_true", help="重新编译全部四篇正文论文与附录")
    args = parser.parse_args(argv)
    if args.all:
        for src_name, pdf_name, label in PAPERS:
            build(THEORY_DIR / src_name, ROOT / pdf_name, label)
        return 0
    build(args.source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
