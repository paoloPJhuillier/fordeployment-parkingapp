"""Render docs/USER_GUIDE.md into a formatted PDF (docs/USER_GUIDE.pdf).

A small, self-contained Markdown-subset renderer built on reportlab. It handles
the constructs used in USER_GUIDE.md: headings (#..####), paragraphs, unordered
lists (-), ordered lists (1.), pipe tables, horizontal rules (---), and inline
**bold** / `code` spans.

Usage:
    python docs/generate_user_guide_pdf.py
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

HERE = Path(__file__).resolve().parent
SRC = HERE / "USER_GUIDE.md"
OUT = HERE / "USER_GUIDE.pdf"

BRAND = colors.HexColor("#0B5FA5")
BRAND_LIGHT = colors.HexColor("#E8F1FA")
GREY = colors.HexColor("#444444")


def _styles():
    ss = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=22, spaceBefore=6,
                             spaceAfter=10, textColor=BRAND, leading=26),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=16, spaceBefore=14,
                             spaceAfter=6, textColor=BRAND, leading=20),
        "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontSize=13, spaceBefore=10,
                             spaceAfter=4, textColor=GREY, leading=17),
        "h4": ParagraphStyle("h4", parent=ss["Heading4"], fontSize=11.5, spaceBefore=8,
                             spaceAfter=3, textColor=GREY, leading=15),
        "body": ParagraphStyle("body", parent=ss["BodyText"], fontSize=10.5, leading=15,
                               spaceAfter=6, alignment=TA_LEFT),
        "li": ParagraphStyle("li", parent=ss["BodyText"], fontSize=10.5, leading=15,
                             leftIndent=14, spaceAfter=2, bulletIndent=2),
        "cell": ParagraphStyle("cell", parent=ss["BodyText"], fontSize=9.5, leading=13),
        "cellh": ParagraphStyle("cellh", parent=ss["BodyText"], fontSize=9.5, leading=13,
                                textColor=colors.white, fontName="Helvetica-Bold"),
    }
    return styles


def _inline(text: str) -> str:
    """Convert a subset of inline markdown to reportlab mini-HTML."""
    # Escape XML special chars first.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold: **x**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Inline code: `x`
    text = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', text)
    return text


def _split_table_row(line: str):
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def build():
    styles = _styles()
    md = SRC.read_text(encoding="utf-8").splitlines()

    flow = []
    i = 0
    n = len(md)

    def flush_table(rows):
        if not rows:
            return
        header, *body = rows
        data = [[Paragraph(_inline(c), styles["cellh"]) for c in header]]
        for r in body:
            data.append([Paragraph(_inline(c), styles["cell"]) for c in r])
        # Column widths: distribute across usable width (~170mm).
        ncols = len(header)
        usable = 170 * mm
        col_w = [usable / ncols] * ncols
        tbl = Table(data, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBBBBB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flow.append(Spacer(1, 4))
        flow.append(tbl)
        flow.append(Spacer(1, 8))

    while i < n:
        line = md[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped == "---":
            flow.append(Spacer(1, 4))
            flow.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CCCCCC")))
            flow.append(Spacer(1, 6))
            i += 1
            continue

        # Table (a line with pipes, followed by a separator row of ---)
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|?[\s:|-]+\|", md[i + 1].strip()):
            rows = [_split_table_row(stripped)]
            i += 2  # skip header + separator
            while i < n and md[i].strip().startswith("|"):
                rows.append(_split_table_row(md[i].strip()))
                i += 1
            flush_table(rows)
            continue

        # Headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            flow.append(Paragraph(_inline(m.group(2)), styles[f"h{level}"]))
            i += 1
            continue

        # Ordered list item
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            flow.append(Paragraph(_inline(m.group(2)), styles["li"],
                                  bulletText=f"{m.group(1)}."))
            i += 1
            continue

        # Unordered list item
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            flow.append(Paragraph(_inline(m.group(1)), styles["li"], bulletText="\u2022"))
            i += 1
            continue

        # Plain paragraph
        flow.append(Paragraph(_inline(stripped), styles["body"]))
        i += 1

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(20 * mm, 12 * mm,
                          "Cebuana Lhuillier Parking App — User Guide")
        canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title="Cebuana Lhuillier Parking App — User Guide",
        author="Parking App",
    )
    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
