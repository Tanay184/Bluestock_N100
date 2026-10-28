"""Shared fixtures for the API tests."""

import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.etl.loader import DB_PATH

BASE = "/api/v1"
CORE_TABLES = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "market_cap",
    "financial_ratios",
    "peer_groups",
]


@pytest.fixture(scope="session")
def client():
    """FastAPI test client (runs the startup hook once)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db_counts():
    """Ground-truth counts straight from the database."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return {
            "companies": conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
            "sectors": conn.execute(
                "SELECT COUNT(DISTINCT broad_sector) FROM sectors"
            ).fetchone()[0],
            "it_companies": conn.execute(
                "SELECT COUNT(*) FROM sectors WHERE broad_sector = 'Information Technology'"
            ).fetchone()[0],
            "tcs_ratio_years": conn.execute(
                "SELECT COUNT(*) FROM financial_ratios WHERE company_id = 'TCS'"
            ).fetchone()[0],
        }
