"""Cached data access layer for the Streamlit dashboard."""

import sqlite3
from contextlib import closing

import pandas as pd
import streamlit as st

from src.analytics.screener import build_snapshot
from src.analytics.valuation import build_valuation
from src.etl.loader import DB_PATH

TTL = 600


def _query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a parameterised read-only query."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=TTL)
def get_companies() -> pd.DataFrame:
    """All companies with sector info."""
    return _query(
        "SELECT c.id AS company_id, c.company_name, c.about_company, c.website, "
        "c.nse_profile, c.bse_profile, s.broad_sector, s.sub_sector, s.market_cap_category "
        "FROM companies c LEFT JOIN sectors s ON s.company_id = c.id ORDER BY c.company_name"
    )


@st.cache_data(ttl=TTL)
def get_ratios(ticker: str, year: str | None = None) -> pd.DataFrame:
    """Ratios for one company (optionally one year), oldest first."""
    if year:
        sql = "SELECT * FROM financial_ratios WHERE company_id = ? AND year = ? ORDER BY year"
        return _query(sql, (ticker, year))
    return _query(
        "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year", (ticker,)
    )


@st.cache_data(ttl=TTL)
def get_all_ratios() -> pd.DataFrame:
    """Ratios for every company and year."""
    return _query("SELECT * FROM financial_ratios")


@st.cache_data(ttl=TTL)
def get_pl(ticker: str) -> pd.DataFrame:
    """Profit and loss history for one company."""
    return _query(
        "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year", (ticker,)
    )


@st.cache_data(ttl=TTL)
def get_bs(ticker: str) -> pd.DataFrame:
    """Balance sheet history for one company."""
    return _query(
        "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year", (ticker,)
    )


@st.cache_data(ttl=TTL)
def get_cf(ticker: str) -> pd.DataFrame:
    """Cash flow history for one company."""
    return _query(
        "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year", (ticker,)
    )


@st.cache_data(ttl=TTL)
def get_sectors() -> pd.DataFrame:
    """Sector mapping for all companies."""
    return _query("SELECT * FROM sectors")


@st.cache_data(ttl=TTL)
def get_snapshot() -> pd.DataFrame:
    """Latest-year metric snapshot (one row per company) used by screener and peers."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return build_snapshot(conn)


@st.cache_data(ttl=TTL)
def get_valuation_all() -> pd.DataFrame:
    """Valuation summary for all companies."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return build_valuation(conn)


@st.cache_data(ttl=TTL)
def get_valuation(ticker: str) -> pd.DataFrame:
    """Valuation row for one company."""
    v = get_valuation_all()
    return v[v["company_id"] == ticker]


@st.cache_data(ttl=TTL)
def get_peer_groups() -> list[str]:
    """Names of all peer groups."""
    return _query("SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY 1")[
        "peer_group_name"
    ].tolist()


@st.cache_data(ttl=TTL)
def get_peers(group_name: str) -> pd.DataFrame:
    """Members of a peer group joined with their latest metrics."""
    members = _query(
        "SELECT company_id, is_benchmark FROM peer_groups WHERE peer_group_name = ?",
        (group_name,),
    )
    return members.merge(get_snapshot(), on="company_id", how="left")


@st.cache_data(ttl=TTL)
def get_market_cap(ticker: str) -> pd.DataFrame:
    """Valuation multiples history for one company."""
    return _query(
        "SELECT * FROM market_cap WHERE company_id = ? ORDER BY year", (ticker,)
    )


@st.cache_data(ttl=TTL)
def get_market_cap_all() -> pd.DataFrame:
    """Valuation multiples for all companies."""
    return _query("SELECT * FROM market_cap")


@st.cache_data(ttl=TTL)
def get_capital() -> pd.DataFrame:
    """Capital allocation labels for all company-years, with company names."""
    return _query(
        "SELECT ca.*, c.company_name FROM capital_allocation ca "
        "JOIN companies c ON c.id = ca.company_id"
    )


@st.cache_data(ttl=TTL)
def get_documents(ticker: str) -> pd.DataFrame:
    """Annual report links for one company, newest first."""
    return _query(
        "SELECT year, Annual_Report FROM documents WHERE company_id = ? ORDER BY year DESC",
        (ticker,),
    )


@st.cache_data(ttl=TTL)
def get_pros_cons(ticker: str) -> pd.DataFrame:
    """Pros and cons rows for one company."""
    return _query("SELECT pros, cons FROM prosandcons WHERE company_id = ?", (ticker,))
