"""Cash flow intelligence: CFO quality, CapEx intensity, FCF CAGR, distress and deleveraging (Days 31-32)."""

import sqlite3
from contextlib import closing

import pandas as pd
from openpyxl.styles import Font

from src.analytics.cagr import cagr
from src.etl.loader import DB_PATH, OUT

COLS = [
    "company_id",
    "company_name",
    "sector",
    "year",
    "cfo_quality_score",
    "cfo_quality_label",
    "capex_intensity_pct",
    "capex_label",
    "fcf_cagr_5yr",
    "fcf_cagr_5yr_flag",
    "fcf_conversion_pct",
    "distress_flag",
    "deleveraging_flag",
    "capital_allocation_label",
]


def is_distress(cfo, cff) -> bool:
    """CFO < 0 and CFF > 0: operations burn cash while financing raises it."""
    return pd.notna(cfo) and pd.notna(cff) and cfo < 0 and cff > 0


def is_deleveraging(cff, debt_now, debt_prev) -> bool:
    """CFF < 0 and borrowings fell year over year."""
    if any(pd.isna(x) for x in (cff, debt_now, debt_prev)):
        return False
    return cff < 0 and debt_now < debt_prev


def build(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (cashflow_intelligence rows, distress alert rows), one row per company."""
    fr = pd.read_sql("SELECT * FROM financial_ratios", conn).sort_values(
        ["company_id", "year"]
    )
    cf = pd.read_sql(
        "SELECT company_id, year, operating_activity, financing_activity FROM cashflow",
        conn,
    )
    pl = pd.read_sql("SELECT company_id, year, net_profit FROM profitandloss", conn)
    comp = pd.read_sql("SELECT id AS company_id, company_name FROM companies", conn)
    sec = pd.read_sql("SELECT company_id, broad_sector AS sector FROM sectors", conn)
    cap = pd.read_sql(
        "SELECT company_id, year, pattern_label FROM capital_allocation", conn
    )
    df = fr.merge(cf, on=["company_id", "year"], how="left").merge(
        pl, on=["company_id", "year"], how="left"
    )
    rows, alerts = [], []
    for cid, g in df.groupby("company_id"):
        g = g.reset_index(drop=True)
        last = g.iloc[-1]
        prev_debt = g["total_debt_cr"].iloc[-2] if len(g) > 1 else None
        fcf = dict(zip(g["year"], g["free_cash_flow_cr"], strict=True))
        start_year = f"{int(last['year'][:4]) - 5}-{last['year'][5:]}"
        growth, flag = cagr(fcf.get(start_year), last["free_cash_flow_cr"], 5)
        distress = is_distress(last["operating_activity"], last["financing_activity"])
        rows.append(
            {
                "company_id": cid,
                "year": last["year"],
                "cfo_quality_score": last["cfo_pat_5yr_avg"],
                "cfo_quality_label": last["cfo_quality_label"],
                "capex_intensity_pct": last["capex_intensity_pct"],
                "capex_label": last["capex_intensity_label"],
                "fcf_cagr_5yr": growth,
                "fcf_cagr_5yr_flag": flag,
                "fcf_conversion_pct": last["fcf_conversion_pct"],
                "distress_flag": bool(distress),
                "deleveraging_flag": bool(
                    is_deleveraging(
                        last["financing_activity"], last["total_debt_cr"], prev_debt
                    )
                ),
            }
        )
        if distress:
            alerts.append(
                {
                    "company_id": cid,
                    "year": last["year"],
                    "cfo_cr": last["operating_activity"],
                    "cff_cr": last["financing_activity"],
                    "net_profit_cr": last["net_profit"],
                }
            )
    out = (
        pd.DataFrame(rows)
        .merge(comp, on="company_id", how="left")
        .merge(sec, on="company_id", how="left")
    )
    latest_cap = (
        cap.sort_values("year")
        .groupby("company_id")
        .tail(1)[["company_id", "pattern_label"]]
    )
    out = out.merge(
        latest_cap.rename(columns={"pattern_label": "capital_allocation_label"}),
        on="company_id",
        how="left",
    )
    out = out[COLS].round(2)
    al = pd.DataFrame(
        alerts, columns=["company_id", "year", "cfo_cr", "cff_cr", "net_profit_cr"]
    )
    al = al.merge(comp, on="company_id", how="left").merge(
        sec, on="company_id", how="left"
    )
    al = al[
        [
            "company_id",
            "company_name",
            "sector",
            "year",
            "cfo_cr",
            "cff_cr",
            "net_profit_cr",
        ]
    ]
    return out, al


def pattern_reports(
    conn: sqlite3.Connection,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Latest-year pattern distribution, year-over-year pattern changes and a completeness check."""
    cap = pd.read_sql(
        "SELECT ca.company_id, c.company_name, ca.year, ca.pattern_label FROM capital_allocation ca "
        "JOIN companies c ON c.id = ca.company_id ORDER BY ca.company_id, ca.year",
        conn,
    )
    n_ratio = pd.read_sql("SELECT COUNT(*) n FROM financial_ratios", conn)["n"].iloc[0]
    latest = cap.groupby("company_id").tail(1)
    dist = (
        latest["pattern_label"]
        .value_counts()
        .rename_axis("pattern_label")
        .reset_index(name="companies")
    )
    cap["from_pattern"] = cap.groupby("company_id")["pattern_label"].shift(1)
    cap["from_year"] = cap.groupby("company_id")["year"].shift(1)
    ch = cap[
        (cap["from_pattern"].notna())
        & (cap["from_pattern"] != cap["pattern_label"])
        & (cap["from_pattern"] != "No Data")
        & (cap["pattern_label"] != "No Data")
    ]
    ch = ch.rename(columns={"year": "to_year", "pattern_label": "to_pattern"})
    ch = ch[
        [
            "company_id",
            "company_name",
            "from_year",
            "to_year",
            "from_pattern",
            "to_pattern",
        ]
    ]
    ch = ch.sort_values(["to_year", "company_id"], ascending=[False, True])
    check = {
        "capital_allocation_rows": len(cap),
        "financial_ratios_rows": int(n_ratio),
        "companies": cap["company_id"].nunique(),
        "complete": len(cap) == n_ratio,
    }
    return dist, ch, check


def write_xlsx(df: pd.DataFrame, path) -> None:
    """Write the sheet with a bold header and readable column widths."""
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="cashflow_intelligence", index=False)
        ws = xw.sheets["cashflow_intelligence"]
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for col in ws.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(
                max(width + 2, 10), 40
            )


def main() -> None:
    """Write cashflow_intelligence.xlsx, distress_alerts.csv, pattern summary and pattern_changes.csv."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        intel, alerts = build(conn)
        dist, changes, check = pattern_reports(conn)
    OUT.mkdir(exist_ok=True)
    write_xlsx(intel, OUT / "cashflow_intelligence.xlsx")
    alerts.to_csv(OUT / "distress_alerts.csv", index=False)
    dist.to_csv(OUT / "capital_allocation_summary.csv", index=False)
    changes.to_csv(OUT / "pattern_changes.csv", index=False)
    print(
        f"cashflow_intelligence rows: {len(intel)} | distress alerts: {len(alerts)} | "
        f"deleveraging: {int(intel['deleveraging_flag'].sum())}"
    )
    print("capital allocation check:", check)
    print(
        "latest-year pattern distribution:",
        dict(zip(dist["pattern_label"], dist["companies"], strict=True)),
    )
    print(
        f"pattern changes (all years): {len(changes)} | in latest year: "
        f"{int((changes['to_year'] == changes['to_year'].max()).sum()) if len(changes) else 0}"
    )


if __name__ == "__main__":
    main()
