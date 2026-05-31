# -*- coding: utf-8 -*-
"""Professional business report generator (PDF, Markdown, HTML)."""

import io
import os
from datetime import datetime
from typing import Optional
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register CJK fonts (macOS system fonts)
_CJK_FONT = "HeitiCJK"
_BOLD_FONT = "HeitiBoldCJK"
pdfmetrics.registerFont(TTFont(_CJK_FONT, "/System/Library/Fonts/STHeiti Medium.ttc", subfontIndex=0))
pdfmetrics.registerFont(TTFont(_BOLD_FONT, "/System/Library/Fonts/STHeiti Medium.ttc", subfontIndex=0))

# ── Color palette ─────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1B3A5C")
MID_BLUE    = colors.HexColor("#2E6DA4")
LIGHT_BLUE  = colors.HexColor("#D6E8F7")
ACCENT_GOLD = colors.HexColor("#C9A84C")
ACCENT_RED  = colors.HexColor("#C0392B")
ACCENT_GREEN= colors.HexColor("#27AE60")
LIGHT_GRAY  = colors.HexColor("#F5F7FA")
MID_GRAY    = colors.HexColor("#7F8C8D")
WHITE       = colors.white


def _p(cell_idx: int) -> str:
    """Alignment for cell index: first col = left, rest = right."""
    return "RIGHT" if cell_idx > 0 else "LEFT"


def _money_table(data: list, cols: list, title: str) -> Table:
    """Build a styled money table with proper Chinese font."""
    header = [
        Paragraph(f"<b>{c}</b>", ParagraphStyle(
            "th", fontName=_BOLD_FONT, fontSize=9,
            textColor=WHITE))
        for c in cols
    ]
    rows = [header]
    for row in data:
        cells = [
            Paragraph(str(c) if c is not None else "", ParagraphStyle(
                "td", fontName=_CJK_FONT, fontSize=8.5))
            for c in row
        ]
        rows.append(cells)

    col_count = len(cols)
    col_widths = [3.5*cm] + [2.0*cm] * (col_count - 1)

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0),  MID_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1,  0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),  [WHITE, LIGHT_GRAY]),
        ("ALIGN",        (0, 0), (-1, -1),  "LEFT"),
        ("ALIGN",        (1, 0), (-1, -1),  "RIGHT"),
        ("FONTNAME",     (0, 0), (-1,  0),  _BOLD_FONT),
        ("FONTSIZE",     (0, 0), (-1, -1),  8.5),
        ("TOPPADDING",   (0, 0), (-1, -1),  5),
        ("BOTTOMPADDING",(0, 0), (-1, -1),  5),
        ("LEFTPADDING",  (0, 0), (-1, -1),  8),
        ("RIGHTPADDING", (0, 0), (-1, -1),  8),
        ("GRID",         (0, 0), (-1, -1),  0.5, colors.HexColor("#BDC3C7")),
    ]))
    return t


def _kpi_table(kpis: list) -> Table:
    """Build KPI summary cards as a table."""
    cells = []
    for label, value, sub in kpis:
        inner = [
            Paragraph(str(value), ParagraphStyle(
                "kv", fontName=_BOLD_FONT, fontSize=16,
                textColor=MID_BLUE, alignment=TA_CENTER)),
            Paragraph(str(label), ParagraphStyle(
                "kl", fontName=_CJK_FONT, fontSize=9,
                textColor=MID_GRAY, alignment=TA_CENTER)),
        ]
        if sub:
            inner.append(Paragraph(str(sub), ParagraphStyle(
                "ks", fontName=_CJK_FONT, fontSize=8,
                textColor=ACCENT_GREEN if str(sub).startswith("+") else ACCENT_RED,
                alignment=TA_CENTER)))
        cells.append(inner)
    n = min(len(cells), 4)
    t = Table([cells[:n]], colWidths=[5.5*cm]*n)
    t.setStyle(TableStyle([
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 12),
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_BLUE),
        ("BOX",          (0, 0), (-1, -1), 1, MID_BLUE),
        ("INNERGRID",    (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
    ]))
    return t


