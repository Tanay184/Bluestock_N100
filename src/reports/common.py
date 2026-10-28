"""Shared report helpers: fonts, styles, data loader and matplotlib charts."""

import io
import math
import sqlite3
from contextlib import closing
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image

from src.etl.loader import DB_PATH

NAVY = colors.HexColor("#1F3A5F")
LIGHT = colors.HexColor("#EEF2F7")
GREEN = colors.HexColor("#1A7F37")
RED = colors.HexColor("#C0392B")
GREY = colors.HexColor("#667085")
HEX = {
    "navy": "#1F3A5F",
    "blue": "#4C78A8",
    "light": "#9CC3E6",
    "orange": "#F28E2B",
    "green": "#1A7F37",
    "red": "#C0392B",
}
PATTERN_COLOURS = {
    "Reinvestor": "#2E86C1",
    "Shareholder Returns": "#1A7F37",
    "Liquidating Assets": "#B9770E",
    "Cash Accumulator": "#117A65",
    "Distress Signal": "#C0392B",
    "Growth Funded by Debt": "#AF601A",
    "Pre-Revenue": "#7D3C98",
    "Mixed": "#5D6D7E",
    "No Data": "#99A3A4",
}


def register_fonts() -> None:
    """Register DejaVu (bundled with matplotlib) so arrows, bullets and rupee text render."""
    base = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("DV", str(base / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DV-B", str(base / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(
        "DV", normal="DV", bold="DV-B", italic="DV", boldItalic="DV-B"
    )


register_fonts()


def style(
    name: str,
    size: float = 9,
    bold: bool = False,
    color=colors.black,
    leading: float | None = None,
    **kw,
):
    """Build a ParagraphStyle using the registered font."""
    return ParagraphStyle(
        name,
        fontName="DV-B" if bold else "DV",
        fontSize=size,
        textColor=color,
        leading=leading or size * 1.3,
        **kw,
    )


BODY = style("body", 8.5)
SMALL = style("small", 7, color=GREY)
CELL = style("cell", 8)
CELL_B = style("cell_b", 8, bold=True)
HEAD = style("head", 8, bold=True, color=colors.white)


def num(v, nd: int = 1, suffix: str = "") -> str:
    """Format a number for display; 'N/A' when missing."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "N/A"
    return "N/A" if math.isnan(f) else f"{f:,.{nd}f}{suffix}"


def year_label(y: str) -> str:
    """'2024-03' -> "'24"; other year-ends keep the month."""
    return f"'{y[2:4]}" if y.endswith("-03") else f"'{y[2:4]}-{y[5:]}"


def png_image(fig, width_pt: float) -> Image:
    """Render a matplotlib figure to a ReportLab Image of the given width."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = width_pt, width_pt * ratio
    return img


def _axes(title: str, size=(8.0, 2.9)):
    fig, ax = plt.subplots(figsize=size)
    ax.set_title(title, fontsize=10, loc="left", fontweight="bold", color=HEX["navy"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=8)
    return fig, ax


def revenue_profit_chart(pl: pd.DataFrame):
    """Side-by-side bars of revenue and net profit for up to 10 years."""
    d = pl.tail(10)
    if d.empty:
        return None
    fig, ax = _axes("Revenue and Net Profit (Rs Cr)")
    x = range(len(d))
    ax.bar([i - 0.2 for i in x], d["sales"], 0.4, label="Revenue", color=HEX["navy"])
    ax.bar(
        [i + 0.2 for i in x],
        d["net_profit"],
        0.4,
        label="Net profit",
        color=HEX["light"],
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels([year_label(y) for y in d["year"]])
    ax.legend(fontsize=8, frameon=False)
    return fig


def roe_roce_chart(fr: pd.DataFrame):
    """ROE (left axis) and ROCE (right axis) lines for up to 10 years."""
    d = fr.tail(10)
    if d.empty:
        return None
    fig, ax = _axes("ROE and ROCE (%)")
    labels = [year_label(y) for y in d["year"]]
    ax.plot(
        labels, d["return_on_equity_pct"], marker="o", color=HEX["navy"], label="ROE %"
    )
    ax.set_ylabel("ROE %", fontsize=8, color=HEX["navy"])
    ax2 = ax.twinx()
    ax2.plot(labels, d["roce_pct"], marker="s", color=HEX["orange"], label="ROCE %")
    ax2.set_ylabel("ROCE %", fontsize=8, color=HEX["orange"])
    ax2.tick_params(labelsize=8)
    ax2.spines["top"].set_visible(False)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(
        lines,
        [ln.get_label() for ln in lines],
        fontsize=8,
        frameon=False,
        loc="upper left",
    )
    return fig


def balance_chart(bs: pd.DataFrame):
    """Stacked bars of equity, borrowings and other liabilities."""
    d = bs.tail(10)
    if d.empty:
        return None
    fig, ax = _axes("Balance Sheet Composition (Rs Cr)")
    labels = [year_label(y) for y in d["year"]]
    equity = (d["equity_capital"].fillna(0) + d["reserves"].fillna(0)).tolist()
    debt = d["borrowings"].fillna(0).tolist()
    other = d["other_liabilities"].fillna(0).tolist()
    ax.bar(labels, equity, label="Equity + reserves", color=HEX["navy"])
    ax.bar(labels, debt, bottom=equity, label="Borrowings", color=HEX["red"])
    ax.bar(
        labels,
        other,
        bottom=[a + b for a, b in zip(equity, debt, strict=True)],
        label="Other liabilities",
        color=HEX["light"],
    )
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper left")
    return fig


def waterfall_chart(cfo, cfi, cff, net, year: str):
    """Cash flow waterfall: CFO, CFI, CFF and net cash flow for the latest year."""
    vals = [cfo, cfi, cff]
    if any(pd.isna(v) for v in vals):
        return None
    fig, ax = _axes(f"Cash Flow Waterfall, FY {year[:4]} (Rs Cr)")
    run = 0.0
    names, bottoms, heights, cols = [], [], [], []
    for name, v in zip(("CFO", "CFI", "CFF"), vals, strict=True):
        bottoms.append(run if v >= 0 else run + v)
        heights.append(abs(v))
        cols.append(HEX["green"] if v >= 0 else HEX["red"])
        names.append(name)
        run += v
    total = net if pd.notna(net) else run
    names.append("Net cash flow")
    bottoms.append(min(0, total))
    heights.append(abs(total))
    cols.append(HEX["navy"])
    ax.bar(names, heights, bottom=bottoms, color=cols, width=0.55)
    ax.axhline(0, color="#999999", linewidth=0.8)
    return fig


def usable_width(page_width: float, margin: float) -> float:
    """Content width inside the default frame padding (6pt each side)."""
    return page_width - 2 * margin - 12


class Data:
    """All tables the reports need, loaded once and grouped by company."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        def grouped(sql: str) -> dict[str, pd.DataFrame]:
            """Grouped."""
            df = pd.read_sql(sql, conn)
            return {k: g.reset_index(drop=True) for k, g in df.groupby("company_id")}

        self._fr = grouped("SELECT * FROM financial_ratios ORDER BY company_id, year")
        self._pl = grouped("SELECT * FROM profitandloss ORDER BY company_id, year")
        self._bs = grouped(
            "SELECT * FROM balancesheet WHERE year IN (SELECT year FROM profitandloss "
            "WHERE profitandloss.company_id = balancesheet.company_id) ORDER BY company_id, year"
        )
        self._cf = grouped("SELECT * FROM cashflow ORDER BY company_id, year")
        self.companies = pd.read_sql(
            "SELECT id, company_name FROM companies ORDER BY id", conn
        ).set_index("id")
        self.sectors = pd.read_sql("SELECT * FROM sectors", conn).set_index(
            "company_id"
        )
        cap = pd.read_sql(
            "SELECT * FROM capital_allocation ORDER BY company_id, year", conn
        )
        self.pattern = (
            cap.groupby("company_id")
            .tail(1)
            .set_index("company_id")["pattern_label"]
            .to_dict()
        )
        try:
            self._pc = grouped("SELECT * FROM pros_cons_generated")
        except (pd.errors.DatabaseError, sqlite3.OperationalError):
            self._pc = {}
        self.latest = (
            pd.concat(self._fr.values())
            .groupby("company_id")
            .tail(1)
            .set_index("company_id")
        )

    @classmethod
    def load(cls) -> "Data":
        """Open the database and load everything."""
        with closing(sqlite3.connect(DB_PATH)) as conn:
            return cls(conn)

    def ratios(self, t: str) -> pd.DataFrame:
        """Financial ratios for a company, oldest first."""
        return self._fr.get(t, pd.DataFrame())

    def pl(self, t: str) -> pd.DataFrame:
        """Profit and loss history."""
        return self._pl.get(t, pd.DataFrame())

    def bs(self, t: str) -> pd.DataFrame:
        """Balance sheet history (annual periods only)."""
        return self._bs.get(t, pd.DataFrame())

    def cf(self, t: str) -> pd.DataFrame:
        """Cash flow history."""
        return self._cf.get(t, pd.DataFrame())

    def name(self, t: str) -> str:
        """Company name (ticker if unknown)."""
        return str(self.companies["company_name"].get(t, t))

    def sector(self, t: str) -> str:
        """Broad sector."""
        return str(self.sectors["broad_sector"].get(t, "N/A"))

    def sub_sector(self, t: str) -> str:
        """Sub-sector."""
        return str(self.sectors["sub_sector"].get(t, "N/A"))

    def years(self, t: str) -> int:
        """Number of annual ratio rows."""
        return len(self.ratios(t))

    def pros_cons(self, t: str, kind: str, n: int = 5) -> pd.DataFrame:
        """Top n generated pros or cons by confidence."""
        d = self._pc.get(t)
        if d is None:
            return pd.DataFrame(columns=["text", "confidence_pct"])
        return (
            d[d["type"] == kind].sort_values("confidence_pct", ascending=False).head(n)
        )

    def tickers(self) -> list[str]:
        """Sorted tickers with ratio data."""
        return sorted(self._fr)
