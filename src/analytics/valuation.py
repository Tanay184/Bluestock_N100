"""Valuation module: FCF yield, sector-relative P/E flags, valuation_summary.xlsx."""

import sqlite3

import pandas as pd

from src.analytics.screener import build_snapshot
from src.etl.loader import DB_PATH, OUT

COLS = [
    "company_id",
    "company_name",
    "sector",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "fcf_yield_pct",
    "median_pe_5yr",
    "sector_median_pe",
    "pe_vs_sector_median_pct",
    "flag",
    "market_cap_crore",
    "div_yield",
]


def flag_pe(pe, sector_median) -> str:
    """Caution if P/E > 1.5x sector median, Discount if < 0.7x, else Fair; N/A if unavailable."""
    if pd.isna(pe) or pd.isna(sector_median) or pe <= 0 or sector_median <= 0:
        return "N/A"
    if pe > sector_median * 1.5:
        return "Caution"
    return "Discount" if pe < sector_median * 0.7 else "Fair"


def build_valuation(conn: sqlite3.Connection) -> pd.DataFrame:
    """Latest valuation multiples, FCF yield, 5yr median P/E and sector-relative flag."""
    snap = build_snapshot(conn)
    mc = pd.read_sql("SELECT company_id, year, pe_ratio FROM market_cap", conn)
    last5 = mc[mc["year"] >= mc["year"].max() - 4]
    med5 = last5.groupby("company_id")["pe_ratio"].median().rename("median_pe_5yr")
    df = snap.merge(med5, on="company_id", how="left")
    df["sector_median_pe"] = df.groupby("broad_sector")["pe"].transform("median")
    df["pe_vs_sector_median_pct"] = (df["pe"] / df["sector_median_pe"] - 1) * 100
    df["flag"] = [flag_pe(a, b) for a, b in zip(df["pe"], df["sector_median_pe"])]
    df = df.rename(
        columns={
            "broad_sector": "sector",
            "pe": "pe_ratio",
            "pb": "pb_ratio",
            "fcf_yield": "fcf_yield_pct",
        }
    )
    return df[COLS].round(2)


def main() -> None:
    """Write valuation_summary.xlsx and valuation_flags.csv."""
    conn = sqlite3.connect(DB_PATH)
    val = build_valuation(conn)
    conn.close()
    OUT.mkdir(exist_ok=True)
    val.to_excel(OUT / "valuation_summary.xlsx", index=False)
    val[val["flag"].isin(["Caution", "Discount"])].to_csv(
        OUT / "valuation_flags.csv", index=False
    )
    print("rows:", len(val), "| nulls in P/E:", int(val["pe_ratio"].isna().sum()))
    print(val["flag"].value_counts().to_string())


if __name__ == "__main__":
    main()
