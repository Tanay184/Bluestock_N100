"""Annual report links endpoint."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import requests
from fastapi import APIRouter, Query

from src.api.deps import CONN, require_company, rows, validate_year

router = APIRouter(tags=["documents"])


def format_ok(url) -> bool:
    """True if the value looks like an http(s) URL."""
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def live_ok(url: str) -> bool:
    """True if a HEAD request answers HTTP 200 within a few seconds."""
    try:
        return requests.head(url, timeout=5, allow_redirects=True).status_code == 200
    except requests.RequestException:
        return False


@router.get("/companies/{ticker}/documents")
def documents(
    ticker: str,
    from_year: str | None = Query(None, description="YYYY"),
    to_year: str | None = Query(None, description="YYYY"),
    validate: bool = Query(
        False, description="true = live HTTP check of every link (slower)"
    ),
    conn: sqlite3.Connection = CONN,
) -> dict:
    """Annual report links per year with an is_url_valid flag (format check, or live check if validate=true)."""
    company = require_company(conn, ticker)
    for name, v in (("from_year", from_year), ("to_year", to_year)):
        validate_year(name, f"{v}-01" if v else None)
    sql, params = (
        "SELECT year, Annual_Report AS url FROM documents WHERE company_id = ?",
        [company["id"]],
    )
    if from_year:
        sql, params = sql + " AND year >= ?", params + [int(from_year)]
    if to_year:
        sql, params = sql + " AND year <= ?", params + [int(to_year)]
    docs = rows(conn, sql + " ORDER BY year DESC", tuple(params))
    if validate:
        with ThreadPoolExecutor(8) as ex:
            flags = list(
                ex.map(lambda d: format_ok(d["url"]) and live_ok(d["url"]), docs)
            )
    else:
        flags = [format_ok(d["url"]) for d in docs]
    return {
        "company_id": company["id"],
        "validation": "live" if validate else "format",
        "documents": [
            {**d, "is_url_valid": f} for d, f in zip(docs, flags, strict=True)
        ],
    }
