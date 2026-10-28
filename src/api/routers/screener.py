"""Screener endpoint: filter and rank companies by the same logic as the dashboard."""

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from src.api.deps import CONN, df_records, get_snapshot, parse_float, resolve_sector

router = APIRouter(tags=["screener"])
FILTERS = (
    {  # query parameter -> (snapshot column, comparison); thresholds are inclusive
        "min_roe": ("roe", ">="),
        "max_de": ("de", "<="),
        "min_fcf": ("fcf", ">="),
        "min_rev_cagr_5yr": ("rev_cagr_5yr", ">="),
        "min_pat_cagr_5yr": ("pat_cagr_5yr", ">="),
        "max_pe": ("pe", "<="),
    }
)
FIELDS = [
    "company_id",
    "company_name",
    "broad_sector",
    "sub_sector",
    "screen_score",
    "sector_rank",
    "roe",
    "roce",
    "npm",
    "opm",
    "de",
    "icr",
    "fcf",
    "rev_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "pe",
    "pb",
    "div_yield",
]


@router.get("/screener")
def screener(
    min_roe: str | None = Query(None, description="Minimum ROE %"),
    max_de: str | None = Query(None, description="Maximum debt/equity"),
    min_fcf: str | None = Query(None, description="Minimum free cash flow (Rs Cr)"),
    sector: str | None = Query(None, description="Broad sector name"),
    min_rev_cagr_5yr: str | None = Query(
        None, description="Minimum 5-year revenue CAGR %"
    ),
    min_pat_cagr_5yr: str | None = Query(
        None, description="Minimum 5-year profit CAGR %"
    ),
    max_pe: str | None = Query(None, description="Maximum P/E"),
    conn: sqlite3.Connection = CONN,
) -> list[dict]:
    """Companies passing every filter, ranked by composite screen score (highest first)."""
    raw = {
        "min_roe": min_roe,
        "max_de": max_de,
        "min_fcf": min_fcf,
        "min_rev_cagr_5yr": min_rev_cagr_5yr,
        "min_pat_cagr_5yr": min_pat_cagr_5yr,
        "max_pe": max_pe,
    }
    values = {name: parse_float(name, v) for name, v in raw.items()}
    df = get_snapshot()
    if sector:
        canonical = resolve_sector(conn, sector)
        if canonical is None:
            raise HTTPException(status_code=400, detail=f"Unknown sector '{sector}'")
        df = df[df["broad_sector"] == canonical]
    for name, value in values.items():
        if value is None:
            continue
        col, op = FILTERS[name]
        df = df[df[col] >= value] if op == ">=" else df[df[col] <= value]
    df = df.sort_values(["screen_score", "company_id"], ascending=[False, True])
    out = df_records(df[FIELDS])
    return [{"rank": i, **r} for i, r in enumerate(out, 1)]
