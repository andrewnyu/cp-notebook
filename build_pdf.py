#!/usr/bin/env python3
"""Render cp_notebook.md to cp_notebook.pdf with reportlab.

Landscape A4, two columns per page, mirrored margins for double-sided
printing/binding -- the standard layout for a printed CP team reference.
"""
import re
import sys
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, NextPageTemplate, PageTemplate, Paragraph,
    Preformatted, Spacer, Table, TableStyle,
)

SRC = Path(__file__).parent / "cp_notebook.md"
DST = Path(__file__).parent / "cp_notebook.pdf"

CODE_BG = colors.Color(0.95, 0.95, 0.95)
RULE_COLOR = colors.Color(0.85, 0.85, 0.85)

CODE_FONT_SIZE = 7.2
CODE_CHAR_WIDTH = 0.6 * CODE_FONT_SIZE   # exact for Courier: 600/1000 em

title_style = ParagraphStyle(
    "title", fontName="Helvetica-Bold", fontSize=15, leading=18,
    spaceAfter=3,
)
subtitle_style = ParagraphStyle(
    "subtitle", fontName="Helvetica-Oblique", fontSize=8, leading=11,
    textColor=colors.Color(0.35, 0.35, 0.35), spaceAfter=10,
)
h2_style = ParagraphStyle(
    "h2", fontName="Helvetica-Bold", fontSize=10.5, leading=13,
    spaceBefore=10, spaceAfter=4, textColor=colors.Color(0.1, 0.1, 0.1),
    borderWidth=0, borderPadding=0,
)
body_style = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=7.6, leading=10,
    spaceAfter=4,
)
code_style = ParagraphStyle(
    "code", fontName="Courier", fontSize=CODE_FONT_SIZE, leading=9.2,
    backColor=CODE_BG, borderPadding=(4, 6, 4, 6),
    borderColor=RULE_COLOR, borderWidth=0.5,
    spaceBefore=2, spaceAfter=7,
)
table_cell_style = ParagraphStyle(
    "cell", fontName="Helvetica", fontSize=7.3, leading=9.5,
)
table_header_style = ParagraphStyle(
    "cellhead", fontName="Helvetica-Bold", fontSize=7.3, leading=9.5,
    textColor=colors.white,
)


def wrap_code_block(code_text: str, max_chars: int) -> str:
    """Hard-wrap any code line too wide for a column.

    Every overlong line in this notebook is `code  # trailing comment` --
    split the comment onto its own indented continuation line(s) rather
    than truncating or overflowing into the next column.
    """
    out_lines = []
    for line in code_text.split("\n"):
        if len(line) <= max_chars:
            out_lines.append(line)
            continue

        indent = len(line) - len(line.lstrip(" "))
        cont_indent = " " * (indent + 4)
        m = re.search(r"( {2,})(#.*)$", line)

        if m and len(line[: m.start()].rstrip()) <= max_chars:
            code_part = line[: m.start()].rstrip()
            comment_text = m.group(2).lstrip("#").strip()
            avail = max(20, max_chars - len(cont_indent) - 2)
            out_lines.append(code_part)
            for wrapped in textwrap.wrap(comment_text, width=avail) or [""]:
                out_lines.append(f"{cont_indent}# {wrapped}")
        else:
            avail = max(20, max_chars - len(cont_indent))
            wrapped_lines = textwrap.wrap(line.strip(), width=avail) or [line.strip()]
            out_lines.append((" " * indent) + wrapped_lines[0])
            for wrapped in wrapped_lines[1:]:
                out_lines.append(cont_indent + wrapped)

    return "\n".join(out_lines)


