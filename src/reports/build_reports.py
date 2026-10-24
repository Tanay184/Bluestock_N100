"""Batch report generation: tearsheets, sector reports and the portfolio summary (Days 34-35).

Usage:
    python -m src.reports.build_reports --sample      # 5 sample tearsheets only
    python -m src.reports.build_reports               # everything
"""

import sys
import time

import pandas as pd

from src.etl.loader import OUT, ROOT
from src.reports.common import Data
from src.reports.portfolio_report import build_portfolio
from src.reports.sector_report import build_sector_report, file_name
from src.reports.tearsheet import build_tearsheet

MIN_YEARS = 3
MIN_KB = 30
SAMPLE = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]
TEAR_DIR = ROOT / "reports" / "tearsheets"
SECTOR_DIR = ROOT / "reports" / "sector"
PORT_DIR = ROOT / "reports" / "portfolio"


def tearsheets(d: Data, tickers: list[str]) -> tuple[list[dict], list[dict]]:
    """Build tearsheets; return (skipped companies, problems such as wrong page count or small file)."""
    TEAR_DIR.mkdir(parents=True, exist_ok=True)
    skipped, problems = [], []
    for t in tickers:
        years = d.years(t)
        if years < MIN_YEARS:
            skipped.append(
                {
                    "company_id": t,
                    "years_of_data": years,
                    "reason": f"fewer than {MIN_YEARS} years of data",
                }
            )
            continue
        path = TEAR_DIR / f"{t}_tearsheet.pdf"
        pages = build_tearsheet(d, t, path)
        kb = path.stat().st_size / 1024
        if pages != 2 or kb < MIN_KB:
            problems.append({"company_id": t, "pages": pages, "size_kb": round(kb, 1)})
    return skipped, problems


def main() -> None:
    """Generate the reports and print a verification summary."""
    sample = "--sample" in sys.argv
    t0 = time.perf_counter()
    d = Data.load()
    tickers = [t for t in SAMPLE if t in d.tickers()] if sample else d.tickers()
    skipped, problems = tearsheets(d, tickers)
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(skipped, columns=["company_id", "years_of_data", "reason"]).to_csv(
        OUT / "skipped_tearsheets.csv", index=False
    )
    made = sorted(TEAR_DIR.glob("*_tearsheet.pdf"))
    print(
        f"tearsheets built: {len(tickers) - len(skipped)} | skipped (<{MIN_YEARS} yrs): {[s['company_id'] for s in skipped]}"
    )
    print(
        f"tearsheet files on disk: {len(made)} | smallest: {min((p.stat().st_size for p in made), default=0) / 1024:.0f} KB"
    )
    print("problems (not 2 pages or under 30 KB):", problems or "none")
    if sample:
        print(
            f"sample done in {time.perf_counter() - t0:.0f}s: open reports/tearsheets/*.pdf and check them visually"
        )
        return
    SECTOR_DIR.mkdir(parents=True, exist_ok=True)
    sectors = sorted(d.sectors["broad_sector"].dropna().unique())
    for s in sectors:
        build_sector_report(d, s, SECTOR_DIR / file_name(s))
    PORT_DIR.mkdir(parents=True, exist_ok=True)
    pages = build_portfolio(d, PORT_DIR / "portfolio_summary.pdf")
    print(
        f"sector reports: {len(list(SECTOR_DIR.glob('*.pdf')))} | portfolio summary pages: {pages}"
    )
    print(f"total time: {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
