"""Nifty 100 Analytics: Streamlit entry point with sidebar navigation."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics", layout="wide", initial_sidebar_state="expanded"
)

PAGES = [
    ("pages/01_home.py", "Home", "🏠"),
    ("pages/02_profile.py", "Company Profile", "🏢"),
    ("pages/03_screener.py", "Screener", "🔎"),
    ("pages/04_peers.py", "Peer Comparison", "👥"),
    ("pages/05_trends.py", "Trend Analysis", "📈"),
    ("pages/06_sectors.py", "Sector Analysis", "🏭"),
    ("pages/07_capital.py", "Capital Allocation", "💰"),
    ("pages/08_reports.py", "Annual Reports", "📄"),
]
nav = st.navigation(
    [st.Page(p, title=t, icon=i) for p, t, i in PAGES if (HERE / p).exists()]
)
st.sidebar.caption(
    "Stock prices, market cap and valuation multiples (P/E, P/B, EV/EBITDA, dividend yield) are SIMULATED data."
)
nav.run()
