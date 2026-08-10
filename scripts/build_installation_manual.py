#!/usr/bin/env python3
"""Build the assessor-facing installation manual PDF from its Markdown source."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "INSTALLATION_MANUAL.md"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "SmartFINN_Installation_Manual.pdf"

INK = colors.HexColor("#20364D")
ACCENT = colors.HexColor("#35658A")
LIGHT_BLUE = colors.HexColor("#EAF1F6")
GRID = colors.HexColor("#B9CBD8")
CODE_BG = colors.HexColor("#F4F6F8")


def inline_markup(value: str) -> str:
    """Convert the small inline Markdown subset used by the manual."""

    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", value)
    rendered: list[str] = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            rendered.append(f'<font name="Courier">{html.escape(part[1:-1])}</font>')
        elif part.startswith("**") and part.endswith("**"):
            rendered.append(f"<b>{html.escape(part[2:-2])}</b>")
        else:
            rendered.append(html.escape(part))
    return "".join(rendered)


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ManualTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            textColor=INK,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=INK,
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualSubheading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=ACCENT,
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13.3,
            textColor=INK,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualList",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.8,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualCode",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#17212B"),
            wordWrap="CJK",
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualTableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.7,
            leading=9.5,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ManualTableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.3,
            textColor=INK,
        )
    )
    return styles


def code_table(lines: list[str], styles, width: float) -> Table:
    flowables = []
    for index, line in enumerate(lines or [""]):
        preserved = html.escape(line).replace(" ", "&nbsp;")
        flowables.append(Paragraph(preserved or "&nbsp;", styles["ManualCode"]))
        if index < len(lines) - 1:
            flowables.append(Spacer(1, 1.5))
    table = Table([[flowables]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def markdown_table(rows: list[list[str]], styles, width: float) -> Table:
    header = rows[0]
    columns = len(header)
    if columns == 3 and header[0] == "Variable":
        widths = [0.38 * width, 0.18 * width, 0.44 * width]
    elif columns == 3:
        widths = [0.28 * width, 0.23 * width, 0.49 * width]
    else:
        widths = [width / columns] * columns

    data = []
    for row_index, row in enumerate(rows):
        style = styles["ManualTableHeader"] if row_index == 0 else styles["ManualTableCell"]
        padded = row + [""] * (columns - len(row))
        data.append([Paragraph(inline_markup(cell), style) for cell in padded[:columns]])

    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
                ("GRID", (0, 0), (-1, -1), 0.45, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def parse_markdown(source: str, styles, width: float):
    lines = source.splitlines()
    story = []
    paragraph: list[str] = []
    code_lines: list[str] | None = None
    table_rows: list[list[str]] = []
    list_items: list[str] = []
    list_kind: str | None = None

    def flush_paragraph():
        if paragraph:
            story.append(Paragraph(inline_markup(" ".join(paragraph)), styles["ManualBody"]))
            paragraph.clear()

    def flush_table():
        if table_rows:
            story.append(markdown_table(table_rows.copy(), styles, width))
            story.append(Spacer(1, 5))
            table_rows.clear()

    def flush_list():
        nonlocal list_kind
        if list_items:
            items = [
                ListItem(Paragraph(inline_markup(item), styles["ManualList"]), leftIndent=12)
                for item in list_items
            ]
            list_options = {
                "bulletType": "1" if list_kind == "number" else "bullet",
                "leftIndent": 18,
                "bulletFontName": "Helvetica",
                "bulletFontSize": 8,
                "spaceAfter": 5,
            }
            if list_kind == "number":
                list_options["start"] = "1"
            story.append(ListFlowable(items, **list_options))
            list_items.clear()
        list_kind = None

    for line in lines:
        stripped = line.strip()
        if code_lines is not None:
            if stripped.startswith("```"):
                story.append(code_table(code_lines, styles, width))
                story.append(Spacer(1, 5))
                code_lines = None
            else:
                code_lines.append(line)
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            flush_table()
            flush_list()
            code_lines = []
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            flush_list()
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            table_rows.append(cells)
            continue
        flush_table()

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            style = {
                1: styles["ManualTitle"],
                2: styles["ManualHeading"],
                3: styles["ManualSubheading"],
            }[level]
            story.append(Paragraph(inline_markup(heading.group(2)), style))
            continue

        numbered = re.match(r"^\d+\.\s+(.+)$", stripped)
        bulleted = re.match(r"^-\s+(.+)$", stripped)
        if numbered or bulleted:
            flush_paragraph()
            kind = "number" if numbered else "bullet"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_items.append((numbered or bulleted).group(1))
            continue
        flush_list()

        if not stripped:
            flush_paragraph()
        else:
            paragraph.append(stripped.removesuffix("  "))

    flush_paragraph()
    flush_table()
    flush_list()
    if code_lines is not None:
        story.append(code_table(code_lines, styles, width))
    return story


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, height - 18 * mm, width - doc.rightMargin, height - 18 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(ACCENT)
    canvas.drawString(doc.leftMargin, height - 14 * mm, "SmartFINN")
    right = "Installation Manual"
    canvas.drawString(width - doc.rightMargin - stringWidth(right, "Helvetica", 8), height - 14 * mm, right)
    canvas.setFillColor(colors.HexColor("#5F7182"))
    page = f"Page {doc.page}"
    canvas.drawString((width - stringWidth(page, "Helvetica", 8)) / 2, 11 * mm, page)
    canvas.restoreState()


def build(source_path: Path, output_path: Path) -> None:
    styles = build_styles()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
        title="SmartFINN Installation Manual",
        author="SmartFINN Project Team",
        subject="COMP9900 Software Quality Submission",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="manual-body",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(
        [PageTemplate(id="manual-pages", frames=[frame], onPage=header_footer)]
    )
    story = parse_markdown(source_path.read_text(encoding="utf-8"), styles, doc.width)
    doc.build(story)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
