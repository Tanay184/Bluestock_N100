"""Health check endpoint."""

import sqlite3
import time

from fastapi import APIRouter, HTTPException

from src.api.deps import CONN, START_TIME, VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
def health(conn: sqlite3.Connection = CONN) -> dict:
    """Server status with row counts for every table in the database."""
    try:
        names = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts = {
            n: conn.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in names
        }
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503, detail=f"Database unavailable: {exc}"
        ) from exc
    return {
        "status": "ok",
        "db_row_counts": counts,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": VERSION,
    }
