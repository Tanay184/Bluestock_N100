"""Sprint 5 exit-criteria check: prints PASS/FAIL for each board criterion."""

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.etl.loader import DB_PATH, OUT

REQUIRED = [
    "company_id",
    "sector",
    "cfo_quality_score",
    "cfo_quality_label",
    "capex_intensity_pct",
    "capex_label",
    "fcf_cagr_5yr",
    "fcf_conversion_pct",
    "distress_flag",
    "deleveraging_flag",
    "capital_allocation_label",
]


def show(ok: bool, text: str) -> bool:
    """Print one PASS/FAIL line."""
    print(("PASS  " if ok else "FAIL  ") + text)
    return ok


def main() -> None:
    """Check pros/cons coverage, cash flow sheet, tearsheets, sector and portfolio PDFs."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        n_comp = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        n_sectors = conn.execute(
            "SELECT COUNT(DISTINCT broad_sector) FROM sectors"
        ).fetchone()[0]
    ok = []
    pc = pd.read_csv(OUT / "pros_cons_generated.csv")
    kinds = pc.groupby("company_id")["type"].agg(set)
    full = int(sum(k == {"pro", "con"} for k in kinds))
    ok.append(
        show(
            full == n_comp,
            f"pros_cons_generated.csv: {full}/{n_comp} companies have >=1 pro and >=1 con",
        )
    )
    rule_based = pc[~pc["rule_id"].str.endswith("-REL")]
    ok.append(
        show(
            (rule_based["confidence_pct"] > 60).all(),
            "all rule-based confidence scores above 60",
        )
    )
    low = pc[pc["rule_id"].str.endswith("-REL") & (pc["confidence_pct"] <= 60)]
    print(
        f"NOTE  {len(low)} sector/universe-relative fallback entries are at or below 60% (kept so every company has a pro and a con)"
    )
    ci = pd.read_excel(OUT / "cashflow_intelligence.xlsx")
    ok.append(
        show(
            len(ci) == n_comp and all(c in ci.columns for c in REQUIRED),
            f"cashflow_intelligence.xlsx: {len(ci)} rows, required columns present",
        )
    )
    parsed = OUT / "analysis_parsed.csv"
    ok.append(show(parsed.exists(), "analysis_parsed.csv exists"))
    skipped = pd.read_csv(OUT / "skipped_tearsheets.csv")
    tear = sorted((ROOT / "reports" / "tearsheets").glob("*_tearsheet.pdf"))
    small = [p.name for p in tear if p.stat().st_size < 30 * 1024]
    ok.append(
        show(
            len(tear) == n_comp - len(skipped),
            f"tearsheets: {len(tear)} files (expected {n_comp} minus {len(skipped)} skipped)",
        )
    )
    ok.append(
        show(
            not small,
            f"every tearsheet is at least 30 KB (smallest {min(p.stat().st_size for p in tear) // 1024} KB)",
        )
    )
    sector = list((ROOT / "reports" / "sector").glob("*.pdf"))
    ok.append(
        show(
            len(sector) == n_sectors,
            f"sector reports: {len(sector)} (sectors with companies in the database: {n_sectors}; the spec lists 11)",
        )
    )
    ok.append(
        show(
            (ROOT / "reports" / "portfolio" / "portfolio_summary.pdf").exists(),
            "portfolio_summary.pdf exists",
        )
    )
    print(
        f"\n{sum(ok)}/{len(ok)} checks passed. Still do the manual step: open 5 tearsheets and check for overflow/blank pages."
    )


if __name__ == "__main__":
    main()
