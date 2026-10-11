"""Markdown -> a styled .docx, a print-ready HTML page and a PDF, in one theme.

Front matter (optional, between --- lines at the top):
  title, subtitle, author, date, theme, paper (letter|a4), toc (true|false), cover (true|false)

Supported Markdown: # to #### headings, paragraphs, - / * / 1. lists (nested by two spaces),
pipe tables, ![caption](path) images on their own line, > quotes, ``` code blocks,
--- rules, <!-- pagebreak -->, and inline **bold**, *italic*, `code`, [links](url).
Image paths are relative to the Markdown file.
"""

from __future__ import annotations

import base64
import html
import mimetypes
import re
from pathlib import Path

from . import inline
from .themes import THEMES, Theme, get_theme, hex_to_rgb

# Documents print on white: dark themes borrow a light sibling's colours.
_LIGHT_SIBLING = {"midnight": "ocean", "ember": "paper"}


def _doc_theme(name: str | None) -> Theme:
    theme = get_theme(name)
    return THEMES[_LIGHT_SIBLING[theme.name]] if theme.dark else theme


# ---------------------------------------------------------------- parsing

_HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
_IMAGE = re.compile(r"^!\[(.*?)\]\((\S+?)(?:\s+\"(.*?)\")?\)\s*$")
_LIST = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")


