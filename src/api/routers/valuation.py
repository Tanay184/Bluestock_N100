"""Valuation (market cap) endpoint."""

import sqlite3

from fastapi import APIRouter

from src.api.deps import CONN, require_company, rows

router = APIRouter(tags=["valuation"])


@router.get("/market-cap/{ticker}")
def market_cap(ticker: str, conn: sqlite3.Connection = CONN) -> dict:
    """Historical valuation multiples (P/E, P/B, EV/EBITDA, dividend yield). Source data is simulated."""
    company = require_company(conn, ticker)
    history = rows(
        conn,
        "SELECT year, market_cap_crore, enterprise_value_crore, pe_ratio, pb_ratio, ev_ebitda, "
        "dividend_yield_pct FROM market_cap WHERE company_id = ? ORDER BY year",
        (company["id"],),
    )
    return {"company_id": company["id"], "simulated": True, "history": history}