def inline_markup(text: str) -> str:
    text = (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    # inline code spans `...`
    text = re.sub(
        r"`([^`]+)`",
        lambda m: f'<font name="Courier" backColor="#f2f2f2">{m.group(1)}</font>',
        text,
    )
    # bold **...**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def parse_table(lines):
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    # drop the "---|---" separator row
    rows = [r for r in rows if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    return rows


def build_story(md_text: str, code_max_chars: int, table_col_widths):
    story = []
    lines = md_text.split("\n")
    i = 0
    n = len(lines)

    # title (# ...) then subtitle line
    if lines[0].startswith("# "):
        story.append(Paragraph(inline_markup(lines[0][2:].strip()), title_style))
        i = 1
        if i < n and lines[i].strip() and not lines[i].startswith("#"):
            story.append(Paragraph(inline_markup(lines[i].strip()), subtitle_style))
            i += 1

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:].strip()), h2_style))
            i += 1
            continue

        if line.startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code_text = wrap_code_block("\n".join(code_lines), code_max_chars)
            story.append(Preformatted(code_text, code_style))
            continue

        if line.strip().startswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = parse_table(table_lines)
            data = []
            for r_idx, row in enumerate(rows):
                style = table_header_style if r_idx == 0 else table_cell_style
                data.append([Paragraph(inline_markup(c), style) for c in row])
            tbl = Table(data, hAlign="LEFT", colWidths=table_col_widths)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.22)),
                ("BACKGROUND", (0, 1), (-1, -1), colors.Color(0.97, 0.97, 0.97)),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.Color(0.96, 0.96, 0.96)]),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 6))
            continue

        # plain paragraph: gather until blank line / next block
        para_lines = []
        while i < n and lines[i].strip() and not lines[i].startswith(("#", "```", "|")):
            para_lines.append(lines[i])
            i += 1
        para_text = " ".join(l.strip() for l in para_lines)
        story.append(Paragraph(inline_markup(para_text), body_style))

    return story


def main():
    md_text = SRC.read_text()

    # Landscape A4, two columns, double-sided: mirrored PAGE margins put the
    # wider "inner" margin on the binding edge (left on odd/recto pages,
    # right on even/verso pages); the gutter between the two columns stays
    # the same on every page.
    pagesize = landscape(A4)
    page_width, page_height = pagesize
    inner_margin = 0.6 * inch   # binding-side margin
    outer_margin = 0.35 * inch
    top_margin = 0.45 * inch
    bottom_margin = 0.45 * inch
    column_gap = 0.25 * inch

    frame_height = page_height - top_margin - bottom_margin
    column_width = (page_width - inner_margin - outer_margin - column_gap) / 2

    def two_columns(left_x):
        return [
            Frame(left_x, bottom_margin, column_width, frame_height, id="c1"),
            Frame(left_x + column_width + column_gap, bottom_margin,
                  column_width, frame_height, id="c2"),
        ]

    doc = BaseDocTemplate(
        str(DST), pagesize=pagesize,
        title="CP Notebook: Tricky Implementation Patterns",
    )
    doc.addPageTemplates([
        PageTemplate(id="Odd", frames=two_columns(inner_margin)),
        PageTemplate(id="Even", frames=two_columns(outer_margin)),
    ])

    # column padding eats into what a Preformatted line can use; keep this
    # in sync with code_style's horizontal borderPadding (6 + 6 = 12pt)
    code_max_chars = int((column_width - 12) / CODE_CHAR_WIDTH)
    table_col_widths = [column_width * 0.34, column_width * 0.62]

    # page 1 uses "Odd" (the default, first-listed template); this cycle
    # then alternates every page after that: 2=Even, 3=Odd, 4=Even, ...
    story = [NextPageTemplate(["Even", "Odd"])]
    story += build_story(md_text, code_max_chars, table_col_widths)
    doc.build(story)

    _set_duplex_hint(DST)
    print(f"wrote {DST}, code_max_chars={code_max_chars}")


def _set_duplex_hint(path: Path):
    """Embed a print-dialog hint for double-sided printing.

    Binding is along the short edge of the landscape sheet (the left/right
    vertical edge), so DuplexFlipShortEdge is the correct flip mode. Not
    every viewer or print dialog honors this, but it's a safe no-op default.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DictionaryObject, NameObject

    reader = PdfReader(str(path))
    writer = PdfWriter()
    writer.append(reader)
    prefs = DictionaryObject()
    prefs[NameObject("/Duplex")] = NameObject("/DuplexFlipShortEdge")
    writer._root_object[NameObject("/ViewerPreferences")] = writer._add_object(prefs)
    with open(path, "wb") as f:
        writer.write(f)


if __name__ == "__main__":
    sys.exit(main())