def _style(name: str, **kwargs) -> ParagraphStyle:
    """Create a named ParagraphStyle with CJK font."""
    base = kwargs.pop("base", "Normal")
    s = ParagraphStyle(name, **kwargs)
    return s


def build_pdf(
    title: str,
    kpis: list,
    commentary: str,
    tables: list,
    footer_note: str = "",
    period: str = "",
) -> bytes:
    """Build a professional A4 PDF report with CJK font support."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.8*cm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportTitle",
        fontName=_BOLD_FONT, fontSize=20,
        textColor=DARK_BLUE, spaceAfter=4))
    styles.add(ParagraphStyle("SectionHeader",
        fontName=_BOLD_FONT, fontSize=13,
        textColor=DARK_BLUE, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle("Body",
        fontName=_CJK_FONT, fontSize=9.5,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=6, leading=14))
    styles.add(ParagraphStyle("Commentary",
        fontName=_CJK_FONT, fontSize=9.5,
        textColor=colors.HexColor("#34495E"),
        leading=16, spaceAfter=8,
        leftIndent=10, rightIndent=10,
        borderColor=LIGHT_BLUE, borderWidth=1,
        borderPadding=8, backColor=LIGHT_GRAY))
    styles.add(ParagraphStyle("Footer",
        fontName=_CJK_FONT, fontSize=8,
        textColor=MID_GRAY, alignment=TA_CENTER))
    styles.add(ParagraphStyle("Period",
        fontName=_CJK_FONT, fontSize=10,
        textColor=MID_GRAY))

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph(title, styles["ReportTitle"]))
    if period:
        story.append(Paragraph(period, styles["Period"]))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_GOLD, spaceAfter=10))

    # ── KPIs ───────────────────────────────────────────────────────────────
    story.append(Paragraph("核心指标", styles["SectionHeader"]))
    if kpis:
        story.append(_kpi_table(kpis))
    story.append(Spacer(1, 8))

    # ── Commentary ──────────────────────────────────────────────────────────
    if commentary:
        story.append(Paragraph("分析批语", styles["SectionHeader"]))
        story.append(Paragraph(commentary, styles["Commentary"]))
        story.append(Spacer(1, 6))

    # ── Tables ─────────────────────────────────────────────────────────────
    for table_title, table_data, table_cols in tables:
        story.append(Paragraph(table_title, styles["SectionHeader"]))
        story.append(_money_table(table_data, table_cols, table_title))
        story.append(Spacer(1, 8))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 4))
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(
        f"{footer_note}  |  报告生成时间: {generated}",
        styles["Footer"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def build_markdown(
    title: str,
    kpis: list,
    commentary: str,
    tables: list,
    footer_note: str = "",
    period: str = "",
) -> str:
    """Build a professional Markdown report."""
    lines = []
    lines.append(f"# {title}\n")
    if period:
        lines.append(f"**分析周期:** {period}\n")

    lines.append("\n## 核心指标\n")
    if kpis:
        header = "| 指标 | 数值 | 变动 |"
        sep    = "|------|------|------|"
        lines.append(header)
        lines.append(sep)
        for label, value, sub in kpis:
            lines.append(f"| {label} | **{value}** | {sub or '—'} |")

    if commentary:
        lines.append(f"\n## 分析批语\n")
        lines.append(f"> {commentary}\n")

    for table_title, table_data, table_cols in tables:
        lines.append(f"\n## {table_title}\n")
        lines.append("| " + " | ".join(table_cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(table_cols)) + " |")
        for row in table_data:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")

    lines.append(f"\n---\n*{footer_note}  |  报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    return "\n".join(lines)


def build_html(
    title: str,
    kpis: list,
    commentary: str,
    tables: list,
    footer_note: str = "",
    period: str = "",
) -> str:
    """Build a self-contained HTML report."""
    kpi_rows = ""
    for label, value, sub in kpis:
        color = ACCENT_GREEN if str(sub).startswith("+") else (ACCENT_RED if str(sub).startswith("-") else MID_BLUE)
        sub_html = f"<div class='kpi-sub'><span class='pos'>{sub}</span></div>" if sub else ""
        kpi_rows += f"""
        <div class="kpi-card">
          <div class="kpi-value" style="color:{color}">{value}</div>
          <div class="kpi-label">{label}</div>
          {sub_html}
        </div>"""

    table_rows = ""
    for table_title, table_data, table_cols in tables:
        header_cells = ""
        for ci, c in enumerate(table_cols):
            align = "left" if ci == 0 else "right"
            header_cells += f"<th style='text-align:{align};'>{c}</th>"
        body = ""
        for i, row in enumerate(table_data):
            cells = []
            for ci, c in enumerate(row):
                align = "left" if ci == 0 else "right"
                cells.append(f"<td style='text-align:{align};'>{c}</td>")
            body += f"<tr class='{'even' if i % 2 == 0 else 'odd'}'>" + "".join(cells) + "</tr>"
        table_rows += f"""
        <div class="section">
          <h2>{table_title}</h2>
          <div class="table-wrap">
          <table><thead><tr>{header_cells}</tr></thead><tbody>{body}</tbody></table>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
          color: #2C3E50; background: #F5F7FA; padding: 24px; }}
  .container {{ max-width: 80%; margin: 0 auto; background: white;
               border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,.08); overflow: hidden; }}
  .header {{ background: #1B3A5C; color: white; padding: 28px 32px; }}
  .header h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .header .period {{ font-size: 13px; color: #A9CCE3; }}
  .gold-bar {{ height: 4px; background: #C9A84C; }}
  .kpi-grid {{ display: flex; flex-wrap: wrap; gap: 12px; padding: 20px 28px;
               background: #D6E8F7; }}
  .kpi-card {{ flex: 1; min-width: 140px; background: white; border-radius: 6px;
               padding: 16px 12px; text-align: center; border: 1px solid #BDC3C7; }}
  .kpi-value {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; word-break: break-all; }}
  .kpi-label {{ font-size: 11px; color: #7F8C8D; margin-bottom: 4px; }}
  .kpi-sub {{ font-size: 11px; color: #27AE60; min-height: 14px; }}
  .kpi-sub:empty {{ display: none; }}
  .pos {{ background:#E8F8F0; color:#27AE60; padding:1px 5px; border-radius:3px; }}
  .neg {{ background:#FDEDEC; color:#C0392B; padding:1px 5px; border-radius:3px; }}
  .commentary {{ margin: 20px 28px; padding: 16px; background: #F5F7FA;
                 border-left: 4px solid #2E6DA4; border-radius: 4px;
                 font-size: 14px; line-height: 1.8; color: #34495E; }}
  .commentary h2 {{ font-size: 14px; color: #1B3A5C; margin-bottom: 10px; }}
  .section {{ padding: 20px 28px; border-top: 1px solid #ECF0F1; }}
  .section h2 {{ font-size: 14px; color: #1B3A5C; margin-bottom: 12px; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 600px; }}
  th {{ background: #2E6DA4; color: white; padding: 8px 12px; white-space: nowrap; }}
  th[style*="text-align:left"] {{ text-align: left; }}
  th[style*="text-align:right"] {{ text-align: right; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #ECF0F1; white-space: nowrap; }}
  tr.even {{ background: white; }}
  tr.odd  {{ background: #F5F7FA; }}
  tr:hover td {{ background: #D6E8F7; }}
  .footer {{ padding: 14px 28px; background: #ECF0F1; font-size: 11px;
              color: #7F8C8D; text-align: center; }}
  @media print {{
    body {{ background: white; padding: 0; }}
    .container {{ box-shadow: none; }}
    .section {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="period">{period}</div>
  </div>
  <div class="gold-bar"></div>

  <div class="kpi-grid">{kpi_rows}</div>

  <div class="commentary">
    <h2>分析批语</h2>
    {commentary}
  </div>

  {table_rows}

  <div class="footer">{footer_note}  |  报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
</body>
</html>"""
