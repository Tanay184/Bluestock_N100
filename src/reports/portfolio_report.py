"""Portfolio summary PDF: one page per company, alphabetical by ticker (Day 35)."""

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.reports.common import (
    CELL,
    CELL_B,
    GREY,
    HEAD,
    LIGHT,
    NAVY,
    SMALL,
    Data,
    num,
    style,
    usable_width,
)

MARGIN = 2.0 * cm
UW = usable_width(A4[0], MARGIN)
FLAT_PCT = 2.0
KPIS = [  # (column, label, decimals, lower_is_better)
    ("return_on_equity_pct", "ROE %", 1, False),
    ("roce_pct", "ROCE %", 1, False),
    ("net_profit_margin_pct", "Net profit margin %", 1, False),
    ("debt_to_equity", "Debt / equity", 2, True),
    ("revenue_cagr_5yr", "Revenue CAGR 5yr %", 1, False),
    ("free_cash_flow_cr", "Free cash flow (Rs Cr)", 0, False),
]
ARROWS = {
    "up": ("↑", "#1A7F37"),
    "down": ("↓", "#C0392B"),
    "flat": ("→", "#667085"),
    "na": ("–", "#667085"),
}


def trend(latest, prev, lower_is_better: bool = False) -> str:
    """'up' if the metric improved, 'down' if it worsened, 'flat' within 2%, 'na' if unknown."""
    if pd.isna(latest) or pd.isna(prev):
        return "na"
    change = latest - prev
    base = abs(prev)
    if (change == 0) or (base > 0 and abs(change) / base * 100 <= FLAT_PCT):
        return "flat"
    improved = change < 0 if lower_is_better else change > 0
    return "up" if improved else "down"


def footer(canvas, doc) -> None:
    """Draw the page footer."""
    canvas.saveState()
    canvas.setFont("DV", 7)
    canvas.setFillColor(GREY)
    canvas.drawString(
        MARGIN,
        1.0 * cm,
        "Nifty 100 Financial Intelligence Platform | Portfolio summary | Market data is simulated",
    )
    canvas.drawRightString(A4[0] - MARGIN, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


def company_page(d: Data, t: str) -> list:
    """Flowables for one company page."""
    fr = d.ratios(t)
    last = fr.iloc[-1]
    prev = fr.iloc[-2] if len(fr) > 1 else None
    head = Table(
        [
            [
                Paragraph(
                    f"<b>{escape(d.name(t))}</b>", style("pn", 16, color=colors.white)
                )
            ],
            [
                Paragraph(
                    f"{escape(t)}  |  {escape(d.sector(t))}  |  Latest financial year: {last['year']}",
                    style("ps", 9, color=colors.HexColor("#D6E4F5")),
                )
            ],
        ],
        colWidths=[UW],
    )
    head.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
            ]
        )
    )
    rows = [[Paragraph(h, HEAD) for h in ("KPI", "Latest", "Previous year", "Trend")]]
    for col, label, nd, lower in KPIS:
        key = trend(last[col], prev[col] if prev is not None else float("nan"), lower)
        glyph, colour = ARROWS[key]
        rows.append(
            [
                Paragraph(label, CELL),
                Paragraph(f"<b>{num(last[col], nd)}</b>", CELL),
                Paragraph(num(prev[col], nd) if prev is not None else "N/A", CELL),
                Paragraph(
                    f'<font color="{colour}" size="13"><b>{glyph}</b></font>',
                    style("ar", 9, leading=15),
                ),
            ]
        )
    kpi = Table(rows, colWidths=[UW * 0.42, UW * 0.2, UW * 0.2, UW * 0.18])
    kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    extra = Paragraph(
        f"Composite quality score: <b>{num(last['composite_quality_score'])}</b> &nbsp;|&nbsp; "
        f"Capital allocation: <b>{escape(d.pattern.get(t, 'No Data'))}</b>",
        CELL,
    )
    legend = Paragraph(
        "Trend arrow: ↑ improved, ↓ declined, → flat (within 2%) versus the previous year. "
        "For debt / equity, lower is better.",
        SMALL,
    )
    return [
        head,
        Spacer(1, 14),
        kpi,
        Spacer(1, 12),
        extra,
        Spacer(1, 8),
        legend,
        Paragraph("", CELL_B),
    ]


def build_portfolio(d: Data, path: Path) -> int:
    """Write the portfolio PDF (one page per company); returns the page count."""
    story: list = []
    for i, t in enumerate(d.tickers()):
        if i:
            story.append(PageBreak())
        story += company_page(d, t)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title="Nifty 100 portfolio summary",
        author="Nifty 100 Platform",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return doc.page
