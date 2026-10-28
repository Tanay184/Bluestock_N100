"""Rule-based pros/cons generator: 12 pro + 12 con rules with confidence scores (Day 30)."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass

import pandas as pd

from src.etl.loader import DB_PATH, OUT

MIN_CONFIDENCE = 60.0  # only entries with confidence strictly above this are kept
FINANCIALS = "Financials"
REL_METRICS = {  # column in financial_ratios -> (label, unit, lower_is_better)
    "return_on_equity_pct": ("ROE", "%", False),
    "roce_pct": ("ROCE", "%", False),
    "net_profit_margin_pct": ("Net profit margin", "%", False),
    "fcf_margin_pct": ("FCF margin", "%", False),
    "revenue_cagr_5yr": ("5-year revenue CAGR", "%", False),
    "pat_cagr_5yr": ("5-year profit CAGR", "%", False),
    "debt_to_equity": ("Debt-to-equity", "x", True),
}


def conf(excess, scale) -> float | None:
    """Map how far a signal passes its threshold to a 60-100 score; None if it does not pass."""
    if excess is None or pd.isna(excess) or excess <= 0 or scale <= 0:
        return None
    return round(60 + 40 * min(1.0, excess / scale), 1)


def all_above(vals: list[float], thr: float, n: int) -> bool:
    """True if the last n values all exceed thr."""
    return len(vals) >= n and all(v > thr for v in vals[-n:])


def all_below(vals: list[float], thr: float, n: int) -> bool:
    """True if the last n values are all below thr."""
    return len(vals) >= n and all(v < thr for v in vals[-n:])


def streak(vals: list[float], n: int, up: bool) -> bool:
    """True if the last n year-on-year changes are all increases (up) or all decreases."""
    if len(vals) < n + 1:
        return False
    pairs = zip(vals[-n - 1 : -1], vals[-n:], strict=True)
    return all((b > a) if up else (b < a) for a, b in pairs)


@dataclass
class Company:
    """Annual history (oldest first) plus a few latest-year extras for one company."""

    cid: str
    sector: str
    df: pd.DataFrame
    div_yield: float | None = None

    def vals(self, col: str) -> list[float]:
        """Non-null values of a column, oldest first."""
        return self.df[col].dropna().tolist() if col in self.df else []

    def last(self, col: str):
        """Latest non-null value of a column, or None."""
        v = self.vals(col)
        return v[-1] if v else None

    def last_raw(self, col: str):
        """Value in the most recent row (may be None)."""
        return self.df[col].iloc[-1] if col in self.df and len(self.df) else None


# ---- pro rules: each returns (confidence or None, info dict) ----
def pro_roe_high(c):
    """Pro roe high."""
    v = c.vals("return_on_equity_pct")
    return (conf(min(v[-3:]) - 20, 20), {}) if all_above(v, 20, 3) else (None, {})


def pro_fcf_positive(c):
    """Pro fcf positive."""
    if not all_above(c.vals("free_cash_flow_cr"), 0, 5):
        return None, {}
    m = c.vals("fcf_margin_pct")[-5:]
    return (conf(sum(m) / len(m), 15) if m else 70.0), {}


def pro_debt_free(c):
    """Pro debt free."""
    return (95.0, {}) if c.last("debt_to_equity") == 0 else (None, {})


def pro_rev_cagr(c):
    """Pro rev cagr."""
    x = c.last("revenue_cagr_5yr")
    return (conf(x - 15, 15), {}) if x is not None else (None, {})


def pro_opm_high(c):
    """Pro opm high."""
    x = c.last("operating_profit_margin_pct")
    return (conf(x - 25, 25), {}) if x is not None else (None, {})


def pro_pat_cagr(c):
    """Pro pat cagr."""
    x = c.last("pat_cagr_5yr")
    return (conf(x - 20, 20), {}) if x is not None else (None, {})


def pro_icr(c):
    """Pro icr."""
    if c.last_raw("icr_label") == "Debt Free":
        return 90.0, {}
    x = c.last("interest_coverage")
    return (conf(x - 10, 20), {}) if x is not None else (None, {})


def pro_dividend(c):
    """Pro dividend."""
    fcf = c.last("free_cash_flow_cr")
    if c.div_yield is None or fcf is None or fcf <= 0:
        return None, {}
    return conf(c.div_yield - 2, 2), {}


def pro_eps_cagr(c):
    """Pro eps cagr."""
    x = c.last("eps_cagr_5yr")
    return (conf(x - 15, 15), {}) if x is not None else (None, {})


def pro_roe_improving(c):
    """Pro roe improving."""
    v = c.vals("return_on_equity_pct")
    return (conf(v[-1] - v[-4], 10), {}) if streak(v, 3, up=True) else (None, {})


def pro_operating_leverage(c):
    """Pro operating leverage."""
    pat, rev = c.last("pat_cagr_5yr"), c.last("revenue_cagr_5yr")
    if pat is None or rev is None or rev <= 0:
        return None, {}
    return conf(pat - rev, 10), {}


def pro_assets_up_debt_down(c):
    """Pro assets up debt down."""
    ta, debt = c.vals("total_assets"), c.vals("total_debt_cr")
    if (
        len(ta) < 2
        or len(debt) < 2
        or ta[-2] <= 0
        or not (ta[-1] > ta[-2] and debt[-1] < debt[-2])
    ):
        return None, {}
    return conf((ta[-1] / ta[-2] - 1) * 100, 10), {}


# ---- con rules ----
def con_de_high(c):
    """Con de high."""
    x = c.last("debt_to_equity")
    return (conf(x - 2, 3), {"x": f"{x:.1f}x"}) if x is not None else (None, {})


def con_fcf_negative(c):
    """Con fcf negative."""
    v = c.vals("free_cash_flow_cr")
    if not all_below(v, 0, 3):
        return None, {}
    m = c.vals("fcf_margin_pct")[-3:]
    return (conf(-sum(m) / len(m), 10) if m else 70.0), {}


def con_opm_declining(c):
    """Con opm declining."""
    v = c.vals("operating_profit_margin_pct")
    return (conf(v[-4] - v[-1], 5), {}) if streak(v, 3, up=False) else (None, {})


def con_net_loss(c):
    """Con net loss."""
    x = c.last("net_profit")
    return (95.0, {}) if x is not None and x < 0 else (None, {})


def con_revenue_declining(c):
    """Con revenue declining."""
    v = c.vals("sales")
    if not streak(v, 2, up=False) or v[-3] <= 0:
        return None, {}
    return conf((v[-3] - v[-1]) / v[-3] * 100, 10), {}


def con_icr_low(c):
    """Con icr low."""
    x = c.last("interest_coverage")
    if x is None or c.last_raw("icr_label") == "Debt Free":
        return None, {}
    return conf(1.5 - x, 1.5), {}


def con_payout_high(c):
    """Con payout high."""
    x = c.last("dividend_payout_ratio_pct")
    return (conf(x - 100, 100), {}) if x is not None else (None, {})


def con_de_rising(c):
    """Con de rising."""
    v = c.vals("debt_to_equity")
    return (conf(v[-1] - v[-4], 1.0), {}) if streak(v, 3, up=True) else (None, {})


def con_eps_declining(c):
    """Con eps declining."""
    v = c.vals("earnings_per_share")
    if not streak(v, 3, up=False) or v[-4] <= 0:
        return None, {}
    return conf((v[-4] - v[-1]) / v[-4] * 100, 30), {}


def con_roce_low(c):
    """Con roce low."""
    x = c.last("roce_pct")
    return (conf(10 - x, 10), {}) if x is not None else (None, {})


def con_net_debt_ebitda(c):
    """Con net debt ebitda."""
    nd, op = c.last("net_debt_cr"), c.last("operating_profit")
    if nd is None or op is None or op <= 0:
        return None, {}
    return conf(nd / op - 3, 3), {}


def con_rev_cagr_low(c):
    """Con rev cagr low."""
    x = c.last("revenue_cagr_5yr")
    return (conf(5 - x, 5), {}) if x is not None else (None, {})


# (rule_id, type, text, function, applies_to_financials)
# Banks/NBFCs are exempt from margin, leverage and coverage rules (D/E, ICR, OPM are structurally different).
RULES = [
    (
        "PRO-01",
        "pro",
        "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
        pro_roe_high,
        True,
    ),
    (
        "PRO-02",
        "pro",
        "Strong free cash flow generation over 5 years signals healthy business fundamentals",
        pro_fcf_positive,
        True,
    ),
    (
        "PRO-03",
        "pro",
        "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
        pro_debt_free,
        False,
    ),
    (
        "PRO-04",
        "pro",
        "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
        pro_rev_cagr,
        True,
    ),
    (
        "PRO-05",
        "pro",
        "Operating profit margin above 25% indicates strong pricing power and cost discipline",
        pro_opm_high,
        False,
    ),
    (
        "PRO-06",
        "pro",
        "Net profit compounding at above 20% over 5 years creates significant shareholder value",
        pro_pat_cagr,
        True,
    ),
    (
        "PRO-07",
        "pro",
        "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
        pro_icr,
        False,
    ),
    (
        "PRO-08",
        "pro",
        "Consistent dividend yield above 2% backed by positive free cash flow",
        pro_dividend,
        True,
    ),
    (
        "PRO-09",
        "pro",
        "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
        pro_eps_cagr,
        True,
    ),
    (
        "PRO-10",
        "pro",
        "Return on equity improving for 3 consecutive years shows strengthening business quality",
        pro_roe_improving,
        True,
    ),
    (
        "PRO-11",
        "pro",
        "Revenue growing slower than profits shows improving operating leverage and scale benefits",
        pro_operating_leverage,
        True,
    ),
    (
        "PRO-12",
        "pro",
        "Growing asset base funded by internal accruals reflects self-sustaining growth",
        pro_assets_up_debt_down,
        False,
    ),
    (
        "CON-01",
        "con",
        "Debt-to-equity ratio of {x} is elevated for a non-financial company and warrants monitoring",
        con_de_high,
        False,
    ),
    (
        "CON-02",
        "con",
        "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
        con_fcf_negative,
        True,
    ),
    (
        "CON-03",
        "con",
        "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
        con_opm_declining,
        False,
    ),
    (
        "CON-04",
        "con",
        "Company reported a net loss in the most recent financial year",
        con_net_loss,
        True,
    ),
    (
        "CON-05",
        "con",
        "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
        con_revenue_declining,
        True,
    ),
    (
        "CON-06",
        "con",
        "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
        con_icr_low,
        False,
    ),
    (
        "CON-07",
        "con",
        "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
        con_payout_high,
        True,
    ),
    (
        "CON-08",
        "con",
        "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
        con_de_rising,
        False,
    ),
    (
        "CON-09",
        "con",
        "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
        con_eps_declining,
        True,
    ),
    (
        "CON-10",
        "con",
        "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
        con_roce_low,
        False,
    ),
    (
        "CON-11",
        "con",
        "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
        con_net_debt_ebitda,
        False,
    ),
    (
        "CON-12",
        "con",
        "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
        con_rev_cagr_low,
        True,
    ),
]


def evaluate(c: Company) -> list[dict]:
    """Run every applicable rule for one company; keep entries above the confidence floor."""
    out = []
    for rule_id, kind, text, fn, fin_ok in RULES:
        if c.sector == FINANCIALS and not fin_ok:
            continue
        score, info = fn(c)
        if score is not None and score > MIN_CONFIDENCE:
            out.append(
                {
                    "company_id": c.cid,
                    "type": kind,
                    "rule_id": rule_id,
                    "text": text.format(**info),
                    "confidence_pct": score,
                }
            )
    return out


def group_percentiles(latest: pd.DataFrame, groups: pd.Series) -> pd.DataFrame:
    """Percentile (0-1, 1 = best) of each relative-strength metric within the given groups."""
    pct = pd.DataFrame(index=latest.index)
    for col, (_, _, lower) in REL_METRICS.items():
        s = latest[col].astype(float)
        ranked = s.groupby(groups).rank(method="min", ascending=lower)
        count = s.groupby(groups).transform("count")
        pct[col] = (
            ((count - ranked) / (count - 1)).where(count > 1, 0.5).where(s.notna())
        )
    return pct


def sector_percentiles(latest: pd.DataFrame) -> pd.DataFrame:
    """Percentiles versus companies in the same broad sector."""
    return group_percentiles(latest, latest["sector"])


def universe_percentiles(latest: pd.DataFrame) -> pd.DataFrame:
    """Percentiles versus all companies."""
    return group_percentiles(latest, pd.Series("ALL", index=latest.index))


def relative_entries(
    cid: str,
    row: pd.Series,
    sector_pct: pd.Series,
    universe_pct: pd.Series,
    kind: str,
    sector: str = "",
) -> dict | None:
    """Fallback entry: strongest (pro) or weakest (con) metric versus sector peers or the whole universe.

    Takes whichever comparison gives the higher confidence. D/E is skipped for Financials.
    """
    best = None  # (score, column, percentile, scope)
    for scope, pct_row in (
        ("sector peers", sector_pct),
        ("Nifty 100 companies", universe_pct),
    ):
        for col, p in pct_row.dropna().items():
            if col == "debt_to_equity" and sector == FINANCIALS:
                continue
            score = p * 100 if kind == "pro" else (1 - p) * 100
            if best is None or score > best[0] + 1e-9:
                best = (score, col, float(p), scope)
    if best is None:
        return None
    score, col, p, scope = best
    label, unit, _ = REL_METRICS[col]
    value = f"{row[col]:.1f}{unit}"
    if kind == "pro":
        text = f"{label} of {value} ranks better than {p * 100:.0f}% of {scope}"
    else:
        text = f"{label} of {value} ranks weaker than {(1 - p) * 100:.0f}% of {scope}"
    return {
        "company_id": cid,
        "type": kind,
        "rule_id": f"{kind.upper()}-REL",
        "text": text,
        "confidence_pct": round(score, 1),
    }


def load_companies(conn: sqlite3.Connection) -> tuple[list[Company], pd.DataFrame]:
    """Build Company objects and the latest-year sector snapshot."""
    fr = pd.read_sql("SELECT * FROM financial_ratios", conn).sort_values(
        ["company_id", "year"]
    )
    pl = pd.read_sql(
        "SELECT company_id, year, sales, operating_profit, net_profit FROM profitandloss",
        conn,
    )
    bs = pd.read_sql("SELECT company_id, year, total_assets FROM balancesheet", conn)
    sec = pd.read_sql("SELECT company_id, broad_sector AS sector FROM sectors", conn)
    mc = pd.read_sql(
        "SELECT company_id, year, dividend_yield_pct FROM market_cap", conn
    )
    df = fr.merge(pl, on=["company_id", "year"], how="left").merge(
        bs, on=["company_id", "year"], how="left"
    )
    df = df.merge(sec, on="company_id", how="left")
    companies = []
    for cid, g in df.groupby("company_id"):
        g = g.reset_index(drop=True)
        yr = int(g["year"].iloc[-1][:4])
        m = mc[(mc["company_id"] == cid) & (mc["year"] <= yr)].sort_values("year")
        dy = float(m["dividend_yield_pct"].iloc[-1]) if len(m) else None
        companies.append(Company(cid, g["sector"].iloc[-1], g, dy))
    latest = df.groupby("company_id").tail(1).set_index("company_id")
    return companies, latest


def generate(conn: sqlite3.Connection) -> pd.DataFrame:
    """Generate pros and cons for every company, guaranteeing at least one of each."""
    companies, latest = load_companies(conn)
    sec_pct, all_pct = sector_percentiles(latest), universe_percentiles(latest)
    rows = []
    for c in companies:
        entries = evaluate(c)
        for kind in ("pro", "con"):
            if not any(e["type"] == kind for e in entries):
                fb = relative_entries(
                    c.cid,
                    latest.loc[c.cid],
                    sec_pct.loc[c.cid],
                    all_pct.loc[c.cid],
                    kind,
                    c.sector,
                )
                if fb:
                    entries.append(fb)
        rows.extend(entries)
    cols = ["company_id", "type", "rule_id", "text", "confidence_pct"]
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(
        ["company_id", "type", "confidence_pct"], ascending=[True, True, False]
    )


def main() -> None:
    """Write output/pros_cons_generated.csv and the pros_cons_generated table."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        out = generate(conn)
        out.to_sql("pros_cons_generated", conn, if_exists="replace", index=False)
        total = pd.read_sql("SELECT COUNT(*) n FROM companies", conn)["n"].iloc[0]
    OUT.mkdir(exist_ok=True)
    out.to_csv(OUT / "pros_cons_generated.csv", index=False)
    by = out.groupby("company_id")["type"].agg(lambda s: set(s))
    missing = [c for c in by.index if by[c] != {"pro", "con"}]
    print(
        f"rows: {len(out)} | companies covered: {by.size}/{total} | missing a pro or a con: {len(missing)}"
    )
    print("rule usage:", out["rule_id"].value_counts().to_dict())
    print(
        "fallback (sector-relative) entries:",
        int(out["rule_id"].str.endswith("REL").sum()),
        "| entries at or below 60% confidence:",
        int((out["confidence_pct"] <= MIN_CONFIDENCE).sum()),
    )


if __name__ == "__main__":
    main()
