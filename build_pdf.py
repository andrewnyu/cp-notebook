#!/usr/bin/env python3
"""Render cp_notebook.md to cp_notebook.pdf with reportlab."""
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle,
)

SRC = Path(__file__).parent / "cp_notebook.md"
DST = Path(__file__).parent / "cp_notebook.pdf"

CODE_BG = colors.Color(0.95, 0.95, 0.95)
RULE_COLOR = colors.Color(0.85, 0.85, 0.85)

title_style = ParagraphStyle(
    "title", fontName="Helvetica-Bold", fontSize=20, leading=24,
    spaceAfter=4,
)
subtitle_style = ParagraphStyle(
    "subtitle", fontName="Helvetica-Oblique", fontSize=10.5, leading=14,
    textColor=colors.Color(0.35, 0.35, 0.35), spaceAfter=16,
)
h2_style = ParagraphStyle(
    "h2", fontName="Helvetica-Bold", fontSize=13.5, leading=16,
    spaceBefore=16, spaceAfter=6, textColor=colors.Color(0.1, 0.1, 0.1),
    borderWidth=0, borderPadding=0,
)
body_style = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=9.7, leading=13.5,
    spaceAfter=6,
)
code_style = ParagraphStyle(
    "code", fontName="Courier", fontSize=8.3, leading=10.6,
    backColor=CODE_BG, borderPadding=(6, 8, 6, 8),
    borderColor=RULE_COLOR, borderWidth=0.5,
    spaceBefore=2, spaceAfter=10,
)
table_cell_style = ParagraphStyle(
    "cell", fontName="Helvetica", fontSize=9, leading=12,
)
table_header_style = ParagraphStyle(
    "cellhead", fontName="Helvetica-Bold", fontSize=9, leading=12,
    textColor=colors.white,
)


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


def build_story(md_text: str):
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
            code_text = "\n".join(code_lines)
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
            tbl = Table(data, hAlign="LEFT", colWidths=[2.6 * inch, 3.6 * inch])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.22)),
                ("BACKGROUND", (0, 1), (-1, -1), colors.Color(0.97, 0.97, 0.97)),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.Color(0.96, 0.96, 0.96)]),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 10))
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
    doc = SimpleDocTemplate(
        str(DST), pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.65 * inch, bottomMargin=0.65 * inch,
        title="CP Notebook: Tricky Implementation Patterns",
    )
    story = build_story(md_text)
    doc.build(story)
    print(f"wrote {DST}")


if __name__ == "__main__":
    sys.exit(main())