def parse(text: str) -> tuple[dict, list[dict]]:
    meta: dict = {}
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[0].strip() == "---":
        end = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), None)
        if end:
            for ln in lines[1:end]:
                if ":" in ln:
                    key, value = ln.split(":", 1)
                    meta[key.strip().lower()] = value.strip().strip('"').strip("'")
            lines = lines[end + 1:]

    blocks: list[dict] = []
    para: list[str] = []

    def flush():
        if para:
            blocks.append({"type": "para", "text": " ".join(s.strip() for s in para)})
            para.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush()
            i += 1
            continue
        if stripped.lower() in {"<!-- pagebreak -->", "\\pagebreak", "\\newpage"}:
            flush()
            blocks.append({"type": "pagebreak"})
            i += 1
            continue
        if stripped.startswith("```"):
            flush()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append({"type": "code", "text": "\n".join(code)})
            i += 1
            continue
        m = _HEADING.match(line)
        if m:
            flush()
            blocks.append({"type": "heading", "level": len(m.group(1)), "text": m.group(2)})
            i += 1
            continue
        m = _IMAGE.match(stripped)
        if m:
            flush()
            blocks.append({"type": "image", "caption": m.group(3) or m.group(1), "path": m.group(2)})
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            flush()

            def cells(row: str) -> list[str]:
                row = row.strip()
                if row.startswith("|"):
                    row = row[1:]
                if row.endswith("|"):
                    row = row[:-1]
                return [c.strip() for c in re.split(r"(?<!\\)\|", row)]

            header = cells(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            blocks.append({"type": "table", "header": header, "rows": rows})
            continue
        if _RULE.match(line) and not para:
            blocks.append({"type": "rule"})
            i += 1
            continue
        m = _LIST.match(line)
        if m and not para:
            items = []
            ordered = m.group(2)[0].isdigit()
            while i < len(lines):
                m = _LIST.match(lines[i])
                if m:
                    level = min(2, len(m.group(1).replace("\t", "  ")) // 2)
                    items.append({"level": level, "text": m.group(3).strip(), "ordered": m.group(2)[0].isdigit()})
                    i += 1
                elif lines[i].strip() and lines[i].startswith((" ", "\t")) and items:
                    items[-1]["text"] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            blocks.append({"type": "list", "ordered": ordered, "items": items})
            continue
        if stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append({"type": "quote", "text": " ".join(q for q in quote if q)})
            continue
        if para and re.match(r"^\s*\[\d+\]", line):
            flush()  # each [n] reference starts its own paragraph
        para.append(line)
        i += 1
    flush()
    return meta, blocks


def check(meta: dict, blocks: list[dict], base: Path) -> list[str]:
    warnings = []
    if not meta.get("title") and not any(b["type"] == "heading" and b["level"] == 1 for b in blocks):
        warnings.append("No title: add 'title:' front matter or a # heading.")
    last = 1
    for b in blocks:
        if b["type"] == "heading":
            if b["level"] > last + 1:
                warnings.append(f"Heading '{inline.plain(b['text'])}' skips a level (h{last} -> h{b['level']}).")
            last = b["level"]
        elif b["type"] == "image" and not (base / b["path"]).exists():
            warnings.append(f"Image not found: {b['path']}")
        elif b["type"] == "para" and len(inline.plain(b["text"]).split()) > 180:
            warnings.append(f"A paragraph runs {len(inline.plain(b['text']).split())} words: split it.")
    return warnings


# ---------------------------------------------------------------- DOCX


def build_docx(meta: dict, blocks: list[dict], base: Path, theme: Theme, out: Path) -> None:
    from docx import Document
    from docx.enum.section import WD_ORIENT  # noqa: F401  (kept for callers extending layouts)
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    t = theme
    doc = Document()

    def rgb(hexv: str) -> RGBColor:
        return RGBColor(*hex_to_rgb(hexv))

    # Page
    sec = doc.sections[0]
    if meta.get("paper", "letter").lower() == "a4":
        sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    else:
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = Inches(1)
    sec.top_margin = sec.bottom_margin = Inches(0.9)
    text_width = sec.page_width - sec.left_margin - sec.right_margin

    def set_font(style_or_run, name: str):
        element = getattr(style_or_run, "element", None)
        if element is None:
            element = style_or_run._element
        rpr = element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.insert(0, fonts)
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if fonts.get(qn(attr)) is not None:
                del fonts.attrib[qn(attr)]
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            fonts.set(qn(attr), name)

    normal = doc.styles["Normal"]
    set_font(normal, t.body_font)
    normal.font.size = Pt(11)
    normal.font.color.rgb = rgb(t.text)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.2

    for level, size, color, before in ((1, 20, t.accent, 20), (2, 15, t.text, 16), (3, 12.5, t.accent, 12), (4, 11.5, t.text, 10)):
        st = doc.styles[f"Heading {level}"]
        set_font(st, t.heading_font)
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.italic = False
        st.font.color.rgb = rgb(color)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.keep_with_next = True

    def add_bottom_border(paragraph, color: str, size: int = 12):
        ppr = paragraph._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), str(size))
        bottom.set(qn("w:space"), "6")
        bottom.set(qn("w:color"), color.lstrip("#"))
        borders.append(bottom)
        ppr.append(borders)

    def shade(element_pr, color: str):
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), color.lstrip("#"))
        element_pr.append(shd)

    def add_hyperlink(paragraph, url: str, text: str, bold: bool, italic: bool):
        r_id = paragraph.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
        link = OxmlElement("w:hyperlink")
        link.set(qn("r:id"), r_id)
        run = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), t.accent.lstrip("#"))
        rpr.append(color)
        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        rpr.append(underline)
        if bold:
            rpr.append(OxmlElement("w:b"))
        if italic:
            rpr.append(OxmlElement("w:i"))
        run.append(rpr)
        text_el = OxmlElement("w:t")
        text_el.text = text
        text_el.set(qn("xml:space"), "preserve")
        run.append(text_el)
        link.append(run)
        paragraph._p.append(link)

    def add_runs(paragraph, text: str, size=None, color=None, italic=False):
        for r in inline.parse(text, italic=italic):
            if r.link:
                add_hyperlink(paragraph, r.link, r.text, r.bold, r.italic)
                continue
            run = paragraph.add_run(r.text)
            run.bold = r.bold
            run.italic = r.italic
            if r.code:
                run.font.name = "Consolas"
            if size:
                run.font.size = Pt(size)
            if color:
                run.font.color.rgb = rgb(color)

    def add_field(paragraph, instr: str):
        run = paragraph.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        code = OxmlElement("w:instrText")
        code.set(qn("xml:space"), "preserve")
        code.text = instr
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(begin)
        run._r.append(code)
        run._r.append(end)
        return run

    numbering_restarts = {"count": 0}

    def restart_numbering(paragraph):
        """Each separate numbered list starts again at 1."""
        try:
            numbering = doc.part.numbering_part.numbering_definitions._numbering
            num_id = doc.styles["List Number"].element.pPr.numPr.numId.val
            abstract_id = numbering.num_having_numId(num_id).abstractNumId.val
            new_num = numbering.add_num(abstract_id)
            new_num.add_lvlOverride(ilvl=0).add_startOverride(1)
            num_pr = paragraph._p.get_or_add_pPr().get_or_add_numPr()
            num_pr.get_or_add_ilvl().val = 0
            num_pr.get_or_add_numId().val = new_num.numId
            numbering_restarts["count"] += 1
        except Exception:
            pass

    # Title block
    title = meta.get("title")
    if title:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(inline.plain(title))
        run.bold = True
        run.font.size = Pt(28)
        run.font.color.rgb = rgb(t.text)
        set_font(run, t.heading_font)
        if meta.get("subtitle"):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            add_runs(p, meta["subtitle"], size=14, color=t.muted)
        info = " · ".join(x for x in [meta.get("author", ""), meta.get("date", "")] if x)
        p = doc.add_paragraph()
        if info:
            add_runs(p, info, size=10, color=t.muted)
        add_bottom_border(p, t.accent, 18)
        p.paragraph_format.space_after = Pt(18)
        if str(meta.get("cover", "")).lower() == "true":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    if str(meta.get("toc", "")).lower() == "true":
        doc.add_paragraph("Contents", style="Heading 2")
        add_field(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u')
        settings = doc.settings.element
        update = OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        settings.append(update)
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    figure = 0
    for b in blocks:
        kind = b["type"]
        if kind == "heading":
            doc.add_paragraph(style=f"Heading {b['level']}")
            add_runs(doc.paragraphs[-1], b["text"])
        elif kind == "para":
            add_runs(doc.add_paragraph(), b["text"])
        elif kind == "list":
            first_numbered = True
            for item in b["items"]:
                base_style = "List Number" if item["ordered"] else "List Bullet"
                style = base_style if item["level"] == 0 else f"{base_style} {item['level'] + 1}"
                p = doc.add_paragraph(style=style)
                p.paragraph_format.space_after = Pt(3)
                add_runs(p, item["text"])
                if item["ordered"] and item["level"] == 0 and first_numbered:
                    restart_numbering(p)
                    first_numbered = False
            doc.paragraphs[-1].paragraph_format.space_after = Pt(10)
        elif kind == "table":
            cols = max(len(b["header"]), *(len(r) for r in b["rows"])) if b["rows"] else len(b["header"])
            table = doc.add_table(rows=1 + len(b["rows"]), cols=cols)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = doc.styles["Table Grid"]
            for r_i, row in enumerate([b["header"], *b["rows"]]):
                for c_i in range(cols):
                    cell = table.cell(r_i, c_i)
                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_after = Pt(0)
                    value = row[c_i] if c_i < len(row) else ""
                    if r_i == 0:
                        for r in inline.parse(value, bold=True):
                            run = p.add_run(r.text)
                            run.bold = True
                            run.font.size = Pt(10)
                            run.font.color.rgb = rgb(t.on_accent)
                        shade(cell._tc.get_or_add_tcPr(), t.accent)
                    else:
                        add_runs(p, value, size=10)
                        if r_i % 2 == 0:
                            shade(cell._tc.get_or_add_tcPr(), t.surface)
            # light borders in the theme's surface colour
            borders = OxmlElement("w:tblBorders")
            for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
                el = OxmlElement(f"w:{edge}")
                el.set(qn("w:val"), "single")
                el.set(qn("w:sz"), "4")
                el.set(qn("w:color"), t.surface.lstrip("#"))
                borders.append(el)
            table._tbl.tblPr.append(borders)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
        elif kind == "image":
            path = base / b["path"]
            if not path.is_file():
                p = doc.add_paragraph()
                add_runs(p, f"[missing image: {b['path']}]", color=t.muted, italic=True)
                continue
            figure += 1
            from .deck import _image_size

            iw, ih = _image_size(path)
            width = min(text_width, Inches(6.5))
            max_h = Inches(5.5)
            if ih and width * ih / iw > max_h:
                width = int(max_h * iw / ih)
            doc.add_picture(str(path), width=width)
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.paragraphs[-1].paragraph_format.keep_with_next = True
            if b.get("caption"):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_runs(p, f"Figure {figure}. {b['caption']}", size=9.5, color=t.muted, italic=True)
        elif kind == "quote":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            ppr = p._p.get_or_add_pPr()
            borders = OxmlElement("w:pBdr")
            left = OxmlElement("w:left")
            left.set(qn("w:val"), "single")
            left.set(qn("w:sz"), "24")
            left.set(qn("w:space"), "12")
            left.set(qn("w:color"), t.accent.lstrip("#"))
            borders.append(left)
            ppr.append(borders)
            add_runs(p, b["text"], size=12, color=t.text, italic=True)
        elif kind == "code":
            p = doc.add_paragraph()
            shade(p._p.get_or_add_pPr(), t.surface)
            run = p.add_run(b["text"])
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
        elif kind == "rule":
            add_bottom_border(doc.add_paragraph(), t.surface, 8)
        elif kind == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # Footer: title left, "page X of Y" right
    footer = sec.footer.paragraphs[0]
    footer.text = ""
    tab_stops = footer.paragraph_format.tab_stops
    tab_stops.add_tab_stop(text_width, alignment=2)  # right
    if title:
        run = footer.add_run(inline.plain(title))
        run.font.size = Pt(8.5)
        run.font.color.rgb = rgb(t.muted)
    footer.add_run("\t")
    for piece in ("Page ", "PAGE", " of ", "NUMPAGES"):
        run = add_field(footer, piece) if piece.isupper() else footer.add_run(piece)
        run.font.size = Pt(8.5)
        run.font.color.rgb = rgb(t.muted)

    doc.core_properties.title = inline.plain(title or "")
    doc.core_properties.author = meta.get("author", "")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))


