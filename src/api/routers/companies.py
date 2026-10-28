"""Company endpoints: list, profile, statement histories, ratios and tearsheet download."""

import sqlite3

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.deps import (
    CONN,
    TEARSHEET_DIR,
    normalise_ticker,
    require_company,
    resolve_sector,
    rows,
    validate_year,
)

router = APIRouter(prefix="/companies", tags=["companies"])
LATEST = "r.year = (SELECT MAX(year) FROM financial_ratios WHERE company_id = c.id)"


@router.get("")
def list_companies(
    sector: str | None = Query(None, description="Broad sector, e.g. 'Energy' or 'IT'"),
    market_cap_category: str | None = Query(
        None, description="'Large Cap' or 'Mid Cap'"
    ),
    search: str | None = Query(None, description="Partial company name or ticker"),
    conn: sqlite3.Connection = CONN,
) -> list[dict]:
    """List all companies with sector and latest ROE/ROCE; optional filters."""
    sql = (
        "SELECT c.id, c.company_name, s.broad_sector, s.sub_sector, s.market_cap_category, "
        "r.return_on_equity_pct AS roe_pct, r.roce_pct AS roce_pct FROM companies c "
        f"LEFT JOIN sectors s ON s.company_id = c.id LEFT JOIN financial_ratios r ON r.company_id = c.id AND {LATEST}"
    )
    where, params = [], []
    if sector:
        canonical = resolve_sector(conn, sector)
        where.append("s.broad_sector = ?")
        params.append(canonical or "\0no-such-sector")
    if market_cap_category:
        where.append("LOWER(s.market_cap_category) = ?")
        params.append(market_cap_category.strip().lower())
    if search:
        where.append("(LOWER(c.company_name) LIKE ? OR LOWER(c.id) LIKE ?)")
        params += [f"%{search.strip().lower()}%"] * 2
    if where:
        sql += " WHERE " + " AND ".join(where)
    return rows(conn, sql + " ORDER BY c.id", tuple(params))


@router.get("/{ticker}")
def company_profile(
    ticker: str,
    year: str | None = Query(None, description="YYYY-MM; default latest"),
    conn: sqlite3.Connection = CONN,
) -> dict:
    """Full company profile: company fields, sector data and the latest-year KPIs."""
    company = require_company(conn, ticker)
    validate_year("year", year)
    sector = rows(
        conn,
        "SELECT broad_sector, sub_sector, index_weight_pct, market_cap_category "
        "FROM sectors WHERE company_id = ?",
        (company["id"],),
    )
    if year:
        kpis = rows(
            conn,
            "SELECT * FROM financial_ratios WHERE company_id = ? AND year = ?",
            (company["id"], year),
        )
    else:
        kpis = rows(
            conn,
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1",
            (company["id"],),
        )
    return {
        **company,
        "sector": sector[0] if sector else None,
        "latest_kpis": kpis[0] if kpis else None,
    }


def history(
    conn: sqlite3.Connection,
    table: str,
    ticker: str,
    from_year: str | None,
    to_year: str | None,
) -> list[dict]:
    """Rows of a statement table for a ticker within an optional YYYY-MM range."""
    company = require_company(conn, ticker)
    validate_year("from_year", from_year)
    validate_year("to_year", to_year)
    if from_year and to_year and from_year > to_year:
        raise HTTPException(
            status_code=400, detail="'from_year' must not be after 'to_year'"
        )
    sql, params = f"SELECT * FROM {table} WHERE company_id = ?", [
        company["id"]
    ]  # table is a fixed internal name
    if from_year:
        sql, params = sql + " AND year >= ?", params + [from_year]
    if to_year:
        sql, params = sql + " AND year <= ?", params + [to_year]
    return [
        {k: v for k, v in r.items() if k != "id"}
        for r in rows(conn, sql + " ORDER BY year", tuple(params))
    ]


@router.get("/{ticker}/pl")
def profit_and_loss(
    ticker: str,
    from_year: str | None = Query(None, description="YYYY-MM"),
    to_year: str | None = Query(None, description="YYYY-MM"),
    conn: sqlite3.Connection = CONN,
) -> list[dict]:
    """Profit and loss history, oldest first."""
    return history(conn, "profitandloss", ticker, from_year, to_year)


@router.get("/{ticker}/bs")
def balance_sheet(
    ticker: str,
    from_year: str | None = Query(None, description="YYYY-MM"),
    to_year: str | None = Query(None, description="YYYY-MM"),
    conn: sqlite3.Connection = CONN,
) -> list[dict]:
    """Balance sheet history, oldest first."""
    return history(conn, "balancesheet", ticker, from_year, to_year)


@router.get("/{ticker}/cashflow")
def cash_flow(
    ticker: str,
    from_year: str | None = Query(None, description="YYYY-MM"),
    to_year: str | None = Query(None, description="YYYY-MM"),
    conn: sqlite3.Connection = CONN,
) -> list[dict]:
    """Cash flow history, oldest first."""
    return history(conn, "cashflow", ticker, from_year, to_year)


@router.get("/{ticker}/ratios")
def ratios(
    ticker: str,
    year: str | None = Query(None, description="YYYY-MM for a single year"),
    conn: sqlite3.Connection = CONN,
) -> list[dict]:
    """All computed KPIs per year (or for one year)."""
    company = require_company(conn, ticker)
    validate_year("year", year)
    sql, params = "SELECT * FROM financial_ratios WHERE company_id = ?", [company["id"]]
    if year:
        sql, params = sql + " AND year = ?", params + [year]
    out = rows(conn, sql + " ORDER BY year", tuple(params))
    if year and not out:
        raise HTTPException(
            status_code=404, detail=f"No ratios for {company['id']} in {year}"
        )
    return [{k: v for k, v in r.items() if k != "id"} for r in out]


@router.get("/{ticker}/tearsheet", response_class=FileResponse)
def tearsheet(ticker: str, conn: sqlite3.Connection = CONN) -> FileResponse:
    """Download the pre-generated two-page tearsheet PDF."""
    company = require_company(conn, ticker)
    t = normalise_ticker(company["id"])
    path = TEARSHEET_DIR / f"{t}_tearsheet.pdf"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No tearsheet generated for {t} (companies with under 3 years of data are skipped)",
        )
    return FileResponse(
        path, media_type="application/pdf", filename=f"{t}_tearsheet.pdf"
    )
