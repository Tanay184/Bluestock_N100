"""Two-page company tearsheet PDF built with ReportLab (Day 33)."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.reports.common import (
    GREEN,
    GREY,
    LIGHT,
    NAVY,
    PATTERN_COLOURS,
    RED,
    SMALL,
    Data,
    balance_chart,
    num,
    png_image,
    revenue_profit_chart,
    roe_roce_chart,
    style,
    usable_width,
    waterfall_chart,
)

MARGIN = 1.6 * cm
UW = usable_width(A4[0], MARGIN)
PAGE_H = A4[1] - 3.0 * cm - 20


def footer(canvas, doc) -> None:
    """Draw the page footer."""
    canvas.saveState()
    canvas.setFont("DV", 7)
    canvas.setFillColor(GREY)
    canvas.drawString(
        MARGIN,
        0.8 * cm,
        "Nifty 100 Financial Intelligence Platform | Source: nifty100.db | Market data is SIMULATED",
    )
    canvas.drawRightString(A4[0] - MARGIN, 0.8 * cm, f"Page {doc.page} of 2")
    canvas.restoreState()


def header_bar(title: str, sub: str) -> Table:
    """Navy header bar with a title and a subtitle line."""
    t = Table(
        [
            [Paragraph(f"<b>{escape(title)}</b>", style("h1", 15, color=colors.white))],
            [
                Paragraph(
                    escape(sub), style("h2", 8.5, color=colors.HexColor("#D6E4F5"))
                )
            ],
        ],
        colWidths=[UW],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ]
        )
    )
    return t


def tiles(last) -> Table:
    """Six KPI tiles in two rows of three."""
    items = [
        ("ROE", num(last["return_on_equity_pct"], 1, "%")),
        ("ROCE", num(last["roce_pct"], 1, "%")),
        ("Net profit margin", num(last["net_profit_margin_pct"], 1, "%")),
        ("Debt / equity", num(last["debt_to_equity"], 2)),
        ("Revenue CAGR 5yr", num(last["revenue_cagr_5yr"], 1, "%")),
        ("Free cash flow (Rs Cr)", num(last["free_cash_flow_cr"], 0)),
    ]
    cells = [
        Paragraph(
            f'<font size="7" color="#667085">{lab}</font><br/><font size="14" color="#1F3A5F"><b>{val}</b></font>',
            style("tile", 9, leading=18),
        )
        for lab, val in items
    ]
    t = Table([cells[:3], cells[3:]], colWidths=[UW / 3] * 3, rowHeights=[1.6 * cm] * 2)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("INNERGRID", (0, 0), (-1, -1), 4, colors.white),
                ("BOX", (0, 0), (-1, -1), 4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return t


def chart_or_note(fig, note: str):
    """Chart image, or a short note when data is missing."""
    return png_image(fig, UW) if fig is not None else Paragraph(note, SMALL)


def bullets(df, colour: str, empty: str) -> list:
    """Bullet paragraphs for pros or cons, with the confidence in grey."""
    if df.empty:
        return [Paragraph(empty, SMALL)]
    bullet = style(
        "bul", 8.2, leading=11, leftIndent=11, firstLineIndent=-11, spaceAfter=4
    )
    return [
        Paragraph(
            f'<font color="{colour}">●</font> {escape(str(r.text))} '
            f'<font size="6" color="#667085">({r.confidence_pct:.0f}%)</font>',
            bullet,
        )
        for r in df.itertuples()
    ]


def build_tearsheet(d: Data, ticker: str, path: Path) -> int:
    """Create the two-page PDF for one company; returns the page count."""
    fr, pl, bs, cf = d.ratios(ticker), d.pl(ticker), d.bs(ticker), d.cf(ticker)
    last = fr.iloc[-1]
    name, sector = d.name(ticker), d.sector(ticker)
    sub = f"{ticker}  |  {sector}  |  {d.sub_sector(ticker)}  |  Latest financial year: {last['year']}"

    page1 = [
        header_bar(name, sub),
        Spacer(1, 8),
        tiles(last),
        Spacer(1, 10),
        chart_or_note(
            revenue_profit_chart(pl), "Revenue and profit history not available."
        ),
        Spacer(1, 8),
        chart_or_note(roe_roce_chart(fr), "ROE and ROCE history not available."),
    ]

    cfl = cf.iloc[-1] if len(cf) else None
    wf = None
    if cfl is not None:
        wf = waterfall_chart(
            cfl["operating_activity"],
            cfl["investing_activity"],
            cfl["financing_activity"],
            cfl["net_cash_flow"],
            cfl["year"],
        )
    pattern = d.pattern.get(ticker, "No Data")
    badge = Table(
        [
            [
                Paragraph(
                    f'<font color="white"><b>Capital allocation: {escape(pattern)}</b></font>',
                    style("bd", 9),
                )
            ]
        ],
        colWidths=[UW],
    )
    badge.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(PATTERN_COLOURS.get(pattern, "#5D6D7E")),
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    head = style("sec", 10, bold=True)
    pros = [
        Paragraph("Pros", style("pros_h", 10, bold=True, color=GREEN)),
        Spacer(1, 4),
    ]
    pros += bullets(
        d.pros_cons(ticker, "pro"), "#1A7F37", "No notable strengths flagged."
    )
    cons = [Paragraph("Cons", style("cons_h", 10, bold=True, color=RED)), Spacer(1, 4)]
    cons += bullets(
        d.pros_cons(ticker, "con"), "#C0392B", "No notable concerns flagged."
    )
    two = Table([[pros, cons]], colWidths=[UW / 2, UW / 2])
    two.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    page2 = [
        header_bar(name, f"{ticker}  |  Balance sheet, cash flow and qualitative view"),
        Spacer(1, 8),
        chart_or_note(balance_chart(bs), "Balance sheet history not available."),
        Spacer(1, 8),
        chart_or_note(wf, "Cash flow data not available for the latest year."),
        Spacer(1, 10),
        Paragraph("Key strengths and concerns (auto-generated, with confidence)", head),
        Spacer(1, 4),
        two,
        Spacer(1, 6),
        badge,
        Spacer(1, 4),
        Paragraph(
            "Pros and cons are generated from KPI threshold rules and are not investment advice. "
            "Ratios use annual filings; market data is SIMULATED.",
            SMALL,
        ),
    ]
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"{name} tearsheet",
        author="Nifty 100 Platform",
    )
    story = [
        KeepInFrame(UW, PAGE_H, page1, mode="shrink"),
        PageBreak(),
        KeepInFrame(UW, PAGE_H, page2, mode="shrink"),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return doc.page
