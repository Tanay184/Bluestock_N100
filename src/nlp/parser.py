"""Parse the free-text growth fields of the analysis table into numbers (Day 29)."""

import re
import sqlite3
from contextlib import closing

import pandas as pd

from src.etl.loader import DB_PATH, OUT

# Spec pattern (\d+)\s*Years?:?\s*([\d.]+)% with an optional minus sign for negative growth.
PATTERN = re.compile(r"(\d+)\s*Years?:?\s*(-?[\d.]+)\s*%", re.IGNORECASE)
FIELDS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]
# analysis field -> prefix of the Ratio Engine CAGR columns it can be checked against
COMPARABLE = {"compounded_sales_growth": "revenue", "compounded_profit_growth": "pat"}
TOLERANCE_PP = 5.0


def parse_text(text) -> tuple[int, float] | None:
    """Return (period_years, value_pct) from text like '10 Years: 21%', else None."""
    if not isinstance(text, str):
        return None
    m = PATTERN.search(text)
    if not m:
        return None
    try:
        return int(m[1]), float(m[2])
    except ValueError:
        return None


def parse_table(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse all target fields; return (parsed rows, failures for non-matching text)."""
    parsed, failures = [], []
    for row in df.to_dict("records"):
        for field in FIELDS:
            raw = row.get(field)
            if raw is None or (not isinstance(raw, str) and pd.isna(raw)):
                continue
            res = parse_text(raw)
            if res is None:
                failures.append(
                    {"company_id": row["company_id"], "field": field, "raw_text": raw}
                )
            else:
                parsed.append(
                    {
                        "company_id": row["company_id"],
                        "metric_type": field,
                        "period_years": res[0],
                        "value_pct": res[1],
                    }
                )
    cols_p = ["company_id", "metric_type", "period_years", "value_pct"]
    cols_f = ["company_id", "field", "raw_text"]
    return pd.DataFrame(parsed, columns=cols_p), pd.DataFrame(failures, columns=cols_f)


def cross_validate(parsed: pd.DataFrame, ratios: pd.DataFrame) -> pd.DataFrame:
    """Compare parsed CAGRs with the Ratio Engine's latest-year CAGRs; flag gaps > 5 points."""
    latest = (
        ratios.sort_values("year").groupby("company_id").tail(1).set_index("company_id")
    )
    rows = []
    for p in parsed.to_dict("records"):
        prefix = COMPARABLE.get(p["metric_type"])
        computed, status = None, "NOT_COMPARABLE"
        if prefix:
            col = f"{prefix}_cagr_{p['period_years']}yr"
            if col in latest.columns and p["company_id"] in latest.index:
                computed = latest.at[p["company_id"], col]
            if computed is None or pd.isna(computed):
                computed, status = None, "NO_COMPUTED_VALUE"
            else:
                status = (
                    "DIVERGENT"
                    if abs(p["value_pct"] - computed) > TOLERANCE_PP
                    else "OK"
                )
        diff = None if computed is None else round(abs(p["value_pct"] - computed), 2)
        rows.append(
            {
                "company_id": p["company_id"],
                "metric_type": p["metric_type"],
                "period_years": p["period_years"],
                "parsed_pct": p["value_pct"],
                "computed_pct": None if computed is None else round(computed, 2),
                "diff_pp": diff,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    """Write analysis_parsed.csv, parse_failures.csv and cross_validation.csv."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        analysis = pd.read_sql("SELECT * FROM analysis", conn)
        ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    parsed, failures = parse_table(analysis)
    cross = cross_validate(parsed, ratios)
    OUT.mkdir(exist_ok=True)
    parsed.to_csv(OUT / "analysis_parsed.csv", index=False)
    failures.to_csv(OUT / "parse_failures.csv", index=False)
    cross.to_csv(OUT / "cross_validation.csv", index=False)
    print(
        f"analysis rows: {len(analysis)} | parsed values: {len(parsed)} | parse failures: {len(failures)}"
    )
    print(
        "cross-validation status:",
        cross["status"].value_counts().to_dict() if len(cross) else {},
    )


if __name__ == "__main__":
    main()