# ---------------------------------------------------------------- HTML


def build_html(meta: dict, blocks: list[dict], base: Path, theme: Theme) -> str:
    t = theme
    parts = []
    title = meta.get("title")
    if title:
        info = " · ".join(html.escape(x) for x in [meta.get("author", ""), meta.get("date", "")] if x)
        sub = f'<p class="subtitle">{inline.to_html(meta["subtitle"])}</p>' if meta.get("subtitle") else ""
        parts.append(f'<header class="doc-title"><h1 class="title">{inline.to_html(title)}</h1>{sub}<p class="meta">{info}</p></header>')
    figure = 0
    for b in blocks:
        kind = b["type"]
        if kind == "heading":
            parts.append(f"<h{b['level']}>{inline.to_html(b['text'])}</h{b['level']}>")
        elif kind == "para":
            parts.append(f"<p>{inline.to_html(b['text'])}</p>")
        elif kind == "list":
            out, stack = [], []
            for item in b["items"]:
                tag = "ol" if item["ordered"] else "ul"
                while len(stack) > item["level"] + 1:
                    out.append(f"</{stack.pop()}>")
                while len(stack) < item["level"] + 1:
                    stack.append(tag)
                    out.append(f"<{tag}>")
                out.append(f"<li>{inline.to_html(item['text'])}</li>")
            while stack:
                out.append(f"</{stack.pop()}>")
            parts.append("".join(out))
        elif kind == "table":
            head = "".join(f"<th>{inline.to_html(c)}</th>" for c in b["header"])
            rows = "".join("<tr>" + "".join(f"<td>{inline.to_html(c)}</td>" for c in r) + "</tr>" for r in b["rows"])
            parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>")
        elif kind == "image":
            path = base / b["path"]
            if path.is_file():
                figure += 1
                mime = mimetypes.guess_type(path.name)[0] or "image/png"
                data = base64.b64encode(path.read_bytes()).decode()
                cap = f"<figcaption>Figure {figure}. {inline.to_html(b['caption'])}</figcaption>" if b.get("caption") else ""
                parts.append(f'<figure><img src="data:{mime};base64,{data}" alt="{html.escape(b.get("caption", ""))}">{cap}</figure>')
            else:
                parts.append(f'<p class="missing">[missing image: {html.escape(b["path"])}]</p>')
        elif kind == "quote":
            parts.append(f"<blockquote>{inline.to_html(b['text'])}</blockquote>")
        elif kind == "code":
            parts.append(f"<pre><code>{html.escape(b['text'])}</code></pre>")
        elif kind == "rule":
            parts.append("<hr>")
        elif kind == "pagebreak":
            parts.append('<div class="pagebreak"></div>')
    paper = "A4" if meta.get("paper", "letter").lower() == "a4" else "Letter"
    footer_title = html.escape(inline.plain(title or "")).replace('"', "'")
    css = f"""
:root{{--text:{t.text};--muted:{t.muted};--accent:{t.accent};--accent2:{t.accent2};--surface:{t.surface};--on-accent:{t.on_accent}}}
@page{{size:{paper};margin:0.9in 1in;
  @bottom-left{{content:"{footer_title}";font:8.5pt {t.body_stack};color:{t.muted}}}
  @bottom-right{{content:"Page " counter(page) " of " counter(pages);font:8.5pt {t.body_stack};color:{t.muted}}}}}
html{{background:#f3f3f1}}
body{{font:11pt/1.55 {t.body_stack};color:var(--text);max-width:7in;margin:0 auto;padding:.6in .8in;background:#fff;box-shadow:0 1px 12px rgba(0,0,0,.08)}}
@media print{{html{{background:none}}body{{max-width:none;margin:0;padding:0;box-shadow:none}}}}
h1,h2,h3,h4,.title{{font-family:{t.heading_stack};line-height:1.2;break-after:avoid}}
.title{{font-size:28pt;margin:0 0 4pt}}
.subtitle{{font-size:14pt;color:var(--muted);margin:0 0 2pt}}
.meta{{font-size:10pt;color:var(--muted);margin:0}}
.doc-title{{border-bottom:3px solid var(--accent);padding-bottom:10pt;margin-bottom:22pt}}
h1{{font-size:20pt;color:var(--accent);margin:22pt 0 6pt}}
h2{{font-size:15pt;margin:18pt 0 6pt}}
h3{{font-size:12.5pt;color:var(--accent);margin:14pt 0 4pt}}
h4{{font-size:11.5pt;margin:12pt 0 4pt}}
p{{margin:0 0 8pt}}
a{{color:var(--accent)}}
ul,ol{{margin:0 0 10pt;padding-left:1.4em}}
li{{margin-bottom:3pt}}
ul li::marker{{color:var(--accent)}}
table{{border-collapse:collapse;width:100%;margin:6pt 0 14pt;font-size:10pt;break-inside:avoid}}
th{{background:var(--accent);color:var(--on-accent);text-align:left;padding:5pt 7pt}}
td{{padding:5pt 7pt;border-bottom:1px solid var(--surface)}}
tbody tr:nth-child(even) td{{background:var(--surface)}}
figure{{margin:12pt 0 14pt;text-align:center;break-inside:avoid}}
figure img{{max-width:100%;max-height:5.5in}}
figcaption{{font-size:9.5pt;color:var(--muted);font-style:italic;margin-top:6pt}}
blockquote{{margin:10pt 0;padding:2pt 0 2pt 14pt;border-left:4px solid var(--accent);font-style:italic;font-size:12pt}}
pre{{background:var(--surface);padding:10pt;border-radius:6px;font-size:9.5pt;overflow-x:auto;white-space:pre-wrap}}
code{{font-family:Consolas,monospace}}
hr{{border:0;border-top:1px solid var(--surface);margin:14pt 0}}
.pagebreak{{break-after:page}}
.missing{{color:var(--muted);font-style:italic}}
"""
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(inline.plain(title or 'Document'))}</title><style>{css}</style></head><body>{''.join(parts)}</body></html>")


