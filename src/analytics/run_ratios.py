"""Run the ratio engine: write financial_ratios, capital_allocation and the edge-case log."""

import logging
import sqlite3

import pandas as pd

from src.analytics import cashflow_kpis as ck
from src.analytics import ratios as r
from src.analytics.cagr import add_cagr
from src.etl.loader import DB_PATH, OUT

logger = logging.getLogger(__name__)
REQUIRED = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "capex_cr",
    "earnings_per_share",
    "book_value_per_share",
    "dividend_payout_ratio_pct",
    "total_debt_cr",
    "cash_from_operations_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "composite_quality_score",
]


def _table(conn, name):
    return pd.read_sql(f"SELECT * FROM {name}", conn).drop(columns="id")


def load_base(conn):
    """Join P&L, balance sheet and cash flow on (company_id, year) plus company/sector info."""
    df = _table(conn, "profitandloss").merge(
        _table(conn, "balancesheet"), on=["company_id", "year"], how="outer"
    )
    df = df.merge(_table(conn, "cashflow"), on=["company_id", "year"], how="outer")
    comp = pd.read_sql(
        "SELECT id AS company_id, face_value, roce_percentage, roe_percentage FROM companies",
        conn,
    )
    sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    return df.merge(comp, on="company_id", how="left").merge(
        sec, on="company_id", how="left"
    )


def drop_partial_periods(df, log):
    """Drop balance-sheet-only periods that are not the company's fiscal year-end month."""
    d = df.assign(m=df["year"].str[-2:])
    fy = d[d["sales"].notna()].groupby("company_id")["m"].agg(lambda s: s.mode().iat[0])
    partial = (
        d["sales"].isna()
        & d["operating_activity"].isna()
        & (d["m"] != d["company_id"].map(fy))
    )
    for c, y in zip(df.loc[partial, "company_id"], df.loc[partial, "year"]):
        log.append(
            f"NON_ANNUAL_PERIOD | {c} | {y} | balance-sheet-only period, not fiscal year-end; excluded"
        )
    return df[~partial]


