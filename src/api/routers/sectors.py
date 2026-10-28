"""Sector endpoints."""

import sqlite3

from fastapi import APIRouter, HTTPException

from src.api.deps import CONN, df_records, get_snapshot, resolve_sector

router = APIRouter(prefix="/sectors", tags=["sectors"])
COMPANY_FIELDS = [
    "company_id",
    "company_name",
    "sub_sector",
    "screen_score",
    "roe",
    "roce",
    "npm",
    "opm",
    "de",
    "fcf",
    "rev_cagr_5yr",
    "pat_cagr_5yr",
    "pe",
    "pb",
]


@router.get("")
def list_sectors() -> list[dict]:
    """All sectors with company count and median ROE, P/E and debt/equity (latest year)."""
    df = get_snapshot()
    g = df.groupby("broad_sector")
    out = g.agg(
        company_count=("company_id", "count"),
        median_roe=("roe", "median"),
        median_pe=("pe", "median"),
        median_de=("de", "median"),
    ).round(2)
    return df_records(out.reset_index().rename(columns={"broad_sector": "sector"}))


@router.get("/{sector}/companies")
def sector_companies(sector: str, conn: sqlite3.Connection = CONN) -> list[dict]:
    """Every company in a sector with its latest-year KPIs."""
    canonical = resolve_sector(conn, sector)
    if canonical is None:
        raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found")
    df = get_snapshot()
    df = df[df["broad_sector"] == canonical].sort_values(
        "screen_score", ascending=False
    )
    return [{"sector": canonical, **r} for r in df_records(df[COMPANY_FIELDS])]