# ---------------------------------------------------------------- entry point


def build(md_path: Path, out_dir: Path | None = None, name: str | None = None, formats: tuple[str, ...] = ("docx", "pdf")) -> dict:
    md_path = Path(md_path).resolve()
    base = md_path.parent
    out_dir = Path(out_dir).resolve() if out_dir else base
    name = name or md_path.stem
    meta, blocks = parse(md_path.read_text(encoding="utf-8"))
    if not meta.get("title"):
        first = next((b for b in blocks if b["type"] == "heading" and b["level"] == 1), None)
        if first:
            meta["title"] = first["text"]
            blocks.remove(first)
    theme = _doc_theme(meta.get("theme"))
    result: dict = {"warnings": check(meta, blocks, base), "theme": theme.name, "words": sum(len(inline.plain(b.get("text", "")).split()) for b in blocks)}
    out_dir.mkdir(parents=True, exist_ok=True)
    if "docx" in formats:
        path = out_dir / f"{name}.docx"
        build_docx(meta, blocks, base, theme, path)
        result["docx"] = str(path)
    if "html" in formats or "pdf" in formats:
        html_path = out_dir / f"{name}.html"
        html_path.write_text(build_html(meta, blocks, base, theme), encoding="utf-8")
        result["html"] = str(html_path)
        if "pdf" in formats:
            from .browser import html_to_pdf

            try:
                result["pdf"] = str(html_to_pdf(html_path, out_dir / f"{name}.pdf"))
            except Exception as exc:
                result["warnings"].append(f"PDF not made: {exc}")
            if "html" not in formats:
                html_path.unlink(missing_ok=True)
                result.pop("html")
    return result