def compute(df, log):
    """Compute per-row KPIs and capital allocation labels."""

    def note(kind, x, detail):
        log.append(f"{kind} | {x['company_id']} | {x['year']} | {detail}")

    rows, cap = [], []
    for x in df.to_dict("records"):
        sales, eq = r.num(x["sales"]), r.equity(x["equity_capital"], x["reserves"])
        if sales == 0:
            note("DIV_ZERO", x, "sales = 0; margins and turnover set to None")
        if eq is not None and eq <= 0:
            note("NEG_EQUITY", x, f"equity+reserves = {eq}; ROE/ROCE/D-E set to None")
        if r.num(x["interest"]) == 0:
            note("DEBT_FREE_ICR", x, "interest = 0; ICR None, label 'Debt Free'")
        if r.opm_mismatch(x["opm_percentage"], x["operating_profit"], x["sales"]):
            calc = r.operating_profit_margin(x["operating_profit"], x["sales"])
            note(
                "OPM_MISMATCH",
                x,
                f"source OPM {x['opm_percentage']} vs computed {calc:.1f}; computed used",
            )
        de = r.debt_to_equity(x["borrowings"], x["equity_capital"], x["reserves"])
        icr = r.interest_coverage(
            x["operating_profit"], x["other_income"], x["interest"]
        )
        fcf = ck.free_cash_flow(x["operating_activity"], x["investing_activity"])
        pat_ratio = ck.cfo_pat_ratio(x["operating_activity"], x["net_profit"])
        intensity = ck.capex_intensity(x["investing_activity"], x["sales"])
        s1, s2, s3, label = ck.capital_allocation(
            x["operating_activity"],
            x["investing_activity"],
            x["financing_activity"],
            pat_ratio,
        )
        cap.append(
            {
                "company_id": x["company_id"],
                "year": x["year"],
                "cfo_sign": s1,
                "cfi_sign": s2,
                "cff_sign": s3,
                "pattern_label": label,
            }
        )
        rows.append(
            {
                "company_id": x["company_id"],
                "year": x["year"],
                "broad_sector": x["broad_sector"],
                "net_profit_margin_pct": r.net_profit_margin(
                    x["net_profit"], x["sales"]
                ),
                "operating_profit_margin_pct": r.operating_profit_margin(
                    x["operating_profit"], x["sales"]
                ),
                "return_on_equity_pct": r.roe(
                    x["net_profit"], x["equity_capital"], x["reserves"]
                ),
                "roce_pct": r.roce(
                    x["operating_profit"],
                    x["depreciation"],
                    x["equity_capital"],
                    x["reserves"],
                    x["borrowings"],
                ),
                "roa_pct": r.roa(x["net_profit"], x["total_assets"]),
                "debt_to_equity": de,
                "high_leverage_flag": r.high_leverage_flag(de, x["broad_sector"]),
                "interest_coverage": icr,
                "icr_label": r.icr_label(x["interest"]),
                "icr_warning": r.icr_warning(icr),
                "net_debt_cr": r.net_debt(x["borrowings"], x["investments"]),
                "asset_turnover": r.asset_turnover(x["sales"], x["total_assets"]),
                "free_cash_flow_cr": fcf,
                "capex_cr": ck.capex(x["investing_activity"]),
                "earnings_per_share": r.num(x["eps"]),
                "book_value_per_share": r.book_value_per_share(
                    x["equity_capital"], x["reserves"], x["face_value"]
                ),
                "dividend_payout_ratio_pct": r.num(x["dividend_payout"]),
                "total_debt_cr": r.num(x["borrowings"]),
                "cash_from_operations_cr": r.num(x["operating_activity"]),
                "cfo_pat_ratio": pat_ratio,
                "capex_intensity_pct": intensity,
                "capex_intensity_label": ck.capex_label(intensity),
                "fcf_conversion_pct": ck.fcf_conversion(fcf, x["operating_profit"]),
                "fcf_margin_pct": r.div(fcf, x["sales"], pct=True),
                "_sales": r.num(x["sales"]),
                "_pat": r.num(x["net_profit"]),
                "_eps": r.num(x["eps"]),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(cap)


def _score(s, higher_better=True):
    """Winsorise at P10/P90 and scale 0-100."""
    lo, hi = s.quantile(0.10), s.quantile(0.90)
    if pd.isna(lo) or hi == lo:
        return pd.Series(float("nan"), index=s.index)
    z = (s.clip(lo, hi) - lo) / (hi - lo) * 100
    return z if higher_better else 100 - z


def add_composite(out):
    """0.30 ROE + 0.25 FCF margin + 0.25 ROCE + 0.20 D/E score (Financials D/E = 50)."""
    by_year = out["year"]
    roe_s = out["return_on_equity_pct"].groupby(by_year).transform(_score)
    roce_s = out["roce_pct"].groupby(by_year).transform(_score)
    fcf_s = out["fcf_margin_pct"].groupby(by_year).transform(_score)
    nf = out["broad_sector"] != "Financials"
    de_s = (
        out["debt_to_equity"]
        .where(nf)
        .groupby(by_year)
        .transform(lambda s: _score(s, False))
    )
    de_s = de_s.where(nf, 50.0).where(out["debt_to_equity"].notna())
    out["composite_quality_score"] = (
        0.30 * roe_s + 0.25 * fcf_s + 0.25 * roce_s + 0.20 * de_s
    ).round(1)
    return out


def log_cagr_flags(out, log):
    """Log every non-INSUFFICIENT CAGR flag; summarise INSUFFICIENT counts."""
    for col in [c for c in out.columns if "_cagr_" in c and c.endswith("_flag")]:
        flags = out[col].dropna()
        for idx, flag in flags[flags != "INSUFFICIENT"].items():
            log.append(
                f"CAGR_{flag} | {out.at[idx, 'company_id']} | {out.at[idx, 'year']} | {col[:-5]}"
            )
        log.append(
            f"SUMMARY | ALL | - | {col[:-5]}: {(flags == 'INSUFFICIENT').sum()} rows INSUFFICIENT"
        )


def _categorise(computed, source):
    if pd.isna(source) or (abs(source) < 2 and abs(computed) > 10):
        return (
            "DATA_SOURCE_ISSUE",
            "source missing/implausible; use ratio-engine value, source for display only",
        )
    if abs(computed - source) <= 0.25 * abs(source):
        return (
            "VERSION_DIFFERENCE",
            "within 25% of source; likely different period or capital definition",
        )
    return "FORMULA_DISCREPANCY", "large unexplained gap; review inputs and formula"


def cross_check(out, comp, log):
    """Compare latest computed ROE/ROCE with companies.xlsx values; log gaps > 5 points."""
    src = comp.set_index("company_id")
    for col, scol, tag in (
        ("return_on_equity_pct", "roe_percentage", "ROE"),
        ("roce_pct", "roce_percentage", "ROCE"),
    ):
        for x in (
            out.dropna(subset=[col]).groupby("company_id").tail(1).to_dict("records")
        ):
            computed, source = x[col], src.at[x["company_id"], scol]
            if pd.isna(source) or abs(computed - source) > 5:
                cat, why = _categorise(computed, source)
                log.append(
                    f"{tag}_ANOMALY | {x['company_id']} | {x['year']} | computed={computed:.2f} "
                    f"source={source} category={cat} | {why}"
                )
    last = out.dropna(subset=["roce_pct"]).groupby("company_id").tail(1)
    notes = last[last["broad_sector"] == "Financials"][
        ["company_id", "year", "roce_pct", "roce_vs_sector_median"]
    ]
    notes.to_csv(OUT / "sector_roce_notes.csv", index=False)


def main():
    """Compute all KPIs and write outputs."""
    logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
    log, OUT_DIR = [], OUT
    OUT_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    base = (
        drop_partial_periods(load_base(conn), log)
        .sort_values(["company_id", "year"])
        .reset_index(drop=True)
    )
    out, cap = compute(base, log)
    for prefix, col in (("revenue", "_sales"), ("pat", "_pat"), ("eps", "_eps")):
        add_cagr(out, col, prefix)
    out = out.drop(columns=["_sales", "_pat", "_eps"])
    out["cfo_pat_5yr_avg"] = out.groupby("company_id")["cfo_pat_ratio"].transform(
        lambda s: s.rolling(5, min_periods=3).mean()
    )
    out["cfo_quality_label"] = out["cfo_pat_5yr_avg"].map(ck.cfo_quality_label)
    out["roce_vs_sector_median"] = out["roce_pct"] - out.groupby(
        ["broad_sector", "year"]
    )["roce_pct"].transform("median")
    out = add_composite(out)
    log_cagr_flags(out, log)
    cross_check(
        out,
        pd.read_sql(
            "SELECT id AS company_id, roe_percentage, roce_percentage FROM companies",
            conn,
        ),
        log,
    )

    out.to_sql("financial_ratios", conn, if_exists="replace", index=False)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_fr ON financial_ratios(company_id, year)"
    )
    cap.to_sql("capital_allocation", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    cap.to_csv(OUT_DIR / "capital_allocation.csv", index=False)
    (OUT_DIR / "ratio_edge_cases.log").write_text("\n".join(log), encoding="utf-8")

    print(
        f"financial_ratios rows: {len(out)} | companies: {out['company_id'].nunique()}"
    )
    print("all-null columns:", [c for c in out.columns if out[c].isna().all()])
    print(out[REQUIRED].notna().sum().to_string())
    print(pd.Series([line.split(" | ")[0] for line in log]).value_counts().to_string())
    late = out[out["year"] == "2024-03"]
    n = ((late["return_on_equity_pct"] > 15) & (late["debt_to_equity"] < 1)).sum()
    print("Screener preview (ROE>15, D/E<1, FY2024-03):", n)


if __name__ == "__main__":
    main()
