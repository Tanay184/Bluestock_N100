"""Load the 12 Excel sources into nifty100.db with validation and audit."""

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.etl.normaliser import PARSE_ERROR, normalize_ticker, normalize_year
from src.etl.validator import YEAR_TABLES, validate

load_dotenv()
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / os.getenv("DB_PATH", "data/nifty100.db")
OUT = ROOT / "output"
CORE = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
]
SUPPORT = ["sectors", "stock_prices", "market_cap", "financial_ratios", "peer_groups"]
LOAD_ORDER = [
    "companies",
    "sectors",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "stock_prices",
    "market_cap",
    "financial_ratios",
    "peer_groups",
]
KEYS = {
    "profitandloss": ["company_id", "year"],
    "balancesheet": ["company_id", "year"],
    "cashflow": ["company_id", "year"],
    "financial_ratios": ["company_id", "year"],
    "market_cap": ["company_id", "year"],
    "stock_prices": ["company_id", "date"],
}


def read_all() -> dict[str, pd.DataFrame]:
    """Read core files (header=1) and supplementary files (header=0)."""
    t = {n: pd.read_excel(ROOT / "data/raw" / f"{n}.xlsx", header=1) for n in CORE}
    t |= {
        n: pd.read_excel(ROOT / "data/supporting" / f"{n}.xlsx", header=0)
        for n in SUPPORT
    }
    return t


def normalise(t: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Normalise tickers, years, text and numeric types in place."""
    c = t["companies"]
    c["id"] = c["id"].map(normalize_ticker)
    c["company_name"] = (
        c["company_name"].str.replace(r"\s+", " ", regex=True).str.strip()
    )
    for col in ("face_value", "book_value", "roce_percentage", "roe_percentage"):
        c[col] = pd.to_numeric(c[col], errors="coerce")
    for n, d in t.items():
        if n != "companies":
            d["company_id"] = d["company_id"].map(normalize_ticker)
    for n in YEAR_TABLES:
        t[n]["year"] = t[n]["year"].map(normalize_year)
    skip = {"id", "company_id", "year", "date"}
    for n in (
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "market_cap",
        "stock_prices",
    ):
        for col in t[n].columns:
            if col not in skip:
                t[n][col] = pd.to_numeric(t[n][col], errors="coerce")
    t["documents"] = t["documents"].rename(columns={"Year": "year"})
    t["documents"]["year"] = pd.to_numeric(t["documents"]["year"], errors="coerce")
    t["stock_prices"]["date"] = pd.to_datetime(t["stock_prices"]["date"]).dt.strftime(
        "%Y-%m-%d"
    )
    return t


def clean(t: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Apply DQ actions: halt on DQ-01, drop bad years/orphans/duplicates, coerce fixes."""
    comp = t["companies"]
    if comp["id"].isna().any() or comp["id"].duplicated().any():
        raise ValueError("DQ-01 failed: missing or duplicate company ids")
    ids = set(comp["id"])
    for n, d in t.items():
        if n == "companies":
            continue
        d = d[d["company_id"].isin(ids)]
        if n in YEAR_TABLES:
            d = d[d["year"] != PARSE_ERROR]
        if n == "documents":
            d = d.dropna(subset=["year"]).astype({"year": int})
        if n in KEYS:
            d = d.drop_duplicates(KEYS[n], keep="last")
        t[n] = d.copy()
    bs, cf = t["balancesheet"], t["cashflow"]
    bs.loc[bs["fixed_assets"] < 0, "fixed_assets"] = 0
    calc = (
        cf["operating_activity"] + cf["investing_activity"] + cf["financing_activity"]
    )
    bad = (cf["net_cash_flow"] - calc).abs() > 10
    cf.loc[bad, "net_cash_flow"] = calc[bad]
    return t


def build_db(t: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Create the schema and load all tables in FK order; return runtimes."""
    DB_PATH.parent.mkdir(exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((ROOT / "db" / "schema.sql").read_text())
    times = {}
    for n in LOAD_ORDER:
        t0 = time.time()
        t[n].to_sql(n, conn, if_exists="append", index=False)
        times[n] = round(time.time() - t0, 3)
    conn.commit()
    conn.close()
    return times


def main() -> None:
    """Run the full ETL: read, normalise, validate, clean, load, audit."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s"
    )
    raw = read_all()
    rows_in = {n: len(d) for n, d in raw.items()}
    t = normalise(raw)
    failures = validate(t, check_urls=os.getenv("CHECK_URLS") == "1")
    t = clean(t)
    times = build_db(t)
    OUT.mkdir(exist_ok=True)
    failures.to_csv(OUT / "validation_failures.csv", index=False)
    crit = failures[failures.severity == "CRITICAL"].groupby("table").size()
    conn = sqlite3.connect(DB_PATH)
    audit = []
    for n in LOAD_ORDER:
        out = conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]
        audit.append(
            {
                "table": n,
                "rows_in": rows_in[n],
                "rows_out": out,
                "rejected": rows_in[n] - out,
                "critical_failures": int(crit.get(n, 0)),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "runtime_s": times[n],
            }
        )
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()
    pd.DataFrame(audit).to_csv(OUT / "load_audit.csv", index=False)
    logger.info("done. FK violations: %d", len(fk))


if __name__ == "__main__":
    main()
