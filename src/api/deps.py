"""Shared API helpers: DB connection, validation, JSON cleaning and cached snapshots."""

import math
import re
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import closing

import numpy as np
import pandas as pd
from fastapi import Depends, HTTPException

from src.analytics.clustering import latest_kpis
from src.analytics.screener import build_snapshot
from src.etl.loader import DB_PATH, ROOT

VERSION = "1.0.0"
START_TIME = time.time()
TEARSHEET_DIR = ROOT / "reports" / "tearsheets"
YEAR_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
SECTOR_ALIASES = {"it": "Information Technology"}
INDEXES = [
    ("financial_ratios", "company_id, year"),
    ("profitandloss", "company_id, year"),
    ("balancesheet", "company_id, year"),
    ("cashflow", "company_id, year"),
    ("stock_prices", "company_id, date"),
    ("market_cap", "company_id, year"),
    ("documents", "company_id, year"),
    ("capital_allocation", "company_id, year"),
    ("peer_percentiles", "peer_group"),
    ("peer_groups", "peer_group_name"),
    ("pros_cons_generated", "company_id"),
    ("sectors", "company_id"),
]
_cache: dict[str, dict] = {
    "snapshot": {"mtime": None, "df": None},
    "kpis": {"mtime": None, "df": None},
}
_lock = threading.Lock()


def get_conn() -> Iterator[sqlite3.Connection]:
    """Per-request SQLite connection returning rows as mappings."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


CONN = Depends(
    get_conn
)  # shared dependency object, reused as the default of every `conn` parameter


def create_indexes() -> int:
    """Create (idempotent) indexes on company_id / year columns; returns how many were requested."""
    done = 0
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table, cols in INDEXES:
                if table in tables:
                    name = f"idx_{table}_{cols.replace(', ', '_')}"
                    conn.execute(
                        f'CREATE INDEX IF NOT EXISTS {name} ON "{table}" ({cols})'
                    )
                    done += 1
            conn.commit()
    except sqlite3.Error:
        pass
    return done


def rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    """Run a parameterised query and return JSON-safe dictionaries."""
    return [clean_dict(dict(r)) for r in conn.execute(sql, params).fetchall()]


def clean_value(v):
    """Convert NaN/inf and numpy scalars to JSON-safe Python values."""
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def clean_dict(d: dict) -> dict:
    """Apply clean_value to every value in a dictionary."""
    return {k: clean_value(v) for k, v in d.items()}


def df_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame to a list of JSON-safe dictionaries."""
    return [
        clean_dict(r) for r in df.replace([np.inf, -np.inf], np.nan).to_dict("records")
    ]


def normalise_ticker(ticker: str) -> str:
    """Strip and upper-case a ticker."""
    return ticker.strip().upper()


def require_company(conn: sqlite3.Connection, ticker: str) -> dict:
    """Return the companies row for a ticker or raise HTTP 404."""
    t = normalise_ticker(ticker)
    found = rows(conn, "SELECT * FROM companies WHERE id = ?", (t,))
    if not found:
        raise HTTPException(status_code=404, detail=f"Ticker '{t}' not found")
    return found[0]


def validate_year(name: str, value: str | None) -> str | None:
    """Check a YYYY-MM parameter; raise HTTP 400 if malformed."""
    if value is not None and not YEAR_RE.match(value):
        raise HTTPException(
            status_code=400, detail=f"'{name}' must be in YYYY-MM format, got '{value}'"
        )
    return value


def parse_float(name: str, value: str | None) -> float | None:
    """Parse a numeric query parameter; raise HTTP 400 if it is not a finite number."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"'{name}' must be a number, got '{value}'"
        ) from None
    if math.isnan(f) or math.isinf(f):
        raise HTTPException(status_code=400, detail=f"'{name}' must be a finite number")
    return f


def resolve_sector(conn: sqlite3.Connection, name: str) -> str | None:
    """Match a sector name case-insensitively (spaces/underscores/hyphens equivalent; 'IT' alias)."""
    key = re.sub(r"[\s_\-]+", " ", name).strip().lower()
    key = SECTOR_ALIASES.get(key, key).lower()
    for (s,) in conn.execute(
        "SELECT DISTINCT broad_sector FROM sectors WHERE broad_sector IS NOT NULL"
    ):
        if re.sub(r"[\s_\-]+", " ", s).strip().lower() == key:
            return s
    return None


def _cached(slot: str, builder) -> pd.DataFrame:
    mtime = DB_PATH.stat().st_mtime_ns
    with _lock:
        entry = _cache[slot]
        if entry["mtime"] != mtime:
            with closing(sqlite3.connect(DB_PATH)) as conn:
                entry["df"] = builder(conn)
            entry["mtime"] = mtime
        return entry["df"].copy()


def get_snapshot() -> pd.DataFrame:
    """Latest-year metric snapshot (shared with the dashboard), cached until the database changes."""
    return _cached("snapshot", build_snapshot)


def get_kpis() -> pd.DataFrame:
    """Latest-year KPI table used for clustering and portfolio statistics, cached."""
    return _cached("kpis", latest_kpis)
