"""Sector report PDFs: summary page with median KPIs plus a company table (Day 34)."""

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
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
    HEAD,
    LIGHT,
    NAVY,
    SMALL,
    Data,
    num,
    style,
    usable_width,
)

PAGE = landscape(A4)
MARGIN = 1.5 * cm
UW = usable_width(PAGE[0], MARGIN)
KPIS = [  # (column, header, decimals, suffix)
    ("return_on_equity_pct", "ROE %", 1, ""),
    ("roce_pct", "ROCE %", 1, ""),
    ("net_profit_margin_pct", "Net margin %", 1, ""),
    ("operating_profit_margin_pct", "OPM %", 1, ""),
    ("debt_to_equity", "D/E", 2, ""),
    ("free_cash_flow_cr", "FCF (Rs Cr)", 0, ""),
    ("revenue_cagr_5yr", "Rev CAGR 5yr %", 1, ""),
    ("pat_cagr_5yr", "PAT CAGR 5yr %", 1, ""),
]


def file_name(sector: str) -> str:
    """'Consumer Discretionary' -> 'Consumer_Discretionary_report.pdf'."""
    return re.sub(r"[^A-Za-z0-9]+", "_", sector).strip("_") + "_report.pdf"


def footer(canvas, doc) -> None:
    """Draw the page footer."""
    canvas.saveState()
    canvas.setFont("DV", 7)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(
        MARGIN,
        0.7 * cm,
        "Nifty 100 Financial Intelligence Platform | Latest financial year per company | Market data is simulated",
    )
    canvas.drawRightString(PAGE[0] - MARGIN, 0.7 * cm, f"Page {doc.page}")
    canvas.restoreState()


def grid(rows: list[list], widths: list[float], extra: list | None = None) -> Table:
    """Table with a navy header row, light zebra stripes and thin grid lines."""
    t = Table(rows, colWidths=widths, repeatRows=1)
    st = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D5DD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    t.setStyle(TableStyle(st + (extra or [])))
    return t


def build_sector_report(d: Data, sector: str, path: Path) -> int:
    """Write one sector PDF; returns the page count."""
    members = [t for t in d.latest.index if d.sector(t) == sector]
    lat = d.latest.loc[members].copy()
    lat["name"] = [d.name(t) for t in lat.index]
    lat = lat.sort_values("composite_quality_score", ascending=False)
    universe = d.latest

    story = [
        Paragraph(f"<b>{escape(sector)}</b> sector report", style("t", 18, color=NAVY)),
        Spacer(1, 4),
        Paragraph(
            f"{len(lat)} companies | median KPIs versus the full Nifty 100 universe ({len(universe)} companies)",
            SMALL,
        ),
        Spacer(1, 12),
    ]
    rows = [
        [
            Paragraph("KPI", HEAD),
            Paragraph(f"{escape(sector)} median", HEAD),
            Paragraph("Nifty 100 median", HEAD),
        ]
    ]
    for col, head, nd, _ in KPIS:
        rows.append(
            [
                Paragraph(head, CELL),
                Paragraph(num(lat[col].median(), nd), CELL),
                Paragraph(num(universe[col].median(), nd), CELL),
            ]
        )
    story += [grid(rows, [UW * 0.4, UW * 0.3, UW * 0.3]), Spacer(1, 14)]

    top, bottom = lat.iloc[0], lat.iloc[-1]
    story += [
        Paragraph(
            "<b>Best and weakest by composite quality score</b>",
            style("sub", 10, color=NAVY),
        ),
        Spacer(1, 4),
        Paragraph(
            f'<font color="#1A7F37"><b>Best:</b></font> {escape(top["name"])} ({top.name}), score {num(top["composite_quality_score"])}',
            CELL,
        ),
        Paragraph(
            f'<font color="#C0392B"><b>Weakest:</b></font> {escape(bottom["name"])} ({bottom.name}), score {num(bottom["composite_quality_score"])}',
            CELL,
        ),
        PageBreak(),
        Paragraph(f"<b>Companies in {escape(sector)}</b>", style("t2", 14, color=NAVY)),
        Spacer(1, 6),
    ]

    head = [Paragraph(h, HEAD) for h in ["Ticker", "Company"] + [k[1] for k in KPIS]]
    body = []
    for t, r in lat.iterrows():
        body.append(
            [Paragraph(escape(t), CELL_B), Paragraph(escape(r["name"]), CELL)]
            + [Paragraph(num(r[c], nd), CELL) for c, _, nd, _ in KPIS]
        )
    first, rest = UW * 0.09, UW * 0.23
    widths = [first, rest] + [(UW - first - rest) / len(KPIS)] * len(KPIS)
    extra = (
        [
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#DFF3E4")),
            ("BACKGROUND", (0, len(body)), (-1, len(body)), colors.HexColor("#FBE3E0")),
        ]
        if len(body) > 1
        else []
    )
    story += [
        grid([head, *body], widths, extra),
        Spacer(1, 6),
        Paragraph(
            '<font color="#1A7F37">Green row</font> = highest quality score, red row = lowest. '
            "Sorted by composite quality score.",
            SMALL,
        ),
    ]
    doc = SimpleDocTemplate(
        str(path),
        pagesize=PAGE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=f"{sector} sector report",
        author="Nifty 100 Platform",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return doc.page
